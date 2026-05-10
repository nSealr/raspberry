from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters import FileButtonQrVaultIO, FileQrVaultIO
from .display import (
    DisplayFrameLimits,
    ReviewDetailPageLimits,
    render_display_frame,
    render_review_detail_pages,
    screen_review_for_request,
)
from .hardware_flow import run_button_qr_vault_flow, run_qr_vault_flow
from .nip06 import derive_nip06_secret
from .qr import decode_qr_envelope, encode_qr_envelope
from .review import review_event_template
from .signer import sign_request, validate_signing_request


def _read_value(path: Path, fmt: str) -> object:
    text = path.read_text(encoding="utf-8").strip()
    if fmt == "qr":
        return decode_qr_envelope(text)
    return json.loads(text)


def _write_value(path: Path, fmt: str, value: object) -> None:
    if fmt == "qr":
        path.write_text(f"{encode_qr_envelope(value)}\n", encoding="utf-8")
        return
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _secret_key_from_args(args: argparse.Namespace) -> str:
    if args.secret_key:
        return args.secret_key
    mnemonic = args.mnemonic_file.read_text(encoding="utf-8")
    return derive_nip06_secret(mnemonic, passphrase=args.passphrase, account=args.account)


def _author_pubkey(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise argparse.ArgumentTypeError("author pubkey must be 32-byte lowercase hex")
    return value


def _button_sequence(value: str) -> list[str]:
    buttons = [item.strip() for item in value.split(",") if item.strip()]
    if not buttons:
        raise argparse.ArgumentTypeError("button sequence must not be empty")
    invalid = [button for button in buttons if button not in {"next", "approve", "reject"}]
    if invalid:
        raise argparse.ArgumentTypeError(f"unsupported button action: {invalid[0]}")
    return buttons


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nseal-vault")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sign = subparsers.add_parser("sign", help="Process one NostrSeal signing request")
    key_source = sign.add_mutually_exclusive_group(required=True)
    key_source.add_argument("--secret-key", help="Test/development secret key as lowercase hex")
    key_source.add_argument("--mnemonic-file", type=Path, help="NIP-06 mnemonic seed phrase file")
    sign.add_argument("--account", type=int, default=0, help="NIP-06 account index for mnemonic derivation")
    sign.add_argument("--passphrase", default="", help="Optional BIP-39 passphrase for mnemonic derivation")
    sign.add_argument("--request", required=True, type=Path, help="Input request path")
    sign.add_argument("--response", required=True, type=Path, help="Output response path")
    sign.add_argument("--input-format", choices=["json", "qr"], default="json")
    sign.add_argument("--output-format", choices=["json", "qr"], default="json")
    sign.add_argument("--approval-digest", help="Optional digest binding approval to reviewed request pages")
    sign.add_argument("--approve", action="store_true", help="Explicitly approve signing for this CLI invocation")

    review = subparsers.add_parser("review", help="Render deterministic review data for one signing request")
    review.add_argument("--request", required=True, type=Path, help="Input request path")
    review.add_argument("--review", required=True, type=Path, help="Output review JSON path")
    review.add_argument("--input-format", choices=["json", "qr"], default="json")
    review.add_argument(
        "--output-format",
        choices=["json", "screen-json", "display-frame-json", "detail-pages-json"],
        default="json",
    )
    review.add_argument("--author-pubkey", type=_author_pubkey, help="Signer author pubkey to bind into review output")
    review.add_argument("--display-page", type=int, default=0, help="Page index for display-frame-json output")
    review.add_argument("--max-title-chars", type=int, default=24, help="Maximum trusted-display title characters")
    review.add_argument("--max-body-lines", type=int, default=6, help="Maximum trusted-display body lines")
    review.add_argument("--max-line-chars", type=int, default=32, help="Maximum trusted-display body line characters")
    review.add_argument(
        "--max-compact-body-lines",
        type=int,
        default=9,
        help="Maximum compact trusted-display body lines for detail-pages-json output",
    )
    review.add_argument(
        "--max-compact-line-chars",
        type=int,
        default=48,
        help="Maximum compact trusted-display body line characters for detail-pages-json output",
    )

    flow = subparsers.add_parser("flow", help="Run one hardware-style QR review/sign flow")
    flow_key_source = flow.add_mutually_exclusive_group(required=True)
    flow_key_source.add_argument("--secret-key", help="Test/development secret key as lowercase hex")
    flow_key_source.add_argument("--mnemonic-file", type=Path, help="NIP-06 mnemonic seed phrase file")
    flow.add_argument("--account", type=int, default=0, help="NIP-06 account index for mnemonic derivation")
    flow.add_argument("--passphrase", default="", help="Optional BIP-39 passphrase for mnemonic derivation")
    flow.add_argument("--request", required=True, type=Path, help="Input QR request path")
    flow.add_argument("--review", required=True, type=Path, help="Output trusted screen review JSON path")
    flow.add_argument("--response", required=True, type=Path, help="Output QR response path")
    flow.add_argument("--approve", action="store_true", help="Explicitly approve signing for this CLI invocation")
    flow.add_argument(
        "--button-sequence",
        type=_button_sequence,
        help="Comma-separated physical button actions, e.g. next,next,next,approve",
    )
    flow.add_argument("--display-frame-log", type=Path, help="Output bounded display frames shown by --button-sequence")
    flow.add_argument(
        "--review-transcript-log",
        type=Path,
        help="Output displayed frame/button/decision transcript shown by --button-sequence",
    )
    flow.add_argument("--max-title-chars", type=int, default=24, help="Maximum trusted-display title characters")
    flow.add_argument("--max-body-lines", type=int, default=6, help="Maximum trusted-display body lines")
    flow.add_argument("--max-line-chars", type=int, default=32, help="Maximum trusted-display body line characters")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "sign":
        request = _read_value(args.request, args.input_format)
        response = sign_request(
            request,
            _secret_key_from_args(args),
            approved=args.approve,
            approval_digest=args.approval_digest,
        )
        _write_value(args.response, args.output_format, response)
        return 0

    if args.command == "review":
        request = _read_value(args.request, args.input_format)
        if not isinstance(request, dict) or request.get("method") != "sign_event":
            parser.error("review requires a sign_event request")
        validation_error = validate_signing_request(request)
        if validation_error is not None:
            parser.error(validation_error["error"]["message"])
        params = request.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
            parser.error("review requires params.event_template")
        review_output = review_event_template(params["event_template"], author_pubkey=args.author_pubkey)
        if args.output_format == "screen-json":
            review_output = screen_review_for_request(request, author_pubkey=args.author_pubkey)
        elif args.output_format == "display-frame-json":
            review_output = render_display_frame(
                screen_review_for_request(request, author_pubkey=args.author_pubkey),
                page_index=args.display_page,
                limits=DisplayFrameLimits(
                    max_title_chars=args.max_title_chars,
                    max_body_lines=args.max_body_lines,
                    max_line_chars=args.max_line_chars,
                ),
            )
        elif args.output_format == "detail-pages-json":
            review_output = render_review_detail_pages(
                review_output,
                limits=ReviewDetailPageLimits(
                    max_title_chars=args.max_title_chars,
                    max_body_lines=args.max_body_lines,
                    max_line_chars=args.max_line_chars,
                    max_compact_body_lines=args.max_compact_body_lines,
                    max_compact_line_chars=args.max_compact_line_chars,
                ),
            )
        _write_value(args.review, "json", review_output)
        return 0

    if args.command == "flow":
        if args.approve and args.button_sequence:
            parser.error("flow accepts either --approve or --button-sequence, not both")
        if args.display_frame_log and not args.button_sequence:
            parser.error("flow --display-frame-log requires --button-sequence")
        if args.review_transcript_log and not args.button_sequence:
            parser.error("flow --review-transcript-log requires --button-sequence")
        if args.button_sequence:
            result = run_button_qr_vault_flow(
                FileButtonQrVaultIO(
                    args.request,
                    args.review,
                    args.response,
                    args.button_sequence,
                    display_frame_log=args.display_frame_log,
                ),
                _secret_key_from_args(args),
                display_limits=DisplayFrameLimits(
                    max_title_chars=args.max_title_chars,
                    max_body_lines=args.max_body_lines,
                    max_line_chars=args.max_line_chars,
                ),
            )
            if args.review_transcript_log is not None:
                args.review_transcript_log.write_text(
                    json.dumps(result.review_transcript, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            return 0
        run_qr_vault_flow(
            FileQrVaultIO(args.request, args.review, args.response, args.approve),
            _secret_key_from_args(args),
        )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2

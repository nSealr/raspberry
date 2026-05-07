from __future__ import annotations

import argparse
import json
from pathlib import Path

from .display import screen_review_for_request
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


class _FileQrVaultIO:
    def __init__(self, request: Path, review: Path, response: Path, approved: bool) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.approved = approved

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def show_review(self, screen_review: dict) -> bool:
        self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.approved

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")


class _FileButtonQrVaultIO:
    def __init__(self, request: Path, review: Path, response: Path, buttons: list[str]) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.buttons = list(buttons)
        self._wrote_review = False

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def display_review_page(self, screen_review: dict, page_index: int, page: dict) -> None:
        if not self._wrote_review:
            self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self._wrote_review = True

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("button sequence ended before approval or rejection")
        return self.buttons.pop(0)

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")


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
    review.add_argument("--output-format", choices=["json", "screen-json"], default="json")

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
        review_output = review_event_template(params["event_template"])
        if args.output_format == "screen-json":
            review_output = screen_review_for_request(request)
        _write_value(args.review, "json", review_output)
        return 0

    if args.command == "flow":
        if args.approve and args.button_sequence:
            parser.error("flow accepts either --approve or --button-sequence, not both")
        if args.button_sequence:
            run_button_qr_vault_flow(
                _FileButtonQrVaultIO(args.request, args.review, args.response, args.button_sequence),
                _secret_key_from_args(args),
            )
            return 0
        run_qr_vault_flow(
            _FileQrVaultIO(args.request, args.review, args.response, args.approve),
            _secret_key_from_args(args),
        )
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2

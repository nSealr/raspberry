from __future__ import annotations

import argparse
import json
from pathlib import Path

from .display import screen_review_for_request
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

    parser.error(f"unsupported command: {args.command}")
    return 2

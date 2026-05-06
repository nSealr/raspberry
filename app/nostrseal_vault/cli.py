from __future__ import annotations

import argparse
import json
from pathlib import Path

from .qr import decode_qr_envelope, encode_qr_envelope
from .signer import sign_request


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nseal-vault")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sign = subparsers.add_parser("sign", help="Process one NostrSeal signing request")
    sign.add_argument("--secret-key", required=True, help="Test/development secret key as lowercase hex")
    sign.add_argument("--request", required=True, type=Path, help="Input request path")
    sign.add_argument("--response", required=True, type=Path, help="Output response path")
    sign.add_argument("--input-format", choices=["json", "qr"], default="json")
    sign.add_argument("--output-format", choices=["json", "qr"], default="json")
    sign.add_argument("--approve", action="store_true", help="Explicitly approve signing for this CLI invocation")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "sign":
        request = _read_value(args.request, args.input_format)
        response = sign_request(request, args.secret_key, approved=args.approve)
        _write_value(args.response, args.output_format, response)
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2

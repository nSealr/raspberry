import json

from .limits import NOSTRSEAL_V0_LIMITS


QR_ENVELOPE_PREFIX = "nseal1:"


def _assert_base64url(value: str) -> None:
    if not value:
        raise ValueError("QR envelope payload must be unpadded base64url")
    if "=" in value:
        raise ValueError("QR envelope payload must be unpadded base64url")
    if any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
        raise ValueError("QR envelope payload must be base64url")


def encode_qr_envelope(value: object) -> str:
    import base64

    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > NOSTRSEAL_V0_LIMITS["max_static_qr_decoded_json_bytes"]:
        raise ValueError("QR decoded JSON exceeds max_static_qr_decoded_json_bytes")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{QR_ENVELOPE_PREFIX}{encoded}"


def decode_qr_envelope(envelope: str) -> object:
    import base64
    import binascii

    if not envelope.startswith(QR_ENVELOPE_PREFIX):
        raise ValueError("QR envelope requires nseal1 prefix")
    payload = envelope[len(QR_ENVELOPE_PREFIX) :]
    _assert_base64url(payload)
    padding = "=" * (-len(payload) % 4)
    try:
        decoded_bytes = base64.b64decode(f"{payload}{padding}".encode("ascii"), altchars=b"-_", validate=True)
    except binascii.Error as exc:
        raise ValueError("QR envelope payload must decode as base64url") from exc
    if len(decoded_bytes) > NOSTRSEAL_V0_LIMITS["max_static_qr_decoded_json_bytes"]:
        raise ValueError("QR decoded JSON exceeds max_static_qr_decoded_json_bytes")
    try:
        decoded = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("QR envelope payload must be valid UTF-8") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("QR envelope payload is not valid JSON") from exc

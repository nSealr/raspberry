import json


QR_ENVELOPE_PREFIX = "nseal1:"


def _assert_base64url(value: str) -> None:
    if not value or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for char in value):
        raise ValueError("QR envelope payload must be unpadded base64url")


def encode_qr_envelope(value: object) -> str:
    import base64

    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{QR_ENVELOPE_PREFIX}{encoded}"


def decode_qr_envelope(envelope: str) -> object:
    import base64

    if not envelope.startswith(QR_ENVELOPE_PREFIX):
        raise ValueError(f"QR envelope must start with {QR_ENVELOPE_PREFIX}")
    payload = envelope[len(QR_ENVELOPE_PREFIX) :]
    _assert_base64url(payload)
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{payload}{padding}").decode("utf-8")
        return json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("QR envelope payload is not valid JSON") from exc

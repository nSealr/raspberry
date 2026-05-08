from __future__ import annotations

from typing import Any

from .crypto import sign_event, xonly_pubkey_from_secret
from .display import approval_digest_for_request
from .limits import NOSTRSEAL_V0_LIMITS, compact_json_utf8_size
from .review import review_event_template


def _error_response(request_id: str, code: str, message: str, retryable: bool) -> dict[str, Any]:
    return {
        "version": 1,
        "request_id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        },
    }


def _request_id(request: object) -> str:
    if isinstance(request, dict) and isinstance(request.get("request_id"), str):
        return request["request_id"]
    return "unknown"


def validate_signing_request(request: dict[str, Any]) -> dict[str, Any] | None:
    if compact_json_utf8_size(request) > NOSTRSEAL_V0_LIMITS["max_decoded_request_json_bytes"]:
        return _error_response(
            _request_id(request),
            "invalid_request",
            "decoded request JSON exceeds max_decoded_request_json_bytes",
            False,
        )
    if request.get("version") != 1:
        return _error_response(_request_id(request), "invalid_request", "Unsupported request version.", False)
    request_id = request.get("request_id")
    if (
        not isinstance(request_id, str)
        or not request_id
        or len(request_id) > NOSTRSEAL_V0_LIMITS["max_request_id_length"]
        or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-" for char in request_id)
    ):
        return _error_response("unknown", "invalid_request", "Missing request_id.", False)
    method = request.get("method")
    if method == "get_capabilities" and "params" in request:
        return _error_response(
            _request_id(request),
            "invalid_request",
            "get_capabilities must not include params",
            False,
        )
    if method == "get_public_key" and "params" in request:
        return _error_response(
            _request_id(request),
            "invalid_request",
            "get_public_key must not include params",
            False,
        )
    if method not in {"get_public_key", "sign_event"}:
        return _error_response(_request_id(request), "unsupported_method", "Unsupported signing method.", False)
    allowed_top_level = {"version", "request_id", "method"}
    if method == "sign_event":
        allowed_top_level.add("params")
    unknown_top_level = sorted(set(request) - allowed_top_level)
    if unknown_top_level:
        return _error_response(
            _request_id(request),
            "invalid_request",
            f"unknown top-level fields: {', '.join(unknown_top_level)}",
            False,
        )
    if method == "sign_event":
        params = request.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
            return _error_response(_request_id(request), "invalid_request", "Missing event_template.", False)
        unknown_params = sorted(set(params) - {"event_template"})
        if unknown_params:
            return _error_response(
                _request_id(request),
                "invalid_request",
                f"sign_event params contain unknown fields: {', '.join(unknown_params)}",
                False,
            )
        try:
            review_event_template(params["event_template"])
        except ValueError as exc:
            return _error_response(_request_id(request), "invalid_request", str(exc), False)
    return None


def sign_request(
    request: object,
    secret_key_hex: str,
    *,
    approved: bool,
    approval_digest: str | None = None,
) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _error_response("unknown", "invalid_request", "Request must be a JSON object.", False)

    validation_error = validate_signing_request(request)
    if validation_error is not None:
        return validation_error

    if request["method"] == "get_public_key":
        return {
            "version": 1,
            "request_id": request["request_id"],
            "ok": True,
            "result": {"public_key": xonly_pubkey_from_secret(secret_key_hex)},
        }

    if not approved:
        return _error_response(request["request_id"], "user_rejected", "User approval is required before signing.", True)

    if approval_digest is not None and approval_digest != approval_digest_for_request(request):
        return _error_response(
            request["request_id"],
            "approval_digest_mismatch",
            "Approval digest does not match the reviewed request.",
            False,
        )

    return {
        "version": 1,
        "request_id": request["request_id"],
        "ok": True,
        "result": {"event": sign_event(request["params"]["event_template"], secret_key_hex)},
    }

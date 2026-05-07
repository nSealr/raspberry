from __future__ import annotations

from typing import Any

from .crypto import sign_event, xonly_pubkey_from_secret
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


def _validate_sign_event_request(request: dict[str, Any]) -> dict[str, Any] | None:
    if request.get("version") != 1:
        return _error_response(_request_id(request), "invalid_request", "Unsupported request version.", False)
    if not isinstance(request.get("request_id"), str):
        return _error_response("unknown", "invalid_request", "Missing request_id.", False)
    if request.get("method") not in {"get_public_key", "sign_event"}:
        return _error_response(_request_id(request), "unsupported_method", "Unsupported signing method.", False)
    if request["method"] == "sign_event":
        params = request.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
            return _error_response(_request_id(request), "invalid_request", "Missing event_template.", False)
        for forbidden in ("id", "pubkey", "sig"):
            if forbidden in params["event_template"]:
                return _error_response(_request_id(request), "invalid_request", f"event_template must not contain {forbidden}.", False)
        try:
            review_event_template(params["event_template"])
        except ValueError as exc:
            return _error_response(_request_id(request), "invalid_request", str(exc), False)
    return None


def sign_request(request: object, secret_key_hex: str, *, approved: bool) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _error_response("unknown", "invalid_request", "Request must be a JSON object.", False)

    validation_error = _validate_sign_event_request(request)
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

    return {
        "version": 1,
        "request_id": request["request_id"],
        "ok": True,
        "result": {"event": sign_event(request["params"]["event_template"], secret_key_hex)},
    }

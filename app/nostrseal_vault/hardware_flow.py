from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .controls import ButtonAction, ReviewControlSession
from .display import DisplayFrameLimits, render_display_frame, screen_review_for_request
from .qr import decode_qr_envelope, encode_qr_envelope
from .signer import sign_request


class QrVaultIO(Protocol):
    def scan_request_qr(self) -> str:
        """Return one scanned NostrSeal QR envelope."""

    def show_review(self, screen_review: dict[str, Any]) -> bool:
        """Display trusted review pages and return the physical approval result."""

    def emit_response_qr(self, response_qr: str) -> None:
        """Publish one QR envelope response for the host to scan."""


class ButtonQrVaultIO(Protocol):
    def scan_request_qr(self) -> str:
        """Return one scanned NostrSeal QR envelope."""

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        """Render one bounded trusted review frame before reading the next physical button."""

    def read_review_button(self) -> ButtonAction:
        """Return the next physical button action."""

    def emit_response_qr(self, response_qr: str) -> None:
        """Publish one QR envelope response for the host to scan."""


@dataclass(frozen=True)
class QrVaultFlowResult:
    request_id: str
    approved: bool
    approval_digest: str
    response: dict[str, Any]


def run_qr_vault_flow(io: QrVaultIO, secret_key_hex: str) -> QrVaultFlowResult:
    request = decode_qr_envelope(io.scan_request_qr())
    if not isinstance(request, dict):
        raise ValueError("QR vault flow requires a JSON object request")

    screen_review = screen_review_for_request(request)
    approval_digest = str(screen_review["approval_digest"])
    approved = io.show_review(screen_review)
    response = sign_request(
        request,
        secret_key_hex,
        approved=approved,
        approval_digest=approval_digest,
    )
    io.emit_response_qr(encode_qr_envelope(response))
    return QrVaultFlowResult(
        request_id=str(request["request_id"]),
        approved=approved,
        approval_digest=approval_digest,
        response=response,
    )


def run_button_qr_vault_flow(
    io: ButtonQrVaultIO,
    secret_key_hex: str,
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
) -> QrVaultFlowResult:
    request = decode_qr_envelope(io.scan_request_qr())
    if not isinstance(request, dict):
        raise ValueError("QR vault flow requires a JSON object request")

    screen_review = screen_review_for_request(request)
    approval_digest = str(screen_review["approval_digest"])
    session = ReviewControlSession(screen_review)
    approved: bool | None = None

    while approved is None:
        frame = render_display_frame(screen_review, session.page_index, display_limits)
        io.display_review_frame(screen_review, session.page_index, frame)
        approved = session.handle_button(io.read_review_button())

    response = sign_request(
        request,
        secret_key_hex,
        approved=approved,
        approval_digest=approval_digest,
    )
    io.emit_response_qr(encode_qr_envelope(response))
    return QrVaultFlowResult(
        request_id=str(request["request_id"]),
        approved=approved,
        approval_digest=approval_digest,
        response=response,
    )

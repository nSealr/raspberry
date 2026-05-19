from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .controls import ButtonAction, ReviewControlSession
from .seed_entry import SessionImportSource, session_source_backup_payload, session_source_backup_review


class SessionSourceBackupFlowError(RuntimeError):
    pass


@dataclass(frozen=True)
class SessionSourceBackupTranscriptStep:
    page_index: int
    button: ButtonAction
    decision: bool | None
    revealed: bool


@dataclass(frozen=True)
class SessionSourceBackupFlowResult:
    review: dict[str, Any]
    approved: bool
    revealed: bool
    backup_payload: dict[str, str] | None
    transcript: list[SessionSourceBackupTranscriptStep]


def run_session_source_backup_flow(
    source: SessionImportSource,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionSourceBackupFlowResult:
    if max_button_steps <= 0:
        raise SessionSourceBackupFlowError("session source backup flow max button steps must be positive")

    review = session_source_backup_review(source)
    controls = ReviewControlSession({"pages": review["pages"]})
    transcript: list[SessionSourceBackupTranscriptStep] = []

    for step_count, button in enumerate(buttons, start=1):
        if step_count > max_button_steps:
            raise SessionSourceBackupFlowError("session source backup review exceeded max button steps")
        page_index = controls.page_index
        decision = controls.handle_button(button)
        revealed = decision is True
        transcript.append(SessionSourceBackupTranscriptStep(page_index, button, decision, revealed))
        if decision is not None:
            return SessionSourceBackupFlowResult(
                review,
                approved=decision,
                revealed=revealed,
                backup_payload=session_source_backup_payload(source) if revealed else None,
                transcript=transcript,
            )

    raise SessionSourceBackupFlowError("session source backup review did not reach approval or rejection")

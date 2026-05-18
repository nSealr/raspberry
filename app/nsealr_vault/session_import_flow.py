from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .controls import ButtonAction, ReviewControlSession
from .seed_entry import SessionImportSource, session_import_review


MAX_STATELESS_SESSION_SOURCES = 8


class SessionImportFlowError(RuntimeError):
    pass


@dataclass
class StatelessSessionKeyring:
    max_sources: int = MAX_STATELESS_SESSION_SOURCES
    _sources: list[SessionImportSource] = field(default_factory=list, init=False)

    def add_source(self, source: SessionImportSource) -> None:
        if len(self._sources) >= self.max_sources:
            raise SessionImportFlowError("stateless session keyring is full")
        # Validation is owned by the shared review builder; only reviewed sources
        # should reach this method through run_session_import_flow.
        session_import_review(source)
        self._sources.append(source)

    def clear(self) -> None:
        self._sources.clear()

    @property
    def empty(self) -> bool:
        return not self._sources

    @property
    def size(self) -> int:
        return len(self._sources)

    def source_at(self, index: int) -> SessionImportSource:
        try:
            return self._sources[index]
        except IndexError as exc:
            raise SessionImportFlowError("session key source index is out of range") from exc


@dataclass(frozen=True)
class SessionImportTranscriptStep:
    page_index: int
    button: ButtonAction
    decision: bool | None
    loaded: bool


@dataclass(frozen=True)
class SessionImportFlowResult:
    review: dict[str, Any]
    approved: bool
    loaded: bool
    transcript: list[SessionImportTranscriptStep]


def run_session_import_flow(
    keyring: StatelessSessionKeyring,
    source: SessionImportSource,
    buttons: list[ButtonAction],
    *,
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    if max_button_steps <= 0:
        raise SessionImportFlowError("session import flow max button steps must be positive")

    review = session_import_review(source)
    controls = ReviewControlSession({"pages": review["pages"]})
    transcript: list[SessionImportTranscriptStep] = []

    for step_count, button in enumerate(buttons, start=1):
        if step_count > max_button_steps:
            raise SessionImportFlowError("session import review exceeded max button steps")
        page_index = controls.page_index
        decision = controls.handle_button(button)
        loaded = False
        if decision is True:
            keyring.add_source(source)
            loaded = True
        transcript.append(SessionImportTranscriptStep(page_index, button, decision, loaded))
        if decision is not None:
            return SessionImportFlowResult(review, approved=decision, loaded=loaded, transcript=transcript)

    raise SessionImportFlowError("session import review did not reach approval or rejection")

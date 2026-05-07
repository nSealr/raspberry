from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ButtonAction = Literal["next", "approve", "reject"]


def review_frame_for_page(screen_review: dict[str, Any], page_index: int, page: dict[str, Any]) -> dict[str, Any]:
    pages = screen_review.get("pages")
    if not isinstance(pages, list) or page_index < 0 or page_index >= len(pages):
        raise ValueError("screen review page index out of range")
    action = page.get("action")
    if action == "next":
        action_hint = "Next"
    elif action == "approve_or_reject":
        action_hint = "Approve / Reject"
    else:
        raise ValueError("unsupported review page action")
    lines = page.get("lines")
    if not isinstance(lines, list):
        raise ValueError("screen review page lines must be a list")
    return {
        "title": page["title"],
        "page_indicator": f"Page {page_index + 1}/{len(pages)}",
        "body_lines": list(lines),
        "action_hint": action_hint,
    }


def review_transcript_for_screen_review(
    screen_review: dict[str, Any],
    buttons: list[ButtonAction],
) -> list[dict[str, Any]]:
    session = ReviewControlSession(screen_review)
    transcript: list[dict[str, Any]] = []
    for button in buttons:
        frame = review_frame_for_page(screen_review, session.page_index, session.current_page)
        decision = session.handle_button(button)
        transcript.append(
            {
                "frame": frame,
                "button": button,
                "decision": decision,
                "approved_for_signing": session.approved,
            }
        )
    return transcript


@dataclass
class ReviewControlSession:
    screen_review: dict[str, Any]
    page_index: int = 0
    approved: bool = False
    rejected: bool = False
    _seen_pages: set[int] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        pages = self._pages()
        if not pages:
            raise ValueError("screen review must contain at least one page")
        if pages[-1].get("action") != "approve_or_reject":
            raise ValueError("screen review must end with an approve_or_reject page")
        for page in pages[:-1]:
            if page.get("action") == "approve_or_reject":
                raise ValueError("only the final review page may approve or reject")
        self._seen_pages.add(self.page_index)

    @property
    def current_page(self) -> dict[str, Any]:
        return self._pages()[self.page_index]

    @property
    def can_approve(self) -> bool:
        return self.current_page.get("action") == "approve_or_reject" and len(self._seen_pages) == len(self._pages())

    def next_page(self) -> dict[str, Any]:
        if self.page_index < len(self._pages()) - 1:
            self.page_index += 1
            self._seen_pages.add(self.page_index)
        return self.current_page

    def approve(self) -> bool:
        if self.rejected:
            raise ValueError("cannot approve after rejection")
        if not self.can_approve:
            raise ValueError("approval requires viewing every review page")
        self.approved = True
        return True

    def reject(self) -> bool:
        if self.approved:
            raise ValueError("cannot reject after approval")
        self.rejected = True
        return False

    def handle_button(self, action: ButtonAction) -> bool | None:
        if action == "next":
            self.next_page()
            return None
        if action == "approve":
            return self.approve()
        if action == "reject":
            return self.reject()
        raise ValueError(f"unsupported button action: {action}")

    def _pages(self) -> list[dict[str, Any]]:
        pages = self.screen_review.get("pages")
        if not isinstance(pages, list) or not all(isinstance(page, dict) for page in pages):
            raise ValueError("screen review pages must be a list of objects")
        return pages

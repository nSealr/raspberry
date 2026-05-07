from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import textwrap
from typing import Any

from .review import review_event_template


@dataclass(frozen=True)
class DisplayFrameLimits:
    max_title_chars: int = 24
    max_body_lines: int = 6
    max_line_chars: int = 32


def render_display_frame(
    screen_review: dict[str, Any],
    page_index: int,
    limits: DisplayFrameLimits = DisplayFrameLimits(),
) -> dict[str, Any]:
    _validate_display_limits(limits)
    pages = screen_review.get("pages")
    if not isinstance(pages, list) or not all(isinstance(page, dict) for page in pages):
        raise ValueError("screen review pages must be a list of objects")
    if page_index < 0 or page_index >= len(pages):
        raise ValueError("screen review page index out of range")

    page = pages[page_index]
    return {
        "title": _truncate_for_display(str(page["title"]), limits.max_title_chars),
        "page_indicator": f"Page {page_index + 1}/{len(pages)}",
        "body_lines": _wrap_body_lines(page.get("lines"), limits),
        "action_hint": _action_hint(str(page.get("action"))),
    }


def render_review_pages(review: dict[str, Any]) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = [
        {
            "title": "Event",
            "lines": [
                f"Kind {review['kind']}",
                str(review["kind_name"]),
                f"Created {review['created_at']}",
            ],
            "action": "next",
        },
        {
            "title": "Content",
            "lines": [str(review["content_preview"])],
            "action": "next",
        },
        {
            "title": "Tags",
            "lines": _tag_lines(review),
            "action": "next",
        },
    ]

    warnings = list(review.get("warnings", []))
    if warnings:
        pages.append(
            {
                "title": "Warnings",
                "lines": [str(warning) for warning in warnings],
                "action": "approve_or_reject",
            }
        )
    else:
        pages.append(
            {
                "title": "Decision",
                "lines": ["Approve signing only if all pages match."],
                "action": "approve_or_reject",
            }
        )
    return pages


def _tag_lines(review: dict[str, Any]) -> list[str]:
    tag_count = int(review["tag_count"])
    if tag_count == 0:
        return ["No tags"]
    label = "1 tag" if tag_count == 1 else f"{tag_count} tags"
    return [label, *[str(item) for item in review.get("tag_summary", [])]]


def _validate_display_limits(limits: DisplayFrameLimits) -> None:
    if limits.max_title_chars <= 0 or limits.max_body_lines <= 0 or limits.max_line_chars <= 0:
        raise ValueError("display limits must be positive")


def _wrap_body_lines(value: object, limits: DisplayFrameLimits) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("screen review page lines must be a list")

    wrapped: list[str] = []
    for line in value:
        text = str(line)
        if text == "":
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                text,
                width=limits.max_line_chars,
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )

    if len(wrapped) > limits.max_body_lines:
        wrapped = wrapped[: limits.max_body_lines]
        wrapped[-1] = _truncate_for_display(wrapped[-1], limits.max_line_chars, force_ellipsis=True)
    return [_truncate_for_display(line, limits.max_line_chars) for line in wrapped]


def _truncate_for_display(text: str, max_chars: int, *, force_ellipsis: bool = False) -> str:
    if len(text) <= max_chars and not force_ellipsis:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return text[: max_chars - 3] + "..."


def _action_hint(action: str) -> str:
    if action == "next":
        return "Next"
    if action == "approve_or_reject":
        return "Approve / Reject"
    raise ValueError("unsupported review page action")


def screen_review_for_request(request: dict[str, Any]) -> dict[str, Any]:
    review = _review_for_request(request)
    pages = render_review_pages(review)
    return {
        "format": "screen-pages",
        "request_id": request["request_id"],
        "approval_digest": _approval_digest(request, review, pages),
        "pages": pages,
    }


def approval_digest_for_request(request: dict[str, Any]) -> str:
    review = _review_for_request(request)
    return _approval_digest(request, review, render_review_pages(review))


def _review_for_request(request: dict[str, Any]) -> dict[str, Any]:
    params = request.get("params")
    if not isinstance(params, dict) or not isinstance(params.get("event_template"), dict):
        raise ValueError("screen review requires params.event_template")
    return review_event_template(params["event_template"])


def _approval_digest(
    request: dict[str, Any],
    review: dict[str, Any],
    pages: list[dict[str, object]],
) -> str:
    payload = {
        "version": request["version"],
        "method": request["method"],
        "request_id": request["request_id"],
        "event_template": request["params"]["event_template"],
        "review": review,
        "pages": pages,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

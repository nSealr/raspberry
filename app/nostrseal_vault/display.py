from __future__ import annotations

import hashlib
import json
from typing import Any

from .review import review_event_template


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

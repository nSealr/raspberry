from __future__ import annotations

from typing import Any


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

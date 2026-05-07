from __future__ import annotations

from typing import Any


KIND_NAMES = {
    0: "Metadata",
    1: "Short Text Note",
    3: "Contacts",
    6: "Repost",
    7: "Reaction",
    9735: "Zap Receipt",
}


def _require_template(template: dict[str, Any]) -> None:
    for field in ("created_at", "kind", "tags", "content"):
        if field not in template:
            raise ValueError(f"event_template missing {field}")
    if not isinstance(template["created_at"], int) or template["created_at"] < 0:
        raise ValueError("created_at must be a non-negative integer")
    if not isinstance(template["kind"], int) or template["kind"] < 0:
        raise ValueError("kind must be a non-negative integer")
    if not isinstance(template["content"], str):
        raise ValueError("content must be a string")
    if not isinstance(template["tags"], list) or not all(
        isinstance(tag, list) and all(isinstance(item, str) for item in tag) for tag in template["tags"]
    ):
        raise ValueError("tags must be an array of string arrays")


def _content_preview(content: str) -> str:
    if len(content) <= 120:
        return content
    return f"{content[:120]}..."


def _tag_summary(tags: list[list[str]]) -> list[str]:
    summary: list[str] = []
    for tag in tags:
        if not tag:
            continue
        name = tag[0]
        value = tag[1] if len(tag) > 1 else ""
        if len(value) > 8 and name in {"p", "e"}:
            value = f"{value[:8]}..."
        summary.append(f"{name}: {value}" if value else name)
    return summary


def review_event_template(template: dict[str, Any]) -> dict[str, Any]:
    _require_template(template)

    kind = template["kind"]
    content = template["content"]
    tags = template["tags"]
    warnings: list[str] = []

    if kind not in KIND_NAMES:
        warnings.append("Unknown event kind.")
    if len(content) > 280:
        warnings.append("Long content.")
    if not content:
        warnings.append("Empty content.")
    if any(tag and tag[0] == "p" for tag in tags):
        warnings.append("Event includes pubkey mentions.")
    if any(tag and tag[0] == "e" for tag in tags):
        warnings.append("Event references other events.")
    if len(tags) > 8:
        warnings.append("Many tags.")

    return {
        "kind": kind,
        "kind_name": KIND_NAMES.get(kind, "Unknown"),
        "created_at": template["created_at"],
        "content_preview": _content_preview(content),
        "content_length": len(content),
        "tag_count": len(tags),
        "tag_summary": _tag_summary(tags),
        "warnings": warnings,
    }

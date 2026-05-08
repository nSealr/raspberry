from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileQrVaultIO:
    def __init__(self, request: Path, review: Path, response: Path, approved: bool) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.approved = approved

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def show_review(self, screen_review: dict[str, Any]) -> bool:
        self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.approved

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")


class FileButtonQrVaultIO:
    def __init__(
        self,
        request: Path,
        review: Path,
        response: Path,
        buttons: list[str],
        display_frame_log: Path | None = None,
    ) -> None:
        self.request = request
        self.review = review
        self.response = response
        self.buttons = list(buttons)
        self.display_frame_log = display_frame_log
        self.display_frames: list[dict[str, Any]] = []
        self._wrote_review = False

    def scan_request_qr(self) -> str:
        return self.request.read_text(encoding="utf-8").strip()

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        if not self._wrote_review:
            self.review.write_text(json.dumps(screen_review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self._wrote_review = True
        if self.display_frame_log is not None:
            self.display_frames.append(frame)
            self.display_frame_log.write_text(
                json.dumps(self.display_frames, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("button sequence ended before approval or rejection")
        return self.buttons.pop(0)

    def emit_response_qr(self, response_qr: str) -> None:
        self.response.write_text(f"{response_qr}\n", encoding="utf-8")

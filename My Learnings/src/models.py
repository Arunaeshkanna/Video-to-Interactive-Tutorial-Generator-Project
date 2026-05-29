from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KeyFrame:
    path: Path
    timestamp_seconds: float
    caption: str

    @property
    def timestamp_label(self) -> str:
        total = int(self.timestamp_seconds)
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


@dataclass(frozen=True)
class Diagram:
    title: str
    code: str


@dataclass(frozen=True)
class TutorialResult:
    summary: str
    blog: str
    diagrams: list[Diagram]
    checkpoints: list[dict[str, str]]
    retrieved_context: list[str]

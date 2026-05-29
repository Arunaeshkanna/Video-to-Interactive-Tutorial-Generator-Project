from __future__ import annotations

import re

from src.models import KeyFrame, TutorialResult


def make_download_name(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return f"{slug or 'tutorial'}.md"


def build_markdown(title: str, result: TutorialResult, frames: list[KeyFrame]) -> str:
    frame_section = "\n".join(
        f"- `{frame.timestamp_label}` - {frame.caption} - `{frame.path}`" for frame in frames
    ) or "- No key frames extracted."
    diagram_section = "\n\n".join(
        f"### {diagram.title}\n\n```mermaid\n{diagram.code}\n```" for diagram in result.diagrams
    )
    checkpoint_section = "\n".join(
        f"- **{item['question']}**\n  {item['answer']}" for item in result.checkpoints
    )

    return f"""# {title}

{result.blog}

## Diagrams

{diagram_section}

## Key Frames

{frame_section}

## Interactive Checkpoints

{checkpoint_section}

## Retrieved RAG Context

{chr(10).join(f"- {chunk}" for chunk in result.retrieved_context)}
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import AppConfig
from src.llm import LLMClient
from src.rag import TranscriptRAG


def _as_json(raw: dict[str, Any], key: str, fallback: Any) -> Any:
    value = raw.get(key)
    return value if value else fallback


class FeatureLab:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = LLMClient(config)

    def answer_question(self, transcript: str, question: str) -> str:
        rag = TranscriptRAG.from_text(transcript[: self.config.max_transcript_chars])
        context = rag.retrieve(question, top_k=5)
        response = self.llm.complete(
            "You answer questions using only the provided technical-video context. Be helpful, concise, and cite the relevant idea.",
            f"Question: {question}\n\nContext:\n{chr(10).join(context)}",
        )
        return response or "I could not call the LLM, but the most relevant transcript sections are:\n\n" + "\n\n".join(context)

    def quiz(self, title: str, transcript: str, difficulty: str) -> list[dict[str, Any]]:
        context = self._context(transcript, "quiz concepts commands errors definitions")
        data = self.llm.complete_json(
            "Return valid JSON only. Create accurate technical quiz questions from the context.",
            f"""
Create 8 quiz questions for "{title}" at {difficulty} difficulty.
Mix MCQ and short-answer questions.
Return:
{{"quiz":[{{"type":"mcq|short","question":"...","options":["A","B","C","D"],"answer":"...","explanation":"..."}}]}}

Context:
{context}
""",
        )
        return _as_json(data, "quiz", self._fallback_quiz(difficulty))

    def code_extract(self, title: str, transcript: str) -> dict[str, Any]:
        context = self._context(transcript, "commands code APIs packages filenames configuration")
        data = self.llm.complete_json(
            "Return valid JSON only. Extract commands, code-like snippets, APIs, packages, and configuration hints.",
            f"""
Extract developer artifacts from "{title}".
Return:
{{"commands":["..."],"apis":["..."],"packages":["..."],"files":["..."],"notes":["..."]}}

Context:
{context}
""",
        )
        return {
            "commands": _as_json(data, "commands", []),
            "apis": _as_json(data, "apis", []),
            "packages": _as_json(data, "packages", []),
            "files": _as_json(data, "files", []),
            "notes": _as_json(data, "notes", ["No strong code artifacts were detected."]),
        }

    def flashcards(self, title: str, transcript: str, difficulty: str) -> list[dict[str, str]]:
        context = self._context(transcript, "terms definitions concepts gotchas")
        data = self.llm.complete_json(
            "Return valid JSON only. Make compact study flashcards.",
            f"""
Create 12 flashcards for "{title}" at {difficulty} difficulty.
Return:
{{"flashcards":[{{"front":"...","back":"..."}}]}}

Context:
{context}
""",
        )
        return _as_json(data, "flashcards", [{"front": "Main topic", "back": "Review the tutorial overview and RAG highlights."}])

    def learning_path(self, title: str, transcript: str, difficulty: str) -> dict[str, Any]:
        context = self._context(transcript, "prerequisites next steps projects learning path")
        data = self.llm.complete_json(
            "Return valid JSON only. Build a practical learning path.",
            f"""
Create a learning path for "{title}" at {difficulty} level.
Return:
{{"before":["..."],"after":["..."],"projects":["..."],"resources":["..."]}}

Context:
{context}
""",
        )
        return {
            "before": _as_json(data, "before", ["Review the prerequisites listed in the tutorial."]),
            "after": _as_json(data, "after", ["Rebuild the workflow without watching the video."]),
            "projects": _as_json(data, "projects", ["Create a mini project using the same concept."]),
            "resources": _as_json(data, "resources", ["Official documentation for the tools mentioned in the transcript."]),
        }

    def summaries(self, title: str, transcript: str) -> dict[str, str]:
        context = self._context(transcript, "summary key ideas implementation recap")
        data = self.llm.complete_json(
            "Return valid JSON only. Write concise summaries in multiple formats.",
            f"""
Create summary variants for "{title}".
Return:
{{"thirty_second":"...","five_minute":"...","linkedin_post":"...","youtube_description":"...","full_notes":"..."}}

Context:
{context}
""",
        )
        return {
            "thirty_second": _as_json(data, "thirty_second", "This video explains a technical topic and turns it into a repeatable learning workflow."),
            "five_minute": _as_json(data, "five_minute", context),
            "linkedin_post": _as_json(data, "linkedin_post", f"I converted {title} into structured learning notes with diagrams and checkpoints."),
            "youtube_description": _as_json(data, "youtube_description", f"Structured tutorial notes for {title}."),
            "full_notes": _as_json(data, "full_notes", context),
        }

    def translate(self, title: str, markdown: str, language: str, difficulty: str) -> str:
        if language.lower() == "english":
            return markdown
        response = self.llm.complete(
            "You translate and adapt technical tutorials while preserving Markdown, code blocks, and commands exactly.",
            f"Translate this tutorial into {language}. Keep difficulty suitable for {difficulty} learners.\n\nTitle: {title}\n\n{markdown[:18000]}",
        )
        return response or markdown

    def rewrite_for_difficulty(self, title: str, markdown: str, difficulty: str) -> str:
        response = self.llm.complete(
            "You adapt technical writing to the requested learner level. Preserve Markdown structure and code blocks.",
            f"Rewrite this tutorial for {difficulty} learners.\n\nTitle: {title}\n\n{markdown[:18000]}",
        )
        return response or markdown

    def _context(self, transcript: str, query: str) -> str:
        rag = TranscriptRAG.from_text(transcript[: self.config.max_transcript_chars])
        return "\n\n".join(rag.retrieve(query, top_k=7))

    def _fallback_quiz(self, difficulty: str) -> list[dict[str, Any]]:
        return [
            {
                "type": "short",
                "question": f"What is the main idea of this {difficulty.lower()} tutorial?",
                "options": [],
                "answer": "Use the overview and transcript highlights to identify the central concept.",
                "explanation": "The generated tutorial is the source of truth when the LLM is unavailable.",
            }
        ]


def speech_html(text: str) -> str:
    safe_text = html.escape(text[:12000])
    return f"""
    <div style="display:grid; gap:12px; font-family:Inter, Segoe UI, sans-serif;">
      <textarea id="voiceText" style="width:100%; min-height:220px; border-radius:8px; border:1px solid #d6e2df; padding:12px;">{safe_text}</textarea>
      <div style="display:flex; gap:10px;">
        <button onclick="speak()" style="border:0; border-radius:8px; padding:10px 16px; background:#0f8b8d; color:white; font-weight:700;">Play Voice</button>
        <button onclick="pauseVoice()" style="border:0; border-radius:8px; padding:10px 16px; background:#f4a261; color:#12202f; font-weight:700;">Pause</button>
        <button onclick="stopVoice()" style="border:0; border-radius:8px; padding:10px 16px; background:#e76f51; color:white; font-weight:700;">Stop</button>
      </div>
      <script>
        function speak() {{
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(document.getElementById('voiceText').value);
          utterance.rate = 0.95;
          utterance.pitch = 1.0;
          window.speechSynthesis.speak(utterance);
        }}
        function pauseVoice() {{
          if (window.speechSynthesis.speaking) window.speechSynthesis.pause();
        }}
        function stopVoice() {{
          window.speechSynthesis.cancel();
        }}
      </script>
    </div>
    """


def save_history(storage_dir: Path, data: dict[str, Any]) -> Path:
    history_dir = storage_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = history_dir / f"{stamp}.json"
    payload = {
        "title": data["title"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "markdown": data["markdown"],
        "transcript": data["transcript"],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_history(storage_dir: Path) -> list[dict[str, Any]]:
    history_dir = storage_dir / "history"
    if not history_dir.exists():
        return []
    items = []
    for path in sorted(history_dir.glob("*.json"), reverse=True):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            item["path"] = str(path)
            items.append(item)
        except json.JSONDecodeError:
            continue
    return items

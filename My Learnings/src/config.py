from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    groq_api_key: str
    groq_model: str
    groq_transcribe_model: str
    storage_dir: Path
    max_key_frames: int
    max_transcript_chars: int
    youtube_frame_download: bool

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
            groq_transcribe_model=os.getenv("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3-turbo").strip(),
            storage_dir=Path(os.getenv("APP_STORAGE_DIR", "outputs")),
            max_key_frames=int(os.getenv("MAX_KEY_FRAMES", "8")),
            max_transcript_chars=int(os.getenv("MAX_TRANSCRIPT_CHARS", "24000")),
            youtube_frame_download=os.getenv("YOUTUBE_FRAME_DOWNLOAD", "false").strip().lower() in {"1", "true", "yes", "on"},
        )

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

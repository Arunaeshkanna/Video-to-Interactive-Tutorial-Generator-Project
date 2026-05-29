from __future__ import annotations

import re
from pathlib import Path


YOUTUBE_RE = re.compile(r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)", re.IGNORECASE)


def is_youtube_url(url: str) -> bool:
    return bool(url and YOUTUBE_RE.search(url))


def download_youtube_video(url: str, output_dir: Path) -> Path:
    from yt_dlp import YoutubeDL

    output_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "mp4/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "outtmpl": str(output_dir / "%(title).80s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        if path.suffix.lower() != ".mp4":
            candidate = path.with_suffix(".mp4")
            if candidate.exists():
                return candidate
        return path

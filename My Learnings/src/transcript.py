from __future__ import annotations

from pathlib import Path

from src.config import AppConfig


def _youtube_id(url: str) -> str:
    if "youtu.be/" in url:
        return url.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    if "youtube.com/shorts/" in url:
        return url.split("youtube.com/shorts/", 1)[1].split("?", 1)[0].split("/", 1)[0]
    if "v=" in url:
        return url.split("v=", 1)[1].split("&", 1)[0]
    return url.rstrip("/").split("/")[-1]


def _transcript_to_text(transcript) -> str:
    lines: list[str] = []
    for item in transcript:
        if isinstance(item, dict):
            value = item.get("text", "")
        else:
            value = getattr(item, "text", "")
        value = str(value).strip()
        if value:
            lines.append(value)
    return "\n".join(lines)


def get_transcript_from_youtube(url: str) -> tuple[str, str]:
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = _youtube_id(url)
    languages = ["en", "en-US", "en-GB"]
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
    else:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    text = _transcript_to_text(transcript)
    title = f"YouTube Tutorial {video_id}"
    return text.strip(), title


def get_transcript_from_upload(video_path: Path, config: AppConfig) -> str:
    if not config.has_groq:
        return ""

    from groq import Groq

    client = Groq(api_key=config.groq_api_key)
    with video_path.open("rb") as media:
        transcript = client.audio.transcriptions.create(
            model=config.groq_transcribe_model,
            file=(video_path.name, media.read()),
            response_format="text",
        )
    return str(transcript).strip()

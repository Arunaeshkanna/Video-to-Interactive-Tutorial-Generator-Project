from __future__ import annotations

import json

from src.config import AppConfig


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = None
        if config.has_groq:
            from groq import Groq

            self.client = Groq(api_key=config.groq_api_key)

    def complete(self, system: str, user: str) -> str:
        if not self.client:
            return ""
        response = self.client.chat.completions.create(
            model=self.config.groq_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.35,
        )
        return response.choices[0].message.content or ""

    def complete_json(self, system: str, user: str) -> dict:
        raw = self.complete(system, user)
        if not raw:
            return {}
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1).replace("json\r\n", "", 1)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}

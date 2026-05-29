from __future__ import annotations

from dataclasses import dataclass


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


@dataclass
class TranscriptRAG:
    chunks: list[str]

    @classmethod
    def from_text(cls, text: str) -> "TranscriptRAG":
        return cls(chunks=chunk_text(text))

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        if not self.chunks:
            return []
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform(self.chunks + [query])
            scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
            ranked = scores.argsort()[::-1][:top_k]
            return [self.chunks[index] for index in ranked]
        except ImportError:
            return self.chunks[:top_k]

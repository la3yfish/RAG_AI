from __future__ import annotations
import hashlib
from backend.core.interfaces import IEmbedder

class StubEmbedder(IEmbedder):
    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    def dimension(self) -> int:
        return self._dim

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        # Детерминированный псевдо-вектор из sha256 (MVP)
        h = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
        # растягиваем байты до dim
        out = []
        for i in range(self._dim):
            b = h[i % len(h)]
            out.append((b / 255.0) * 2.0 - 1.0)  # [-1, 1]
        return out

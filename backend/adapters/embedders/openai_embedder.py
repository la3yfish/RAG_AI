from __future__ import annotations
from backend.core.interfaces import IEmbedder

class OpenAIEmbedder(IEmbedder):
    def __init__(self, model: str) -> None:
        self.model = model

    def dimension(self) -> int:
        raise NotImplementedError("OpenAIEmbedder not implemented yet")

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("OpenAIEmbedder not implemented yet")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("OpenAIEmbedder not implemented yet")

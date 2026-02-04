from __future__ import annotations

from typing import Protocol


class IEmbedder(Protocol):
    """Embeddings provider abstraction (OpenAI/local/stub)."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embeddings for chunks."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Single embedding for query."""
        ...

    def dimension(self) -> int:
        """Embedding dimension (for validation / vector store schema)."""
        ...

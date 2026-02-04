from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Source:
    document_id: str
    chunk_id: str
    title: str
    score: float
    snippet: str
    location: str | None  # e.g., "p.3", "sec:2.1", "row:42"
    metadata: dict[str, Any]


class IVectorStore(Protocol):
    """Vector DB abstraction (Qdrant/Chroma/etc.)."""

    def upsert(
        self,
        *,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """Insert/update chunks + embeddings.
        chunks: canonical dicts produced by core pipeline (id, document_id, text, metadata...)
        """
        ...

    def search(
        self,
        *,
        query_embedding: list[float],
        filters: dict[str, Any] | None,
        top_k: int,
    ) -> list[Source]:
        """Similarity search with optional metadata filters."""
        ...

    def delete_by_document(self, *, document_id: str) -> int:
        """Return number of deleted vectors/chunks."""
        ...

    def health(self) -> dict[str, Any]:
        """Health info for readiness checks."""
        ...

from __future__ import annotations

from typing import Protocol

from .vector_store import Source


class IReranker(Protocol):
    """Optional reranker (stub in MVP)."""

    def rerank(self, *, query: str, candidates: list[Source], top_k: int) -> list[Source]:
        ...

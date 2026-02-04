from __future__ import annotations
from backend.core.interfaces import IReranker, Source

class StubReranker(IReranker):
    def rerank(self, *, query: str, candidates: list[Source], top_k: int) -> list[Source]:
        # MVP: сохраняем порядок как пришло из vectorstore
        return candidates[:top_k]

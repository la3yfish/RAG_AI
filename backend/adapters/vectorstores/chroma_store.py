from __future__ import annotations
from typing import Any
from backend.core.interfaces import IVectorStore, Source

class ChromaVectorStore(IVectorStore):
    def __init__(self, path: str, collection: str) -> None:
        self.path = path
        self.collection = collection

    def upsert(self, *, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        raise NotImplementedError("ChromaVectorStore not implemented yet")

    def search(self, *, query_embedding: list[float], filters: dict[str, Any] | None, top_k: int) -> list[Source]:
        raise NotImplementedError("ChromaVectorStore not implemented yet")

    def delete_by_document(self, *, document_id: str) -> int:
        raise NotImplementedError("ChromaVectorStore not implemented yet")

    def health(self) -> dict[str, Any]:
        return {"provider": "chroma", "status": "stub", "path": self.path, "collection": self.collection}

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Document:
    id: str
    source_type: str          # "pdf" | "docx" | "csv" | "md" | ...
    title: str
    department: str | None
    access_level: str         # "public" | "internal" | "confidential"
    created_at: str | None    # ISO8601 string in MVP to avoid datetime coupling
    content: str              # normalized plain text


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    text: str
    chunk_index: int
    metadata: dict[str, Any]


class IChunker(Protocol):
    """Chunking abstraction (safe wrapper can live in adapters)."""

    def chunk(self, document: Document) -> list[Chunk]:
        ...

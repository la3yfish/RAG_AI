from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IngestedDocument:
    id: str
    source_type: str
    title: str
    department: str | None
    access_level: str
    created_at: str | None
    content: str


class IIngestor(Protocol):
    """File parser abstraction (PDF/DOCX/CSV/MD)."""

    def can_handle(self, *, mime: str, filename: str) -> bool:
        ...

    def parse(self, *, file_bytes: bytes, filename: str) -> IngestedDocument:
        """Return normalized document text + core metadata.
        NOTE: binary parsing lives in adapters. Core receives normalized text.
        """
        ...

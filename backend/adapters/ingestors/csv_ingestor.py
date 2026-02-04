from __future__ import annotations

from backend.core.interfaces import IIngestor, IngestedDocument


class CsvIngestor(IIngestor):
    def can_handle(self, *, mime: str, filename: str) -> bool:
        return filename.lower().endswith(".csv") or mime in ("text/csv", "application/csv")

    def parse(self, *, file_bytes: bytes, filename: str) -> IngestedDocument:
        raise NotImplementedError("CsvIngestor not implemented yet")

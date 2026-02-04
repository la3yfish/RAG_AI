from __future__ import annotations

from backend.core.interfaces import IIngestor, IngestedDocument


class PdfIngestor(IIngestor):
    def can_handle(self, *, mime: str, filename: str) -> bool:
        return filename.lower().endswith(".pdf") or mime == "application/pdf"

    def parse(self, *, file_bytes: bytes, filename: str) -> IngestedDocument:
        raise NotImplementedError("PdfIngestor not implemented yet")

from __future__ import annotations
from backend.core.interfaces import IIngestor, IngestedDocument

class MarkdownIngestor(IIngestor):
    def can_handle(self, *, mime: str, filename: str) -> bool:
        return filename.lower().endswith(".md") or mime in ("text/markdown", "text/plain")

    def parse(self, *, file_bytes: bytes, filename: str) -> IngestedDocument:
        text = file_bytes.decode("utf-8", errors="replace")
        return IngestedDocument(
            id=filename,
            source_type="md",
            title=filename,
            department=None,
            access_level="internal",
            created_at=None,
            content=text,
        )

from __future__ import annotations

import time
from dataclasses import replace

import pytest

from backend.core.interfaces import Document
from backend.adapters.chunkers.default_chunker import DefaultChunker, DefaultChunkerConfig
from backend.adapters.sandbox.safe_chunker import SafeChunker


# @pytest.mark.stage
def test_stage_chunker_corner_cases_safe() -> None:
    """
    Stage: Chunker MVP
    Requirements:
      - must not crash OS (run via SafeChunker -> subprocess)
      - must finish without warnings/errors (test must PASS cleanly)
      - must handle corner cases deterministically
    """

    base = DefaultChunker(
        config=DefaultChunkerConfig(
            target_chars=1200,
            overlap_chars=150,
            max_document_chars=300_000,   # keep smaller for tests
            max_paragraph_chars=20_000,
            max_chunks=2000,
        )
    )

    # Tight but safe limits: if chunker goes crazy, it gets killed.
    safe = SafeChunker(
        base_chunker=base,
        timeout_sec=8,
        memory_mb=256,
        cpu_sec=4,
    )

    # Base doc template
    doc0 = Document(
        id="doc_test_1",
        source_type="md",
        title="Chunker Stage Test",
        department="Engineering",
        access_level="internal",
        created_at=None,
        content="",
    )

    cases: list[tuple[str, Document, dict]] = []

    # 1) Empty doc -> no chunks
    cases.append(("empty", doc0, {"min_chunks": 0, "max_chunks": 0}))

    # 2) Small text -> 1 chunk
    cases.append(("small", replace(doc0, content="Hello world.\n\nSecond paragraph."), {"min_chunks": 1, "max_chunks": 3}))

    # 3) Unicode + RTL + emojis
    unicode_text = (
        "English paragraph.\n\n"
        "עברית: זה טקסט לבדיקה של RTL.\n\n"
        "Русский текст для проверки.\n\n"
        "Emoji ✅🚀✨"
    )
    cases.append(("unicode_rtl", replace(doc0, content=unicode_text), {"min_chunks": 1, "max_chunks": 10}))

    # 4) Huge single line (corner case)
    huge_line = "A" * 120_000
    cases.append(("huge_line", replace(doc0, content=huge_line), {"min_chunks": 50, "max_chunks": 200}))

    # 5) Large multi-paragraph doc
    paras = [f"Paragraph {i}: " + ("lorem ipsum " * 40) for i in range(200)]
    big_doc = "\n\n".join(paras)
    cases.append(("big_doc", replace(doc0, id="doc_test_2", content=big_doc), {"min_chunks": 50, "max_chunks": 500}))

    # Run all cases (stage test)
    started = time.monotonic()
    for name, doc, expect in cases:
        chunks = safe.chunk(doc)

        assert isinstance(chunks, list), f"{name}: chunks must be list"
        assert len(chunks) >= expect["min_chunks"], f"{name}: too few chunks"
        assert len(chunks) <= expect["max_chunks"], f"{name}: too many chunks (possible runaway)"

        # Basic invariants
        for i, ch in enumerate(chunks):
            assert ch.document_id == doc.id, f"{name}: chunk {i} document_id mismatch"
            assert ch.text.strip(), f"{name}: chunk {i} empty text"
            assert ch.chunk_index == i, f"{name}: chunk_index must be sequential starting at 0"

        # Determinism: run again and compare stable IDs/text count
        chunks2 = safe.chunk(doc)
        assert len(chunks2) == len(chunks), f"{name}: chunk count must be deterministic"
        # We only compare IDs to ensure stable output; text can be compared too, but ID check is enough.
        assert [c.id for c in chunks2] == [c.id for c in chunks], f"{name}: chunk IDs must be deterministic"

    total_ms = int((time.monotonic() - started) * 1000)
    # Optional soft constraint: stage must finish quickly under safe limits
    assert total_ms < 25_000, f"stage too slow: {total_ms}ms"

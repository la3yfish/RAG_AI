from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from backend.core.interfaces import Chunk, Document, IChunker


@dataclass(frozen=True)
class DefaultChunkerConfig:
    # Rough target size in characters (MVP). You can switch to tokens later.
    target_chars: int = 1200
    overlap_chars: int = 150

    # Hard guards to avoid pathological memory/time behavior
    max_document_chars: int = 2_000_000       # 2MB text cap for MVP ingestion -> chunking
    max_paragraph_chars: int = 50_000         # prevent single paragraph explosion
    max_chunks: int = 2000                    # sanity cap


class DefaultChunker(IChunker):
    def __init__(self, config: DefaultChunkerConfig | None = None) -> None:
        self.config = config or DefaultChunkerConfig()

    def chunk(self, document: Document) -> list[Chunk]:
        text = (document.content or "").strip()

        # Corner case: empty doc
        if not text:
            return []

        # Hard cap to protect pipeline
        if len(text) > self.config.max_document_chars:
            text = text[: self.config.max_document_chars]

        paragraphs = _split_into_paragraphs(text)

        # Cap huge paragraphs (e.g., a 5MB single line)
        safe_paragraphs: list[str] = []
        for p in paragraphs:
            if len(p) <= self.config.max_paragraph_chars:
                safe_paragraphs.append(p)
            else:
                safe_paragraphs.extend(_split_huge_paragraph(p, self.config.max_paragraph_chars))

        chunks_text = _pack_paragraphs_into_chunks(
            safe_paragraphs,
            target=self.config.target_chars,
            overlap=self.config.overlap_chars,
            max_chunks=self.config.max_chunks,
        )

        chunks: list[Chunk] = []
        for idx, ch_text in enumerate(chunks_text):
            ch_id = _stable_chunk_id(document_id=document.id, chunk_index=idx, text=ch_text)
            chunks.append(
                Chunk(
                    id=ch_id,
                    document_id=document.id,
                    text=ch_text,
                    chunk_index=idx,
                    metadata={
                        "source_type": document.source_type,
                        "title": document.title,
                        "department": document.department,
                        "access_level": document.access_level,
                        "created_at": document.created_at,
                        "chunker": "default",
                        "target_chars": self.config.target_chars,
                        "overlap_chars": self.config.overlap_chars,
                    },
                )
            )

        return chunks


_PAR_SPLIT_RE = re.compile(r"(?:\r?\n){2,}")  # 2+ newlines


def _split_into_paragraphs(text: str) -> list[str]:
    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = [p.strip() for p in _PAR_SPLIT_RE.split(text)]
    # Filter empties
    return [p for p in parts if p]


def _split_huge_paragraph(p: str, max_len: int) -> list[str]:
    """Split huge paragraph by sentence-ish boundaries, fallback to hard slicing."""
    if len(p) <= max_len:
        return [p]

    # Try to split by sentence boundaries first
    sentences = re.split(r"(?<=[.!?])\s+", p)
    out: list[str] = []
    buf: list[str] = []
    cur = 0

    def flush() -> None:
        nonlocal buf, cur
        if buf:
            out.append(" ".join(buf).strip())
            buf = []
            cur = 0

    for s in sentences:
        if not s:
            continue
        if len(s) > max_len:
            # sentence itself is too large -> hard slice
            flush()
            for i in range(0, len(s), max_len):
                out.append(s[i : i + max_len].strip())
            continue

        if cur + len(s) + 1 <= max_len:
            buf.append(s)
            cur += len(s) + 1
        else:
            flush()
            buf.append(s)
            cur = len(s) + 1

    flush()

    # Safety: if splitting failed for some reason
    if not out:
        return [p[i : i + max_len].strip() for i in range(0, len(p), max_len)]
    return out


def _pack_paragraphs_into_chunks(
    paragraphs: list[str],
    *,
    target: int,
    overlap: int,
    max_chunks: int,
) -> list[str]:
    """
    Pack paragraphs into chunks near target size.
    Adds simple character overlap between consecutive chunks.
    """
    if target <= 100:
        raise ValueError("target must be > 100 chars")
    if overlap < 0 or overlap >= target:
        raise ValueError("overlap must be in [0, target)")

    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0

    def emit() -> None:
        nonlocal cur, cur_len
        if not cur:
            return
        chunk_text = "\n\n".join(cur).strip()
        if chunk_text:
            chunks.append(chunk_text)
        cur = []
        cur_len = 0

    for p in paragraphs:
        add_len = len(p) + (2 if cur else 0)  # account for separators roughly
        if cur_len + add_len <= target:
            cur.append(p)
            cur_len += add_len
        else:
            emit()
            # Start new chunk with overlap from previous chunk tail
            if overlap > 0 and chunks:
                tail = chunks[-1][-overlap:].strip()
                if tail:
                    cur.append(tail)
                    cur_len = len(tail)
            # Now add paragraph (may still be large but capped earlier)
            if len(p) > target:
                # If paragraph is still larger than target, split hard
                for i in range(0, len(p), target):
                    part = p[i : i + target].strip()
                    if part:
                        chunks.append(part)
                        if len(chunks) >= max_chunks:
                            return chunks
                cur = []
                cur_len = 0
            else:
                cur.append(p)
                cur_len += len(p)

        if len(chunks) >= max_chunks:
            return chunks

    emit()
    return chunks[:max_chunks]


def _stable_chunk_id(*, document_id: str, chunk_index: int, text: str) -> str:
    """
    Deterministic chunk id: sha1(document_id | chunk_index | first/last bytes).
    Keeps IDs stable across reruns when chunking is stable.
    """
    head = text[:256]
    tail = text[-256:] if len(text) > 256 else ""
    payload = f"{document_id}|{chunk_index}|{head}|{tail}".encode("utf-8", errors="ignore")
    h = hashlib.sha1(payload).hexdigest()
    return f"ch_{h}"

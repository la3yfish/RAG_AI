from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from backend.app.settings import Settings
from backend.app.container import build_container


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def index_folder(folder: str | Path) -> dict[str, Any]:
    settings = Settings.load()
    c = build_container(settings)

    root = Path(folder)
    files = sorted([p for p in root.rglob("*") if p.is_file()])

    docs_ok = 0
    chunks_ok = 0

    for p in files:
        mime = _guess_mime(p)
        ing = next((i for i in c.ingestors if i.can_handle(mime=mime, filename=p.name)), None)
        if not ing:
            continue

        doc = ing.parse(file_bytes=p.read_bytes(), filename=p.name)
        if not doc.content.strip():
            # scanned-like PDF without usable OCR -> skip indexing
            continue

        chunks = c.chunker.chunk(doc)
        if not chunks:
            continue

        texts = [ch.text for ch in chunks]
        vecs = c.embedder.embed_texts(texts)

        # canonical chunk dicts for vectorstore
        chunk_dicts: list[dict[str, Any]] = []
        for ch in chunks:
            md = dict(ch.metadata or {})
            md.setdefault("document_id", ch.document_id)
            md.setdefault("chunk_id", ch.id)
            md.setdefault("chunk_index", ch.chunk_index)

            chunk_dicts.append(
                {
                    "id": ch.id,
                    "document_id": ch.document_id,
                    "text": ch.text,
                    "metadata": md,
                }
            )

        c.vectorstore.delete_by_document(document_id=doc.id)
        c.vectorstore.upsert(chunks=chunk_dicts, embeddings=vecs)

        docs_ok += 1
        chunks_ok += len(chunks)

    return {"docs_indexed": docs_ok, "chunks_indexed": chunks_ok, "vectorstore": c.vectorstore.health()}


def main() -> int:
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "data/synthetic_data"
    report = index_folder(folder)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

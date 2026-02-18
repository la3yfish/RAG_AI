"""Local smoke utility: ingest a folder -> chunk all documents -> print summary.

Usage:
  python -m backend.app.chunk_smoke data/synthetic_data
"""

from __future__ import annotations

import os
from pathlib import Path

from backend.app.settings import Settings
from backend.app.container import build_container
from backend.app.ingest_smoke import ingest_folder  # reuse


def main(folder: str) -> int:
    settings = Settings.load()
    c = build_container(settings)

    root = Path(folder)
    results = ingest_folder(root)

    # rebuild docs (ingest_folder currently returns summaries)
    # We need actual IngestedDocument objects -> ingest again using the same ingestors.
    # This keeps chunk_smoke independent from internal pipeline refactors.
    docs = []
    for p in sorted([p for p in root.rglob("*") if p.is_file()]):
        mime = _guess_mime(p)
        ing = next((i for i in c.ingestors if i.can_handle(mime=mime, filename=p.name)), None)
        if not ing:
            continue
        try:
            docs.append(ing.parse(file_bytes=p.read_bytes(), filename=p.name))
        except Exception:
            pass

    chunker = c.chunker  # container should expose a chunker (SafeChunker wrapping DefaultChunker)

    ok = 0
    fail = 0

    for doc in docs:
        try:
            chunks = chunker.chunk(doc)
            total_chars = sum(len(ch.content) for ch in chunks)
            print(f"OK    {doc.id:28s} chunks={len(chunks):3d} total_chars={total_chars:7d}")
            ok += 1
        except Exception as e:
            print(f"FAIL  {doc.id}: {e}")
            fail += 1

    print(f"\nSummary: ok={ok} fail={fail} total={len(docs)}")
    return 0 if fail == 0 else 1


def _guess_mime(path: Path) -> str:
    import mimetypes

    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "data/synthetic_data"
    raise SystemExit(main(folder))

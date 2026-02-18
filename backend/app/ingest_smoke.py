"""Local smoke utility: ingest a folder and print short summaries.

Usage:
  python -m backend.app.ingest_smoke data/synthetic_data

Optional:
  RAG_AI_ENABLE_OCR=1   # enable OCR fallback for scanned PDFs
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from backend.app.settings import Settings
from backend.app.container import build_container


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def ingest_folder(folder: str | Path) -> list[dict[str, Any]]:
    """
    Ingest all files under `folder` using container ingestors.

    Returns list of dicts:
      {
        "filename": str,
        "path": str,
        "mime": str,
        "status": "ok" | "fail" | "skip",
        "source_type": str | None,
        "chars": int,
        "error": str | None,
      }
    """
    settings = Settings.load()
    c = build_container(settings)

    root = Path(folder)
    files = sorted([p for p in root.rglob("*") if p.is_file()])

    results: list[dict[str, Any]] = []
    for p in files:
        mime = _guess_mime(p)
        ing = next((i for i in c.ingestors if i.can_handle(mime=mime, filename=p.name)), None)
        if not ing:
            results.append(
                {
                    "filename": p.name,
                    "path": str(p),
                    "mime": mime,
                    "status": "skip",
                    "source_type": None,
                    "chars": 0,
                    "error": "no ingestor",
                }
            )
            continue

        try:
            doc = ing.parse(file_bytes=p.read_bytes(), filename=p.name)
            results.append(
                {
                    "filename": p.name,
                    "path": str(p),
                    "mime": mime,
                    "status": "ok",
                    "source_type": doc.source_type,
                    "chars": len(doc.content),
                    "error": None,
                }
            )
        except Exception as e:
            results.append(
                {
                    "filename": p.name,
                    "path": str(p),
                    "mime": mime,
                    "status": "fail",
                    "source_type": None,
                    "chars": 0,
                    "error": str(e),
                }
            )

    return results


def main(folder: str) -> int:
    root = Path(folder)
    results = ingest_folder(root)

    if not results:
        print(f"No files found: {root}")
        return 2

    ok = [r for r in results if r["status"] == "ok"]
    fail = [r for r in results if r["status"] == "fail"]
    skip = [r for r in results if r["status"] == "skip"]

    # печать в формате, максимально близком к текущему
    for r in results:
        name = r["filename"]
        if r["status"] == "ok":
            st = r["source_type"] or "?"
            print(f"OK    {name:28s} type={st:4s} chars={r['chars']:7d}")
        elif r["status"] == "skip":
            print(f"SKIP  {name} (mime={r['mime']}): no ingestor")
        else:
            print(f"FAIL  {name}: {r['error']}")

    print(f"\nSummary: ok={len(ok)} fail={len(fail)} total={len(results)}")
    return 0 if len(fail) == 0 else 1


if __name__ == "__main__":
    import sys

    folder = sys.argv[1] if len(sys.argv) > 1 else "data/synthetic_data"
    raise SystemExit(main(folder))

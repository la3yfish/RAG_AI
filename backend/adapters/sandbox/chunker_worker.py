from __future__ import annotations

import json
import sys
import traceback
from dataclasses import asdict
from typing import Any

from backend.core.interfaces import Chunk, Document


def main() -> int:
    try:
        payload = _read_stdin_json()
        doc = _parse_document(payload.get("document"))
        chunker_id = str(payload.get("chunker_id") or "DefaultChunker")
        chunker_params = payload.get("chunker_params") or {}

        chunker = _build_chunker(chunker_id=chunker_id, params=chunker_params)
        chunks = chunker.chunk(doc)

        out = {
            "ok": True,
            "chunks": [asdict(c) for c in chunks],
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
        return 0

    except Exception as e:
        err = {
            "ok": False,
            "error_type": e.__class__.__name__,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        # Important: worker prints JSON even on error (caller relies on JSON).
        sys.stdout.write(json.dumps(err, ensure_ascii=False))
        return 1


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("Empty stdin JSON payload.")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Payload must be a JSON object.")
    return obj


def _parse_document(doc_obj: Any) -> Document:
    if not isinstance(doc_obj, dict):
        raise ValueError("document must be an object.")
    # Minimal required fields
    return Document(
        id=str(doc_obj["id"]),
        source_type=str(doc_obj["source_type"]),
        title=str(doc_obj["title"]),
        department=(str(doc_obj["department"]) if doc_obj.get("department") is not None else None),
        access_level=str(doc_obj["access_level"]),
        created_at=(str(doc_obj["created_at"]) if doc_obj.get("created_at") is not None else None),
        content=str(doc_obj["content"]),
    )


def _build_chunker(*, chunker_id: str, params: dict[str, Any]):
    """
    Registry for chunkers.
    MVP: only DefaultChunker supported.
    Later: add other implementations with explicit keys.
    """
    # Keep imports local to avoid importing heavy deps unless needed.
    if chunker_id in ("DefaultChunker", "default", "default_chunker"):
        from backend.adapters.chunkers.default_chunker import DefaultChunker
        return DefaultChunker(**_safe_kwargs(params))

    # Fallback: be strict to avoid accidental arbitrary code paths.
    raise ValueError(f"Unknown chunker_id: {chunker_id}")


def _safe_kwargs(params: dict[str, Any]) -> dict[str, Any]:
    # MVP: allow only dict kwargs; you can add allowlist later.
    return dict(params) if isinstance(params, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())

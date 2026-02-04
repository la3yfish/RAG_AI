from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from core.interfaces import Chunk, Document, IChunker

from .safe_runner import SafeRunnerError, run_python_module


class SafeChunker(IChunker):
    """
    Wrap any IChunker and run it in a separate process to avoid OS freezes / OOM disasters.

    Contract:
      - input: core.interfaces.Document
      - output: list[core.interfaces.Chunk]
    """

    def __init__(
        self,
        *,
        base_chunker: IChunker,
        timeout_sec: int = 20,
        memory_mb: int = 512,
        cpu_sec: int = 10,
    ) -> None:
        self._base_chunker = base_chunker
        self._timeout_sec = timeout_sec
        self._memory_mb = memory_mb
        self._cpu_sec = cpu_sec

    def chunk(self, document: Document) -> list[Chunk]:
        payload = {
            "document": asdict(document),
            # This is the key trick: we do NOT import base chunker class in the worker.
            # We pass a "chunker_id" for selecting implementation inside worker.
            "chunker_id": _chunker_id(self._base_chunker),
            "chunker_params": _chunker_params(self._base_chunker),
        }

        res = run_python_module(
            module="backend.adapters.sandbox.chunker_worker",
            input_json=payload,
            timeout_sec=self._timeout_sec,
            memory_mb=self._memory_mb,
            cpu_sec=self._cpu_sec,
        )

        if res.timed_out:
            raise RuntimeError(
                f"Chunker timed out after {self._timeout_sec}s (killed safely)."
            )
        if res.oom_suspected:
            raise RuntimeError(
                f"Chunker suspected OOM (killed safely). stderr:\n{_trim(res.stderr)}"
            )
        if not res.ok:
            raise RuntimeError(
                f"Chunker failed (rc={res.returncode}). stderr:\n{_trim(res.stderr)}"
            )

        try:
            obj = json.loads(res.stdout)
        except Exception as e:
            raise SafeRunnerError(
                f"Chunker worker returned non-JSON output. stdout:\n{_trim(res.stdout)}"
            ) from e

        if not isinstance(obj, dict) or obj.get("ok") is not True:
            raise RuntimeError(
                f"Chunker worker reported failure. stdout:\n{_trim(res.stdout)}"
            )

        chunks_raw = obj.get("chunks")
        if not isinstance(chunks_raw, list):
            raise RuntimeError("Chunker worker JSON missing 'chunks' list.")

        chunks: list[Chunk] = []
        for i, c in enumerate(chunks_raw):
            try:
                chunks.append(
                    Chunk(
                        id=str(c["id"]),
                        document_id=str(c["document_id"]),
                        text=str(c["text"]),
                        chunk_index=int(c["chunk_index"]),
                        metadata=dict(c.get("metadata") or {}),
                    )
                )
            except Exception as e:
                raise RuntimeError(f"Invalid chunk at index {i}: {c}") from e

        return chunks


def _chunker_id(chunker: IChunker) -> str:
    """
    Minimal registry key. For MVP we use class name.
    Later you can add explicit attribute chunker.chunker_id if you want.
    """
    return chunker.__class__.__name__


def _chunker_params(chunker: IChunker) -> dict[str, Any]:
    """
    Optional parameters snapshot (MVP: empty).
    If your DefaultChunker has config, expose it here.
    """
    # Example:
    # return getattr(chunker, "config", {}) if isinstance(getattr(chunker, "config", None), dict) else {}
    return {}


def _trim(s: str, limit: int = 2000) -> str:
    s = s or ""
    return s if len(s) <= limit else (s[:limit] + "\n...<trimmed>...")

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Settings:
    environment: str
    strict_mode: bool

    vectorstore_provider: str
    qdrant_url: str
    qdrant_collection: str
    chroma_path: str
    chroma_collection: str

    embeddings_provider: str
    openai_embedding_model: str
    stub_embedding_dim: int

    frontend_mode: str

    @staticmethod
    def load(config_path: str | None = None) -> "Settings":
        path = Path(config_path or os.getenv("RAG_AI_CONFIG", "config.yaml"))
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path.resolve()}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        raw = _apply_env_overrides(raw)

        rt = raw.get("runtime", {})
        vs = raw.get("vectorstore", {})
        em = raw.get("embeddings", {})
        fe = raw.get("frontend", {})

        provider_vs = str(vs.get("provider", "qdrant")).lower()
        provider_em = str(em.get("provider", "openai")).lower()

        q = vs.get("qdrant", {}) if isinstance(vs.get("qdrant", {}), dict) else {}
        c = vs.get("chroma", {}) if isinstance(vs.get("chroma", {}), dict) else {}
        o = em.get("openai", {}) if isinstance(em.get("openai", {}), dict) else {}
        s = em.get("stub", {}) if isinstance(em.get("stub", {}), dict) else {}

        return Settings(
            environment=str(rt.get("environment", "dev")),
            strict_mode=bool(rt.get("strict_mode", True)),

            vectorstore_provider=provider_vs,
            qdrant_url=str(q.get("url", "http://localhost:6333")),
            qdrant_collection=str(q.get("collection", "rag_ai")),
            chroma_path=str(c.get("path", "./data/chroma")),
            chroma_collection=str(c.get("collection", "rag_ai")),

            embeddings_provider=provider_em,
            openai_embedding_model=str(o.get("model", "text-embedding-3-small")),
            stub_embedding_dim=int(s.get("dim", 384)),

            frontend_mode=str(fe.get("mode", "streamlit")).lower(),
        )


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """Optional overrides. Keep minimal to avoid config complexity."""
    # Example: RAG_AI_VECTORSTORE_PROVIDER=qdrant
    vs_provider = os.getenv("RAG_AI_VECTORSTORE_PROVIDER")
    if vs_provider:
        raw.setdefault("vectorstore", {})["provider"] = vs_provider

    emb_provider = os.getenv("RAG_AI_EMBEDDINGS_PROVIDER")
    if emb_provider:
        raw.setdefault("embeddings", {})["provider"] = emb_provider

    qdrant_url = os.getenv("RAG_AI_QDRANT_URL")
    if qdrant_url:
        raw.setdefault("vectorstore", {}).setdefault("qdrant", {})["url"] = qdrant_url

    return raw

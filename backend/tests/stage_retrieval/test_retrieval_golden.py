from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.settings import Settings
from backend.app.container import build_container

DATA_DIR = Path("data/synthetic_data")
GOLDEN = DATA_DIR / "ground_truth_queries.json"


def _load_cases() -> list[dict]:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cases" in data:
        cases = data["cases"]
    else:
        cases = data
    if not isinstance(cases, list):
        raise AssertionError(f"ground_truth_queries.json: expected list or dict{{cases:list}}, got {type(data)}")
    return cases


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chroma_stage")
    settings = replace(
        Settings.load(),
        vectorstore_provider="chroma",
        embeddings_provider="stub",
        chroma_path=str(tmp / "chroma"),
        chroma_collection="rag_ai_stage_test",
        stub_embedding_dim=384,
    )
    c = build_container(settings)

    # index once
    for p in sorted([p for p in DATA_DIR.rglob("*") if p.is_file()]):
        import mimetypes

        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "application/octet-stream"

        ing = next((i for i in c.ingestors if i.can_handle(mime=mime, filename=p.name)), None)
        if not ing:
            continue

        doc = ing.parse(file_bytes=p.read_bytes(), filename=p.name)
        if not doc.content.strip():
            continue

        chunks = c.chunker.chunk(doc)
        if not chunks:
            continue

        vecs = c.embedder.embed_texts([ch.text for ch in chunks])
        chunk_dicts = []
        for ch in chunks:
            md = dict(ch.metadata or {})
            md.setdefault("document_id", ch.document_id)
            md.setdefault("chunk_id", ch.id)
            md.setdefault("chunk_index", ch.chunk_index)
            chunk_dicts.append(
                {"id": ch.id, "document_id": ch.document_id, "text": ch.text, "metadata": md}
            )

        c.vectorstore.delete_by_document(document_id=doc.id)
        c.vectorstore.upsert(chunks=chunk_dicts, embeddings=vecs)

    return c


def test_golden_schema():
    cases = _load_cases()
    assert len(cases) > 0
    # минимальная проверка полей
    for case in cases[:5]:
        assert "q" in case
        assert "expected_sources" in case
        assert isinstance(case["expected_sources"], list)


def test_retrieval_smoke_topk(rig):
    cases = _load_cases()
    # smoke: хотя бы 10 запросов должны возвращать >=1 результата
    for case in cases[:10]:
        q = case["q"]
        qv = rig.embedder.embed_query(q)
        hits = rig.vectorstore.search(query_embedding=qv, filters=None, top_k=5)
        assert isinstance(hits, list)
        assert len(hits) > 0


def test_golden_hit_at_5_semantic_gate(rig):
    # StubEmbedder не семантический -> hit@k как качество будет бессмысленным.
    if getattr(rig.settings, "embeddings_provider", None) == "stub":
        pytest.skip("hit@k gate is disabled for StubEmbedder (non-semantic). Enable real embeddings to use this gate.")

    cases = _load_cases()
    for case in cases[:20]:
        q = case["q"]
        expected = set(case.get("expected_sources", []))

        qv = rig.embedder.embed_query(q)
        hits = rig.vectorstore.search(query_embedding=qv, filters=None, top_k=5)
        got = {h.document_id for h in hits}

        assert expected & got, f"hit@5 failed for q={q!r}. expected={expected}, got={got}"

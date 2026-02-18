from pathlib import Path

from backend.app.settings import Settings
from backend.app.container import build_container

DATA_DIR = Path("data/synthetic_data")


def test_chunk_all_ingested_docs():
    settings = Settings.load()
    c = build_container(settings)

    root = DATA_DIR
    files = sorted([p for p in root.rglob("*") if p.is_file()])

    docs = []
    for p in files:
        mime = _guess_mime(p)
        ing = next((i for i in c.ingestors if i.can_handle(mime=mime, filename=p.name)), None)
        if not ing:
            continue
        docs.append(ing.parse(file_bytes=p.read_bytes(), filename=p.name))

    chunker = c.chunker

    for doc in docs:
        # если документ пустой (например scanned PDF без OCR) — допускаем 0 chunks
        if not doc.content.strip():
            continue

        chunks = chunker.chunk(doc)

        assert len(chunks) > 0
        assert len(chunks) <= 300  # guardrail sanity

        for ch in chunks:
            # Под твой реальный контракт:
            assert ch.document_id == doc.id
            assert ch.text.strip()
            assert ch.chunk_index >= 0
            assert isinstance(ch.metadata, dict)


def _guess_mime(path: Path) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"

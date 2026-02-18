import os
from pathlib import Path

from backend.app.ingest_smoke import ingest_folder

DATA_DIR = Path("data/synthetic_data")


def test_ingest_smoke_no_ocr():
    os.environ.pop("RAG_AI_ENABLE_OCR", None)

    result = ingest_folder(DATA_DIR)
    ok = [r for r in result if r["status"] == "ok"]
    fail = [r for r in result if r["status"] == "fail"]
    skip = [r for r in result if r["status"] == "skip"]

    assert len(fail) == 0
    assert len(ok) == 12
    assert len(skip) == 2


def test_ingest_invoice_with_ocr():
    os.environ["RAG_AI_ENABLE_OCR"] = "1"

    result = ingest_folder(DATA_DIR)
    inv = next(r for r in result if r["filename"] == "invoice_scanned.pdf")
    assert inv["status"] == "ok"
    assert inv["chars"] > 50

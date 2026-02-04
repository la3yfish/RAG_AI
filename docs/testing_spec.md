# Testing: staged tests, golden set, master_test

## 1) Definitions

- **Stage test**: a test suite created at the end of a development stage; validates only the completed stage + required contracts.
- **Master test**: a runner that executes all stage tests sequentially and **must finish with zero warnings/errors**. 
- **Golden set**: a fixed set of questions/expected evidence used for RAG/evaluation (JSON format). 
- MVP requires “RAG with sources (20+ test questions)” and “pytest tests/”. 

## 2) Safety requirement: tests must not be able to freeze the OS

Observed risk: a test starts buggy code (e.g., `chunker.py`) that consumes all RAM and can hang the OS.

Mandatory harness protections:

1. Run risky code **in a subprocess** (never in the main pytest process).
2. Hard **timeouts** (per stage + per test).
3. Hard **memory limits** for subprocesses.
4. Kill process tree on breach (timeout/memory).
5. Temp working dir (no writes outside).
6. No network by default.

## 3) Minimal folder layout

```
tests/
  stage_01_ingestion/
  stage_02_vector_retrieval/
  stage_03_api/
  stage_05_analytics/
  stage_06_evaluation/
  golden_sets/
    rag_golden_v1.json
scripts/
  master_test.py
  run_stage.py
```

## 4) Stage test contract

Each stage test:

- is created at the end of the stage
- fully verifies implemented functionality
- includes corner cases (see §8)
- is deterministic (fixed seeds / fixed golden set)
- produces clear logs

## 5) Master test: pass/fail

Execution: run stages in order: 01 → 02 → … → N.

PASS if:

- all stages exit code = 0
- **zero warnings** and **zero errors**
- report + logs are produced

FAIL if any:

- non-zero exit
- timeout
- memory limit breach / OOM in child
- any warning
- missing artifacts

## 6) Isolation contract for running a stage

Stages must be executed via a shared runner (e.g., `scripts/run_stage.py`) that enforces:

- `TIMEOUT_S` (per stage)
- `TEST_TIMEOUT_S` (per test, if supported)
- `MEMORY_LIMIT_MB` (hard cap)
- `NO_NETWORK=1` default
- `TMPDIR=<stage_temp>`

Runner returns (for master aggregation):

- `status: pass|fail|timeout|mem_kill|error`
- `duration_ms`
- `warnings_count`
- `failures_count`
- `logs_path`

## 7) Golden set: minimal JSON schema

Path: `tests/golden_sets/rag_golden_v1.json`

```json
{
  "version": "v1",
  "generated_at": "YYYY-MM-DD",
  "items": [
    {
      "id": "q001",
      "question": "string",
      "intent": "kpi|sales|hr|support|logistics|general",
      "expected": {
        "must_have_facts": ["string"],
        "must_not_claim": ["string"]
      },
      "evidence": {
        "min_sources": 2,
        "allowed_doc_ids": ["string"],
        "required_filters": {
          "department": "string",
          "access_level": "public|internal|confidential"
        }
      }
    }
  ]
}
```

Rule: answers must provide 2–5 relevant sources; if none found → “в базе не найдено подтверждений”. fileciteturn9file5L18-L21

## 8) Corner cases checklist (mandatory)

- empty input (empty file / empty question)
- malformed input (corrupt PDF/DOCX/CSV)
- very large input within harness limits
- weird encoding / multilingual text
- extreme chunk sizes (min/max)
- duplicate docs / re-ingest same doc_id
- no retrieval (“no sources found”) path 

## 9) Minimal acceptance metrics per stage

### Stage 01: Ingestion

PASS if:

- supports PDF, DOCX, CSV/XLSX for MVP DoD 
- outputs unified `Document` schema: `doc_id`, `source_type`, `content_text`, `chunks[]` 
- chunker never hangs/crashes under limits

### Stage 02: Vector DB + Retrieval + basic RAG

PASS if:

- retrieval returns top-k chunks
- answer includes citations format + sources list 
- golden set has ≥20 questions (MVP DoD) 

### Stage 03: API + Logging

PASS if:

- `/ingest`, `/query`, `/health` work (per API contracts)
- logs include request_id, top_sources, latency 

### Stage 05: Analytics

PASS if:

- analytics produce correct tables and 2–3 matplotlib charts (MVP DoD). 

### Stage 06: Evaluation

PASS if:

- computes retrieval metrics: precision@k, recall@k, MRR; faithfulness checklist exists. 

## 10) Warnings policy (strict)

Master test must end with zero warnings.
Implementation option: run pytest with warnings-as-errors.

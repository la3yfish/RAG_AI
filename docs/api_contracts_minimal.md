# Minimal API Contracts (MVP) — RAG_AI

These contracts define the minimum request/response shapes needed to start backend + frontend development for:
- `GET /api/health`
- `POST /api/ingest`
- `POST /api/query`
- `POST /api/analytics`

## Common

### SuccessEnvelope
```json
{
  "request_id": "uuid",
  "status": "ok",
  "data": {}
}
```

### ErrorEnvelope
```json
{
  "request_id": "uuid",
  "status": "error",
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### AccessLevel
```json
"public" | "internal" | "confidential"
```

### SourceItem
```json
{
  "doc_id": "string",
  "chunk_id": "string",
  "score": 0.0,
  "page": 0,
  "snippet": "string"
}
```
Notes:
- `page` and `snippet` are optional; include when available.

## Endpoints

### GET /api/health

**200**
```json
{
  "request_id": "uuid",
  "status": "ok",
  "data": {
    "service": "rag_ai",
    "version": "string",
    "time": "ISO-8601",
    "components": {
      "vector_db": "ok|down",
      "llm": "ok|down",
      "storage": "ok|down"
    }
  }
}
```

**Errors**: 503

---

### POST /api/ingest

**Request**: `multipart/form-data`
- `file` (required)
- `doc_id` (optional)
- `source_type` (optional string, e.g. `pdf|docx|xlsx|csv`)
- `access_level` (optional AccessLevel)
- `department` (optional string)
- `tags` (optional string, CSV: `"a,b,c"`)

**200**
```json
{
  "request_id": "uuid",
  "status": "ok",
  "data": {
    "doc_id": "string",
    "source_type": "string",
    "access_level": "internal",
    "department": "string",
    "chunks_count": 0,
    "bytes": 0,
    "warnings": [
      { "code": "string", "message": "string" }
    ]
  }
}
```

**Errors**: 400, 413, 415, 422, 500, 503

---

### POST /api/query

**Request JSON**
```json
{
  "question": "string",
  "access_level": "public",
  "department": "string",
  "top_k": 5,
  "return_snippets": true
}
```

**200**
```json
{
  "request_id": "uuid",
  "status": "ok",
  "data": {
    "answer": "string",
    "sources": [
      {
        "doc_id": "string",
        "chunk_id": "string",
        "score": 0.78,
        "page": 12,
        "snippet": "string"
      }
    ],
    "applied_filters": {
      "access_level": "string",
      "department": "string",
      "top_k": 0
    },
    "usage": {
      "token_usage": { "prompt": 0, "completion": 0, "total": 0 }
    },
    "latency_ms": {
      "retrieval_ms": 0,
      "llm_ms": 0,
      "total_ms": 0
    }
  }
}
```

**Errors**: 400, 429, 500, 503

---

### POST /api/analytics (optional)

**Request JSON**
```json
{
  "task": "string",
  "params": {}
}
```

**200**
```json
{
  "request_id": "uuid",
  "status": "ok",
  "data": {
    "tables": [
      {
        "name": "string",
        "columns": ["string"],
        "rows": []
      }
    ],
    "charts": [
      {
        "name": "string",
        "mime": "image/png",
        "data_base64": "string"
      }
    ]
  }
}
```

**Errors**: 400, 422, 503, 500


## Error codes (minimal)

- `invalid_request` → 400  
- `validation_error` → 422  
- `payload_too_large` → 413  
- `unsupported_media_type` → 415  
- `rate_limit` → 429  
- `dependency_unavailable` → 503  
- `internal_error` → 500  

# Knowledge Base — RAG_AI

## 0) Назначение документа
Этот файл — **единственный обязательный источник знаний** для реализации проекта RAG_AI: архитектура, контракты, данные, тестирование, эксплуатация.  
Системный промпт (**docs/system_prompt.md**) ссылается на этот документ.

---

## 1) Проект: цель и контекст

### 1.1 Цель
Создать **Retrieval-Augmented Generation ассистент** для бизнес-аналитики на синтетических корпоративных данных компании **UnitTech LLC**.

### 1.2 Основные функции
- Диалоговые ответы на вопросы по внутренним данным компании.
- Поиск и сводка по документам (с источниками).
- Аналитика (агрегации/сравнения/выводы) поверх retrieved evidence.
- Мультимодальный ingestion (MVP: PDF/DOCX/MD/CSV; OCR — по необходимости).

### 1.3 Язык проекта
- Язык проекта, документация/комментарии: **русский**.
- Технические идентификаторы (библиотеки/API/эндпоинты/JSON-ключи): **английский**.

---

## 2) Ключевые принципы (обязательные)

### 2.1 Reality Filter
Правила применения — см. `docs/system_prompt.md` (кратко) и требования из `docs/REALITY FILTER.md` (для актуализации документации).

### 2.2 Поэтапная реализация
- Проект реализуется небольшими этапами.
- После каждого значимого этапа: автоматические тесты + ручная проверка.
- После успешного тестирования обновляются: `CHANGELOG.md`, при необходимости `README.md`, `docs/knowledge_base.md`, `docs/system_prompt.md`.
- Есть `master_test`, который запускает все этапные тесты последовательно.

### 2.3 Модульность и заменяемость
Компоненты должны быть **заменяемыми модулями**:
- LLM
- Embeddings / Embedder
- Vector DB / VectorStore
- UI (веб, локальный)
- OCR/парсеры/ingestion

Требование: сохранять совместимость интерфейсов между версиями (желательно backwards compatible).

### 2.4 LLM для разработки и тестирования
- Для разработки/тестирования использовать OpenAI **`gpt-5-nano`**.
- Архитектура должна поддерживать замену модели и развертывание локально/в облаке.

---

## 3) Архитектура (MVP → расширение)

### 3.1 Пайплайн
1) Ingestion → `Document`
2) Chunking → `Chunk`
3) Embeddings → вектора
4) VectorStore → similarity search + мета-фильтры
5) Retrieval → evidence с фильтрами
6) RAG Pipeline → prompt → LLM
7) Answer → ответ + источники + логи

### 3.2 Контрактные модели

#### 3.2.1 Document (canonical)
```json
{
  "id": "string",
  "title": "string",
  "source_type": "pdf|docx|md|csv|text|image",
  "source_uri": "string",
  "created_at": "ISO-8601",
  "ingested_at": "ISO-8601",
  "department": "string|null",
  "access_level": "public|internal|confidential",
  "tags": ["string"],
  "text": "string",
  "metadata": {}
}
```

#### 3.2.2 Chunk
```json
{
  "chunk_id": "string",
  "doc_id": "string",
  "text": "string",
  "span": {"start": 0, "end": 0},
  "metadata": {
    "title": "string",
    "page": 1,
    "section": "string",
    "department": "string|null",
    "access_level": "public|internal|confidential"
  }
}
```

#### 3.2.3 Интерфейсы модулей (минимум)
- `Ingester`: input → `Document[]`
- `Chunker`: `Document` → `Chunk[]`
- `Embedder`: `Chunk[]` → `Vector[]`
- `VectorStore`: upsert/query → `RetrievedChunk[]`
- `RAGPipeline`: query + retrieved → answer
- `LLMClient`: messages → completion (text + token usage)

---

## 4) Контроль доступа
- `access_level`: `public|internal|confidential`.
- Фильтрация должна выполняться на backend retrieval.
- Политика: `docs/access_control_policy.md`.

---

## 5) API (MVP)
Эндпоинты: `GET /api/health`, `POST /api/ingest`, `POST /api/query`, `POST /api/analytics` (опционально).  
Контракты: `docs/api_contracts_minimal.md`.

---

## 6) Синтетические данные
Источники: `/synthetic_data/*` (company_passport, employees, client_projects, projects_report, contract_sample, sales_report_Q3_2025).  
Схемы/валидность/генерация/corner cases: `docs/synthetic_data_schemas.md`.

---

## 7) Тестирование
- На каждый этап: отдельный stage test.
- `master_test`: запускает stage tests по очереди, **0 warnings/errors**.
- Опасные компоненты (chunker и т.п.) тестировать в изолированном процессе (timeout + memory limit + kill-tree).
- Спецификация: `docs/testing_spec.md`.

---

## 8) Логи (минимум)
Для `/api/query`: `request_id`, `query`, `filters`, `top_sources`, `latency_ms`, `token_usage`.

---

## 9) UI (минимум)
Web UI (адаптивный) + базовые функции: ingest, чат-запрос, просмотр источников.

---

## 10) Диплом
Оформление: `docs/thesis_formatting_requirements.md` (локальный шаблон вуза имеет приоритет).

---

## 11) Структура репозитория (рекомендуемая)
```
/app
  /api
  /core
  /ingestion
  /chunking
  /embeddings
  /vectorstore
  /rag
  /evaluation
/tests
/docs
/synthetic_data
CHANGELOG.md
README.md
```

---

## 12) Definition of Done для этапа
Этап завершён, если: есть stage tests, обновлён `master_test`, обновлены changelog и нужная документация, функционал воспроизводим на синтетических данных.

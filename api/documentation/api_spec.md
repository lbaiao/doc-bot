# AI Document Analyzer API Backend Specification (FastAPI)

> **Important directive for any code agent:** **Do not modify core logic or domain code** (parsers, retrieval, embeddings, ranking, VLM tools). Your task is to **implement the API layer** and **wire it up** to the existing core application services via clearly defined service interfaces. Any missing interface should be stubbed with TODOs and clear contracts, not implemented with placeholder logic that changes business behavior.

---

## 0. Goals & Scope
- Production-minded FastAPI backend that provides:
  - User authentication (JWT access/refresh via `fastapi-users`).
  - File/PDF upload & ingestion orchestration.
  - CRUD access to documents, pages, figures, tables.
  - Chat creation, message posting, and history retrieval.
  - Search endpoints (text, image, table) that call into core retrieval services.
  - Health & admin endpoints.
- Storage & persistence:
  - Relational DB: PostgreSQL (SQLAlchemy 2.0 async + Alembic).
  - Vector DB: Qdrant/Milvus/Weaviate (IDs stored in Postgres rows).
  - Object storage abstraction (local disk for now; S3-compatible later).
- DevX:
  - Versioned API (`/v1`).
  - OpenAPI-driven TypeScript client generation using `openapi-generator-cli`.

**Out of scope**: Implementing parsing/embeddings/VLM logic. Those are provided by the core app as services.

---

## 1. Architecture & Conventions
- **Framework**: FastAPI, Pydantic v2, async everywhere.
- **Routers**: modular, tagged, and versioned under `/v1`.
- **Auth**: `fastapi-users` with JWT (access/refresh) and password hashing via `passlib[bcrypt]`.
- **DB**: SQLAlchemy async with `asyncpg`; migrations via Alembic.
- **Background jobs**: Celery + Redis (or RQ) for ingestion/indexing ETL.
- **Logging & tracing**: structlog or loguru; optional OpenTelemetry.
- **Security**: CORS, rate limiting (`slowapi`), upload limits, content-type validation.
- **Error model**: JSON Problem Details (RFC 7807 style) or standard FastAPI errors.

### 1.1 Project Layout
```
app/
  core/
    config.py            # BaseSettings for env
    security.py          # JWT, pwd hashing, fastapi-users adapters
    logging.py           # logging/OTel setup
    dependencies.py      # common DI
  db/
    base.py              # engine/session + Base
    models/              # SQLAlchemy models
    schemas/             # Pydantic schemas
    migrations/          # Alembic versions
  services/
    storage.py           # Storage interface (Local/S3)
    embeddings.py        # Facade: text/image/table embeddings (delegates to core)
    ocr.py               # Facade: OCR hooks
    figures.py           # Facade: figure extraction hooks
    tables.py            # Facade: table extraction hooks
    chats.py             # Chat orchestration (delegates to core agent)
    search.py            # Facade: text/image/table search via core retrieval
  routers/
    auth.py
    users.py
    documents.py
    chats.py
    search.py
    admin.py
  workers/
    celery_app.py        # Celery init
    tasks.py             # ETL orchestration (calls core)
  main.py                # app factory, include_routers, lifespan

scripts/
  generate_ts_client.sh

clients/
  ts/                    # generated TypeScript client
```

> **Note:** Routers call into `services/*` which are thin adapters onto core domain services. The code agent must not change domain behavior — only implement adapters and API.

---

## 2. Data Model (PostgreSQL)
**Table: users**
- `id UUID PK`, `email UNIQUE`, `hashed_password`, `is_active BOOL`, `created_at TIMESTAMP`

**Table: documents**
- `id UUID PK`, `owner_id UUID FK users`, `title TEXT`, `status TEXT` (enum: `ingesting|ready|failed`),
  `original_filename TEXT`, `mime TEXT`, `bytes_size BIGINT`, `storage_uri TEXT`, `hash_sha256 TEXT`, `created_at TIMESTAMP`

**Table: pages**
- `id UUID PK`, `document_id UUID FK`, `page_no INT`, `width FLOAT`, `height FLOAT`, `text TEXT NULL`

**Table: chunks** (text spans)
- `id UUID PK`, `document_id UUID FK`, `page_id UUID FK`, `start_char INT`, `end_char INT`,
  `section_path TEXT`, `bbox_json JSONB`, `text TEXT`, `embedding_id UUID NULL`

**Table: figures** (images/diagrams)
- `id UUID PK`, `document_id UUID FK`, `page_id UUID FK`, `figure_no INT`, `bbox_json JSONB`,
  `caption_text TEXT`, `ocr_text TEXT`, `storage_uri TEXT`, `phash TEXT`, `image_embedding_id UUID NULL`

**Table: tables** (structured)
- `id UUID PK`, `document_id UUID FK`, `page_id UUID FK`, `table_no INT`, `bbox_json JSONB`,
  `caption_text TEXT`, `schema_json JSONB`, `data_uri TEXT`, `table_embedding_id UUID NULL`

**Table: embeddings_text / embeddings_image / embeddings_table**
- `id UUID PK`, `provider TEXT`, `dim INT`, `vector_id TEXT` (ID in vector DB), `score_meta JSONB`, `created_at TIMESTAMP`

**Table: chats**
- `id UUID PK`, `owner_id UUID FK users`, `title TEXT`, `created_at TIMESTAMP`

**Table: messages**
- `id UUID PK`, `chat_id UUID FK`, `role TEXT` (`user|assistant|system`), `content JSONB`, `tool_invocations JSONB`, `created_at TIMESTAMP`

**Table: tool_runs**
- `id UUID PK`, `chat_id UUID FK`, `message_id UUID FK`, `tool_name TEXT`, `status TEXT`, `request_payload JSONB`, `response_payload JSONB`, `latency_ms INT`

> Vector DB stores vectors; Postgres stores references (`vector_id`) + provenance.

---

## 3. Storage Abstraction
- Interface: `Storage` with methods `put(bytes, path_hint) -> storage_uri`, `get(storage_uri) -> stream`, `delete(storage_uri)`.
- Implementations: `LocalStorage` now; `S3Storage` later. Persist canonical `storage_uri` on rows.

---

## 4. Auth
- Use `fastapi-users` with JWT auth (access & refresh tokens). Password hashing via `passlib[bcrypt]`.
- Endpoints exposed by `fastapi-users` routers; plug SQLAlchemy user DB adapter.
- Token lifetimes: access ~15m, refresh ~7d (configurable).

---

## 5. Endpoints (v1)
All endpoints require auth unless stated. Use tags and clear response models.

### 5.1 Auth
- `POST /v1/auth/jwt/login` → `{access_token, refresh_token}`
- `POST /v1/auth/jwt/refresh` → `{access_token}`
- `POST /v1/auth/register` → `{user}`

### 5.2 Documents & Files
- `POST /v1/documents:upload` (multipart form: `file`) → `{document_id}`
  - Validates PDF MIME/size; stores via `Storage`; creates `documents` row with `status=ingesting`.
  - Enqueues ETL task `ingest_document(document_id)`.
- `GET /v1/documents/{document_id}` → metadata & status
- `GET /v1/documents/{document_id}/pages` → page list
- `GET /v1/documents/{document_id}/figures` → figures list (id, bbox, caption, storage_uri)
- `GET /v1/documents/{document_id}/tables` → tables list (id, caption, schema, data_uri)
- `DELETE /v1/documents/{document_id}` → soft/hard delete (configurable)

### 5.3 Chats
- `POST /v1/chats` (optional `document_ids: UUID[]`) → `{chat_id}`
- `GET /v1/chats` → user’s chats
- `GET /v1/chats/{chat_id}` → chat info
- `POST /v1/chats/{chat_id}/messages` → posts a user message `{content}`; the API calls core **agent**; stores assistant reply & tool runs
- `GET /v1/chats/{chat_id}/messages?cursor=` → paginated history

### 5.4 Search
- `POST /v1/search/text` → input: `{query, document_ids?, top_k?}`; returns ranked chunks with provenance
- `POST /v1/search/image` → input: `{query_text? , image_id? , image_upload? , top_k?}`; returns ranked figures
- `POST /v1/search/table` → input: `{query, filters?}`; returns table hits (and optional CSV preview)

### 5.5 Admin/Ops
- `POST /v1/documents/{document_id}:reindex` → re-run ETL
- `GET /v1/health` → liveness
- `GET /v1/ready` → readiness (checks DB, vector DB)

---

## 6. Services Contracts (API ↔ Core)
**Important:** The API calls these interfaces only. Implementations are in the core app.

```python
class IngestionService(Protocol):
    async def ingest_document(self, document_id: UUID) -> None: ...  # parse, extract, embed, index

class RetrievalService(Protocol):
    async def search_text(self, user_id: UUID, query: str, doc_ids: list[UUID]|None, top_k: int) -> list[ChunkHit]: ...
    async def search_image(self, user_id: UUID, query_text: str|None, image_bytes: bytes|None, image_id: UUID|None, top_k: int) -> list[FigureHit]: ...
    async def search_table(self, user_id: UUID, query: str, filters: dict|None, top_k: int) -> list[TableHit]: ...

class ChatService(Protocol):
    async def post_message(self, chat_id: UUID, user_id: UUID, content: dict) -> Message: ...  # orchestrates agent loop
```

> The code agent must inject adapters to these Protocols via DI in `dependencies.py`. If implementations are missing, create **stubs** that raise `NotImplementedError` with clear TODOs.

---

## 7. Background Processing
- Celery app in `workers/celery_app.py` (Redis broker); task `ingest_document(document_id)` calls `IngestionService.ingest_document`.
- Fast endpoints return 202 Accepted after enqueue.

---

## 8. Schemas (Pydantic v2 examples)
```python
class DocumentOut(BaseModel):
    id: UUID
    title: str
    status: Literal["ingesting","ready","failed"]
    original_filename: str
    bytes_size: int
    storage_uri: str
    created_at: datetime

class UploadResult(BaseModel):
    document_id: UUID

class ChatCreateIn(BaseModel):
    title: str | None = None
    document_ids: list[UUID] | None = None

class ChatOut(BaseModel):
    id: UUID
    title: str
    created_at: datetime

class MessageIn(BaseModel):
    content: dict  # structured message, include text and optional tool hints

class MessageOut(BaseModel):
    id: UUID
    role: Literal["user","assistant","system"]
    content: dict
    created_at: datetime
```

---

## 9. OpenAPI & TypeScript Client Generation
- Expose OpenAPI at `/openapi.json`.
- Script `scripts/generate_ts_client.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
API_SPEC_URL=${1:-http://localhost:8000/openapi.json}
OUT_DIR=./clients/ts
npx @openapitools/openapi-generator-cli version-manager set 7.6.0
npx @openapitools/openapi-generator-cli generate \
  -i "$API_SPEC_URL" \
  -g typescript-fetch \
  -o "$OUT_DIR" \
  --additional-properties=supportsES6=true,useSingleRequestParameter=true,npmName=@yourorg/ai-docs-client,npmVersion=0.1.0
```

- Add NPM script in consumer repo:
```json
{
  "scripts": { "gen:client": "bash scripts/generate_ts_client.sh http://localhost:8000/openapi.json" },
  "devDependencies": { "@openapitools/openapi-generator-cli": "^2.13.4" }
}
```

---

## 10. Dependencies (Python)
```
fastapi, uvicorn[standard], pydantic
sqlalchemy[asyncio], asyncpg, alembic
fastapi-users[sqlalchemy], passlib[bcrypt]
python-multipart
qdrant-client or pymilvus (choose one)
Pillow, pymupdf, pdfplumber, camelot-py or tabula-py
loguru or structlog
slowapi[redis], redis
opentelemetry-instrumentation-fastapi (optional)
```

---

## 11. Security & Ops
- CORS allowlist; rate limit auth & search endpoints; limit multipart size.
- Health/readiness: DB + vector DB connectivity.
- Structured logging with request IDs; capture latency per endpoint.
- Alembic migrations enforced in CI.

---

## 12. Deployment
- Dockerized services: API, Postgres, Vector DB, Redis, Celery worker, (optional) MinIO.
- Secrets from env; no secrets in repo.

---

## 13. Testing
- Use `httpx.AsyncClient` + pytest for API tests; create DB schema in a test database.
- Stub `IngestionService`, `RetrievalService`, and `ChatService` in tests.

---

## 14. Non-Modification Policy (Repeat)
> **Do not modify core logic or domain code.** The API layer must:
> - expose endpoints & contracts;
> - call core services via interfaces;
> - perform validation, auth, and persistence;
> - never embed, parse, rank, or otherwise change business logic.


# AI Document Analyzer API

FastAPI-based backend for the AI Document Analyzer system, providing document ingestion, search, and chat capabilities.

## Architecture

This API follows a clean architecture pattern:

- **`app/core/`** - Core configuration, security, and dependencies
- **`app/db/`** - Database models, schemas, and migrations
- **`app/services/`** - Business logic facades (thin adapters to core services)
- **`app/routers/`** - API endpoints (v1)
- **`app/workers/`** - Background job processing (Celery)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/docbot

# Auth
SECRET_KEY=your-secret-key-here

# Storage
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./storage

# Vector DB
VECTOR_DB_TYPE=qdrant
QDRANT_URL=http://localhost:6333

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### 4. Start the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

### 5. Start Celery Worker (Optional)

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## API Endpoints

### Authentication (`/v1/auth`)
- `POST /v1/auth/jwt/login` - Login and get JWT tokens
- `POST /v1/auth/jwt/refresh` - Refresh access token
- `POST /v1/auth/register` - Register new user

### Documents (`/v1/documents`)
- `POST /v1/documents:upload` - Upload PDF document
- `GET /v1/documents/{id}` - Get document metadata
- `GET /v1/documents/{id}/pages` - List document pages
- `GET /v1/documents/{id}/figures` - List document figures
- `GET /v1/documents/{id}/tables` - List document tables
- `DELETE /v1/documents/{id}` - Delete document
- `POST /v1/documents/{id}:reindex` - Reindex document

### Chats (`/v1/chats`)
- `POST /v1/chats` - Create new chat
- `GET /v1/chats` - List user's chats
- `GET /v1/chats/{id}` - Get chat details
- `POST /v1/chats/{id}/messages` - Post message and get AI response
- `GET /v1/chats/{id}/messages` - Get message history

### Search (`/v1/search`)
- `POST /v1/search/text` - Search text chunks
- `POST /v1/search/image` - Search figures
- `POST /v1/search/table` - Search tables

### Admin
- `GET /health` - Health check
- `GET /ready` - Readiness check

## TypeScript Client Generation

Generate a TypeScript client from the OpenAPI spec:

```bash
./scripts/generate_ts_client.sh http://localhost:8000/openapi.json
```

The client will be generated in `./clients/ts/`.

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Structure

The API is designed as a thin layer over core business logic:

1. **Routers** handle HTTP requests/responses
2. **Services** are facades that delegate to core application logic
3. **Core logic** (parsing, embeddings, agents) lives in the parent modules

**Important:** Service implementations should NOT contain business logic. They should only:
- Call into existing core services (from `preprocessing/`, `analyzer/`, `agents/`)
- Handle persistence to PostgreSQL
- Coordinate with vector DB and storage

## TODO: Integration Points

The following services need to be wired to existing core modules:

### IngestionService (`app/services/ingestion.py`)
- [ ] Wire to `preprocessing.pdf_extraction.PdfExtractor`
- [ ] Integrate with existing embedding generation
- [ ] Connect to vector DB for indexing

### RetrievalService (`app/services/retrieval.py`)
- [ ] Wire to `analyzer.faiss_wrapper` for text search
- [ ] Wire to `analyzer.woosh_searcher` for hybrid search
- [ ] Implement image and table search

### ChatService (`app/services/chats.py`)
- [ ] Wire to `agents.agent` (LangGraph agent)
- [ ] Integrate tool execution tracking
- [ ] Connect to retrieval for RAG

### EmbeddingsService (`app/services/embeddings.py`)
- [ ] Wire to core text embedding service
- [ ] Wire to core image embedding service
- [ ] Wire to core table embedding service

### Celery Tasks (`app/workers/tasks.py`)
- [ ] Set up async context for Celery workers
- [ ] Wire ingestion task to IngestionService

## Deployment

See the main project documentation for Docker deployment instructions.

## License

See main project LICENSE file.

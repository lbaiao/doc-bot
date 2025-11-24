# Quick Start Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis 7
- Qdrant (vector DB)

## Installation

### 1. Clone and Setup

```bash
cd /home/lucas/dev/doc-bot/api
source venv/bin/activate  # Already created
pip install -r requirements.txt  # Already installed
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DATABASE_URL=postgresql+asyncpg://docbot:docbot_password@localhost:5432/docbot
SECRET_KEY=your-secret-key-here-use-openssl-rand-hex-32
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./storage
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
```

### 3. Start Infrastructure

#### Option A: Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL, Redis, Qdrant)
docker-compose up -d

# Check status
docker-compose ps
```

#### Option B: Local Services

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Start Redis
sudo systemctl start redis

# Start Qdrant
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 4. Initialize Database

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### 5. Start API Server

```bash
# Development mode (auto-reload)
./scripts/dev.sh start

# Or manually:
uvicorn app.main:app --reload --port 8000
```

### 6. Verify Installation

Visit http://localhost:8000/docs to see the API documentation.

Test health endpoint:
```bash
curl http://localhost:8000/health
```

## First Steps

### 1. Register a User

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/v1/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=securepassword123"
```

Save the returned `access_token` for authenticated requests.

### 3. Upload a Document

```bash
TOKEN="your-access-token-here"

curl -X POST http://localhost:8000/v1/documents:upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your/document.pdf"
```

### 4. Create a Chat

```bash
curl -X POST http://localhost:8000/v1/chats \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Chat"}'
```

## Development Commands

```bash
# Start development server
./scripts/dev.sh start

# Run tests
./scripts/dev.sh test

# Create migration
./scripts/dev.sh migration "add new field"

# Apply migrations
./scripts/dev.sh migrate

# Start Celery worker
./scripts/dev.sh worker

# Generate TypeScript client
./scripts/dev.sh generate-client

# Docker commands
./scripts/dev.sh docker-up
./scripts/dev.sh docker-down
```

## Project Structure

```
app/
├── core/          # Config, security, dependencies
├── db/            # Models, schemas, migrations
├── services/      # Business logic facades
├── routers/       # API endpoints
├── workers/       # Background tasks
└── main.py        # FastAPI app

scripts/           # Helper scripts
tests/             # Test suite
storage/           # Local file storage (gitignored)
```

## API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `STORAGE_TYPE` | Storage backend (local/s3) | `local` |
| `LOCAL_STORAGE_PATH` | Local storage directory | `./storage` |
| `QDRANT_URL` | Qdrant vector DB URL | `http://localhost:6333` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `MAX_UPLOAD_SIZE_MB` | Max PDF upload size | `100` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry time | `15` |

## Common Tasks

### Reset Database

```bash
# Drop all tables
alembic downgrade base

# Recreate schema
alembic upgrade head
```

### Run Specific Tests

```bash
pytest tests/test_main.py -v
pytest tests/ -k "health" -v
```

### Check API Routes

```bash
python -c "from app.main import app; \
for route in app.routes: \
    if hasattr(route, 'path'): \
        print(f'{route.methods} {route.path}')"
```

### View Logs

```bash
# Docker logs
docker-compose logs -f api

# Celery logs
docker-compose logs -f celery_worker
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill $(lsof -ti:8000)
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
psql postgresql://docbot:docbot_password@localhost:5432/docbot
```

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

## Next Steps

1. ✅ **Review** `IMPLEMENTATION_SUMMARY.md` for architecture details
2. 🔧 **Integrate** core services (see TODOs in `app/services/`)
3. 🧪 **Test** endpoints using the Swagger UI
4. 📝 **Wire** existing extraction/search/agent logic
5. 🚀 **Deploy** using Docker Compose

## Support

- **API Spec:** `documentation/api_spec.md`
- **README:** `README.md`
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`

## Status

✅ **API Layer Complete** - Ready for integration with core services

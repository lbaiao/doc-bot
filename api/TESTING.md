# 🧪 Testing Guide - Doc-Bot API

## Quick Start (5 minutes)

### 1. Start Infrastructure

```bash
cd /home/lucas/dev/doc-bot/api

# Start all services
docker-compose up -d

# Check everything is running
docker-compose ps
```

**Expected output:**
```
NAME                STATUS              PORTS
api                 Up                  0.0.0.0:8000->8000/tcp
celery_worker       Up                  
postgres            Up (healthy)        0.0.0.0:5432->5432/tcp
qdrant              Up                  0.0.0.0:6333-6334->6333-6334/tcp
redis               Up (healthy)        0.0.0.0:6379->6379/tcp
```

### 2. Run Database Migrations

```bash
# Wait for postgres to be ready
sleep 5

# Run migrations
docker-compose exec api alembic upgrade head
```

### 3. Check API is Running

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status":"ok"}
```

---

## Full Test Flow (15 minutes)

### Step 1: Create a Test User

```bash
# Register
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "is_active": true,
    "is_superuser": false,
    "is_verified": true
  }'
```

**Expected:**
```json
{
  "id": "uuid-here",
  "email": "test@example.com",
  "is_active": true,
  "is_superuser": false,
  "is_verified": true
}
```

### Step 2: Login & Get Token

```bash
# Login
curl -X POST http://localhost:8000/v1/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123!"
```

**Expected:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Save the token:**
```bash
export TOKEN="paste-your-token-here"
```

### Step 3: Upload a PDF

```bash
# Create a test PDF (or use your own)
echo "This is a test PDF content" > test.pdf

# Upload
curl -X POST http://localhost:8000/v1/documents:upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
```

**Expected:**
```json
{
  "document_id": "uuid-here",
  "filename": "test.pdf",
  "status": "ingesting",
  "created_at": "2024-11-24T09:56:47Z"
}
```

**Save the document ID:**
```bash
export DOC_ID="paste-document-id-here"
```

### Step 4: Check Document Status

```bash
# Check status (wait ~30 seconds for processing)
curl -X GET http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Expected (after processing):**
```json
{
  "id": "uuid",
  "filename": "test.pdf",
  "status": "ready",
  "page_count": 1,
  "created_at": "2024-11-24T09:56:47Z"
}
```

### Step 5: Search in Document

```bash
# Text search
curl -X POST http://localhost:8000/v1/search/text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test content",
    "top_k": 5
  }'
```

**Expected:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "text": "This is a test PDF content",
      "score": 0.95,
      "page_id": "uuid"
    }
  ],
  "total": 1
}
```

### Step 6: Create a Chat

```bash
# Create chat
curl -X POST http://localhost:8000/v1/chats \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Chat"
  }'
```

**Expected:**
```json
{
  "id": "uuid",
  "title": "Test Chat",
  "created_at": "2024-11-24T09:56:47Z"
}
```

**Save chat ID:**
```bash
export CHAT_ID="paste-chat-id-here"
```

### Step 7: Send a Message to Chat

```bash
# Send message
curl -X POST http://localhost:8000/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": {
      \"text\": \"Search for 'test' in document $DOC_ID\"
    }
  }"
```

**Expected:**
```json
{
  "id": "uuid",
  "chat_id": "uuid",
  "role": "assistant",
  "content": {
    "text": "I found the following results for 'test'..."
  },
  "created_at": "2024-11-24T09:56:47Z"
}
```

### Step 8: Get Chat History

```bash
# Get messages
curl -X GET http://localhost:8000/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:**
```json
{
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": {"text": "Search for 'test'..."},
      "created_at": "..."
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": {"text": "I found..."},
      "created_at": "..."
    }
  ],
  "total": 2
}
```

---

## Testing with a Real PDF

### Get a Sample PDF

```bash
# Download a sample research paper
wget https://arxiv.org/pdf/1706.03762.pdf -O attention_paper.pdf
```

### Upload & Test

```bash
# Upload
curl -X POST http://localhost:8000/v1/documents:upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@attention_paper.pdf"

# Wait for processing (check logs)
docker-compose logs -f celery_worker

# Once status is "ready", search
curl -X POST http://localhost:8000/v1/search/text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "attention mechanism",
    "top_k": 5
  }'

# Search for figures
curl -X POST http://localhost:8000/v1/search/image \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "architecture diagram",
    "top_k": 3
  }'

# Chat with the document
curl -X POST http://localhost:8000/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": {
      \"text\": \"What is the main contribution of this paper? Use document $DOC_ID\"
    }
  }"
```

---

## Testing Agent Tools Directly

### Option 1: Python Script

Create `test_agent.py`:

```python
import asyncio
from session.db_registry import default_registry
from agents.agent import make_document_agent

async def test_agent():
    # Set user context (replace with real user ID)
    import uuid
    user_id = uuid.uuid4()  # Or get from database
    default_registry.set_user(user_id)
    
    # Set active document (replace with real doc ID)
    doc_id = "your-doc-uuid-here"
    default_registry.ensure(doc_id)
    
    # Create agent
    agent = make_document_agent()
    
    # Test vector search
    from agents.tools import vector_search
    result = vector_search("attention mechanism", k=3)
    print("Vector search result:", result)
    
    # Test text search
    from agents.tools import text_search
    result = text_search("transformer", limit=3)
    print("Text search result:", result)
    
    # Test agent
    response = agent.invoke({
        "messages": [
            {"role": "user", "content": "What is this paper about?"}
        ]
    })
    print("Agent response:", response)

# Run
asyncio.run(test_agent())
```

Run:
```bash
docker-compose exec api python test_agent.py
```

### Option 2: Interactive Shell

```bash
# Enter container
docker-compose exec api bash

# Start Python
python

# In Python:
from session.db_registry import default_registry
from agents.tools import vector_search, text_search
import uuid

# Set context
user_id = uuid.UUID("your-user-id")
doc_id = "your-doc-id"

default_registry.set_user(user_id)
default_registry.ensure(doc_id)

# Test search
result = vector_search("test query", k=5)
print(result)
```

---

## Monitoring & Debugging

### Check Logs

```bash
# All services
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just Celery worker
docker-compose logs -f celery_worker

# Last 100 lines
docker-compose logs --tail=100 api
```

### Check Qdrant Collections

```bash
# List collections
curl http://localhost:6333/collections

# Check text_chunks collection
curl http://localhost:6333/collections/text_chunks

# Check image_embeddings collection
curl http://localhost:6333/collections/image_embeddings
```

### Check Postgres

```bash
# Connect to DB
docker-compose exec postgres psql -U docbot -d docbot

# In psql:
\dt                           # List tables
SELECT * FROM documents;      # View documents
SELECT * FROM pages;          # View pages
SELECT * FROM chunks LIMIT 5; # View chunks
SELECT * FROM figures;        # View figures
\q                            # Quit
```

### Check Redis

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# In redis-cli:
KEYS *                  # List all keys
GET some_key            # Get value
QUIT                    # Exit
```

### Check Storage

```bash
# List stored files
ls -lah storage/

# View file structure
tree storage/
```

---

## Performance Testing

### Load Test with Apache Bench

```bash
# Install ab (if not installed)
# sudo apt-get install apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test search (need to create test.json with auth header)
ab -n 100 -c 5 -p search.json -T application/json \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/search/text
```

### Memory/CPU Usage

```bash
# Check container stats
docker stats

# Check specific container
docker stats api
```

---

## Automated Tests

### Run Unit Tests

```bash
# Run pytest
docker-compose exec api pytest tests/ -v

# With coverage
docker-compose exec api pytest tests/ --cov=app --cov-report=html

# Specific test
docker-compose exec api pytest tests/test_ingestion.py -v
```

### Integration Tests

Create `tests/integration/test_full_flow.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register
        response = await client.post(
            "/v1/auth/register",
            json={"email": "test@test.com", "password": "test123"}
        )
        assert response.status_code == 201
        
        # Login
        response = await client.post(
            "/v1/auth/jwt/login",
            data={"username": "test@test.com", "password": "test123"}
        )
        token = response.json()["access_token"]
        
        # Upload document
        files = {"file": ("test.pdf", b"test content", "application/pdf")}
        response = await client.post(
            "/v1/documents:upload",
            headers={"Authorization": f"Bearer {token}"},
            files=files
        )
        assert response.status_code == 200
        doc_id = response.json()["document_id"]
        
        # Wait for processing...
        # Search
        # etc.
```

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker-compose logs api

# Common issues:
# - Database not ready: Wait longer or check postgres logs
# - Port already in use: Change port in docker-compose.yml
# - Missing env vars: Check .env file
```

### Celery Worker Not Processing

```bash
# Check worker logs
docker-compose logs celery_worker

# Check Redis connection
docker-compose exec celery_worker python -c "
from app.workers.celery_app import celery_app
print(celery_app.connection())
"

# Check for stuck tasks
docker-compose exec redis redis-cli
> KEYS celery*
```

### Qdrant Connection Issues

```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Check from container
docker-compose exec api python -c "
from qdrant_client import QdrantClient
client = QdrantClient(url='http://qdrant:6333')
print(client.get_collections())
"
```

### Ingestion Fails

```bash
# Check celery worker logs
docker-compose logs -f celery_worker

# Check document status
curl -X GET http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# Check storage directory
docker-compose exec api ls -la storage/

# Check extraction directory
docker-compose exec api ls -la extraction/
```

---

## Clean Up

### Stop Everything

```bash
# Stop services
docker-compose down

# Stop and remove volumes (DELETES ALL DATA)
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

### Reset Database

```bash
# Drop all tables
docker-compose exec postgres psql -U docbot -d docbot -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
"

# Re-run migrations
docker-compose exec api alembic upgrade head
```

### Clear Qdrant

```bash
# Delete all collections
curl -X DELETE http://localhost:6333/collections/text_chunks
curl -X DELETE http://localhost:6333/collections/image_embeddings
curl -X DELETE http://localhost:6333/collections/table_embeddings
```

### Clear Storage

```bash
rm -rf storage/*
```

---

## Quick Test Script

Create `quick_test.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Starting Quick Test..."

# Start services
echo "Starting services..."
docker-compose up -d
sleep 10

# Run migrations
echo "Running migrations..."
docker-compose exec -T api alembic upgrade head

# Check health
echo "Checking health..."
curl -f http://localhost:8000/health || exit 1

# Register user
echo "Registering user..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}')
echo $REGISTER_RESPONSE

# Login
echo "Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/jwt/login \
  -d "username=test@example.com&password=test123" | jq -r .access_token)

if [ "$TOKEN" == "null" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Got token: ${TOKEN:0:20}..."

# Upload test PDF
echo "Uploading test PDF..."
echo "Test content" > /tmp/test.pdf
DOC_ID=$(curl -s -X POST http://localhost:8000/v1/documents:upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.pdf" | jq -r .document_id)

echo "✅ Uploaded document: $DOC_ID"

echo "🎉 All tests passed!"
```

Make it executable:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

## Summary

**Basic Test (5 min):**
```bash
docker-compose up -d
docker-compose exec api alembic upgrade head
curl http://localhost:8000/health
```

**Full Test (15 min):**
1. Register user
2. Login
3. Upload PDF
4. Search
5. Chat
6. Check results

**Production Checklist:**
- ✅ All services healthy
- ✅ Migrations run
- ✅ Can upload & process PDFs
- ✅ Search returns results
- ✅ Chat agent responds
- ✅ Qdrant has vectors
- ✅ Postgres has data

Need help with a specific test? Let me know! 🚀

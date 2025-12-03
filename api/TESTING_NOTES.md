# API Testing Notes (December 2025)

## Overview
This project now includes lightweight integration tests that exercise the core API flows (auth, documents, chats) using faked dependencies for storage, ingestion, and chat to keep runs fast and isolated.

## Key Test Additions
- `tests/test_integration.py`
  - Login and create chat
  - Upload PDF → status becomes `ready` (via fake ingestion)
  - Chat message echo flow
- `tests/conftest.py`
  - In‑memory storage fake
  - Fake ingestion (marks doc ready and seeds a stub page)
  - Fake chat service (echoes text instead of invoking the agent)
  - Seeded user: `admin@example.com` / `changeme123!`
  - Dependency overrides applied to the app during tests

## Running Tests
Set `TEST_DATABASE_URL` to a reachable database. Examples:
```bash
# Postgres (matches docker-compose defaults)
export TEST_DATABASE_URL=postgresql+asyncpg://docbot:docbot_password@localhost:5432/docbot

# Or SQLite file (no external services)
export TEST_DATABASE_URL=sqlite+aiosqlite:///./test.db

cd api
venv/bin/pytest
```

## Defaults & Credentials
- Seeded test user: `admin@example.com` / `changeme123!`
- Default `TEST_DATABASE_URL` if unset: `postgresql+asyncpg://docbot:docbot_password@localhost:5432/docbot`

## Known Limitations
- Tests require a reachable DB; if the environment blocks sockets or file-based SQLite, pytest will hang at startup.
- Image/table ingestion and real agent calls are faked in tests to keep runs deterministic.

## Relevant Files
- Tests: `tests/test_integration.py`, `tests/test_main.py`
- Fixtures/Fakes: `tests/conftest.py`
- Registry fixes: `session/db_registry.py`
- Chat error handling: `app/services/chats.py`

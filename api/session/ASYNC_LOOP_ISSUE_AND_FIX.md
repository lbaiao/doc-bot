# Async Loop Issue in `DBSessionRegistry.ensure`: Root Cause and Fix

## Summary

When `POST /v1/chats/{chat_id}/messages` called `default_registry.ensure(...)` from async FastAPI code, the request failed with:

`RuntimeError: Cannot run the event loop while another loop is running`

This happened because the registry method was written as a synchronous API that internally created/runs an event loop (`run_until_complete`) even when called from code that already runs inside an active event loop (Uvicorn/FastAPI).

## What Caused the Error

### Original behavior

- `DBSessionRegistry.ensure(document_id)` is synchronous.
- It validated document readiness by building an async coroutine and running it via `_run_sync(...)`.
- `_run_sync(...)` created a new event loop and called `run_until_complete(...)` in same thread in the common path.

### Why this fails in FastAPI endpoints

- FastAPI endpoint handlers are async and run inside Uvicorn's already-running loop.
- Calling `run_until_complete(...)` from code already executing inside that loop is not allowed.
- Python/uvloop raises the exact runtime error we observed.

## Why We Still Need Sync + Async Support

`DBSessionRegistry` is used from two different contexts:

1. Async request/service code (`api/app/routers/chats.py`, `api/app/services/chats.py`)
2. Synchronous LangChain tools (`api/agents/tools.py`) where `set_active_document` is sync and expects sync registry methods

So we cannot simply make everything sync or everything async without breaking one of those integration points.

## Fix Implemented

### 1. Added async-safe path

- New method: `DBSessionRegistry.ensure_async(document_id)`
- It performs the same readiness checks but uses direct `await` instead of loop-spinning.

### 2. Shared core validation logic

- New internal method: `DBSessionRegistry._check_document_ready(document_id)`
- Async function that:
  - Validates UUID format
  - Loads `Document` from DB
  - Verifies it exists
  - Verifies status is `ready`

Both `ensure` and `ensure_async` call this shared method.

### 3. Kept sync compatibility

- Existing `ensure(document_id)` remains for sync callers (agent tools).
- It now wraps only the shared async checker via `_run_sync(...)`.
- This preserves old tool-facing behavior without breaking existing tool interfaces.

### 4. Updated async call sites

- `api/app/routers/chats.py`
  - `default_registry.ensure(...)` -> `await default_registry.ensure_async(...)`
- `api/app/services/chats.py`
  - `default_registry.ensure(...)` -> `await default_registry.ensure_async(...)`

This removes nested loop attempts in request-path async code.

## Design Principle

Use:

- `ensure_async(...)` from async code (FastAPI handlers, async services)
- `ensure(...)` from sync code (tools, non-async wrappers)

Avoid calling sync wrappers that spin event loops from inside already-running async request loops.

## Expected Outcome

- No more `Cannot run the event loop while another loop is running` on chat message requests.
- Existing sync tools continue to work without interface changes.
- Registry behavior (document existence/status validation + active context setup) stays consistent across sync/async callers.

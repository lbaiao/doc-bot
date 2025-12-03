# AI Agent Integration Notes

Summary of changes to wire the agent into the HTTP chat flow and CLI.

What was done
- Hooked the FastAPI chat endpoint to the agent:
  - `app/routers/chats.py` now delegates to `ChatService.post_message`.
  - `app/services/chats.py` normalizes user content, supports optional `document_id`, builds agent messages (adds a system primer), sets user + active document in the DB-backed registry, invokes the agent, and stores assistant replies and tool runs (stub for now).
- Updated agent/tool stack to use DB/Qdrant instead of local files:
  - `agents/tools.py`: `set_active_document` now accepts a document UUID; uses `session.db_registry.default_registry`; keeps search/chunk/caption/image analysis tools.
  - `agents/agent.py`: injects Anthropic key from config, includes `set_active_document` in the tool list, uses `claude-haiku` with retries.
- Added a Typer CLI with interactive chat:
  - `cli/main.py`, `cli/config.py`, `cli/requirements.txt` (Rich for formatting).
  - Commands for login, upload, status, search (text/image/table), chat create/send/history, and `chat-loop` (interactive) with optional `--document-id` and `--show-thoughts`.
- Image embedding cleanup:
  - `app/services/ingestion.py` deletes existing image embeddings for a document before upserting new ones to avoid stale/None `figure_id` payloads.
  - `app/services/vector_db.py` adds a helper to delete image embeddings by document filter.

How to run the CLI (from repo root)
```bash
pip install -r cli/requirements.txt
python -m cli.main login         # prompt email/password, save token to ~/.docbot/config.json
python -m cli.main upload path/to/file.pdf
python -m cli.main status <doc_id>
python -m cli.main search-text --doc <doc_id> "query"
python -m cli.main chat-loop --document-id <doc_id>   # interactive chat
```

If you prefer to sit inside the `cli/` folder, run `python main <command>` (wrapper) or `PYTHONPATH=.. python main.py <command>` so Python can find the package now that it lives at the project root.

Default login helper
- Seeded user defaults: `admin@example.com` / `changeme123!`
- Quick login: `python -m cli.main login --use-default`

Notes / expectations
- The agent uses the DB/Qdrant-backed registry (`session/db_registry.py`) for search and retrieval tools.
- `document_id` should be supplied (e.g., in chat content or via CLI `--document-id`) so tools know which doc to target.
- Tool run persistence is stubbed; if you need full trace logging, we can extract tool calls from the agent response and store them in `tool_runs`.
- The backend still needs a `/v1/files` proxy if clients should fetch `storage_uri` assets via HTTP.

Next steps (optional)
- Persist tool runs from agent responses (parse tool calls).
- Add a download proxy route for `storage_uri`.
- Enhance image caption extraction quality (bitmap captions vs. vector captions) and reingest docs after fixes.

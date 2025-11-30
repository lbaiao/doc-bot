# CLI Integration (Python + Typer)

Assumptions
- CLI in Python with Typer.
- Token stored locally (e.g., `~/.docbot/config.json`) containing `{ "base_url": "...", "token": "..." }`.
- Uses generated models (optional) from OpenAPI via `datamodel-code-generator`, or simple typed dicts.

Setup
1) Install deps: `pip install typer requests`
2) Fetch OpenAPI: `curl -o openapi.json http://localhost:8000/openapi.json`
3) (Optional) Generate Pydantic models: `datamodel-code-generator --input openapi.json --input-file-type openapi --output cli_models.py`

Config
- Default `base_url`: `http://localhost:8000`
- Config file: `~/.docbot/config.json` with `base_url` and `token`
- Flags override config: `--base-url`, `--token`

Commands (suggested)
- `login`: prompt email/password → `POST /v1/auth/jwt/login`; save token in config.
- `upload <pdf_path>`: `POST /v1/documents:upload` multipart; print `document_id`.
- `status <document_id>`: `GET /v1/documents/{id}`; print `status`, `title`.
- `search text --doc <id> --query "<q>" --top-k 5`: `POST /v1/search/text`; print hits (score, page_id, snippet).
- `search image --doc <id> --query "<caption>" --top-k 5`: `POST /v1/search/image`; print hits (score, figure_id, caption, storage_uri).
- `search table --doc <id> --query "<q>" --top-k 5`: `POST /v1/search/table`; print hits (score, table_id, caption).
- `chat create --title "..."`: `POST /v1/chats`; print chat_id.
- `chat send --chat-id <id> --message "..."`: `POST /v1/chats/{id}/messages`; print assistant reply (if wired).
- `chat history --chat-id <id>`: `GET /v1/chats/{id}/messages`; print ordered messages.

Implementation notes
- Wrap HTTP calls with a helper that injects the bearer token; raise on non-2xx.
- For uploads, use `requests` multipart form. For other calls, JSON bodies.
- Handle 401 by prompting re-login; handle 404 with clear doc/chat identifiers.
- Consider 600 permissions on the config file for token storage.

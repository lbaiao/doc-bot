# Backend Integration (Generic Clients)

Base URL and health
- API base: `http(s)://<host>:8000`
- Health: `GET /health` (liveness), readiness: `GET /ready`

Auth
- JWT via fastapi-users.
- Register: `POST /v1/auth/register`
- Login: `POST /v1/auth/jwt/login` → `{ access_token }`
- Send `Authorization: Bearer <token>` on all protected endpoints.

Core flows
1) Upload PDF  
   - `POST /v1/documents:upload` (multipart `file`). Response: `{ document_id }`.
2) Poll status  
   - `GET /v1/documents/{id}` until `status == "ready"`.
3) Browse document artifacts  
   - Pages: `GET /v1/documents/{id}/pages`  
   - Figures: `GET /v1/documents/{id}/figures`  
   - Tables: `GET /v1/documents/{id}/tables`
4) Search  
   - Text: `POST /v1/search/text` `{ query, document_ids?, top_k? }`  
   - Image (caption-based): `POST /v1/search/image` `{ query_text, top_k? }`  
   - Table: `POST /v1/search/table` `{ query, filters?, top_k? }`
5) Chat  
   - Create chat: `POST /v1/chats` `{ title? }`  
   - Send message: `POST /v1/chats/{chat_id}/messages` `{ content: string | object }`  
   - History: `GET /v1/chats/{chat_id}/messages`

Storage URIs
- Figures/tables reference `storage_uri` (e.g., `local://figures/...`). Expose a download proxy (recommended): `GET /v1/files?uri=<storage_uri>` that streams the file or redirects (for S3/signed URLs). Clients should call the proxy; avoid handling `local://` directly in frontends.

OpenAPI and codegen
- OpenAPI spec: `GET /openapi.json`.
- Generate types/clients from OpenAPI to keep routes and models in sync (see per-client sections).

Errors
- Standard HTTP codes. 400 for bad input, 401/403 for auth, 404 for missing doc/chat. Include payload content in error handling/logs for clarity.

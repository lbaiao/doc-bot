# Web Integration (React + TypeScript + TanStack Query + fetch)

Assumptions
- React + TypeScript.
- TanStack React Query for data fetching/caching.
- Plain fetch wrapper with bearer token injection.
- Use generated API types/hooks via Orval (OpenAPI-driven).

Codegen
1) Fetch OpenAPI: `curl -o openapi.json http://localhost:8000/openapi.json`
2) Install Orval: `npm i -D orval`
3) Configure `orval.config.js`:
```js
module.exports = {
  docbot: {
    input: './openapi.json',
    output: {
      client: 'fetch',
      mode: 'split',
      target: './src/api/generated.ts',
      override: {
        mutator: { path: './src/api/fetcher.ts', name: 'customFetcher' },
      },
    },
  },
};
```
4) `src/api/fetcher.ts` (inject token):
```ts
export const customFetcher = async <T>({ url, method, headers, body }: any) => {
  const token = localStorage.getItem('docbot_token'); // swap for httpOnly/cookie if you add a proxy
  const res = await fetch(url, {
    method,
    headers: {
      ...(headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
  });
  if (!res.ok) throw await res.json();
  return (await res.json()) as T;
};
```
5) Run `npx orval` to generate typed hooks/endpoints.

Auth
- Forms for register (`/v1/auth/register`) and login (`/v1/auth/jwt/login`).
- Store access token in memory/localStorage (or switch to backend cookie proxy).
- On 401, clear token and redirect to login.

Views / flows
- Upload:
  - Form: select PDF → `POST /v1/documents:upload`.
  - After upload, poll `/v1/documents/{id}` (React Query + `refetchInterval`) until `status === "ready"`.
  - Show `document_id`, status, and actions to browse/search.
- Browse:
  - Pages: `GET /v1/documents/{id}/pages`
  - Figures: `GET /v1/documents/{id}/figures`
  - Tables: `GET /v1/documents/{id}/tables`
  - For figure/table assets, call your download proxy: `GET /v1/files?uri=<storage_uri>`; render images from that URL.
- Search:
  - Text: form `{ query, doc ids, top_k }` → `/v1/search/text`; render hits (score, page link, snippet).
  - Image (caption-based): `{ query_text, top_k }` → `/v1/search/image`; render figure cards (score, caption, image via proxy).
  - Table: `{ query, filters?, top_k }` → `/v1/search/table`; render caption/schema summary.
- Chat:
  - Create chat: `POST /v1/chats`
  - Messages: `POST /v1/chats/{id}/messages` and `GET /v1/chats/{id}/messages`
  - UI: chat list, message thread, composer. (Assistant responses are stubbed until agent wiring is complete.)

Storage proxy
- Implement a backend route (e.g., `GET /v1/files?uri=<storage_uri>`) to stream files referenced by `storage_uri`.
- In the web app, map `storage_uri` to that route; avoid exposing `local://` directly.

Error handling
- Show inline errors from failed fetches (400/401/404).
- Retry logic via React Query (backoff) where sensible; disable retries on auth failures.

Env/config
- Centralize `API_BASE_URL` and token access in the fetcher.
- Build-time env (VITE_/NEXT_PUBLIC_) to point to the backend URL per environment.

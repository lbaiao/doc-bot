love it — here’s a crisp, production-minded frontend plan for your PDF-centric chat app, in **React + TypeScript**.

# UX flow (end-to-end)

1. **Auth → Home (Upload)**

   * User logs in/signs up → lands on a friendly drag-and-drop PDF uploader.
   * On successful upload, backend returns a new **chat session id**.
2. **Chat**

   * App routes to `/app/s/:sessionId` with a **ChatGPT-style** UI.
   * Left sidebar lists sessions; each session expandable to show **PDF Viewer** and **Images Gallery** actions.
   * Messages stream (SSE/WebSocket). All messages scoped to that session/document.
3. **Utilities**

   * Modal **PDF viewer** for the original file.
   * Modal **Image gallery** (with metadata). Supports **uploading new images** with title & description.

---

# Routing (React Router)

* `/login`, `/signup`
* `/app` → protected layout (with sidebar)

  * `/app/home` → upload page
  * `/app/s/:sessionId` → chat page
  * `/app/settings`

> Redirect `/` → `/app/home` if authed; otherwise → `/login`.

---

# Component architecture (key pieces)

**Layouts**

* `AppLayout`

  * `Sidebar` (sessions list, new chat, settings, delete)
  * `Topbar` (user menu, search, quick actions)
  * `Outlet` (Chat or Home)

**Auth**

* `LoginForm`, `SignupForm`

**Home / Upload**

* `PdfUploadCard` (drag-drop + progress + file validation)
* `RecentSessions` (optional)

**Chat**

* `ChatView`

  * `MessageList` (virtualized)
  * `Composer` (textarea, send, attach image)
  * `CitationsBar` (optional: show page/figure badges used)

**Sidebar (ChatGPT-like)**

* `SessionList`

  * `SessionItem` (collapsible)

    * Buttons: **Open PDF**, **Open Images**
    * Sub-Dir: Images list (thumbnail + metadata)
* `NewChatButton`, `DeleteChatButton`, `SettingsButton`

**Modals**

* `PdfViewerModal` (react-pdf/pdfjs; page nav, zoom, thumbnails)
* `ImageGalleryModal` (grid + detail drawer)

  * `ImageCard` (thumbnail, title, description, tags, metadata)
  * `ImageUpload` (file picker, title, description)

**State/infra**

* `useAuth` (auth guard)
* `useSessions`, `useMessages`, `useImages`, `usePdf` (React Query hooks)
* `useUIStore` (Zustand) for UI bits (which modal is open, expanded session ids, etc.)

---

# State management

* **Server state:** **React Query** (tanstack) for fetching, caching, optimistic updates (sessions, messages, images, pdf meta).
* **Client/UI state:** **Zustand** for lightweight local store: modal visibility, selected image, expanded sidebar items, toast queue.
* **Streaming:** SSE or WebSocket → push tokens into the current message in `MessageList`.
* **Persistence:** Keep last open session id in URL + `localStorage`.

---

# Data models (TypeScript)

```ts
// session
export type Session = {
  id: string;
  title: string;           // auto from PDF title or first H1
  createdAt: string;
  updatedAt: string;
  document: {
    id: string;
    name: string;
    pages: number;
    sizeBytes: number;
    mime: 'application/pdf';
    url?: string;          // signed URL for viewer (fetched on demand)
  };
};

// chat message
export type ChatMessage = {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;         // markdown
  attachments?: Array<{ type: 'image'; imageId: string }>;
  citations?: Array<{ type: 'page' | 'figure' | 'table'; ref: string; page?: number }>;
  createdAt: string;
  streaming?: boolean;
};

// image metadata
export type DocImage = {
  id: string;
  sessionId: string;
  title: string;
  description?: string;
  page: number;
  bbox?: [number, number, number, number]; // x,y,w,h in PDF coords
  width?: number;
  height?: number;
  contentType: string;     // e.g., 'image/png'
  sizeBytes: number;
  url?: string;            // signed URL (fetched lazily)
  vectors?: { model: string; dim: number }[];
  createdAt: string;
  source: 'extracted' | 'uploaded';
};

// table summary for UI (optional)
export type DocTable = {
  id: string;
  sessionId: string;
  title?: string;
  page: number;
  nRows: number;
  nCols: number;
  previewCsvUrl?: string;
};
```

---

# API contracts (frontend expectations)

**Auth**

* `POST /auth/login` → `{token}` (or httpOnly cookie)
* `POST /auth/signup` → `{token}`

**Sessions**

* `GET /sessions` → `Session[]`
* `POST /sessions` with `{pdfUploadSignedUrl}` (or direct file upload flow) → `Session`
* `DELETE /sessions/:id`

**PDF**

* `GET /sessions/:id/pdf` → `{signedUrl, pages, name, sizeBytes}`
  (Viewer fetches PDF bytes via signed URL)

**Images**

* `GET /sessions/:id/images` → `DocImage[]`
* `POST /sessions/:id/images` (multipart) with `file`, `title`, `description` → `DocImage`
* `GET /images/:imageId/url` → `{signedUrl}`
* (Optional) `PATCH /images/:imageId` for title/description edits
* (Optional) pagination for large galleries

**Messages**

* `GET /sessions/:id/messages?cursor=...` → paginated list
* `POST /sessions/:id/messages` → starts **SSE/WebSocket** stream (assistant response)

**Utilities**

* `POST /sessions/:id/actions/open-pdf` (touch to issue a fresh signed URL)
* `POST /sessions/:id/actions/reindex` (if you expose maintenance ops)

> Upload flow: request **signed URL** → PUT file to storage (S3/GCS) → `POST /sessions` with file key → backend kicks off preprocessing → frontend polls session status or gets a webhook/signal to enable chat.

---

# Streaming UX (assistant)

* Use SSE (EventSource) or WS.
* In `MessageList`, render a **streaming bubble** with token accumulation and a tiny spinner.
* On complete, store final message and citations.
* Handle **tool events** (e.g., “Looking at Fig. 2…”) as lightweight system messages for transparency.

---

# PDF viewer modal

* Use `react-pdf` (pdfjs) with: page thumbnails, zoom, “open current page in chat” action.
* When a citation references `page=3`, clicking the badge opens this modal scrolled to page 3.
* Lazy load the signed URL on open; revoke object URLs on close.

---

# Image gallery modal

* Grid with infinite scroll.
* Sidebar/drawer for metadata (title, description, page, dims, size, source, createdAt).
* **Upload new image** (top-right): drag-drop → title & description → `POST /images` → optimistic add.
* **Filter/sort** (page number, source, createdAt).

---

# Composer (chat input)

* Large text area with submit on Cmd/Ctrl+Enter.
* “Attach image” allows picking from the gallery or uploading a **new image** ad-hoc (same flow as gallery).
* Show token/char counter (optional).
* Disable send while a response is streaming (or queue).

---

# Sidebar behaviors

* Sessions list (virtualized if needed).
* Each `SessionItem` is **collapsible**; on expand, show:

  * **Open PDF Viewer** (modal)
  * **Open Images** (modal)
  * (Optional) quick stats: pages, #images, #tables
* Context menu: Rename session, Duplicate, Delete (confirm).

---

# Styling & theming

* Tailwind + shadcn/ui for fast, consistent UI.
* Dark mode toggle.
* Ensure **focus states** and a11y labels for modals, lists, and buttons.

---

# Performance & resilience

* Virtualize message list and session list.
* Cache signed URLs per modal open; never store them long-term.
* Retry on transient upload/stream errors; show toasts.
* Guard routes; skeleton loaders for chat and modals.

---

# Testing

* Component tests (React Testing Library), routing guards, streaming reducer tests.
* Cypress e2e: login → upload → chat → open PDF → open images → upload new image → stream answer.

---

## Nice-to-haves (later)

* Global search across sessions.
* Per-message “view sources” panel (page/figure popovers).
* Shareable read-only links for a session.

---

If you want, I can next sketch a file/folder structure and key components’ prop signatures, or produce a minimal React Router + Query + Zustand scaffold you can drop into a repo.

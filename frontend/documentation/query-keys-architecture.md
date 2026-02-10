# React Query Key Architecture

## Purpose

TanStack React Query keys are centralized to a single source of truth so key shape is consistent across:

- `useQuery`
- `invalidateQueries`
- future cache operations (`setQueryData`, `getQueryData`, etc.)

This prevents cache misses caused by typo or key-shape drift.

## Source of Truth

All query keys live in:

- `frontend/src/lib/query-keys.ts`

## Key Design Rules

1. Use root constants for domains (`chats`, `messages`, `document`, etc.).
2. Expose keys through helper functions in `queryKeys`.
3. Use helpers everywhere instead of inline array literals.
4. Keep key order stable and deterministic.

## Current Query Keys

- `queryKeys.chats()` -> `['chats']`
- `queryKeys.messages(sessionId)` -> `['messages', sessionId]`
- `queryKeys.document(documentId)` -> `['document', documentId]`
- `queryKeys.pdfBlob(documentId)` -> `['pdf-blob', documentId]`
- `queryKeys.figures(documentId)` -> `['figures', documentId]`

## Usage Examples

### Query

```ts
useQuery({
  queryKey: queryKeys.messages(sessionId),
  queryFn: fetchMessages,
});
```

### Invalidation

```ts
queryClient.invalidateQueries({ queryKey: queryKeys.chats() });
```

## Adding New Keys

1. Add a root in `QUERY_KEY_ROOTS`.
2. Add a helper function in `queryKeys`.
3. Replace inline key literals in feature code with the helper.

Do not introduce ad-hoc `queryKey: ['...']` literals in feature files.

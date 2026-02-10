export const QUERY_KEY_ROOTS = {
  chats: 'chats',
  messages: 'messages',
  document: 'document',
  pdfBlob: 'pdf-blob',
  figures: 'figures',
} as const;

export const queryKeys = {
  chats: () => [QUERY_KEY_ROOTS.chats] as const,
  messages: (sessionId: string | undefined) => [QUERY_KEY_ROOTS.messages, sessionId] as const,
  document: (documentId: string | undefined) => [QUERY_KEY_ROOTS.document, documentId] as const,
  pdfBlob: (documentId: string | undefined) => [QUERY_KEY_ROOTS.pdfBlob, documentId] as const,
  figures: (documentId: string | undefined) => [QUERY_KEY_ROOTS.figures, documentId] as const,
} as const;

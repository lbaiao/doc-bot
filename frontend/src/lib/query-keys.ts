export const QUERY_KEY_ROOTS = {
  chats: 'chats',
  messages: 'messages',
  document: 'document',
  pdfBlob: 'pdf-blob',
  figures: 'figures',
  fileBlob: 'file-blob',
} as const;

export const queryKeys = {
  chats: () => [QUERY_KEY_ROOTS.chats] as const,
  messages: (sessionId: string | undefined) => [QUERY_KEY_ROOTS.messages, sessionId] as const,
  document: (documentId: string | undefined) => [QUERY_KEY_ROOTS.document, documentId] as const,
  pdfBlob: (documentId: string | undefined) => [QUERY_KEY_ROOTS.pdfBlob, documentId] as const,
  figures: (documentId: string | undefined) => [QUERY_KEY_ROOTS.figures, documentId] as const,
  fileBlob: (src: string | undefined) => [QUERY_KEY_ROOTS.fileBlob, src] as const,
} as const;

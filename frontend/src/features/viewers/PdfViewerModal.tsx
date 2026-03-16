import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';

// Setup pdf worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString();

export function PdfViewerModal({
    isOpen,
    onClose,
    documentId,
    initialPage = 1
}: {
    isOpen: boolean;
    onClose: () => void;
    documentId: string;
    initialPage?: number;
}) {
    const [pageNumber, setPageNumber] = useState(initialPage);
    const [numPages, setNumPages] = useState<number | null>(null);

    // Fetch signed URL or stream
    // Since Generic API doesn't have a direct "get signed url" for viewer,
    // we might need to proxy or use a specific endpoint. 
    // Spec said: GET /sessions/:id/pdf -> {signedUrl}
    // Backend says: GET /v1/documents/:id -> storage_uri
    // We will assume there is a file proxy at /v1/files?uri=... or similar as per integration_generic.md
    // OR we just use a blob URL if we fetch it.

    // For now, let's try to fetch document metadata to get storage_uri, then construct a fetch url
    const { data: doc } = useQuery({
        queryKey: queryKeys.document(documentId),
        queryFn: async () => {
            const res = await apiClient.get(`/v1/documents/${documentId}`);
            return res.data;
        },
        enabled: isOpen && !!documentId
    });


    // IMPORTANT: Access token needs to be passed to headers for `react-pdf` to fetch protected PDF
    // But react-pdf options are limited. We might need to fetch blob first.
    // Simplifying: assume we can fetch blob.

    const { data: pdfBlobValues } = useQuery({
        queryKey: queryKeys.pdfBlob(documentId),
        queryFn: async () => {
            if (!doc) return null;
            // We'll use our apiClient to fetch the bytes, handling Auth header
            const res = await apiClient.get('/v1/files', {
                params: { uri: doc.storage_uri },
                responseType: 'blob'
            });
            return res.data;
        },
        enabled: !!doc
    });

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
        setNumPages(numPages);
        setPageNumber(initialPage);
    }

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl h-[90vh] overflow-hidden flex flex-col p-0">
                <div className="flex items-center justify-between p-2 border-b">
                    <h3 className="font-semibold px-2">{doc?.title || 'Document'}</h3>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="icon"
                            disabled={pageNumber <= 1}
                            onClick={() => setPageNumber(p => p - 1)}
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span className="text-sm">
                            {pageNumber} / {numPages || '--'}
                        </span>
                        <Button
                            variant="outline"
                            size="icon"
                            disabled={!numPages || pageNumber >= numPages}
                            onClick={() => setPageNumber(p => p + 1)}
                        >
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                <div className="flex-1 bg-muted/20 overflow-auto flex justify-center p-4">
                    {!pdfBlobValues ? (
                        <div className="flex items-center gap-2">
                            <Loader2 className="animate-spin" /> Loading PDF...
                        </div>
                    ) : (
                        <Document
                            file={pdfBlobValues}
                            onLoadSuccess={onDocumentLoadSuccess}
                            className="shadow-lg"
                        >
                            <Page
                                pageNumber={pageNumber}
                                renderTextLayer={false}
                                renderAnnotationLayer={false}
                                width={800} // responsive width?
                            />
                        </Document>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

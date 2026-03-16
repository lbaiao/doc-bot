import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { AuthImage } from '@/components/ui/auth-image';
import { queryKeys } from '@/lib/query-keys';

export function ImageGalleryModal({ isOpen, onClose, documentId }: { isOpen: boolean; onClose: () => void; documentId: string }) {
    const { data: figures } = useQuery({
        queryKey: queryKeys.figures(documentId),
        queryFn: async () => {
            const res = await apiClient.get(`/v1/documents/${documentId}/figures`);
            return res.data;
        },
        enabled: isOpen && !!documentId
    });

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-5xl h-[80vh] overflow-auto">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4">
                    {figures?.map((fig: any) => (
                        <div key={fig.id} className="border rounded p-2">
                            <AuthImage
                                src={`/v1/files?uri=${encodeURIComponent(fig.storage_uri)}`}
                                alt={`Figure ${fig.figure_no}`}
                                className="w-full h-auto object-contain"
                            />
                            <p className="text-sm mt-2 text-muted-foreground">{fig.caption_text}</p>
                        </div>
                    ))}
                </div>
            </DialogContent>
        </Dialog>
    );
}

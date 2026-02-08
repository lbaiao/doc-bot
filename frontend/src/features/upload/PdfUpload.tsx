import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function PdfUpload() {
    const navigate = useNavigate();
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (!file) return;

        setUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            // 1. Upload Document
            // Note: endpoint is /v1/documents:upload (colon!)
            const uploadRes = await apiClient.post('/v1/documents:upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            const { document_id } = uploadRes.data;

            // 2. Create Chat linked to validation
            // We pass document_ids even if backend might ignore it for now (per plan)
            const chatRes = await apiClient.post('/v1/chats', {
                title: file.name.replace('.pdf', ''),
                document_ids: [document_id],
            });
            const chat = chatRes.data;

            // 3. Redirect to chat
            navigate(`/app/s/${chat.id}`);

        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || 'Upload failed');
            setUploading(false);
        }
    }, [navigate]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'] },
        maxFiles: 1,
        disabled: uploading,
    });

    return (
        <Card className="w-full max-w-xl mx-auto mt-10">
            <CardContent className="p-6">
                <div
                    {...getRootProps()}
                    className={cn(
                        "border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors",
                        isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
                        uploading && "opacity-50 cursor-not-allowed"
                    )}
                >
                    <input {...getInputProps()} />

                    <div className="flex flex-col items-center justify-center gap-4">
                        <div className="p-4 bg-muted rounded-full">
                            {uploading ? (
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            ) : (
                                <Upload className="h-8 w-8 text-muted-foreground" />
                            )}
                        </div>

                        <div className="space-y-2">
                            <h3 className="font-semibold text-lg">
                                {uploading ? "Processing..." : "Upload PDF"}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                {uploading
                                    ? "Analyzing document structure..."
                                    : "Drag and drop your PDF here, or click to select"}
                            </p>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 text-destructive text-sm mt-2">
                                <AlertCircle className="h-4 w-4" />
                                <span>{error}</span>
                            </div>
                        )}

                        {!uploading && (
                            <Button variant="secondary" className="mt-2">
                                Select File
                            </Button>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

import { PdfUpload } from '@/features/upload/PdfUpload';

export function HomeView() {
    return (
        <div className="space-y-8">
            <div className="flex flex-col space-y-2 text-center">
                <h1 className="text-3xl font-bold tracking-tighter">New Analysis</h1>
                <p className="text-muted-foreground">
                    Upload a PDF document to start chatting and extracting insights.
                </p>
            </div>
            <PdfUpload />
        </div>
    );
}

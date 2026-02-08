import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Loader2, ImageOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AuthImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    src: string; // The API endpoint URI (e.g. /v1/files?uri=...)
}

export function AuthImage({ src, className, alt, ...props }: AuthImageProps) {
    const [imgSrc, setImgSrc] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let active = true;
        setLoading(true);
        setError(false);

        apiClient.get(src, { responseType: 'blob' })
            .then((res) => {
                if (active) {
                    const url = URL.createObjectURL(res.data);
                    setImgSrc(url);
                    setLoading(false);
                }
            })
            .catch((err) => {
                console.error("Failed to load image", src, err);
                if (active) {
                    setError(true);
                    setLoading(false);
                }
            });

        return () => {
            active = false;
            if (imgSrc) URL.revokeObjectURL(imgSrc);
        };
    }, [src]);

    if (loading) {
        return (
            <div className={cn("flex items-center justify-center bg-muted/20", className)}>
                <Loader2 className="animate-spin h-6 w-6 text-muted-foreground" />
            </div>
        );
    }

    if (error || !imgSrc) {
        return (
            <div className={cn("flex items-center justify-center bg-muted/20 text-muted-foreground", className)}>
                <ImageOff className="h-6 w-6" />
            </div>
        );
    }

    return (
        <img
            src={imgSrc}
            alt={alt}
            className={className}
            {...props}
        />
    );
}

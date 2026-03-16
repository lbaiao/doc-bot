import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { Loader2, ImageOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/query-keys';

interface AuthImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    src: string; // The API endpoint URI (e.g. /v1/files?uri=...)
}

export function AuthImage({ src, className, alt, ...props }: AuthImageProps) {
    const [imgSrc, setImgSrc] = useState<string | null>(null);

    const { data: blob, isLoading, isError } = useQuery({
        queryKey: queryKeys.fileBlob(src),
        queryFn: async () => {
            const res = await apiClient.get(src, { responseType: 'blob' });
            return res.data as Blob;
        },
        enabled: !!src,
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 30,
    });

    useEffect(() => {
        if (!blob) {
            setImgSrc(null);
            return;
        }

        const objectUrl = URL.createObjectURL(blob);
        setImgSrc(objectUrl);

        return () => {
            URL.revokeObjectURL(objectUrl);
        };
    }, [blob]);

    if (isLoading) {
        return (
            <div className={cn("flex items-center justify-center bg-muted/20", className)}>
                <Loader2 className="animate-spin h-6 w-6 text-muted-foreground" />
            </div>
        );
    }

    if (isError || !imgSrc) {
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

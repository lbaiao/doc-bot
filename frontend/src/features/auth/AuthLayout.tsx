export function AuthLayout({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/50 p-4">
            <div className="w-full max-w-md space-y-6">
                <div className="space-y-2 text-center">
                    <h1 className="text-3xl font-bold tracking-tighter">{title}</h1>
                    {subtitle && <p className="text-gray-500 dark:text-gray-400">{subtitle}</p>}
                </div>
                {children}
            </div>
        </div>
    );
}

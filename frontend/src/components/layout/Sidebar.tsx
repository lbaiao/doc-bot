import { Link, NavLink } from 'react-router-dom';
import { Plus, MessageSquare, Settings, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { formatRelativeTime } from '@/lib/date-utils';

interface Chat {
    id: string;
    title: string;
    created_at: string;
}

export function Sidebar({ className }: { className?: string }) {
    const { data: chats, isLoading } = useQuery({
        queryKey: ['chats'],
        queryFn: async () => {
            const res = await apiClient.get<Chat[]>('/v1/chats');
            return res.data;
        },
    });

    return (
        <div className={cn("flex h-screen w-64 flex-col border-r bg-muted/10", className)}>
            <div className="p-4">
                <Button asChild className="w-full justify-start gap-2" variant="default">
                    <Link to="/app/home">
                        <Plus className="h-4 w-4" />
                        New Chat / Upload
                    </Link>
                </Button>
            </div>

            <div className="flex-1 overflow-auto py-2">
                <div className="px-4 text-xs font-semibold text-muted-foreground mb-2">
                    Recent
                </div>

                {isLoading ? (
                    <div className="flex justify-center p-4">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    <nav className="space-y-1 px-2">
                        {chats?.map((chat) => (
                            <NavLink
                                key={chat.id}
                                to={`/app/s/${chat.id}`}
                                className={({ isActive }) =>
                                    cn(
                                        "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-muted",
                                        isActive ? "bg-muted font-medium text-primary" : "text-muted-foreground"
                                    )
                                }
                            >
                                <MessageSquare className="h-4 w-4 shrink-0" />
                                <div className="flex-1 overflow-hidden">
                                    <div className="truncate font-medium">{chat.title}</div>
                                    <div className="text-xs text-muted-foreground truncate">
                                        {formatRelativeTime(chat.created_at)}
                                    </div>
                                </div>
                            </NavLink>
                        ))}

                        {chats?.length === 0 && (
                            <div className="px-4 py-2 text-sm text-muted-foreground text-center">
                                No chats yet
                            </div>
                        )}
                    </nav>
                )}
            </div>

            <div className="border-t p-4">
                <nav className="space-y-1">
                    <Button variant="ghost" className="w-full justify-start gap-2 h-9 px-2" asChild>
                        <Link to="/app/settings">
                            <Settings className="h-4 w-4" />
                            Settings
                        </Link>
                    </Button>
                </nav>
            </div>
        </div>
    );
}

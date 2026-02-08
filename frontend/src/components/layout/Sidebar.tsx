import { Link, NavLink } from 'react-router-dom';
import { Plus, MessageSquare, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

// Mock sessions for now
const sessions = [
    { id: '1', title: 'Q1 Financial Report', date: '2h ago' },
    { id: '2', title: 'User Research 2024', date: '1d ago' },
];

export function Sidebar({ className }: { className?: string }) {
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
                <nav className="space-y-1 px-2">
                    {sessions.map((session) => (
                        <NavLink
                            key={session.id}
                            to={`/app/s/${session.id}`}
                            className={({ isActive }) =>
                                cn(
                                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-muted",
                                    isActive ? "bg-muted font-medium text-primary" : "text-muted-foreground"
                                )
                            }
                        >
                            <MessageSquare className="h-4 w-4" />
                            <div className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
                                {session.title}
                            </div>
                        </NavLink>
                    ))}
                </nav>
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

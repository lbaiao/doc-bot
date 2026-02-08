import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string | any; // content can be dict in backend, but usually string in frontend view
    created_at: string;
}

export function MessageList({ messages, isLoading }: { messages: Message[]; isLoading?: boolean }) {
    return (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
                <div
                    key={msg.id}
                    className={cn(
                        "flex w-full",
                        msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    <div
                        className={cn(
                            "rounded-lg px-4 py-2 max-w-[80%]",
                            msg.role === 'user'
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-foreground"
                        )}
                    >
                        {msg.role === 'assistant' ? (
                            <div className="prose dark:prose-invert text-sm">
                                <ReactMarkdown>{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</ReactMarkdown>
                            </div>
                        ) : (
                            <div className="text-sm whitespace-pre-wrap">{typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)}</div>
                        )}
                    </div>
                </div>
            ))}
            {isLoading && (
                <div className="flex w-full justify-start">
                    <div className="bg-muted rounded-lg px-4 py-2">
                        <span className="animate-pulse">...</span>
                    </div>
                </div>
            )}
        </div>
    );
}

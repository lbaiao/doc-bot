import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { MessageOut } from '@/types/chat';

function getMessageText(msg: MessageOut): string {
    const textValue = msg.content?.text;
    if (typeof textValue === 'string') {
        return textValue;
    }
    return '';
}

export function MessageList({ messages, isLoading }: { messages: MessageOut[]; isLoading?: boolean }) {
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
                    {msg.role === 'user' ? (
                        <div className="rounded-2xl px-4 py-2 max-w-[80%] bg-primary text-primary-foreground">
                            <div className="text-sm whitespace-pre-wrap">{getMessageText(msg)}</div>
                        </div>
                    ) : (
                        <div className="max-w-[80%] px-1 py-1 text-foreground">
                            <div className="prose dark:prose-invert text-sm">
                                <ReactMarkdown>{getMessageText(msg)}</ReactMarkdown>
                            </div>
                        </div>
                    )}
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

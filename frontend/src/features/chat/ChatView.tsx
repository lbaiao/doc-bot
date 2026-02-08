import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { MessageList } from './MessageList';
import { Composer } from './Composer';
import { Loader2 } from 'lucide-react';

export function ChatView() {
    const { sessionId } = useParams<{ sessionId: string }>();
    const [messages, setMessages] = useState<any[]>([]);

    // Fetch initial messages
    const { data: history, isLoading } = useQuery({
        queryKey: ['messages', sessionId],
        queryFn: async () => {
            const res = await apiClient.get(`/v1/chats/${sessionId}/messages`);
            return res.data;
        },
        enabled: !!sessionId,
    });

    // Sync state with history
    useEffect(() => {
        if (history) {
            setMessages(history);
        }
    }, [history]);

    const sendMessageMutation = useMutation({
        mutationFn: async (content: string) => {
            const res = await apiClient.post(`/v1/chats/${sessionId}/messages`, { content });
            return res.data;
        },
        onMutate: async (newContent) => {
            // Optimistic update
            const tempMsg = {
                id: 'temp-' + Date.now(),
                role: 'user',
                content: newContent,
                created_at: new Date().toISOString()
            };
            setMessages((prev) => [...prev, tempMsg]);
            return { tempMsg };
        },
        onSuccess: (data) => {
            // Append assistant response
            setMessages((prev) => [...prev, data]);
        },
        onError: (err, _variables, context) => {
            console.error("Failed to send message", err);
            // Remove temp message on error (simplified)
            // @ts-ignore
            setMessages((prev) => prev.filter(m => m.id !== context?.tempMsg.id));
        }
    });

    const handleSend = (content: string) => {
        sendMessageMutation.mutate(content);
    };

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            <MessageList messages={messages} isLoading={sendMessageMutation.isPending} />
            <Composer onSend={handleSend} disabled={sendMessageMutation.isPending} />
        </div>
    );
}

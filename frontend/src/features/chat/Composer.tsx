import { useState, useRef } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export function Composer({ onSend, disabled }: { onSend: (content: string) => void; disabled?: boolean }) {
    const [input, setInput] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || disabled) return;
        onSend(input);
        setInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="p-4 border-t bg-background">
            <form onSubmit={handleSubmit} className="relative flex items-end gap-2 max-w-3xl mx-auto">
                <Textarea
                    ref={textareaRef}
                    className="min-h-[50px] resize-none pr-12"
                    placeholder="Ask a question..."
                    value={input}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    rows={1}
                />
                <Button type="submit" size="icon" disabled={!input.trim() || disabled} className="absolute right-2 bottom-2 h-8 w-8">
                    <Send className="h-4 w-4" />
                    <span className="sr-only">Send</span>
                </Button>
            </form>
        </div>
    );
}

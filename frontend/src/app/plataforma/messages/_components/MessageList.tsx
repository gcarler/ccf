"use client";

import type { DirectMessageItem } from '@/types/directMessages';
import { Loader2, MessageCircle } from 'lucide-react';
import { useCallback, useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
    messages: DirectMessageItem[];
    loading: boolean;
    currentUserId: string;
    onLoadOlder: () => void;
    onReply: (msg: DirectMessageItem) => void;
}

export function MessageList({ messages, loading, currentUserId, onLoadOlder, onReply }: MessageListProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const shouldAutoScroll = useRef(true);

    const handleScroll = useCallback(() => {
        const el = scrollRef.current;
        if (!el) return;
        const threshold = 100;
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
        shouldAutoScroll.current = nearBottom;
    }, []);

    useEffect(() => {
        if (!shouldAutoScroll.current || !scrollRef.current) return;
        const el = scrollRef.current;
        el.scrollTop = el.scrollHeight;
    }, [messages]);

    return (
        <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto scrollbar-thin p-3 md:p-4 space-y-3 bg-[hsl(var(--surface-1))]/30 dark:bg-[#111213]"
        >
            {loading && messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--text-secondary))]">
                    <Loader2 size={20} className="animate-spin" />
                    <p className="text-sm">Cargando mensajes...</p>
                </div>
            ) : messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--text-secondary))]">
                    <div className="size-10 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                        <MessageCircle size={18} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                    </div>
                    <p className="text-sm font-semibold text-[hsl(var(--text-secondary))]">Sin mensajes aún</p>
                    <p className="text-xs text-[hsl(var(--text-secondary))]">Sé el primero en escribir</p>
                </div>
            ) : (
                messages.map((msg, idx) => {
                    const isOwn = msg.sender_id === currentUserId;
                    const showSender = idx === 0 || messages[idx - 1]?.sender_id !== msg.sender_id;
                    return (
                        <MessageBubble
                            key={msg.id}
                            message={msg}
                            isOwn={isOwn}
                            showSender={showSender}
                            onReply={onReply}
                        />
                    );
                })
            )}
        </div>
    );
}

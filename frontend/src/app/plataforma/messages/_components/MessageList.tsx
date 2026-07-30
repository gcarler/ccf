"use client";

import type { DirectMessageItem } from '@/types/directMessages';
import { Loader2, MessageCircle } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
    messages: DirectMessageItem[];
    loading: boolean;
    currentUserId: string;
    onLoadOlder: () => void;
    onReply: (msg: DirectMessageItem) => void;
    hasMore?: boolean;
}

export function MessageList({ messages, loading, currentUserId, onLoadOlder, onReply, hasMore = true }: MessageListProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const shouldAutoScroll = useRef(true);
    const lastMessageIdRef = useRef<string | null>(null);
    const topTriggerRef = useRef(false);
    const preLoadHeightRef = useRef(0);
    const preLoadFirstIdRef = useRef<string | null>(null);

    // Auto-scroll only when a new message is appended (last id changed), not when older messages prepend.
    useEffect(() => {
        const last = messages[messages.length - 1];
        if (!scrollRef.current) return;
        const prev = lastMessageIdRef.current;
        lastMessageIdRef.current = last?.id ?? null;
        if (prev === last?.id) return;
        if (!shouldAutoScroll.current) return;
        const el = scrollRef.current;
        el.scrollTop = el.scrollHeight;
    }, [messages]);

    // Reset the top trigger once the older-message load finishes.
    useEffect(() => {
        if (!loading) topTriggerRef.current = false;
    }, [loading]);

    // Preserve scroll position when older messages are prepended.
    useEffect(() => {
        if (loading && messages.length > 0) {
            preLoadHeightRef.current = scrollRef.current?.scrollHeight ?? 0;
            preLoadFirstIdRef.current = messages[0]?.id ?? null;
        }
    }, [loading, messages]);

    useEffect(() => {
        if (
            !loading &&
            preLoadFirstIdRef.current &&
            preLoadFirstIdRef.current !== messages[0]?.id &&
            scrollRef.current
        ) {
            const diff = (scrollRef.current.scrollHeight ?? 0) - preLoadHeightRef.current;
            scrollRef.current.scrollTop += diff;
            preLoadFirstIdRef.current = null;
        }
    }, [loading, messages]);

    const handleScroll = () => {
        const el = scrollRef.current;
        if (!el) return;
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
        shouldAutoScroll.current = nearBottom;
        if (!loading && !topTriggerRef.current && hasMore && el.scrollTop < 60) {
            topTriggerRef.current = true;
            onLoadOlder();
        } else if (el.scrollTop >= 60) {
            topTriggerRef.current = false;
        }
    };

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

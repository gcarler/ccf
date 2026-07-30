"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket';
import { apiFetch } from '@/lib/http';
import type { ConversationRead, DirectMessageItem, WsEvent } from '@/types/directMessages';

export interface AttachmentMeta {
    url: string;
    type: string;
    name: string;
    size: number;
}

interface UseChatThreadOptions {
    token: string | null;
    activeConv: ConversationRead | null;
    onMessage?: (conversationId: string, message: DirectMessageItem) => void;
}

const INITIAL_LIMIT = 100;
const OLDER_LIMIT = 50;

export function useChatThread({ token, activeConv, onMessage }: UseChatThreadOptions) {
    const [messages, setMessages] = useState<DirectMessageItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [replyTo, setReplyTo] = useState<DirectMessageItem | null>(null);
    const [hasMoreOlder, setHasMoreOlder] = useState(true);

    const messagesRef = useRef<DirectMessageItem[]>([]);
    const activeConvIdRef = useRef<string | null>(null);
    const onMessageRef = useRef(onMessage);

    const activeConvId = activeConv?.id ?? null;

    // Keep refs in sync with latest values without re-subscribing the socket.
    useEffect(() => {
        activeConvIdRef.current = activeConvId;
    }, [activeConvId]);

    useEffect(() => {
        messagesRef.current = messages;
    }, [messages]);

    useEffect(() => {
        onMessageRef.current = onMessage;
    }, [onMessage]);

    // Load messages when conversation changes
    useEffect(() => {
        if (!token || !activeConvId) return;
        const controller = new AbortController();
        setMessages([]);
        setLoading(true);
        setHasMoreOlder(true);
        apiFetch<DirectMessageItem[]>(
            `/chat/conversations/${activeConvId}/messages`,
            { token, query: { limit: String(INITIAL_LIMIT) }, signal: controller.signal }
        )
            .then((data) => {
                if (!Array.isArray(data)) return;
                if (data.length < INITIAL_LIMIT) {
                    setHasMoreOlder(false);
                }
                setMessages(data.reverse());
            })
            .catch(() => {})
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });
        apiFetch(`/chat/conversations/${activeConvId}/read`, {
            method: 'POST',
            token,
            signal: controller.signal,
        }).catch(() => {});

        return () => controller.abort();
    }, [activeConvId, token]);

    const loadOlderMessages = useCallback(async () => {
        if (!token || !activeConvId || loading || messagesRef.current.length === 0 || !hasMoreOlder) return;
        setLoading(true);
        try {
            const oldest = messagesRef.current[0];
            const older = await apiFetch<DirectMessageItem[]>(
                `/chat/conversations/${activeConvId}/messages`,
                { token, query: { limit: String(OLDER_LIMIT), before: oldest.created_at } }
            );
            if (!Array.isArray(older)) return;
            if (older.length < OLDER_LIMIT) {
                setHasMoreOlder(false);
            }
            if (older.length > 0) {
                setMessages((prev) => {
                    const existing = new Set(prev.map((m) => m.id));
                    const reversed = older
                        .reverse()
                        .filter((m) => !existing.has(m.id));
                    return [...reversed, ...prev];
                });
            }
        } catch {
            // silent
        } finally {
            setLoading(false);
        }
    }, [activeConvId, loading, token, hasMoreOlder]);

    const handleSocketEvent = useCallback((payload: WsEvent) => {
        if (
            payload.event === 'direct_message' &&
            'conversation_id' in payload &&
            'message' in payload
        ) {
            const evt = payload as { conversation_id: string; message: DirectMessageItem };
            const currentId = activeConvIdRef.current;
            if (evt.conversation_id === currentId) {
                setMessages((prev) => {
                    if (prev.some((m) => m.id === evt.message.id)) return prev;
                    return [...prev, evt.message];
                });
            }
            onMessageRef.current?.(evt.conversation_id, evt.message);
        }
    }, []);

    const { status: wsStatus } = useWorkspaceSocket({
        rooms: activeConvId ? [`dm_${activeConvId}`] : [],
        enabled: !!token && !!activeConvId,
        onEvent: handleSocketEvent,
    });

    const sendMessage = useCallback(
        async (content: string, opts: { attachment?: File; replyTo?: DirectMessageItem; mentions: string[] }) => {
            if (!token || !activeConvId) return { error: 'send' as const };
            setSending(true);

            let att: AttachmentMeta | null = null;
            if (opts.attachment) {
                try {
                    const formData = new FormData();
                    formData.append('file', opts.attachment);
                    const uploaded = await apiFetch<AttachmentMeta>('/chat/upload-attachment', {
                        method: 'POST',
                        token,
                        body: formData,
                    });
                    if (uploaded) att = uploaded;
                } catch {
                    setSending(false);
                    return { error: 'upload' as const };
                }
            }

            const body: Record<string, unknown> = { content };
            if (att) {
                body.attachment_url = att.url;
                body.attachment_type = att.type;
                body.attachment_name = att.name;
                body.attachment_size = att.size;
            }
            if (opts.replyTo) body.reply_to_id = opts.replyTo.id;
            if (opts.mentions.length > 0) body.mentions = opts.mentions;

            try {
                const msg = await apiFetch<DirectMessageItem>(
                    `/chat/conversations/${activeConvId}/messages`,
                    { method: 'POST', token, body }
                );
                setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
                setReplyTo(null);
                return { error: null as null, message: msg };
            } catch {
                return { error: 'send' as const };
            } finally {
                setSending(false);
            }
        },
        [activeConvId, token]
    );

    return {
        messages,
        loading,
        sending,
        replyTo,
        setReplyTo,
        loadOlderMessages,
        sendMessage,
        wsStatus,
        hasMoreOlder,
    };
}

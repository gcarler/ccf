"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '@/lib/http';
import type { ConversationRead, DirectMessageItem } from '@/types/directMessages';

interface UseConversationsOptions {
    token: string | null;
    userPersonaId: string;
}

export function useConversations({ token, userPersonaId }: UseConversationsOptions) {
    const [conversations, setConversations] = useState<ConversationRead[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState('');

    const loadConversations = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<ConversationRead[]>('/chat/conversations', { token, silent: true });
            if (Array.isArray(data)) {
                setConversations(data);
            }
        } catch {
            // Surface the failure so the UI can show a retry instead of a
            // misleading empty "no conversations" state.
            setError('No se pudieron cargar las conversaciones');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    const addConversation = useCallback((conv: ConversationRead) => {
        setConversations((prev) => {
            if (prev.some((c) => c.id === conv.id)) return prev;
            return [conv, ...prev];
        });
    }, []);

    const getOtherParticipant = useCallback(
        (conv: ConversationRead) => conv.participants.find((p) => p.persona_id !== userPersonaId),
        [userPersonaId]
    );

    const updateConversationFromMessage = useCallback(
        (convId: string, message: DirectMessageItem, isActive: boolean) => {
            setConversations((prev) => {
                const updated = prev.map((c) => {
                    if (c.id !== convId) return c;
                    return {
                        ...c,
                        last_message_content: message.content,
                        last_message_at: message.created_at,
                        last_sender_id: message.sender_id,
                        unread_count: isActive ? 0 : (c.unread_count ?? 0) + 1,
                    };
                });
                // Re-sort by last_message_at descending so the thread with the
                // newest message rises to the top, matching user expectation.
                return updated.sort((a, b) => {
                    const aTime = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
                    const bTime = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
                    return bTime - aTime;
                });
            });
        },
        []
    );

    const filteredConversations = useMemo(() => {
        const term = filter.trim().toLowerCase();
        if (!term) return conversations;
        return conversations.filter((c) => {
            const other = getOtherParticipant(c);
            const name = (other?.username || '').toLowerCase();
            return name.includes(term);
        });
    }, [conversations, filter, getOtherParticipant]);

    const totalUnread = useMemo(
        () => conversations.reduce((sum, c) => sum + (c.unread_count || 0), 0),
        [conversations]
    );

    return {
        conversations,
        filteredConversations,
        loading,
        error,
        filter,
        setFilter,
        loadConversations,
        addConversation,
        updateConversationFromMessage,
        getOtherParticipant,
        totalUnread,
    };
}

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
    const [filter, setFilter] = useState('');

    const loadConversations = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const data = await apiFetch<ConversationRead[]>('/chat/conversations', { token });
            if (Array.isArray(data)) {
                setConversations(data);
            }
        } catch {
            // Error handled via silent fail; parent can toast if needed
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
            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id !== convId) return c;
                    return {
                        ...c,
                        last_message_content: message.content,
                        last_message_at: message.created_at,
                        last_sender_id: message.sender_id,
                        unread_count: isActive ? 0 : (c.unread_count ?? 0) + 1,
                    };
                })
            );
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
        filter,
        setFilter,
        loadConversations,
        addConversation,
        updateConversationFromMessage,
        getOtherParticipant,
        totalUnread,
    };
}

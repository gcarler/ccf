import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useConversations } from './useConversations';
import { apiFetch } from '@/lib/http';
import type { ConversationRead } from '@/types/directMessages';

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

describe('useConversations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    const sampleConversations: ConversationRead[] = [
        {
            id: 'c1',
            participants: [
                { persona_id: 'me', username: 'me_user', last_read_at: null },
                { persona_id: 'p1', username: 'ana', last_read_at: null },
            ],
            last_message_content: 'Hola',
            last_message_at: '2024-01-01T00:00:00Z',
            last_sender_id: 'p1',
            unread_count: 1,
            created_at: '2024-01-01T00:00:00Z',
        },
        {
            id: 'c2',
            participants: [
                { persona_id: 'me', username: 'me_user', last_read_at: null },
                { persona_id: 'p2', username: 'beto', last_read_at: null },
            ],
            last_message_content: 'Ok',
            last_message_at: '2024-01-02T00:00:00Z',
            last_sender_id: 'me',
            unread_count: 0,
            created_at: '2024-01-02T00:00:00Z',
        },
    ];

    it('loads conversations on mount', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));

        expect(result.current.loading).toBe(true);
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));
        expect(result.current.totalUnread).toBe(1);
        expect(result.current.loading).toBe(false);
    });

    it('filters conversations by the other participant username', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        act(() => result.current.setFilter('ana'));
        expect(result.current.filteredConversations).toHaveLength(1);
        expect(result.current.filteredConversations[0].id).toBe('c1');
    });

    it('adds a new conversation avoiding duplicates', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        const newConv: ConversationRead = { ...sampleConversations[0], id: 'c3' };
        act(() => result.current.addConversation(newConv));
        expect(result.current.conversations).toHaveLength(3);

        act(() => result.current.addConversation(newConv));
        expect(result.current.conversations).toHaveLength(3);
    });

    it('returns the other participant for a conversation', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        const other = result.current.getOtherParticipant(result.current.conversations[0]);
        expect(other?.username).toBe('ana');
    });
});

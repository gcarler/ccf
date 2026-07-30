import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useConversations } from './useConversations';
import { apiFetch } from '@/lib/http';
import type { ConversationRead, DirectMessageItem } from '@/types/directMessages';

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

describe('useConversations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
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

    it('does not fetch when token is null', async () => {
        renderHook(() => useConversations({ token: null, userPersonaId: 'me' }));
        expect(apiFetch).not.toHaveBeenCalled();
    });

    it('handles fetch errors gracefully', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network error'));

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.conversations).toHaveLength(0);
    });

    it('updates conversation metadata when a new message arrives', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        const message: DirectMessageItem = {
            id: 'm3',
            sender_id: 'p1',
            sender_name: 'ana',
            content: 'Nuevo mensaje',
            created_at: '2024-01-03T00:00:00Z',
            is_read: false,
        };

        act(() => result.current.updateConversationFromMessage('c1', message, false));

        const updated = result.current.conversations.find((c) => c.id === 'c1');
        expect(updated?.last_message_content).toBe('Nuevo mensaje');
        expect(updated?.unread_count).toBe(2);
        expect(result.current.totalUnread).toBe(2);
    });

    it('marks unread as 0 for the active conversation', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        const message: DirectMessageItem = {
            id: 'm3',
            sender_id: 'p1',
            sender_name: 'ana',
            content: 'Nuevo mensaje',
            created_at: '2024-01-03T00:00:00Z',
            is_read: false,
        };

        act(() => result.current.updateConversationFromMessage('c1', message, true));

        const updated = result.current.conversations.find((c) => c.id === 'c1');
        expect(updated?.unread_count).toBe(0);
    });

    it('allows manual refetch of conversations', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(sampleConversations);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(2));

        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce([sampleConversations[0]]);
        await act(async () => { await result.current.loadConversations(); });
        expect(result.current.conversations).toHaveLength(1);
    });

    it('ignores non-array responses from the server', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ notAnArray: true });

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.conversations).toHaveLength(0);
    });

    it('handles conversations with missing participant username and unread count', async () => {
        const convWithMissingData = {
            id: 'c3',
            participants: [{ persona_id: 'me', username: 'me_user', last_read_at: null }, { persona_id: 'p3', last_read_at: null }],
            last_message_content: 'Hola',
            last_message_at: '2024-01-03T00:00:00Z',
            last_sender_id: 'p3',
            unread_count: undefined,
            created_at: '2024-01-03T00:00:00Z',
        } as unknown as ConversationRead;
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([...sampleConversations, convWithMissingData]);

        const { result } = renderHook(() => useConversations({ token: 'token', userPersonaId: 'me' }));
        await waitFor(() => expect(result.current.conversations).toHaveLength(3));

        act(() => result.current.setFilter('zzz'));
        expect(result.current.filteredConversations).toHaveLength(0);

        act(() => result.current.setFilter(''));
        const message: DirectMessageItem = {
            id: 'm4',
            sender_id: 'p3',
            sender_name: 'carlos',
            content: 'Nuevo',
            created_at: '2024-01-04T00:00:00Z',
            is_read: false,
        };
        act(() => result.current.updateConversationFromMessage('c3', message, false));
        const updated = result.current.conversations.find((c) => c.id === 'c3');
        expect(updated?.unread_count).toBe(1);
    });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useChatThread } from './useChatThread';
import { apiFetch } from '@/lib/http';
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket';
import type { DirectMessageItem, ConversationRead, WsEvent } from '@/types/directMessages';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

let capturedOnEvent: ((payload: WsEvent) => void) | null = null;

vi.mock('@/hooks/useWorkspaceSocket', () => ({
  useWorkspaceSocket: vi.fn(({ onEvent }: { onEvent: (payload: WsEvent) => void }) => {
    capturedOnEvent = onEvent;
    return { status: 'connected' };
  }),
}));

const conversation: ConversationRead = {
  id: 'conv-1',
  participants: [],
  last_message_content: null,
  last_message_at: null,
  last_sender_id: null,
  unread_count: 0,
  created_at: '2026-07-30T10:00:00Z',
};

function makeMessage(id: string, content: string, createdAt = '2026-07-30T10:00:00Z'): DirectMessageItem {
  return {
    id,
    sender_id: 'sender-1',
    sender_name: 'Ana',
    content,
    created_at: createdAt,
    is_read: false,
  };
}

describe('useChatThread', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
    capturedOnEvent = null;
  });

  it('loads initial messages and marks conversation as read', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([makeMessage('m2', 'Segundo'), makeMessage('m1', 'Primero')])
      .mockResolvedValueOnce({});

    const { result } = renderHook(() =>
      useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.messages).toHaveLength(2);
    expect(apiFetch).toHaveBeenCalledWith(
      '/chat/conversations/conv-1/messages',
      expect.objectContaining({ query: { limit: '100' } })
    );
    expect(apiFetch).toHaveBeenCalledWith(
      '/chat/conversations/conv-1/read',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('sends a message and appends it to the list', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce(makeMessage('m3', 'Enviado'));

    const { result } = renderHook(() =>
      useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    const sendResult = await result.current.sendMessage('Hola', { mentions: [] });
    await waitFor(() => expect(result.current.messages.some((m) => m.content === 'Enviado')).toBe(true));

    expect(sendResult.error).toBeNull();
    expect(result.current.sending).toBe(false);
  });

  it('uploads attachment before sending message with attachment metadata', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ url: '/file.png', type: 'image', name: 'file.png', size: 123 })
      .mockResolvedValueOnce(makeMessage('m4', 'Con adjunto'));

    const { result } = renderHook(() =>
      useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File(['x'], 'file.png', { type: 'image/png' });
    const sendResult = await result.current.sendMessage('Mira esto', { attachment: file, mentions: [] });

    expect(sendResult.error).toBeNull();
    expect(apiFetch).toHaveBeenCalledWith(
      '/chat/upload-attachment',
      expect.objectContaining({ method: 'POST' })
    );
  });    it('loads older messages and prepends them', async () => {
        const initial = Array.from({ length: 100 }, (_, i) => makeMessage(`m${i + 1}`, `Msg ${i + 1}`));
        vi.mocked(apiFetch)
            .mockResolvedValueOnce(initial)
            .mockResolvedValueOnce({})
            .mockResolvedValueOnce([makeMessage('m0', 'Cero')]);

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.messages).toHaveLength(100);

        await result.current.loadOlderMessages();
        await waitFor(() => expect(result.current.loading).toBe(false));

        await waitFor(() => expect(result.current.messages).toHaveLength(101));
        expect(result.current.messages[0].content).toBe('Cero');
    });

    it('handles errors while loading older messages', async () => {
        const initial = Array.from({ length: 100 }, (_, i) => makeMessage(`m${i + 1}`, `Msg ${i + 1}`));
        vi.mocked(apiFetch)
            .mockResolvedValueOnce(initial)
            .mockResolvedValueOnce({})
            .mockRejectedValueOnce(new Error('network error'));

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.hasMoreOlder).toBe(true);

        await result.current.loadOlderMessages();
        await waitFor(() => expect(result.current.loading).toBe(false));
        expect(result.current.hasMoreOlder).toBe(true);
    });

    it('returns upload error when attachment upload fails', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({})
            .mockRejectedValueOnce(new Error('upload failed'));

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));

        const file = new File(['x'], 'file.png', { type: 'image/png' });
        const sendResult = await result.current.sendMessage('Mira esto', { attachment: file, mentions: [] });

        expect(sendResult.error).toBe('upload');
        expect(result.current.sending).toBe(false);
    });

  it('appends incoming websocket messages for the active conversation', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({});

    const { result } = renderHook(() =>
      useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    const incoming = makeMessage('ws-1', 'Nuevo mensaje');
    capturedOnEvent?.({ event: 'direct_message', conversation_id: 'conv-1', message: incoming });

    await waitFor(() => expect(result.current.messages).toHaveLength(1));
    expect(result.current.messages[0].content).toBe('Nuevo mensaje');
  });    it('ignores websocket messages for other conversations', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({});

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));

        capturedOnEvent?.({
            event: 'direct_message',
            conversation_id: 'conv-other',
            message: makeMessage('ws-2', 'Otro chat'),
        });

        await waitFor(() => expect(result.current.messages).toHaveLength(0));
    });

    it('does not append duplicate websocket messages', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({});

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));

        const incoming = makeMessage('ws-1', 'Mensaje único');
        act(() => capturedOnEvent?.({ event: 'direct_message', conversation_id: 'conv-1', message: incoming }));
        act(() => capturedOnEvent?.({ event: 'direct_message', conversation_id: 'conv-1', message: incoming }));

        await waitFor(() => expect(result.current.messages).toHaveLength(1));
    });

    it('calls onMessage callback even for non-active conversations', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({});

        const onMessage = vi.fn();
        renderHook(() => useChatThread({ token: 't', activeConv: conversation, onMessage }));
        await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2));

        const incoming = makeMessage('ws-2', 'Otro chat');
        act(() => capturedOnEvent?.({ event: 'direct_message', conversation_id: 'conv-other', message: incoming }));

        expect(onMessage).toHaveBeenCalledWith('conv-other', incoming);
    });

    it('clears messages when active conversation changes', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([makeMessage('m1', 'A')])
            .mockResolvedValueOnce({})
            .mockResolvedValueOnce([makeMessage('m2', 'B')])
            .mockResolvedValueOnce({});

        const { result, rerender } = renderHook(
            ({ activeConv }) => useChatThread({ token: 't', activeConv, onMessage: vi.fn() }),
            { initialProps: { activeConv: conversation } }
        );
        await waitFor(() => expect(result.current.messages).toHaveLength(1));

        rerender({ activeConv: { ...conversation, id: 'conv-2' } });
        await waitFor(() => {
            expect(result.current.messages).toHaveLength(1);
            expect(result.current.messages[0].content).toBe('B');
        });
    });

    it('sends message with replyTo and mentions', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({})
            .mockResolvedValueOnce(makeMessage('m3', 'Con mención'));

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));

        const replyTo = makeMessage('r1', 'Respuesta');
        await result.current.sendMessage('Hola', { replyTo, mentions: ['u1', 'u2'] });

        expect(apiFetch).toHaveBeenCalledWith(
            '/chat/conversations/conv-1/messages',
            expect.objectContaining({
                body: expect.objectContaining({ reply_to_id: 'r1', mentions: ['u1', 'u2'] }),
            })
        );
    });

    it('returns send error when message post fails', async () => {
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([])
            .mockResolvedValueOnce({})
            .mockRejectedValueOnce(new Error('fail'));

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.loading).toBe(false));

        const sendResult = await result.current.sendMessage('Hola', { mentions: [] });
        expect(sendResult.error).toBe('send');
    });

    it('does not subscribe to the socket without token or active conversation', async () => {
        renderHook(() => useChatThread({ token: null, activeConv: null, onMessage: vi.fn() }));
        const lastCall = vi.mocked(useWorkspaceSocket).mock.calls.at(-1)?.[0];
        expect(lastCall?.enabled).toBe(false);
        expect(lastCall?.rooms).toEqual([]);
    });

    it('returns send error when no token or active conversation is provided', async () => {
        const { result } = renderHook(() =>
            useChatThread({ token: null, activeConv: null, onMessage: vi.fn() })
        );
        const sendResult = await result.current.sendMessage('Hola', { mentions: [] });
        expect(sendResult.error).toBe('send');
    });

    it('does not append duplicate messages returned by the API', async () => {
        const existing = makeMessage('dup-1', 'Existente');
        vi.mocked(apiFetch)
            .mockResolvedValueOnce([existing])
            .mockResolvedValueOnce({})
            .mockResolvedValueOnce(existing);

        const { result } = renderHook(() =>
            useChatThread({ token: 't', activeConv: conversation, onMessage: vi.fn() })
        );
        await waitFor(() => expect(result.current.messages).toHaveLength(1));

        await result.current.sendMessage('Hola', { mentions: [] });
        await waitFor(() => expect(result.current.sending).toBe(false));
        expect(result.current.messages).toHaveLength(1);
    });
});

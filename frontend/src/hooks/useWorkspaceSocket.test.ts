import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkspaceSocket, MAX_RECONNECT_ATTEMPTS } from './useWorkspaceSocket';
import type { WsEvent } from '@/types/directMessages';

class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    static instances: MockWebSocket[] = [];
    static lastInstance: MockWebSocket | null = null;

    readyState = MockWebSocket.CONNECTING;
    onopen: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;

    public url = '';
    public closed = false;

    constructor(url: string) {
        this.url = url;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (MockWebSocket as any).lastInstance = this;
        MockWebSocket.instances.push(this);
    }

    close() {
        this.closed = true;
        this.readyState = MockWebSocket.CLOSING;
    }

    triggerOpen() {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.();
    }

    triggerClose() {
        this.readyState = MockWebSocket.CLOSED;
        this.closed = true;
        this.onclose?.();
    }

    triggerError() {
        this.onerror?.();
    }

    triggerMessage(data: unknown) {
        this.onmessage?.({ data: typeof data === 'string' ? data : JSON.stringify(data) });
    }
}

vi.mock('@/lib/websocket', () => ({
    buildWsUrl: vi.fn((path: string) => `ws://localhost${path}`),
    resolveClientId: vi.fn(() => 'client-123'),
}));

import { buildWsUrl } from '@/lib/websocket';

describe('useWorkspaceSocket', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (globalThis as any).WebSocket = MockWebSocket;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (MockWebSocket as any).lastInstance = null;
        MockWebSocket.instances = [];
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    it('connects and reports open status', () => {
        const { result } = renderHook(() => useWorkspaceSocket({}));
        expect(result.current.status).toBe('connecting');

        act(() => MockWebSocket.lastInstance?.triggerOpen());
        expect(result.current.status).toBe('open');
    });

    it('passes rooms in the WebSocket URL', () => {
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1', 'general'], clientId: 'u1' }));
        expect(buildWsUrl).toHaveBeenCalledWith(expect.stringContaining('rooms=dm_1%2Cgeneral'));
    });

    it('calls onEvent with parsed JSON payload', () => {
        const onEvent = vi.fn();
        const payload: WsEvent = { event: 'direct_message', conversation_id: 'c1', message: { id: 'm1', sender_id: 's1', sender_name: 'Ana', content: 'Hola', created_at: '2024-01-01T00:00:00Z', is_read: false } };

        renderHook(() => useWorkspaceSocket({ onEvent, rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        act(() => MockWebSocket.lastInstance?.triggerMessage(payload));

        expect(onEvent).toHaveBeenCalledWith(payload);
    });

    it('falls back to raw event on malformed JSON', () => {
        const onEvent = vi.fn();
        renderHook(() => useWorkspaceSocket({ onEvent }));
        act(() => MockWebSocket.lastInstance?.triggerMessage('not-json'));
        expect(onEvent).toHaveBeenCalledWith({ event: 'raw', body: 'not-json' });
    });

    it('does not call onEvent when no handler is provided', () => {
        const unpassedHandler = vi.fn();
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerMessage({ event: 'direct_message', conversation_id: 'c1', message: { id: 'm1', sender_id: 's1', sender_name: 'Ana', content: 'Hola', created_at: '2024-01-01T00:00:00Z', is_read: false } }));
        expect(unpassedHandler).not.toHaveBeenCalled();
    });

    it('passes invalid non-JSON strings to onEvent as raw events', () => {
        const onEvent = vi.fn();
        renderHook(() => useWorkspaceSocket({ onEvent, rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerMessage('{not-json'));
        expect(onEvent).toHaveBeenCalledWith({ event: 'raw', body: '{not-json' });
    });

    it('reports error status on socket error', () => {
        const { result } = renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        act(() => MockWebSocket.lastInstance?.triggerError());
        expect(result.current.status).toBe('error');
    });

    it('keeps status as error when the socket errors and then closes', () => {
        const { result } = renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        act(() => MockWebSocket.lastInstance?.triggerError());
        act(() => MockWebSocket.lastInstance?.triggerClose());
        expect(result.current.status).toBe('error');

        // The error should be cleared only after a successful reconnect.
        act(() => vi.advanceTimersByTime(1000));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        expect(result.current.status).toBe('open');
    });

    it('resets error state when the hook is disabled', () => {
        const { result, rerender } = renderHook(({ enabled }) => useWorkspaceSocket({ enabled, rooms: ['dm_1'] }), {
            initialProps: { enabled: true },
        });
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        act(() => MockWebSocket.lastInstance?.triggerError());
        expect(result.current.status).toBe('error');

        rerender({ enabled: false });
        expect(result.current.status).toBe('idle');
    });

    it('schedules reconnect after close', () => {
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        const first = MockWebSocket.lastInstance;
        act(() => MockWebSocket.lastInstance?.triggerClose());

        act(() => vi.advanceTimersByTime(1000));
        expect(MockWebSocket.lastInstance).not.toBe(first);
    });

    it('closes the socket and stops reconnect when disabled', () => {
        const { rerender } = renderHook(({ enabled }) => useWorkspaceSocket({ enabled, rooms: ['dm_1'] }), {
            initialProps: { enabled: true },
        });
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        const instance = MockWebSocket.lastInstance;
        rerender({ enabled: false });
        expect(instance?.closed).toBe(true);
    });

    it('stays idle when initially disabled and connects once enabled', () => {
        const { result, rerender } = renderHook(({ enabled }) => useWorkspaceSocket({ enabled, rooms: ['dm_1'] }), {
            initialProps: { enabled: false },
        });
        expect(result.current.status).toBe('idle');
        expect(MockWebSocket.instances).toHaveLength(0);
        expect(buildWsUrl).not.toHaveBeenCalled();

        rerender({ enabled: true });
        expect(MockWebSocket.instances).toHaveLength(1);
        expect(result.current.status).toBe('connecting');
    });

    it('cleans up the socket and pending reconnect timers on unmount', () => {
        const { unmount } = renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        const initial = MockWebSocket.lastInstance;
        act(() => MockWebSocket.lastInstance?.triggerClose());

        unmount();
        act(() => vi.advanceTimersByTime(32000));
        expect(MockWebSocket.instances).toHaveLength(1);
        expect(initial?.closed).toBe(true);
    });

    it('closes an open socket on unmount even when no close event fired', () => {
        const { unmount } = renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        const initial = MockWebSocket.lastInstance;

        unmount();
        expect(initial?.closed).toBe(true);
        act(() => vi.advanceTimersByTime(32000));
        expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('uses exponential backoff between reconnect attempts', () => {
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        const initial = MockWebSocket.lastInstance;

        // First close -> reconnect after 1000 ms.
        act(() => MockWebSocket.lastInstance?.triggerClose());
        act(() => vi.advanceTimersByTime(999));
        expect(MockWebSocket.lastInstance).toBe(initial);
        act(() => vi.advanceTimersByTime(1));
        expect(MockWebSocket.lastInstance).not.toBe(initial);

        // Second close -> next reconnect uses 2000 ms (double the previous delay).
        const second = MockWebSocket.lastInstance;
        act(() => MockWebSocket.lastInstance?.triggerClose());
        act(() => vi.advanceTimersByTime(1000));
        expect(MockWebSocket.lastInstance).toBe(second);
        act(() => vi.advanceTimersByTime(1000));
        expect(MockWebSocket.lastInstance).not.toBe(second);

        // Third close -> next reconnect uses 4000 ms.
        const third = MockWebSocket.lastInstance;
        act(() => MockWebSocket.lastInstance?.triggerClose());
        act(() => vi.advanceTimersByTime(2000));
        expect(MockWebSocket.lastInstance).toBe(third);
        act(() => vi.advanceTimersByTime(2000));
        expect(MockWebSocket.lastInstance).not.toBe(third);
    });

    it('resets backoff delay after a successful reconnect', () => {
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());

        act(() => MockWebSocket.lastInstance?.triggerClose());
        act(() => vi.advanceTimersByTime(1000));
        // New socket opens successfully -> attempts reset to 0.
        act(() => MockWebSocket.lastInstance?.triggerOpen());

        const afterReconnect = MockWebSocket.lastInstance;
        act(() => MockWebSocket.lastInstance?.triggerClose());
        // After reset, the next delay should be the base delay (1000 ms), not 2000 ms.
        act(() => vi.advanceTimersByTime(999));
        expect(MockWebSocket.lastInstance).toBe(afterReconnect);
        act(() => vi.advanceTimersByTime(1));
        expect(MockWebSocket.lastInstance).not.toBe(afterReconnect);
    });

    it('stops reconnecting after the maximum number of attempts is reached', () => {
        renderHook(() => useWorkspaceSocket({ rooms: ['dm_1'] }));
        act(() => MockWebSocket.lastInstance?.triggerOpen());
        expect(MockWebSocket.instances).toHaveLength(1);

        // Trigger MAX_RECONNECT_ATTEMPTS failures without opening the new sockets.
        // Each new reconnect uses a longer delay (1000, 2000, 4000, 8000, 16000 ms).
        for (let i = 0; i < MAX_RECONNECT_ATTEMPTS; i += 1) {
            act(() => MockWebSocket.lastInstance?.triggerClose());
            act(() => vi.advanceTimersByTime(1000 * Math.pow(2, i)));
        }
        expect(MockWebSocket.instances).toHaveLength(1 + MAX_RECONNECT_ATTEMPTS);

        // One more close should not schedule another reconnect, even after the max delay.
        act(() => MockWebSocket.lastInstance?.triggerClose());
        act(() => vi.advanceTimersByTime(32000));
        expect(MockWebSocket.instances).toHaveLength(1 + MAX_RECONNECT_ATTEMPTS);
    });
});

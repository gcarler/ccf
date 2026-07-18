"use client";

import { useEffect, useMemo, useRef, useState } from 'react';
import { buildWsUrl, resolveClientId } from '@/lib/websocket';
import type { WsEvent } from '@/types/directMessages';

type SocketStatus = 'idle' | 'connecting' | 'open' | 'error';

interface UseWorkspaceSocketOptions {
    clientId?: string;
    rooms?: string[];
    enabled?: boolean;
    onEvent?: (payload: WsEvent) => void;
}

interface WorkspaceSocketResult {
    status: SocketStatus;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_DELAY_MS = 1000;

export function useWorkspaceSocket({ clientId, rooms = [], enabled = true, onEvent }: UseWorkspaceSocketOptions): WorkspaceSocketResult {
    const [status, setStatus] = useState<SocketStatus>('idle');
    const fallbackIdRef = useRef(resolveClientId());
    const socketRef = useRef<WebSocket | null>(null);
    const onEventRef = useRef(onEvent);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    onEventRef.current = onEvent;

    const resolvedClientId = useMemo(() => clientId ?? fallbackIdRef.current, [clientId]);
    const roomsKey = useMemo(() => (rooms && rooms.length ? rooms.join(',') : ''), [rooms]);

    useEffect(() => {
        if (!enabled) {
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
            reconnectAttemptsRef.current = 0;
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
                reconnectTimerRef.current = null;
            }
            setStatus('idle');
            return;
        }

        function connect() {
            const roomQuery = roomsKey ? `?rooms=${encodeURIComponent(roomsKey)}` : '';
            const socket = new WebSocket(buildWsUrl(`/messaging/ws/${encodeURIComponent(resolvedClientId)}${roomQuery}`));
            socketRef.current = socket;
            setStatus('connecting');

            socket.onopen = () => {
                setStatus('open');
                reconnectAttemptsRef.current = 0;
            };
            socket.onclose = () => {
                setStatus('idle');
                socketRef.current = null;
                if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
                    const delay = BASE_DELAY_MS * Math.pow(2, reconnectAttemptsRef.current);
                    reconnectAttemptsRef.current += 1;
                    reconnectTimerRef.current = setTimeout(() => {
                        if (enabled) connect();
                    }, delay);
                }
            };
            socket.onerror = () => setStatus('error');
            socket.onmessage = (event) => {
                if (!onEventRef.current) return;
                try {
                    const payload = JSON.parse(event.data);
                    onEventRef.current(payload);
                } catch {
                    onEventRef.current({ event: 'raw', body: event.data });
                }
            };
        }

        connect();

        return () => {
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
                reconnectTimerRef.current = null;
            }
            reconnectAttemptsRef.current = MAX_RECONNECT_ATTEMPTS;
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
        };
    }, [enabled, resolvedClientId, roomsKey]);

    return { status };
}

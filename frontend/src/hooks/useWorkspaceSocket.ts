"use client";

import { useEffect, useMemo, useRef, useState } from 'react';
import { buildWsUrl, resolveClientId } from '@/lib/websocket';

type SocketStatus = 'idle' | 'connecting' | 'open' | 'error';

interface UseWorkspaceSocketOptions {
    clientId?: string;
    rooms?: string[];
    enabled?: boolean;
    onEvent?: (payload: any) => void;
}

interface WorkspaceSocketResult {
    status: SocketStatus;
}

export function useWorkspaceSocket({ clientId, rooms = [], enabled = true, onEvent }: UseWorkspaceSocketOptions): WorkspaceSocketResult {
    const [status, setStatus] = useState<SocketStatus>('idle');
    const fallbackIdRef = useRef(resolveClientId());
    const socketRef = useRef<WebSocket | null>(null);

    const resolvedClientId = useMemo(() => clientId ?? fallbackIdRef.current, [clientId]);
    const roomsKey = useMemo(() => (rooms && rooms.length ? rooms.join(',') : ''), [rooms]);

    useEffect(() => {
        if (!enabled) {
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
            setStatus('idle');
            return;
        }

        const roomQuery = roomsKey ? `?rooms=${encodeURIComponent(roomsKey)}` : '';
        const socket = new WebSocket(buildWsUrl(`/ws/${encodeURIComponent(resolvedClientId)}${roomQuery}`));
        socketRef.current = socket;
        setStatus('connecting');

        socket.onopen = () => setStatus('open');
        socket.onclose = () => setStatus('idle');
        socket.onerror = () => setStatus('error');
        socket.onmessage = (event) => {
            if (!onEvent) return;
            try {
                const payload = JSON.parse(event.data);
                onEvent(payload);
            } catch (error) {
                onEvent({ event: 'raw', body: event.data });
            }
        };

        return () => {
            socket.close();
            socketRef.current = null;
        };
    }, [enabled, resolvedClientId, roomsKey, onEvent]);

    return { status };
}

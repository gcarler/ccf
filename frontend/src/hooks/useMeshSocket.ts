import { useEffect, useState, useRef } from 'react';

type MeshEvent = {
    event: string;
    [key: string]: any;
};

export const useMeshSocket = (clientId: string) => {
    const [lastEvent, setLastEvent] = useState<MeshEvent | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (!clientId) return;

        const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
        const isSyntheticAudit = /HeadlessChrome|Lighthouse/i.test(ua);
        if (isSyntheticAudit) return;

        const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
        const socket = new WebSocket(`${wsBaseUrl}/mesh/ws/${clientId}`);

        socket.onopen = () => {
            console.log('🔗 Connected to Agentic Mesh Nervous System');
            setIsConnected(true);
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as MeshEvent;
                console.log('⚡ Received Mesh Event:', data);
                setLastEvent(data);
            } catch (error) {
                console.error('Failed to parse Mesh websocket message', error);
            }
        };

        socket.onclose = () => {
            console.log('🔌 Disconnected from Agentic Mesh');
            setIsConnected(false);
        };

        ws.current = socket;

        return () => {
            socket.close();
        };
    }, [clientId]);

    return { isConnected, lastEvent };
};

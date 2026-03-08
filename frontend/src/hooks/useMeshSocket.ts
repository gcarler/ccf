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

        // Connect to the Mesh WebSocket Gateway
        const socket = new WebSocket(`ws://localhost:8000/mesh/ws/${clientId}`);

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

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { Canvas } from "fabric";
import type { RefObject } from "react";

export interface CursorPosition {
  x: number;
  y: number;
  userId: string;
  userName: string;
}

export interface UseWhiteboardCollabOptions {
  projectId: string;
  token: string | null;
  canvasRef: RefObject<Canvas | null>;
  userName: string;
  canvasReady: boolean;
}

/** Random per-tab identity so we can ignore our own echoed broadcasts. */
function makeClientId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `c-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

const RECONNECT_BASE_MS = 1200;
const RECONNECT_MAX_MS = 12000;

/** Max frequency for cursor broadcasts (MED-4 audit throttle). */
const CURSOR_THROTTLE_MS = 100;

export function useWhiteboardCollab({ projectId, token, canvasRef, userName, canvasReady }: UseWhiteboardCollabOptions) {
  const [cursors, setCursors] = useState<Record<string, CursorPosition>>({});
  const [connected, setConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const clientId = useRef<string>(makeClientId());
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldRun = useRef(true);

  // Cursor-throttle state (MED-4 audit)
  const lastCursorSend = useRef(0);
  const pendingCursor = useRef<{ x: number; y: number } | null>(null);
  const cursorFlushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Buffer to prevent echo on our own updates (keyed by object id)
  const ignoreNextUpdateIds = useRef<Set<string>>(new Set());

  const isSelf = useCallback((senderId: string | undefined | null) => {
    return !!senderId && senderId === clientId.current;
  }, []);

  useEffect(() => {
    if (!projectId || !token || !canvasReady) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    shouldRun.current = true;
    let socket: WebSocket | null = null;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // PZ-05/PZ-13: el endpoint real vive en /api/projects (mismo router que
    // el resto del módulo), no en /api/v1/projects (404). clientId permite
    // al backend ecoar sender_id para que esta pestaña filtre su propio eco.
    const url =
      `${protocol}//${window.location.host}/api/projects/${projectId}/whiteboard/ws` +
      `?token=${encodeURIComponent(token)}&clientId=${encodeURIComponent(clientId.current)}`;

    const connect = () => {
      if (!shouldRun.current) return;
      socket = new WebSocket(url);
      ws.current = socket;

      socket.onopen = () => {
        setConnected(true);
        reconnectAttempt.current = 0;
        socket?.send(JSON.stringify({ type: "join", name: userName, clientId: clientId.current }));
      };

      socket.onmessage = (event) => {
        let data: {
          type?: string;
          sender_id?: string;
          x?: number;
          y?: number;
          name?: string;
          objData?: Record<string, unknown> & { id?: string };
          objId?: string;
        };
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }

        if (data.type === "cursor") {
          if (!data.sender_id || isSelf(data.sender_id)) return;
          const senderId = data.sender_id;
          setCursors((prev) => ({
            ...prev,
            [senderId]: {
              x: data.x ?? 0,
              y: data.y ?? 0,
              userId: senderId,
              userName: data.name ?? "",
            },
          }));
        } else if (data.type === "object_modified" || data.type === "object_added") {
          if (!data.objData || !data.objData.id) return;
          const objData = data.objData;
          const objId = data.objData.id;
          if (ignoreNextUpdateIds.current.has(objId)) {
            ignoreNextUpdateIds.current.delete(objId);
            return;
          }
          const existingObj = canvas.getObjects().find((o) => (o as { id?: string }).id === objId);
          if (existingObj) {
            existingObj.set(objData);
            existingObj.setCoords();
          } else if (data.type === "object_added") {
            import("fabric").then(({ util }) => {
              util.enlivenObjects([objData]).then((enlivened: unknown[]) => {
                const newObj = enlivened[0] as Parameters<typeof canvas.add>[0] | undefined;
                if (newObj) canvas.add(newObj);
              });
            });
          }
          canvas.renderAll();
        } else if (data.type === "object_removed") {
          if (!data.objId) return;
          const existingObj = canvas.getObjects().find((o) => (o as { id?: string }).id === data.objId);
          if (existingObj) {
            canvas.remove(existingObj);
            canvas.renderAll();
          }
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (!shouldRun.current) return;
        // Exponential backoff reconnect
        const wait = Math.min(RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt.current), RECONNECT_MAX_MS);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(connect, wait);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      shouldRun.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (cursorFlushTimer.current) clearTimeout(cursorFlushTimer.current);
      socket?.close();
      ws.current = null;
      setConnected(false);
      setCursors({});
    };
  }, [projectId, token, canvasRef, canvasReady, userName, isSelf]);

  const broadcastCursor = useCallback((x: number, y: number) => {
    // Throttle cursor broadcasts (MED-4 audit) to avoid flooding the socket
    // with a message per mousemove. Send up to ~10/s and always flush the
    // latest position after the throttle window.
    const now = Date.now();
    if (now - lastCursorSend.current < CURSOR_THROTTLE_MS) {
      pendingCursor.current = { x, y };
      return;
    }
    lastCursorSend.current = now;
    pendingCursor.current = null;
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "cursor", x, y, name: userName }));
    }
    if (cursorFlushTimer.current) clearTimeout(cursorFlushTimer.current);
    cursorFlushTimer.current = setTimeout(() => {
      const p = pendingCursor.current;
      pendingCursor.current = null;
      if (p && ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "cursor", x: p.x, y: p.y, name: userName }));
      }
    }, CURSOR_THROTTLE_MS);
  }, [userName]);

  const broadcastObjectUpdate = useCallback(
    (
      type: "object_modified" | "object_added" | "object_removed",
      obj: { id?: string; toJSON?: () => Record<string, unknown> }
    ) => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        if (type === "object_removed") {
          ws.current.send(JSON.stringify({ type, objId: obj.id }));
        } else {
          const objData: Record<string, unknown> = obj.toJSON
            ? obj.toJSON()
            : { ...(obj as unknown as Record<string, unknown>) };
          objData.id = obj.id;
          if (obj.id) ignoreNextUpdateIds.current.add(obj.id);
          ws.current.send(JSON.stringify({ type, objData }));
        }
      }
    },
    []
  );

  return {
    cursors,
    connected,
    broadcastCursor,
    broadcastObjectUpdate,
  };
}
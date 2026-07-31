"use client";

import { useEffect, useRef, useState } from "react";

export interface PresenceUser {
  id: string;
  name: string;
  color: string;
  initials: string;
  avatar_initials?: string;
}

export interface UsePresenceOptions {
  siteKey?: string | null;
  slug?: string | null;
  token?: string | null;
  user?: {
    id?: string;
    name?: string;
    nombre_completo?: string;
    initials?: string;
    avatar_initials?: string;
    color?: string;
  } | null;
}

export interface UsePresenceReturn {
  presenceUsers: PresenceUser[];
  isConnected: boolean;
}

const RECONNECT_DELAYS = [1000, 2000, 4000];

export function usePresence({
  siteKey,
  slug,
  token,
  user,
}: UsePresenceOptions): UsePresenceReturn {
  const [presenceUsers, setPresenceUsers] = useState<PresenceUser[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef<number>(0);
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;

    if (!siteKey || !slug) {
      setPresenceUsers([]);
      setIsConnected(false);
      return;
    }

    // Determine active token or user json fallback token
    let activeToken = token;
    if (!activeToken && user) {
      const uId = user.id || "user-anon";
      const uName = user.nombre_completo || user.name || "Usuario";
      const uInitials = user.avatar_initials || user.initials || "U";
      const uColor = user.color || "#3B82F6";
      activeToken = JSON.stringify({
        id: uId,
        name: uName,
        initials: uInitials,
        color: uColor,
      });
    }

    const connectWebSocket = () => {
      if (!isMountedRef.current) return;

      // Close existing socket if any
      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
        socketRef.current = null;
      }

      let host = "localhost:8000";
      let protocol = "ws:";
      if (typeof window !== "undefined") {
        host = window.location.host;
        protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      }

      const wsBase = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${host}`;
      const encodedSiteKey = encodeURIComponent(siteKey);
      const encodedSlug = encodeURIComponent(slug);
      const queryParam = activeToken ? `?token=${encodeURIComponent(activeToken)}` : "";
      const wsUrl = `${wsBase}/api/cms/v2/ws/presence/${encodedSiteKey}/${encodedSlug}${queryParam}`;

      try {
        if (typeof window === "undefined" || typeof WebSocket === "undefined") {
          return;
        }
        const socket = new WebSocket(wsUrl);
        socketRef.current = socket;

        socket.onopen = () => {
          if (!isMountedRef.current) return;
          setIsConnected(true);
          retryCountRef.current = 0;
        };

        socket.onmessage = (event: MessageEvent) => {
          if (!isMountedRef.current) return;
          try {
            const data = JSON.parse(event.data);
            let rawUsers: unknown[] = [];
            if (Array.isArray(data)) {
              rawUsers = data;
            } else if (data && typeof data === "object") {
              if (Array.isArray((data as { presence_users?: unknown[] }).presence_users)) {
                rawUsers = (data as { presence_users: unknown[] }).presence_users;
              } else if (Array.isArray((data as { users?: unknown[] }).users)) {
                rawUsers = (data as { users: unknown[] }).users;
              }
            }

            const formattedUsers: PresenceUser[] = rawUsers.map((uItem, index) => {
              const u = (uItem || {}) as Record<string, unknown>;
              const uid = String(u.id || u.auth_user_id || u.identifier || `user-${index}`);
              const name = String(u.name || u.full_name || u.nombre_completo || "Usuario");
              const initials = String(u.initials || u.avatar_initials || name.slice(0, 2).toUpperCase());
              const color = String(u.color || "#3B82F6");
              return {
                id: uid,
                name,
                color,
                initials,
                avatar_initials: initials,
              };
            });

            setPresenceUsers(formattedUsers);
          } catch (err) {
            console.error("Failed to parse presence websocket message", err);
          }
        };

        socket.onerror = () => {
          if (!isMountedRef.current) return;
          setIsConnected(false);
        };

        socket.onclose = () => {
          if (!isMountedRef.current) return;
          setIsConnected(false);

          // Schedule automatic reconnect with exponential backoff (1s, 2s, 4s)
          const delayIndex = Math.min(retryCountRef.current, RECONNECT_DELAYS.length - 1);
          const delay = RECONNECT_DELAYS[delayIndex];
          retryCountRef.current += 1;

          reconnectTimerRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              connectWebSocket();
            }
          }, delay);
        };
      } catch (err) {
        console.error("Failed to initialize presence WebSocket", err);
      }
    };

    connectWebSocket();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [siteKey, slug, token, user]);

  return { presenceUsers, isConnected };
}

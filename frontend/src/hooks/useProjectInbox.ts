"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type { ProjectInboxItem } from "@/types/projects";

export interface UseProjectInboxResult {
  items: ProjectInboxItem[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  markAsRead: (itemId: string) => Promise<void>;
}

/**
 * Reads the existing unified projects inbox and scopes it to one project.
 * The backend remains the source of truth; local state only reflects the
 * optimistic read marker until the next refresh.
 */
export function useProjectInbox(projectId?: string | null): UseProjectInboxResult {
  const { token } = useAuth();
  const [items, setItems] = useState<ProjectInboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const readMutationRef = useRef(new Map<string, number>());

  const refresh = useCallback(async () => {
    if (!token || !projectId) {
      setItems([]);
      setLoading(false);
      return;
    }

    const requestId = ++requestIdRef.current;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ProjectInboxItem[]>("/projects/inbox", {
        token,
        cache: "no-store",
        query: { limit: 200 },
        signal: controller.signal,
      });
      if (requestId !== requestIdRef.current) return;
      const projectItems = Array.isArray(data)
        ? data.filter((item) => item.project_id === projectId)
        : [];
      setItems(projectItems);
    } catch {
      if (requestId !== requestIdRef.current) return;
      setItems([]);
      setError("No se pudo cargar el inbox del proyecto.");
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    void refresh();
    return () => {
      requestIdRef.current += 1;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [refresh]);

  const markAsRead = useCallback(async (itemId: string) => {
    if (!token) return;

    const current = items.find((item) => item.id === itemId);
    if (!current || current.is_read) return;

    const mutationId = Date.now() + Math.random();
    const previousRead = current.is_read;
    readMutationRef.current.set(itemId, mutationId);
    setItems((previous) => previous.map((item) => (
      item.id === itemId ? { ...item, is_read: true } : item
    )));

    try {
      await apiFetch(`/projects/inbox/${encodeURIComponent(itemId)}/read`, {
        method: "POST",
        token,
        body: { is_read: true },
      });
    } catch {
      if (readMutationRef.current.get(itemId) === mutationId) {
        setItems((previous) => previous.map((item) => (
          item.id === itemId ? { ...item, is_read: previousRead } : item
        )));
        setError("No se pudo marcar el elemento como leído.");
      }
    } finally {
      if (readMutationRef.current.get(itemId) === mutationId) {
        readMutationRef.current.delete(itemId);
      }
    }
  }, [items, token]);

  const unreadCount = useMemo(
    () => items.filter((item) => !item.is_read).length,
    [items],
  );

  return { items, unreadCount, loading, error, refresh, markAsRead };
}

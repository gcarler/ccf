"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";

export type CommentModuleType = "project" | "agenda";

export interface CommentAttachment {
  url: string;
  type: string;
  name: string;
  size: number;
}

export interface CommentCenterItem {
  id: string;
  project_id: string;
  task_id: string | null;
  author_id: string | null;
  author_name: string;
  content: string;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
  attachments: CommentAttachment[];
  mentions: string[];
  module_type: CommentModuleType;
  context_title: string | null;
}

export type CommentCenterTab = "created" | "mentions";

export interface UseCommentCenterOptions {
  tab: CommentCenterTab;
  typeFilter: "all" | CommentModuleType;
  limit?: number;
}

export function useCommentCenter({ tab, typeFilter, limit = 50 }: UseCommentCenterOptions) {
  const [items, setItems] = useState<CommentCenterItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query: Record<string, string> = { limit: String(limit) };
      if (typeFilter !== "all") {
        query.type = typeFilter;
      }
      const data = await apiFetch<CommentCenterItem[]>(`/api/comments/me/${tab}`, {
        query,
      });
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar comentarios");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [tab, typeFilter, limit]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  return { items, loading, error, refresh: fetchItems };
}

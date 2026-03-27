"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/http";
import type { GraphSnapshot } from "@/types/graph";

type UseGraphInsightsOptions = {
  types?: string[];
  limit?: number;
  offset?: number;
  enabled?: boolean;
};

export function useGraphInsights({
  types = [],
  limit = 120,
  offset = 0,
  enabled = true,
}: UseGraphInsightsOptions = {}) {
  const [snapshot, setSnapshot] = useState<GraphSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(
    () => ({
      limit,
      offset,
      types: types.join(","),
    }),
    [limit, offset, types],
  );

  const refresh = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<GraphSnapshot>("/graph/snapshot", { cache: "no-store", query });
      setSnapshot(data);
    } catch (err) {
      console.error(err);
      setError("No pudimos cargar insights del grafo.");
    } finally {
      setLoading(false);
    }
  }, [enabled, query]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const insights = useMemo(() => {
    if (!snapshot) return [] as Array<{ id: string; label: string; value: string }>;
    const counts = snapshot.meta?.counts || {};
    const items = [
      { id: "nodes", label: "Nodos", value: String(counts.nodes || 0) },
      { id: "edges", label: "Conexiones", value: String(counts.edges || 0) },
      { id: "courses", label: "Cursos", value: String(counts.courses || 0) },
      { id: "people", label: "Personas", value: String(counts.people || 0) },
      { id: "assets", label: "Activos", value: String(counts.assets || 0) },
    ];
    return items;
  }, [snapshot]);

  return {
    snapshot,
    insights,
    loading,
    error,
    refresh,
  };
}

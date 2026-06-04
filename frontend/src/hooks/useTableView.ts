"use client";

import { useCallback,useRef,useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/http";

export interface TableHistoryEntry {
  rowId: string;
  colId: string;
  oldValue: any;
  newValue: any;
}

export interface UseTableViewOptions {
  storageKey?: string;
  apiEndpoint?: string;
  token?: string;
}

export function useTableView(options: UseTableViewOptions = {}) {
  const { apiEndpoint, token } = options;

  const [history, setHistory] = useState<TableHistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const optimisticCache = useRef<Map<string, Record<string, any>>>(new Map());

  const recordChange = useCallback((rowId: string, colId: string, oldValue: any, newValue: any) => {
    setHistory(prev => [...prev.slice(0, historyIndex + 1), { rowId, colId, oldValue, newValue }]);
    setHistoryIndex(prev => prev + 1);
  }, [historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex < 0) return null;
    const entry = history[historyIndex];
    setHistoryIndex(prev => prev - 1);
    return { rowId: entry.rowId, colId: entry.colId, value: entry.oldValue };
  }, [history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex >= history.length - 1) return null;
    const entry = history[historyIndex + 1];
    setHistoryIndex(prev => prev + 1);
    return { rowId: entry.rowId, colId: entry.colId, value: entry.newValue };
  }, [history, historyIndex]);

  const handleChange = useCallback(async (rowId: string, colId: string, newValue: any) => {
    const oldValue = optimisticCache.current.get(rowId)?.[colId];
    recordChange(rowId, colId, oldValue ?? null, newValue);

    if (apiEndpoint && token) {
      try {
        await apiFetch(`${apiEndpoint}/${rowId}`, {
          method: "PATCH",
          token,
          body: { [colId]: newValue },
        });
      } catch {
        toast.error("Error al guardar cambio");
      }
    }
  }, [apiEndpoint, token, recordChange]);

  const clearHistory = useCallback(() => {
    setHistory([]);
    setHistoryIndex(-1);
  }, []);

  return {
    handleChange,
    undo,
    redo,
    canUndo: historyIndex >= 0,
    canRedo: historyIndex < history.length - 1,
    historyLength: history.length,
    clearHistory,
  };
}

"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiFetch } from "@/lib/http";

export interface ContentBlock {
  page_key: string;
  content?: string;
  raw_content?: string;
  [key: string]: any;
}

export interface ParsedContentBlock extends ContentBlock {
  parsed?: Record<string, unknown> | string;
}

interface HookState<T> {
  data: T;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

const INITIAL_STATE = { data: null, loading: false, error: null } as const;

export function mergeContent(block?: ContentBlock | null): ParsedContentBlock | null {
  if (!block) return null;
  if (!block.content) {
    return { ...block };
  }

  try {
    const parsed = JSON.parse(block.content);
    if (parsed && typeof parsed === "object") {
      const reserved = new Set(["page_key", "title", "image_url", "id", "created_at", "updated_at"]);
      const sanitizedEntries = Object.entries(parsed).filter(([key]) => !reserved.has(key));
      const sanitized = Object.fromEntries(sanitizedEntries);
      return { ...block, ...sanitized, parsed, raw_content: block.content };
    }
    return { ...block, parsed, raw_content: block.content };
  } catch {
    return { ...block, parsed: block.content, raw_content: block.content };
  }
}

export function useContentBlock(key?: string, { enabled = true }: { enabled?: boolean } = {}): HookState<ParsedContentBlock | null> {
  const [data, setData] = useState<ParsedContentBlock | null>(INITIAL_STATE.data);
  const [loading, setLoading] = useState<boolean>(!!key && enabled);
  const [error, setError] = useState<Error | null>(INITIAL_STATE.error);

  const load = useCallback(async () => {
    if (!key || !enabled) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<ContentBlock>(`/cms/content/${key}`, { cache: "no-store" });
      setData(mergeContent(response));
    } catch (err) {
      setError(err as Error);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [key, enabled]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, refresh: load };
}

export function useContentBlocks(keys: string[], { enabled = true }: { enabled?: boolean } = {}): HookState<Record<string, ParsedContentBlock | null>> {
  const normalizedKeys = useMemo(() => keys.filter(Boolean), [keys]);
  const [data, setData] = useState<Record<string, ParsedContentBlock | null>>({});
  const [loading, setLoading] = useState<boolean>(normalizedKeys.length > 0 && enabled);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      setData({});
      return;
    }

    if (normalizedKeys.length === 0) {
      setData({});
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const entries = await Promise.all(
        normalizedKeys.map(async (key) => {
          try {
            const response = await apiFetch<ContentBlock>(`/cms/content/${key}`, { cache: "no-store" });
            return [key, mergeContent(response)];
          } catch (err) {
            console.error(`Content block ${key} failed`, err);
            return [key, null];
          }
        })
      );
      setData(Object.fromEntries(entries));
    } catch (err) {
      setError(err as Error);
      setData({});
    } finally {
      setLoading(false);
    }
  }, [enabled, normalizedKeys]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, refresh: load };
}

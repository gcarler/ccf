"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, Loader2, Search, User, X } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useOptionalAuth } from "@/context/AuthContext";

interface UserRecord {
  id: string;
  username: string;
}

export function normalizeText(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

/**
 * TCR-003 · PR-2 — Priorización en cliente por prefijo:
 * - Tier 0: nombre de usuario empieza por el término ('l' -> Laura/Luis, 'ca' -> Carlos/Camilo).
 * - Tier 1: apellido o palabra secundaria empieza por el término ('l' -> Ana López, Juan Luis).
 * - Tier 2: coincidencia parcial ('l' -> Mila Ferrer).
 * - Tier 3: resto de candidatos.
 * Conserva el orden alfabético dentro de cada tier.
 */
export function clientPrefixSortUsers(list: UserRecord[], termRaw: string): UserRecord[] {
  const term = normalizeText(termRaw);
  if (!term) return list;
  const tokens = term.split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return list;

  const filtered = list.filter((u) => {
    const full = normalizeText(u.username);
    return tokens.every((tok) => full.includes(tok));
  });

  const rank = (u: UserRecord) => {
    const full = normalizeText(u.username);
    if (full.startsWith(term) || (tokens.length > 0 && full.startsWith(tokens[0]))) return 0;
    const words = full.split(/\s+/);
    if (words.some((w, idx) => idx > 0 && w.startsWith(tokens[0]))) return 1;
    return 2;
  };

  return filtered.sort((a, b) => {
    const ra = rank(a);
    const rb = rank(b);
    if (ra !== rb) return ra - rb;
    return a.username.localeCompare(b.username, "es", { sensitivity: "base" });
  });
}

interface PersonaLookupRecord {
  id: string;
  nombre_completo?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  username?: string | null;
  user?: { id?: string | null; username?: string | null } | null;
}

interface InlineUserPickerProps {
  value?: string | null;
  onChange: (userId: string | null, userName: string | null) => void;
  disabled?: boolean;
  endpoint?: string;
}

export function InlineUserPicker({ value, onChange, disabled, endpoint = "/crm/personas" }: InlineUserPickerProps) {
  const auth = useOptionalAuth();
  const token = auth?.token;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const nextPageRef = useRef<number | null>(null);
  const termRef = useRef<string>("");
  const [loadError, setLoadError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const lastFetchedValueRef = useRef<string | null | undefined>(undefined);

  // Sync displayName when the externally-provided value changes (e.g. row reload).
  // If we already have the user in the cached list, reuse it; otherwise hit the API.
  // Also re-syncs when the value changes WHILE closed (e.g. after PATCH success).
  //
  // ``displayName`` is intentionally NOT in the deps array: including it would
  // re-fire this effect every time we write the new name, which can double-
  // fetch and waste bandwidth. We read it through a stable ref for comparison.
  const displayNameRef = useRef<string | null>(null);
  useEffect(() => { displayNameRef.current = displayName; }, [displayName]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedQuery(query), 300);
    return () => window.clearTimeout(timeoutId);
  }, [query]);

  useEffect(() => {
    if (!value) {
      if (displayNameRef.current !== null) setDisplayName(null);
      return;
    }
    const found = users.find((u) => u.id === value);
    if (found) {
      if (found.username !== displayNameRef.current) setDisplayName(found.username);
      lastFetchedValueRef.current = value;
      return;
    }
    if (lastFetchedValueRef.current === value) return;
    lastFetchedValueRef.current = value;
    let canceled = false;
    const controller = new AbortController();
    apiFetch<PersonaLookupRecord>(`${endpoint}/${encodeURIComponent(value)}`, {
      method: "GET",
      token: token ?? undefined,
      signal: controller.signal,
    })
      .then((m) => {
        if (canceled) return;
        const fullName = [m.first_name, m.last_name].filter(Boolean).join(" ").trim();
        const name = m.nombre_completo || fullName || m.user?.username || m.username || null;
        if (name && name !== displayNameRef.current) setDisplayName(name);
      })
      .catch(() => {
        /* leave displayName as-is; user can re-open picker to retry */
      });
    return () => {
      canceled = true;
      controller.abort();
    };
  }, [value, users, token, endpoint]);

  const PAGE_SIZE = 1000;

  const loadPage = useCallback(
    async (trimmed: string, page: number, append: boolean, signal?: AbortSignal) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setLoadError(false);
      }
      try {
        const data = await apiFetch<PersonaLookupRecord[]>(endpoint, {
          method: "GET",
          token: token ?? undefined,
          query: { search: trimmed || undefined, limit: PAGE_SIZE, skip: page * PAGE_SIZE },
          signal,
        });
        if (signal?.aborted) return;
        const list: UserRecord[] = Array.isArray(data)
          ? data.map((person) => {
              const fullName = [person.first_name, person.last_name].filter(Boolean).join(" ").trim();
              return {
                id: String(person.user?.id ?? person.id),
                username:
                  person.nombre_completo || fullName || person.user?.username || person.username || `#${person.id}`,
              };
            })
          : [];
        setUsers((prev) => {
          if (!append) return list;
          const seen = new Set(prev.map((u) => u.id));
          return [...prev, ...list.filter((u) => !seen.has(u.id))];
        });
        termRef.current = trimmed;
        const hasNext = list.length === PAGE_SIZE;
        nextPageRef.current = hasNext ? page + 1 : null;
        setHasMore(hasNext);
        if (!append && value) {
          const found = list.find((u) => u.id === value);
          if (found) setDisplayName(found.username);
        }
      } catch {
        if (!signal?.aborted && !append) {
          setUsers([]);
          setLoadError(true);
        }
      } finally {
        if (!signal?.aborted) {
          if (append) setLoadingMore(false);
          else setLoading(false);
        }
      }
    },
    [endpoint, token, value]
  );

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void loadPage(debouncedQuery.trim(), 0, false, controller.signal);
    return () => controller.abort();
  }, [open, debouncedQuery, retryKey, loadPage]);

  const handleLoadMore = useCallback(() => {
    if (nextPageRef.current === null || loading || loadingMore) return;
    const controller = new AbortController();
    void loadPage(termRef.current, nextPageRef.current, true, controller.signal);
  }, [loadPage, loading, loadingMore]);

  const isDebouncing = query.trim() !== debouncedQuery.trim();
  const activeTerm = query.trim() || debouncedQuery.trim();
  const filtered = clientPrefixSortUsers(users, activeTerm);

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
      if (scrollHeight - scrollTop - clientHeight < 48) {
        if (hasMore && !loading && !loadingMore && nextPageRef.current !== null) {
          handleLoadMore();
        }
      }
    },
    [hasMore, loading, loadingMore, handleLoadMore]
  );

  const initials = displayName?.slice(0, 2).toUpperCase() || "";

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "group flex items-center justify-center min-w-[40px] min-h-[40px] rounded-lg transition-all",
            "hover:bg-[hsl(var(--surface-2))] dark:hover:bg-[hsl(var(--surface-2))]",
            open && "bg-info-soft ring-1 ring-info/30",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          title={displayName ? `Asignado a ${displayName}` : "Asignar persona"}
          aria-label="Selector de persona asignada"
        >
          {value ? (
            <div className="size-6 rounded-full bg-gradient-to-br from-primary to-info flex items-center justify-center font-semibold text-white shrink-0 shadow-sm text-2xs">
              {initials}
            </div>
          ) : (
            <div className="size-6 rounded-full bg-[hsl(var(--surface-3))] dark:bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--info-muted))] dark:group-hover:bg-[hsl(var(--info)/0.2)] group-hover:text-[hsl(var(--primary))] transition-colors">
              <User size={12} />
            </div>
          )}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] w-[240px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-[hsl(var(--border))] overflow-hidden"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))]">
            {loading || isDebouncing ? (
              <Loader2 size={13} className="text-[hsl(var(--primary))] shrink-0 animate-spin" />
            ) : (
              <Search size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />
            )}
            <input
              aria-label="Buscar persona asignable"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar usuario..."
              className="flex-1 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-transparent outline-none placeholder:text-[hsl(var(--text-secondary))]"
            />
            {query && (
              <button type="button" aria-label="Limpiar búsqueda" onClick={() => setQuery("")}>
                <X size={12} className="text-[hsl(var(--text-secondary))]" />
              </button>
            )}
          </div>
          <div
            className="max-h-[200px] overflow-y-auto py-1"
            aria-busy={loading || isDebouncing}
            onScroll={handleScroll}
          >
            {value && (
              <button
                type="button"
                aria-label="Quitar asignación"
                onClick={() => {
                  onChange(null, null);
                  setDisplayName(null);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-[hsl(var(--danger-muted))] dark:hover:bg-[hsl(var(--danger)/0.1)] text-danger transition-colors"
              >
                <X size={12} />
                <span className="text-xs font-bold">Quitar asignación</span>
              </button>
            )}
            {(loading || isDebouncing) && filtered.length === 0 ? (
              <div className="flex items-center justify-center py-1.5">
                <Loader2 size={16} className="text-[hsl(var(--primary))] animate-spin" />
              </div>
            ) : loadError ? (
              <div className="px-3 py-2 text-center" role="alert">
                <p className="text-xs text-[hsl(var(--destructive))]">No se pudieron cargar las personas.</p>
                <button
                  type="button"
                  className="mt-1 text-xs font-medium text-[hsl(var(--primary))] underline-offset-2 hover:underline"
                  onClick={() => setRetryKey((current) => current + 1)}
                >
                  Reintentar
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-1.5">Sin resultados</p>
            ) : (
              <>
                {filtered.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => {
                      onChange(u.id, u.username);
                      setDisplayName(u.username);
                      setOpen(false);
                    }}
                    className={clsx(
                      "w-full flex items-center gap-2.5 px-3 py-2 transition-colors",
                      u.id === value
                        ? "bg-info-soft text-info-text"
                        : "hover:bg-[hsl(var(--surface-1))] dark:hover:bg-[hsl(var(--surface-2))]"
                    )}
                  >
                    <div className="size-6 rounded-full bg-info-soft flex items-center justify-center font-semibold text-info-text shrink-0 text-2xs">
                      {u.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{u.username}</p>
                    </div>
                    {u.id === value && <Check size={12} className="text-[hsl(var(--primary))]" />}
                  </button>
                ))}
                {hasMore && (
                  <button
                    type="button"
                    data-testid="userpicker-load-more"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="w-full flex items-center justify-center gap-1.5 py-2 text-2xs font-bold text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-[hsl(var(--surface-2))] transition-colors disabled:opacity-60"
                  >
                    {loadingMore && <Loader2 size={10} className="animate-spin" />}
                    Cargar más personas
                  </button>
                )}
              </>
            )}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

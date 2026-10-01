"use client";

import React, { useEffect, useRef, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, Loader2, Search, User, X } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

interface UserRecord {
  id: string;
  username: string;
  email?: string;
}

interface PersonaApiRecord {
  id: string | number;
  nombre_completo?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  username?: string | null;
  email?: string | null;
  user?: {
    id?: string | number;
    username?: string | null;
    email?: string | null;
  } | null;
}

function toUserRecord(persona: PersonaApiRecord): UserRecord {
  const fullName = [persona.first_name, persona.last_name].filter(Boolean).join(" ");
  return {
    id: String(persona.user?.id ?? persona.id),
    username:
      persona.nombre_completo ||
      fullName ||
      persona.user?.username ||
      persona.username ||
      `#${persona.id}`,
    email: persona.user?.email ?? persona.email ?? undefined,
  };
}

interface InlineUserPickerProps {
  value?: string | null;
  onChange: (userId: string | null, userName: string | null) => void;
  disabled?: boolean;
}

export function InlineUserPicker({ value, onChange, disabled }: InlineUserPickerProps) {
  const { token } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
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
    if (!value) {
      lastFetchedValueRef.current = null;
      if (displayNameRef.current !== null) setDisplayName(null);
      return;
    }
    const found = users.find(u => u.id === value);
    if (found) {
      if (found.username !== displayNameRef.current) setDisplayName(found.username);
      lastFetchedValueRef.current = value;
      return;
    }
    if (lastFetchedValueRef.current === value) return;
    lastFetchedValueRef.current = value;
    let canceled = false;
    apiFetch<PersonaApiRecord>(`/crm/personas/${encodeURIComponent(value)}`, { method: "GET", token: token ?? undefined })
      .then(persona => {
        if (canceled) return;
        const name = toUserRecord(persona).username;
        if (name && name !== displayNameRef.current) setDisplayName(name);
      })
      .catch(() => {
        /* leave displayName as-is; user can re-open picker to retry */
      });
    return () => {
      canceled = true;
    };
  }, [value, users, token]);

  useEffect(() => {
    if (!open) {
      setLoading(false);
      return;
    }

    let canceled = false;
    const controller = new AbortController();
    setLoading(true);
    const trimmed = query.trim();
    const timeoutId = setTimeout(() => {
      apiFetch<PersonaApiRecord[]>("/crm/personas", {
        method: "GET",
        token: token ?? undefined,
        query: { search: trimmed || undefined, limit: 50 },
        signal: controller.signal,
      })
        .then(data => {
          if (canceled) return;
          const list: UserRecord[] = Array.isArray(data)
            ? data.map(toUserRecord)
            : [];
          setUsers(list);
          if (value) {
            const found = list.find(u => u.id === value);
            if (found) setDisplayName(found.username);
          }
        })
        .catch(() => {
          if (!canceled && !controller.signal.aborted) {
            setUsers([]);
            toast.error("No se pudieron cargar las personas.");
          }
        })
        .finally(() => {
          if (!canceled) setLoading(false);
        });
    }, 300);

    return () => {
      canceled = true;
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [open, query, token, value]);

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
            open && "bg-[hsl(var(--surface-2))] ring-1 ring-[hsl(var(--primary))]/30",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          title={displayName ? `Asignado a ${displayName}` : "Asignar persona"}
          aria-label="Selector de persona asignada"
        >
          {value ? (
            <div className="size-6 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center font-semibold shrink-0 shadow-sm text-2xs">
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
            <Search size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar usuario..."
              className="flex-1 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-transparent outline-none placeholder:text-[hsl(var(--text-secondary))]"
            />
            {query && (
              <button aria-label="Limpiar búsqueda" onClick={() => setQuery("")}>
                <X size={12} className="text-[hsl(var(--text-secondary))]" />
              </button>
            )}
          </div>
          <div className="max-h-[200px] overflow-y-auto py-1">
            {value && (
              <button
                onClick={() => {
                  onChange(null, null);
                  setDisplayName(null);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))] transition-colors"
              >
                <X size={12} />
                <span className="text-xs font-bold">Quitar asignación</span>
              </button>
            )}
            {loading ? (
              <div className="flex items-center justify-center py-1.5" role="status" aria-label="Buscando personas">
                <Loader2 size={16} className="text-[hsl(var(--primary))] animate-spin" />
              </div>
            ) : users.length === 0 ? (
              <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-1.5">Sin resultados</p>
            ) : (
              <>
                {users.map((u) => (
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
                        ? "bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]"
                        : "hover:bg-[hsl(var(--surface-1))] dark:hover:bg-[hsl(var(--surface-2))]"
                    )}
                  >
                    <div className="size-6 rounded-full bg-[hsl(var(--surface-2))] flex items-center justify-center font-semibold text-[hsl(var(--text-primary))] shrink-0 text-2xs">
                      {u.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{u.username}</p>
                      {u.email && <p className="text-2xs text-[hsl(var(--text-secondary))] truncate">{u.email}</p>}
                    </div>
                    {u.id === value && <Check size={12} className="text-[hsl(var(--primary))]" />}
                  </button>
                ))}
              </>
            )}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

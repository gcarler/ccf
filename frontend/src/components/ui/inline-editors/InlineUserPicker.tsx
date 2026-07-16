"use client";

import React, { useEffect, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, Loader2, Search, User, X } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";

interface UserRecord {
  id: string;
  username: string;
  email?: string;
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

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    apiFetch<any[]>("/crm/personas/", { method: "GET", token: token ?? undefined })
      .then((data) => {
        const list: UserRecord[] = Array.isArray(data)
          ? data.map((m: any) => ({
              id: String(m.user?.id ?? m.id),
              username: m.nombre_completo || m.user?.username || m.username || `#${m.id}`,
              email: m.user?.email ?? m.email,
            }))
          : [];
        setUsers(list);
        if (value) {
          const found = list.find((u) => u.id === value);
          if (found) setDisplayName(found.username);
        }
      })
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  }, [open, token, value]);

  const filtered = query
    ? users.filter((u) => u.username.toLowerCase().includes(query.toLowerCase()))
    : users;

  const initials = displayName?.slice(0, 2).toUpperCase() || "";

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "group flex items-center justify-center min-w-[40px] min-h-[40px] rounded-lg transition-all",
            "hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5",
            open && "bg-blue-50 dark:bg-blue-500/10 ring-1 ring-blue-300 dark:ring-blue-500/40",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          title={displayName ? `Asignado a ${displayName}` : "Asignar persona"}
          aria-label="Selector de persona asignada"
        >
          {value ? (
            <div className="size-6 rounded-full bg-gradient-to-br from-blue-500 to-sky-600 flex items-center justify-center font-semibold text-white shrink-0 shadow-sm text-[10px]">
              {initials}
            </div>
          ) : (
            <div className="size-6 rounded-full bg-[hsl(var(--surface-3))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] group-hover:bg-blue-100 dark:group-hover:bg-blue-500/20 group-hover:text-[hsl(var(--primary))] transition-colors">
              <User size={12} />
            </div>
          )}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] w-[240px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 overflow-hidden"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[hsl(var(--border))] dark:border-white/5">
            <Search size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar usuario..."
              className="flex-1 text-[12px] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-transparent outline-none placeholder:text-[hsl(var(--text-secondary))]"
            />
            {query && (
              <button onClick={() => setQuery("")}>
                <X size={12} className="text-[hsl(var(--text-secondary))]" />
              </button>
            )}
          </div>
          <div className="max-h-[200px] overflow-y-auto py-1">
            {loading ? (
              <div className="flex items-center justify-center py-1.5">
                <Loader2 size={16} className="text-[hsl(var(--primary))] animate-spin" />
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center py-1.5">Sin resultados</p>
            ) : (
              <>
                {value && (
                  <button
                    onClick={() => {
                      onChange(null, null);
                      setDisplayName(null);
                      setOpen(false);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500 transition-colors"
                  >
                    <X size={12} />
                    <span className="text-[11px] font-bold">Quitar asignación</span>
                  </button>
                )}
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
                        ? "bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-blue-300"
                        : "hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                    )}
                  >
                    <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center font-semibold text-[hsl(var(--primary))] shrink-0 text-[10px]">
                      {u.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{u.username}</p>
                      {u.email && <p className="text-[10px] text-[hsl(var(--text-secondary))] truncate">{u.email}</p>}
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

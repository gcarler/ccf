"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Check, ChevronDown, User as UserIcon, Search, Shield, Loader2, CircleAlert } from "lucide-react";

export interface PersonaOption {
    id: string;
    first_name?: string;
    last_name?: string;
    nombre_completo?: string;
    church_role?: string;
    spiritual_status?: string;
}

export interface PersonaSelectProps {
    value: string | null;
    onChange: (personaId: string | null) => void;
    placeholder?: string;
    className?: string;
    showMetadata?: boolean;
}

const PAGE_SIZE = 1000;

export function displayName(p: PersonaOption): string {
    if (p.nombre_completo) return p.nombre_completo;
    return [p.first_name, p.last_name].filter(Boolean).join(" ") || "Sin nombre";
}

function nameParts(p: PersonaOption): string {
    if (p.nombre_completo) return p.nombre_completo;
    return [p.first_name, p.last_name].filter(Boolean).join(" ");
}

export function normalizeText(text: string): string {
    return text
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

/**
 * TCR-003 · PR-2 — Priorización en cliente por prefijo con filtrado estricto:
 * - Filtra: la persona DEBE contener todos los tokens normalizados sin tildes.
 * - Tier 0: primer nombre o nombre completo empieza por el término ('l' -> Laura/Luis, 'ca' -> Carlos/Camilo).
 * - Tier 1: apellido o segunda palabra empieza por el término ('l' -> Ana López, Juan Luis).
 * - Tier 2: coincidencia parcial en nombre/apellido ('l' -> Mila Ferrer).
 * Dentro de cada tier se conserva el orden alfabético por nombre completo.
 */
export function clientPrefixSort(list: PersonaOption[], termRaw: string): PersonaOption[] {
    const term = normalizeText(termRaw);
    if (!term) return list;
    const tokens = term.split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return list;

    const filtered = list.filter((p) => {
        const name = normalizeText(nameParts(p));
        const first = normalizeText(p.first_name ?? "");
        const last = normalizeText(p.last_name ?? "");
        const full = `${name} ${first} ${last}`;
        return tokens.every((tok) => full.includes(tok));
    });

    const rank = (p: PersonaOption) => {
        const name = normalizeText(nameParts(p));
        const first = normalizeText(p.first_name ?? "");
        const last = normalizeText(p.last_name ?? "");
        if (first.startsWith(term) || name.startsWith(term) || (tokens.length > 0 && (first.startsWith(tokens[0]) || name.startsWith(tokens[0])))) return 0;
        const words = name.split(/\s+/);
        if (last.startsWith(term) || (tokens.length > 0 && last.startsWith(tokens[0])) || words.some((w, idx) => idx > 0 && w.startsWith(tokens[0]))) return 1;
        return 2;
    };

    return filtered.sort((a, b) => {
        const ra = rank(a);
        const rb = rank(b);
        if (ra !== rb) return ra - rb;
        return nameParts(a).localeCompare(nameParts(b), "es", { sensitivity: "base" });
    });
}

export default function PersonaSelect({
    value,
    onChange,
    placeholder = "Sin asignar",
    className = "",
    showMetadata = true,
}: PersonaSelectProps) {
    const { token } = useAuth();
    const [open, setOpen] = useState(false);
    const [personas, setPersonas] = useState<PersonaOption[]>([]);
    const [selectedPersona, setSelectedPersona] = useState<PersonaOption | null>(null);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [loading, setLoading] = useState(false);
    const [loadError, setLoadError] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const activeTermRef = useRef<string>(""); // término original (sin trim) de la página cargada
    const nextPageRef = useRef<number | null>(null);
    // Espejo síncrono de `personas` para fusionar páginas dentro de callbacks.
    const personasRef = useRef<PersonaOption[]>([]);
    useEffect(() => {
        personasRef.current = personas;
    }, [personas]);

    // Debounce de 300ms para la búsqueda reactiva
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedSearch(search);
        }, 300);
        return () => clearTimeout(handler);
    }, [search]);

    const fetchPage = useCallback(
        async (
            query: string,
            skip: number,
            append: boolean
        ): Promise<{ ok: boolean; list: PersonaOption[] }> => {
            if (!token) return { ok: false, list: [] };
            const active = true;
            if (!append) {
                setLoading(true);
                setLoadError(false);
            } else {
                setLoadingMore(true);
            }
            try {
                const params = new URLSearchParams({ limit: String(PAGE_SIZE), skip: String(skip) });
                if (query) params.set("search", query);
                const endpoint = `/crm/personas?${params.toString()}`;
                const data = await apiFetch<PersonaOption[]>(endpoint, { token });
                if (!active) return { ok: false, list: [] };
                const list = Array.isArray(data) ? data : [];
                const base = append ? personasRef.current : [];
                const seen = new Set(base.map((p) => p.id));
                const merged = [...base];
                for (const p of list) {
                    if (p && p.id && !seen.has(p.id)) {
                        seen.add(p.id);
                        merged.push(p);
                    }
                }
                setPersonas(merged);
                // El backend anota `next_page` absoluta (sub-skip); si no viene,
                // inferimos que hay más cuando la página vino llena.
                const reported = (data as unknown as { next_page?: unknown } | null)?.next_page;
                const hasNext = typeof reported === "number" && reported > 0;
                nextPageRef.current = hasNext
                    ? (reported as number)
                    : list.length === PAGE_SIZE
                      ? Math.floor(skip / PAGE_SIZE) + 1
                      : null;
                activeTermRef.current = query;
                setHasMore(hasNext || list.length === PAGE_SIZE);
                return { ok: true, list: merged };
            } catch (err) {
                console.error("[PersonaSelect] Error cargando personas:", err);
                if (!append) setLoadError(true);
                return { ok: false, list: [] };
            } finally {
                if (active) {
                    if (!append) setLoading(false);
                    else setLoadingMore(false);
                }
            }
        },
        [token]
    );

    const fetchFromFallback = useCallback(
        async (query: string): Promise<{ ok: boolean; list: PersonaOption[] }> => {
            if (!token) return { ok: false, list: [] };
            setLoading(true);
            setLoadError(false);
            const active = true;
            try {
                const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
                if (query) params.set("search", query);
                const endpoint = `/projects/assignee-candidates?${params.toString()}`;
                const data = await apiFetch<PersonaOption[]>(endpoint, { token });
                if (!active) return { ok: false, list: [] };
                const list = Array.isArray(data) ? data : [];
                setPersonas(list);
                setHasMore(false);
                return { ok: true, list };
            } catch (err) {
                console.error("[PersonaSelect] Error en endpoint alternativo:", err);
                if (active) setLoadError(true);
                return { ok: false, list: [] };
            } finally {
                if (active) setLoading(false);
            }
        },
        [token]
    );

    // Búsqueda server-side reactiva con debounce y paginación incremental
    useEffect(() => {
        if (!token) return;
        let cancelled = false;

        const query = debouncedSearch.trim();
        void (async () => {
            const result = await fetchPage(query, 0, false);
            // Reintento por un path / fallback solo si falló la primera vez
            if (!result.ok && !cancelled) {
                const fallback = await fetchFromFallback(query);
                if (fallback.ok) return;
            }
            if (!cancelled && value) {
                // Si hay un value seleccionado y está en la lista obtenida, sincronizar selectedPersona
                const match = result.list.find((p) => p.id === value);
                if (match) setSelectedPersona(match);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [token, debouncedSearch, fetchPage, fetchFromFallback, value]);

    const handleLoadMore = useCallback(async () => {
        if (nextPageRef.current === null || loading || loadingMore) return;
        const term = activeTermRef.current;
        await fetchPage(term, nextPageRef.current * PAGE_SIZE, true);
    }, [fetchPage, loading, loadingMore]);

    const handleRetry = useCallback(async () => {
        const term = debouncedSearch.trim();
        const result = await fetchPage(term, 0, false);
        if (result.ok) return;
        await fetchFromFallback(term);
    }, [debouncedSearch, fetchPage, fetchFromFallback]);

    // Preservar / consultar la persona seleccionada por ID si no está en la lista actual
    useEffect(() => {
        if (!value) {
            setSelectedPersona(null);
            return;
        }

        // Si ya tenemos la persona seleccionada con ese id, no re-consultar
        if (selectedPersona && selectedPersona.id === value) {
            return;
        }

        // Si está en la lista actual de personas cargadas, usarla
        const found = personas.find((p) => p.id === value);
        if (found) {
            setSelectedPersona(found);
            return;
        }

        // Si no está en personas y tenemos token, consultar /crm/personas/{value}
        if (!token) return;

        let active = true;
        apiFetch<PersonaOption>(`/crm/personas/${value}`, { token })
            .then((data) => {
                if (active && data && data.id) {
                    setSelectedPersona(data);
                }
            })
            .catch((err) => {
                console.error("[PersonaSelect] Error al consultar persona por id:", err);
            });

        return () => {
            active = false;
        };
    }, [value, personas, selectedPersona, token]);

    // Manejo de clic fuera para cerrar el menú desplegable
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    // Autofocus en el input al abrir el dropdown
    useEffect(() => {
        if (open) {
            inputRef.current?.focus();
        }
    }, [open]);

    // La persona seleccionada para mostrar en el botón
    const currentSelected = selectedPersona || personas.find((p) => p.id === value);
    const activeSearch = search.trim() || debouncedSearch.trim();
    const sortedPersonas = clientPrefixSort(personas, activeSearch);

    const handleScroll = useCallback(
        (e: React.UIEvent<HTMLDivElement>) => {
            const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
            if (scrollHeight - scrollTop - clientHeight < 48) {
                if (hasMore && !loading && !loadingMore && nextPageRef.current !== null) {
                    void handleLoadMore();
                }
            }
        },
        [hasMore, loading, loadingMore, handleLoadMore]
    );

    const handleSelect = useCallback(
        (persona: PersonaOption) => {
            setSelectedPersona(persona);
            onChange(persona.id);
            setOpen(false);
            setSearch("");
            triggerRef.current?.focus();
        },
        [onChange]
    );

    const handleClear = useCallback(() => {
        setSelectedPersona(null);
        onChange(null);
        setOpen(false);
        setSearch("");
        triggerRef.current?.focus();
    }, [onChange]);

    return (
        <div ref={ref} className={`relative ${className}`}>
            <button
                ref={triggerRef}
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm font-medium text-left hover:border-[hsl(var(--primary)_/_0.6)] transition-colors"
                aria-haspopup="listbox"
                aria-expanded={open}
                aria-controls={open ? "persona-select-options" : undefined}
            >
                {currentSelected ? (
                    <>
                        <div className="size-6 rounded-full bg-[hsl(var(--primary)_/_0.12)] flex items-center justify-center shrink-0">
                            <UserIcon size={12} className="text-[hsl(var(--primary))]" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">
                                {displayName(currentSelected)}
                            </p>
                            {showMetadata && currentSelected.church_role && (
                                <p className="text-2xs text-[hsl(var(--text-secondary))] truncate">
                                    {currentSelected.church_role}
                                </p>
                            )}
                        </div>
                    </>
                ) : (
                    <span className="text-xs text-[hsl(var(--foreground))]">{placeholder}</span>
                )}
                <ChevronDown
                    size={14}
                    className={`ml-auto shrink-0 text-[hsl(var(--text-secondary))] transition-transform ${
                        open ? "rotate-180" : ""
                    }`}
                />
            </button>

            {open && (
                <div
                    className="absolute z-50 mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] shadow-xl max-h-72 overflow-hidden"
                    onKeyDown={(event) => {
                        if (event.key === "Escape") {
                            event.preventDefault();
                            event.stopPropagation();
                            setOpen(false);
                            triggerRef.current?.focus();
                        }
                    }}
                >
                    <div className="p-2 border-b border-[hsl(var(--border))]">
                        <div className="flex items-center gap-2 rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
                            {loading ? (
                                <Loader2
                                    size={12}
                                    className="animate-spin text-[hsl(var(--primary))] shrink-0"
                                    data-testid="persona-search-spinner"
                                />
                            ) : (
                                <Search size={12} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            )}
                            <input
                                ref={inputRef}
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Buscar persona..."
                                className="bg-transparent text-xs font-medium outline-none w-full text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
                                aria-label="Buscar persona"
                            />
                        </div>
                    </div>
                    <div
                        id="persona-select-options"
                        className="overflow-y-auto max-h-56"
                        role="listbox"
                        aria-label="Personas disponibles"
                        onScroll={handleScroll}
                    >
                        <button
                            type="button"
                            onClick={handleClear}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-colors text-left"
                            role="option"
                            aria-selected={value === null}
                        >
                            <div className="size-6 rounded-full bg-[hsl(var(--surface-2))] flex items-center justify-center">
                                <UserIcon size={12} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            Sin asignar
                            {value === null && <Check size={12} className="ml-auto text-[hsl(var(--primary))]" />}
                        </button>
                        {sortedPersonas.map((persona) => {
                            const isSelected = persona.id === value;
                            return (
                                <button
                                    key={persona.id}
                                    type="button"
                                    onClick={() => handleSelect(persona)}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-[hsl(var(--surface-1))] transition-colors text-left"
                                    role="option"
                                    aria-selected={isSelected}
                                >
                                    <div className="size-6 rounded-full bg-[hsl(var(--primary)_/_0.12)] flex items-center justify-center shrink-0">
                                        <UserIcon size={12} className="text-[hsl(var(--primary))]" />
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate">
                                            {displayName(persona)}
                                        </p>
                                        {showMetadata && persona.church_role && (
                                            <p className="text-2xs text-[hsl(var(--text-secondary))] truncate flex items-center gap-1">
                                                <Shield size={8} /> {persona.church_role}
                                            </p>
                                        )}
                                    </div>
                                    {isSelected && (
                                        <Check size={12} className="ml-auto shrink-0 text-[hsl(var(--primary))]" />
                                    )}
                                </button>
                            );
                        })}
                        {hasMore && !loading && (
                            <div className="border-t border-[hsl(var(--border))]">
                                <button
                                    type="button"
                                    onClick={handleLoadMore}
                                    disabled={loadingMore}
                                    data-testid="persona-load-more"
                                    className="w-full flex items-center justify-center gap-2 py-2 text-2xs font-semibold text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-1))] transition-colors disabled:opacity-60"
                                >
                                    {loadingMore && <Loader2 size={10} className="animate-spin" />}
                                    Cargar más personas
                                </button>
                            </div>
                        )}
                    </div>
                    {loading && personas.length === 0 && (
                        <p role="status" className="px-3 py-4 text-center text-2xs text-[hsl(var(--text-secondary))]">
                            Buscando personas…
                        </p>
                    )}
                    {loadError && (
                        <div
                            role="alert"
                            data-testid="persona-load-error"
                            className="mx-3 my-2 flex flex-col items-start gap-2 rounded-md border border-[hsl(var(--destructive)_/_0.4)] bg-[hsl(var(--destructive)_/_0.08)] p-2.5"
                        >
                            <p className="flex items-center gap-1.5 text-2xs font-semibold text-[hsl(var(--destructive))]">
                                <CircleAlert size={12} />
                                No se pudo cargar el listado. Revisa tu conexión.
                            </p>
                            <button
                                type="button"
                                onClick={handleRetry}
                                className="rounded-md border border-[hsl(var(--destructive)_/_0.5)] px-2 py-1 text-2xs font-bold text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)_/_0.12)] transition-colors"
                            >
                                Reintentar
                            </button>
                        </div>
                    )}
                    {!loading && !loadError && personas.length === 0 && (
                        <p role="status" className="px-3 py-4 text-center text-2xs text-[hsl(var(--text-secondary))]">
                            No se encontraron personas
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

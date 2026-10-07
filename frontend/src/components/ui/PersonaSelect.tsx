"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Check, ChevronDown, User as UserIcon, Search, Shield, Loader2 } from "lucide-react";

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

export function displayName(p: PersonaOption): string {
    if (p.nombre_completo) return p.nombre_completo;
    return [p.first_name, p.last_name].filter(Boolean).join(" ") || "Sin nombre";
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
    const ref = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);

    // Debounce de 300ms para la búsqueda reactiva
    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedSearch(search);
        }, 300);
        return () => clearTimeout(handler);
    }, [search]);

    // Búsqueda server-side reactiva con debouncedSearch
    useEffect(() => {
        if (!token) return;

        let active = true;
        setLoading(true);

        const query = debouncedSearch.trim();
        const endpoint = query
            ? `/crm/personas?search=${encodeURIComponent(query)}&limit=50`
            : `/crm/personas?limit=50`;

        apiFetch<PersonaOption[]>(endpoint, { token })
            .then((data) => {
                if (!active) return;
                const list = Array.isArray(data) ? data : [];
                setPersonas(list);

                // Si hay un value seleccionado y está en la lista obtenida, sincronizar selectedPersona
                if (value) {
                    const match = list.find((p) => p.id === value);
                    if (match) {
                        setSelectedPersona(match);
                    }
                }
            })
            .catch((err) => {
                console.error("[PersonaSelect] Error cargando personas:", err);
            })
            .finally(() => {
                if (active) {
                    setLoading(false);
                }
            });

        return () => {
            active = false;
        };
    }, [token, debouncedSearch, value]);

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
                    <div id="persona-select-options" className="overflow-y-auto max-h-56" role="listbox" aria-label="Personas disponibles">
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
                        {personas.map((persona) => {
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
                    </div>
                    {!loading && personas.length === 0 && (
                        <p role="status" className="px-3 py-4 text-center text-2xs text-[hsl(var(--text-secondary))]">
                            No se encontraron personas
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

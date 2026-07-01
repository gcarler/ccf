"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Check, ChevronDown, User as UserIcon, Search, Shield } from "lucide-react";

interface PersonaOption {
    id: string;
    first_name?: string;
    last_name?: string;
    nombre_completo?: string;
    church_role?: string;
    spiritual_status?: string;
}

interface PersonaSelectProps {
    value: string | null;
    onChange: (personaId: string | null) => void;
    placeholder?: string;
    className?: string;
    showMetadata?: boolean;
}

function displayName(p: PersonaOption): string {
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
    const [search, setSearch] = useState("");
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!token || personas.length > 0) return;
        apiFetch<PersonaOption[]>("/crm/personas", { token })
            .then((data) => setPersonas(Array.isArray(data) ? data : []))
            .catch((err) => { console.error("[PersonaSelect] Failed to load personas:", err); });
    }, [token, personas.length]);

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const selected = personas.find((p) => p.id === value);

    const filtered = search.trim()
        ? personas.filter((p) => {
              const name = displayName(p).toLowerCase();
              const q = search.toLowerCase();
              return name.includes(q) || (p.church_role ?? "").toLowerCase().includes(q);
          })
        : personas;

    return (
        <div ref={ref} className={`relative ${className}`}>
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-2 text-sm font-medium text-left hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
            >
                {selected ? (
                    <>
                        <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                            <UserIcon size={12} className="text-[hsl(var(--primary))]" />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">
                                {displayName(selected)}
                            </p>
                            {showMetadata && selected.church_role && (
                                <p className="text-[10px] text-[hsl(var(--text-secondary))] truncate">{selected.church_role}</p>
                            )}
                        </div>
                    </>
                ) : (
                    <span className="text-xs text-[hsl(var(--text-secondary))]">{placeholder}</span>
                )}
                <ChevronDown
                    size={14}
                    className={`ml-auto shrink-0 text-[hsl(var(--text-secondary))] transition-transform ${open ? "rotate-180" : ""}`}
                />
            </button>

            {open && (
                <div className="absolute z-50 mt-1 w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] shadow-xl max-h-72 overflow-hidden">
                    <div className="p-2 border-b border-[hsl(var(--border))] dark:border-white/5">
                        <div className="flex items-center gap-2 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-1.5">
                            <Search size={12} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            <input
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Buscar persona..."
                                className="bg-transparent text-xs font-medium outline-none w-full text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))]"
                            />
                        </div>
                    </div>
                    <div className="overflow-y-auto max-h-56">
                        <button
                            type="button"
                            onClick={() => {
                                onChange(null);
                                setOpen(false);
                                setSearch("");
                            }}
                            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-left"
                        >
                            <div className="size-6 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                                <UserIcon size={12} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            Sin asignar
                            {value === null && <Check size={12} className="ml-auto text-[hsl(var(--primary))]" />}
                        </button>
                        {filtered.map((persona) => (
                            <button
                                key={persona.id}
                                type="button"
                                onClick={() => {
                                    onChange(persona.id);
                                    setOpen(false);
                                    setSearch("");
                                }}
                                className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-left"
                            >
                                <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                                    <UserIcon size={12} className="text-[hsl(var(--primary))]" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">
                                        {displayName(persona)}
                                    </p>
                                    {showMetadata && persona.church_role && (
                                        <p className="text-[10px] text-[hsl(var(--text-secondary))] truncate flex items-center gap-1">
                                            <Shield size={8} /> {persona.church_role}
                                        </p>
                                    )}
                                </div>
                                {persona.id === value && (
                                    <Check size={12} className="ml-auto shrink-0 text-[hsl(var(--primary))]" />
                                )}
                            </button>
                        ))}
                        {filtered.length === 0 && (
                            <p className="px-3 py-4 text-center text-[10px] text-[hsl(var(--text-secondary))]">
                                No se encontraron personas
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

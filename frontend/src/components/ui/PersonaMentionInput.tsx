"use client";

/**
 * PersonaMentionInput — búsqueda de personas estilo mensajería.
 *
 * Escribiendo "@luis" se abre un dropdown con las personas que coinciden
 * (filtroAPersona, cliente-side) y al seleccionar se inserta "@Nombre
 * Completo " en el texto. Reutilizable en cualquier módulo de la plataforma.
 */
import { AvatarInitial } from '@/components/ui/AvatarInitial';
import { filtroAPersona, type PersonaBusqueda } from '@/lib/filtroAPersonas';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface MentionCandidate {
    query: string;
    start: number;
}

interface PersonaMentionInputProps {
    personas: PersonaBusqueda[];
    value: string;
    onChange: (value: string, mencionadas: PersonaBusqueda[]) => void;
    placeholder?: string;
    disabled?: boolean;
    maxResults?: number;
    rows?: number;
    ariaLabel?: string;
}

function nombreDe(persona: PersonaBusqueda): string {
    return (
        persona.nombre_completo ||
        [persona.first_name, persona.last_name].filter(Boolean).join(' ').trim() ||
        ''
    );
}

export default function PersonaMentionInput({
    personas,
    value,
    onChange,
    placeholder = 'Escribe... (@ para mencionar personas)',
    disabled = false,
    maxResults = 6,
    rows = 2,
    ariaLabel = 'Escribe un mensaje',
}: PersonaMentionInputProps) {
    const [mentionState, setMentionState] = useState<MentionCandidate | null>(null);
    const [mencionadas, setMencionadas] = useState<PersonaBusqueda[]>([]);
    const [activeIndex, setActiveIndex] = useState(0);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; width: number } | null>(null);

    const results = useMemo(() => {
        if (!mentionState || mentionState.query.trim().length < 1) return [];
        return personas.filter((p) => filtroAPersona(p, mentionState.query)).slice(0, maxResults);
    }, [mentionState, personas, maxResults]);

    // Dropdown por encima del input (misma UX que mensajería).
    useEffect(() => {
        if (results.length > 0 && mentionState && containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            setDropdownPos({ top: rect.top, left: rect.left + 8, width: rect.width - 16 });
        } else {
            setDropdownPos(null);
        }
    }, [results, mentionState]);

    useEffect(() => setActiveIndex(0), [results]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value;
        onChange(val, mencionadas);
        const textBeforeCursor = val.slice(0, e.target.selectionStart);
        const lastAt = textBeforeCursor.lastIndexOf('@');
        if (lastAt !== -1) {
            const query = textBeforeCursor.slice(lastAt + 1);
            if (!query.includes(' ')) {
                setMentionState({ query, start: lastAt });
                return;
            }
        }
        setMentionState(null);
    };

    const selectMention = (persona: PersonaBusqueda) => {
        if (!mentionState) return;
        const nombre = nombreDe(persona);
        const before = value.slice(0, mentionState.start);
        const after = value.slice(mentionState.start + 1 + mentionState.query.length);
        const next = `${before}@${nombre} ${after}`;
        setMencionadas((prev) => (prev.some((m) => m.id === persona.id) ? prev : [...prev, persona]));
        onChange(next, mencionadas.some((m) => m.id === persona.id) ? mencionadas : [...mencionadas, persona]);
        setMentionState(null);
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Escape') {
            setMentionState(null);
            return;
        }
        if (!mentionState || results.length === 0) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex((i) => (i + 1) % results.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex((i) => (i - 1 + results.length) % results.length);
        } else if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            selectMention(results[activeIndex]);
        }
    };

    return (
        <div ref={containerRef} className="relative">
            {results.length > 0 && mentionState && dropdownPos && createPortal(
                <div
                    role="listbox"
                    aria-label="Personas que coinciden"
                    className="fixed rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] shadow-2xl overflow-hidden z-[9999] max-h-[240px] overflow-y-auto"
                    style={{
                        top: dropdownPos.top,
                        left: dropdownPos.left,
                        width: dropdownPos.width,
                        transform: 'translateY(-100%)',
                        marginBottom: '4px',
                    }}
                >
                    {results.map((p, index) => (
                        <button
                            key={p.id}
                            role="option"
                            aria-selected={index === activeIndex}
                            onMouseEnter={() => setActiveIndex(index)}
                            onClick={() => selectMention(p)}
                            className={`w-full flex items-center gap-2.5 px-3 py-2 transition-colors ${index === activeIndex ? 'bg-[hsl(var(--surface-1))] dark:bg-white/5' : 'hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'}`}
                        >
                            <AvatarInitial name={nombreDe(p)} size="sm" />
                            <div className="text-left flex-1 min-w-0">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{nombreDe(p)}</p>
                                {p.church_role && (
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] truncate">{p.church_role}</p>
                                )}
                            </div>
                        </button>
                    ))}
                </div>,
                document.body
            )}

            <textarea
                ref={inputRef}
                rows={rows}
                value={value}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder={placeholder}
                aria-label={ariaLabel}
                className="w-full px-3 py-2 text-sm bg-[hsl(var(--surface-1))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/10 rounded-xl outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] resize-none disabled:opacity-50"
            />
        </div>
    );
}

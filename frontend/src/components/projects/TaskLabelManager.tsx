"use client";

import { useState, useRef, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import { Check, Plus, X, Tag } from 'lucide-react';
import clsx from 'clsx';
import { useOptionalProjectUpdate } from '@/context/ProjectUpdateContext';
import ProjectLabelsDrawer from './ProjectLabelsDrawer';

const LABEL_COLORS = [
    { bg: 'bg-[hsl(var(--destructive)/0.15)]', text: 'text-[hsl(var(--destructive))]', border: 'border-[hsl(var(--destructive)/0.3)]', dot: 'bg-[hsl(var(--destructive))]' },
    { bg: 'bg-[hsl(var(--warning)/0.15)]', text: 'text-[hsl(var(--warning))]', border: 'border-[hsl(var(--warning)/0.3)]', dot: 'bg-[hsl(var(--warning))]' },
    { bg: 'bg-[hsl(var(--warning)/0.2)]',  text: 'text-[hsl(var(--warning))]', border: 'border-[hsl(var(--warning)/0.4)]', dot: 'bg-[hsl(var(--warning))]' },
    { bg: 'bg-[hsl(var(--success)/0.15)]', text: 'text-[hsl(var(--success))]', border: 'border-[hsl(var(--success)/0.3)]', dot: 'bg-[hsl(var(--success))]' },
    { bg: 'bg-[hsl(var(--primary)/0.15)]', text: 'text-[hsl(var(--primary))]', border: 'border-[hsl(var(--primary)/0.3)]', dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-[hsl(var(--primary)/0.2)]', text: 'text-[hsl(var(--primary))]', border: 'border-[hsl(var(--primary)/0.4)]', dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-[hsl(var(--domain-pink)/0.2)]', text: 'text-[hsl(var(--domain-pink))]', border: 'border-[hsl(var(--domain-pink)/0.3)]', dot: 'bg-[hsl(var(--domain-pink))]' },
    { bg: 'bg-[hsl(var(--surface-2))]', text: 'text-[hsl(var(--muted-foreground))]', border: 'border-[hsl(var(--border))]', dot: 'bg-[hsl(var(--muted-foreground))]' },
];

export function getLabelColor(label: string) {
    let hash = 0;
    for (let i = 0; i < label.length; i++) hash = label.charCodeAt(i) + ((hash << 5) - hash);
    return LABEL_COLORS[Math.abs(hash) % LABEL_COLORS.length];
}

const DEFAULT_SUGGESTIONS = ['Alabanza', 'Urgente', 'Reunión', 'Pastoral', 'Admin', 'Diseño'];

const PMI_GOVERNANCE_TAGS = [
    'Ruta Crítica',
    'Entregable Verificable',
    'Control de Calidad QA',
    'Riesgo Alto',
    'Bloqueo Externo',
    'Cambio CCB',
];

export default function TaskLabelManager({
    task,
    labels,
    onLabelsChange,
    token,
    onManageLabels,
}: {
    task: ProjectTaskRecord;
    labels: string[];
    onLabelsChange: (labels: string[]) => void;
    token: string | null;
    onManageLabels?: () => void;
}) {
    const [labelPopoverOpen, setLabelPopoverOpen] = useState(false);
    const [newLabelInput, setNewLabelInput] = useState('');
    const [isLabelsDrawerOpen, setIsLabelsDrawerOpen] = useState(false);
    const labelInputRef = useRef<HTMLInputElement>(null);

    const projectUpdateContext = useOptionalProjectUpdate();

    const pmiGovernanceNormalized = useMemo(
        () => new Set(PMI_GOVERNANCE_TAGS.map((t) => t.toLowerCase())),
        []
    );
    const matchedPmiCount = useMemo(
        () => labels.filter((l) => pmiGovernanceNormalized.has((l ?? '').trim().toLowerCase())).length,
        [labels, pmiGovernanceNormalized]
    );
    const availablePmiQuickTags = useMemo(() => {
        const lowerCurrent = new Set(labels.map((l) => (l ?? '').trim().toLowerCase()));
        return PMI_GOVERNANCE_TAGS.filter((tag) => !lowerCurrent.has(tag.toLowerCase()));
    }, [labels]);

    // Dynamically calculate suggestions from context tasks + localStorage catalog + default suggestions
    const suggestedLabels = useMemo(() => {
        const pool = new Set<string>();

        // 1. Context tasks
        if (projectUpdateContext?.tasks) {
            for (const t of projectUpdateContext.tasks) {
                if (!t.deleted_at && Array.isArray(t.labels)) {
                    for (const l of t.labels) {
                        const trimmed = l?.trim();
                        if (trimmed) pool.add(trimmed);
                    }
                }
            }
        }

        // 2. Local catalog
        if (typeof window !== 'undefined' && task.project_id) {
            try {
                const raw = localStorage.getItem(`projectLabelsCatalog:${task.project_id}`);
                if (raw) {
                    const parsed = JSON.parse(raw);
                    if (Array.isArray(parsed)) {
                        for (const item of parsed) {
                            if (typeof item === 'string' && item.trim()) {
                                pool.add(item.trim());
                            }
                        }
                    }
                }
            } catch {
                // Ignore storage parse issues
            }
        }

        // 3. Defaults
        for (const def of DEFAULT_SUGGESTIONS) {
            pool.add(def);
        }

        // Filter out already selected labels on this task
        return Array.from(pool).filter(s => !labels.includes(s));
    }, [projectUpdateContext?.tasks, task.project_id, labels]);

    const handleAddLabel = async () => {
        if (!token) return;
        const trimmed = newLabelInput.trim();
        if (!trimmed || labels.includes(trimmed)) { setNewLabelInput(''); return; }
        const nextLabels = [...labels, trimmed];
        onLabelsChange(nextLabels);
        setNewLabelInput('');
        setLabelPopoverOpen(false);
        try {
            await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token, body: { labels: nextLabels }
            });
        } catch { /* optimistic */ }
    };

    const handleSelectSuggestion = async (suggestion: string) => {
        if (!token) return;
        const trimmed = suggestion.trim();
        if (!trimmed || labels.includes(trimmed)) return;
        const nextLabels = [...labels, trimmed];
        onLabelsChange(nextLabels);
        setNewLabelInput('');
        setLabelPopoverOpen(false);
        try {
            await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token, body: { labels: nextLabels }
            });
        } catch { /* optimistic */ }
    };

    const handleRemoveLabel = async (label: string) => {
        if (!token) return;
        const nextLabels = labels.filter(l => l !== label);
        onLabelsChange(nextLabels);
        try {
            await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token, body: { labels: nextLabels }
            });
        } catch { /* optimistic */ }
    };

    return (
        <div className="flex flex-wrap items-center gap-1.5 relative">
            <span
                data-testid="task-label-pmi-coverage"
                className={clsx(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-bold border',
                    matchedPmiCount > 0
                        ? 'bg-[hsl(var(--success)/0.14)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]'
                        : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]'
                )}
            >
                {matchedPmiCount > 0 ? `Gobernanza PMI (${matchedPmiCount})` : 'Sin etiqueta PMI'}
            </span>

            {labels.map(label => {
                const c = getLabelColor(label);
                return (
                    <span key={label} className={clsx(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-bold border',
                        c.bg, c.text, c.border
                    )}>
                        <span className={clsx('size-1.5 rounded-full', c.dot)} />
                        {label}
                        <button
                            type="button"
                            onClick={() => handleRemoveLabel(label)}
                            className="ml-0.5 opacity-60 hover:opacity-100 transition-opacity"
                            title={`Quitar etiqueta "${label}"`}
                            aria-label={`Quitar etiqueta "${label}"`}
                        >
                            <X size={9} strokeWidth={3} />
                        </button>
                    </span>
                );
            })}

            <div className="relative">
                <button
                    type="button"
                    onClick={() => { setLabelPopoverOpen(v => !v); setTimeout(() => labelInputRef.current?.focus(), 50); }}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-1))] border border-dashed border-[hsl(var(--border))] transition-all"
                >
                    <Plus size={10} /> Añadir etiqueta
                </button>

                <AnimatePresence>
                    {labelPopoverOpen && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -4 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -4 }}
                            transition={{ duration: 0.12 }}
                            className="absolute top-full left-0 mt-1.5 z-50 w-64 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-2xl p-3 space-y-2.5"
                        >
                            <div className="flex items-center justify-between">
                                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Nueva etiqueta</p>
                                <button
                                    type="button"
                                    onClick={() => { setLabelPopoverOpen(false); setNewLabelInput(''); }}
                                    className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                                >
                                    <X size={12} />
                                </button>
                            </div>

                            <div className="flex gap-1.5">
                                <input
                                    ref={labelInputRef}
                                    type="text"
                                    value={newLabelInput}
                                    onChange={e => setNewLabelInput(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') handleAddLabel();
                                        if (e.key === 'Escape') { setLabelPopoverOpen(false); setNewLabelInput(''); }
                                    }}
                                    placeholder="Ej: Alabanza, Urgente..."
                                    className="flex-1 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] rounded-lg px-2 py-1.5 outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] transition-all"
                                />
                                <button
                                    type="button"
                                    onClick={handleAddLabel}
                                    disabled={!newLabelInput.trim()}
                                    className="px-2.5 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <Check size={11} strokeWidth={3} />
                                </button>
                            </div>

                            {/* Etiquetas Rápidas de Gobernanza PMI */}
                            {availablePmiQuickTags.length > 0 && (
                                <div
                                    data-testid="task-label-pmi-quick-tags"
                                    className="space-y-1 pt-1 border-t border-[hsl(var(--border))]"
                                >
                                    <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                                        Taxonomía de Gobernanza PMI
                                    </p>
                                    <div className="flex flex-wrap gap-1">
                                        {availablePmiQuickTags.map((tag) => (
                                            <button
                                                key={tag}
                                                type="button"
                                                data-testid={`task-label-pmi-tag-${tag}`}
                                                onClick={() => handleSelectSuggestion(tag)}
                                                className="px-2 py-0.5 rounded-full text-2xs font-bold border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.2)] transition-all"
                                            >
                                                {tag}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Suggestions */}
                            {suggestedLabels.length > 0 && (
                                <div className="space-y-1 pt-1 border-t border-[hsl(var(--border))]">
                                    <p className="text-3xs font-medium text-[hsl(var(--muted-foreground))]">Sugerencias del proyecto</p>
                                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-0.5">
                                        {suggestedLabels.slice(0, 10).map(s => (
                                            <button
                                                key={s}
                                                type="button"
                                                onClick={() => handleSelectSuggestion(s)}
                                                className={clsx(
                                                    'px-2 py-0.5 rounded-full text-2xs font-bold border transition-all hover:scale-105',
                                                    getLabelColor(s).bg,
                                                    getLabelColor(s).text,
                                                    getLabelColor(s).border
                                                )}
                                            >
                                                {s}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Manage Labels Link */}
                            <div className="pt-2 border-t border-[hsl(var(--border))] flex items-center justify-between">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setLabelPopoverOpen(false);
                                        if (onManageLabels) {
                                            onManageLabels();
                                        } else {
                                            setIsLabelsDrawerOpen(true);
                                        }
                                    }}
                                    className="inline-flex items-center gap-1.5 text-2xs font-semibold text-[hsl(var(--primary))] hover:underline"
                                >
                                    <Tag size={11} /> Gestionar etiquetas
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {labelPopoverOpen && (
                <div className="fixed inset-0 z-40" onClick={() => { setLabelPopoverOpen(false); setNewLabelInput(''); }} />
            )}

            {/* Standalone drawer if opened internally */}
            {isLabelsDrawerOpen && (
                <ProjectLabelsDrawer
                    projectId={task.project_id}
                    isOpen={isLabelsDrawerOpen}
                    onClose={() => setIsLabelsDrawerOpen(false)}
                    onUpdated={() => {
                        projectUpdateContext?.reloadProject?.();
                    }}
                />
            )}
        </div>
    );
}

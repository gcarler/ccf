"use client";

import { useState, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import { Check, Plus, X } from 'lucide-react';
import clsx from 'clsx';

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

export default function TaskLabelManager({
    task,
    labels,
    onLabelsChange,
    token,
}: {
    task: ProjectTaskRecord;
    labels: string[];
    onLabelsChange: (labels: string[]) => void;
    token: string | null;
}) {
    const [labelPopoverOpen, setLabelPopoverOpen] = useState(false);
    const [newLabelInput, setNewLabelInput] = useState('');
    const labelInputRef = useRef<HTMLInputElement>(null);

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
                            onClick={() => handleRemoveLabel(label)}
                            className="ml-0.5 opacity-60 hover:opacity-100 transition-opacity"
                            title={`Quitar etiqueta "${label}"`}
                        >
                            <X size={9} strokeWidth={3} />
                        </button>
                    </span>
                );
            })}

            <div className="relative">
                <button
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
                            className="absolute top-full left-0 mt-1.5 z-50 w-56 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-2xl p-3 space-y-2"
                        >
                            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-1">Nueva etiqueta</p>
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
                                    onClick={handleAddLabel}
                                    disabled={!newLabelInput.trim()}
                                    className="px-2.5 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <Check size={11} strokeWidth={3} />
                                </button>
                            </div>
                            <div className="flex flex-wrap gap-1 pt-1 border-t border-[hsl(var(--border))]">
                                {['Alabanza', 'Urgente', 'Reunión', 'Pastoral', 'Admin', 'Diseño'].filter(s => !labels.includes(s)).map(s => (
                                    <button
                                        key={s}
                                        onClick={() => { setNewLabelInput(s); labelInputRef.current?.focus(); }}
                                        className={clsx('px-2 py-0.5 rounded-full text-2xs font-bold border transition-all hover:scale-105', getLabelColor(s).bg, getLabelColor(s).text, getLabelColor(s).border)}
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {labelPopoverOpen && (
                <div className="fixed inset-0 z-40" onClick={() => { setLabelPopoverOpen(false); setNewLabelInput(''); }} />
            )}
        </div>
    );
}

"use client";

import { useState, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import { Check, Plus, X } from 'lucide-react';
import clsx from 'clsx';

const LABEL_COLORS = [
    { bg: 'bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger))]/30',   text: 'text-danger-text dark:text-danger-text',   border: 'border-[hsl(var(--danger)/30%)]/50 dark:border-[hsl(var(--danger)/100%)]/30',   dot: 'bg-[hsl(var(--danger))]' },
    { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-300/50 dark:border-orange-500/30', dot: 'bg-orange-500' },
    { bg: 'bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning))]/30',  text: 'text-warning-text dark:text-warning-text',  border: 'border-[hsl(var(--warning)/30%)]/50 dark:border-[hsl(var(--warning)/100%)]/30',  dot: 'bg-[hsl(var(--warning))]' },
    { bg: 'bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success))]/30', text: 'text-success-text dark:text-success-text', border: 'border-[hsl(var(--success)/30%)]/50 dark:border-[hsl(var(--success)/100%)]/30', dot: 'bg-[hsl(var(--success))]' },
    { bg: 'bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/30',   text: 'text-[hsl(var(--primary))] dark:text-info-text',   border: 'border-[hsl(var(--info)/30%)]/50 dark:border-[hsl(var(--info)/100%)]/30',   dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/30', text: 'text-[hsl(var(--primary))] dark:text-info-text', border: 'border-[hsl(var(--info)/30%)]/50 dark:border-[hsl(var(--info)/100%)]/30', dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-[hsl(var(--domain-pink)/20%)] dark:bg-[hsl(var(--domain-pink)/30%)]',   text: 'text-[hsl(var(--domain-pink)/90%)] dark:text-[hsl(var(--domain-pink))]',   border: 'border-[hsl(var(--domain-pink)/50%)] dark:border-[hsl(var(--domain-pink)/30%)]',   dot: 'bg-[hsl(var(--domain-pink))]' },
    { bg: 'bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))]/60', text: 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]', border: 'border-[hsl(var(--border))]/50 dark:border-[hsl(var(--border))]/30', dot: 'bg-[hsl(var(--surface-2))]' },
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
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border',
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
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] border border-dashed border-[hsl(var(--border))] dark:border-white/[0.1] transition-all"
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
                            className="absolute top-full left-0 mt-1.5 z-50 w-56 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-2xl p-3 space-y-2"
                        >
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Nueva etiqueta</p>
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
                                    className="flex-1 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-2 py-1.5 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 focus:border-[hsl(var(--info)/40%)] transition-all"
                                />
                                <button
                                    onClick={handleAddLabel}
                                    disabled={!newLabelInput.trim()}
                                    className="px-2.5 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <Check size={11} strokeWidth={3} />
                                </button>
                            </div>
                            <div className="flex flex-wrap gap-1 pt-1 border-t border-[hsl(var(--border))] dark:border-white/5">
                                {['Alabanza', 'Urgente', 'Reunión', 'Pastoral', 'Admin', 'Diseño'].filter(s => !labels.includes(s)).map(s => (
                                    <button
                                        key={s}
                                        onClick={() => { setNewLabelInput(s); labelInputRef.current?.focus(); }}
                                        className={clsx('px-2 py-0.5 rounded-full text-[10px] font-bold border transition-all hover:scale-105', getLabelColor(s).bg, getLabelColor(s).text, getLabelColor(s).border)}
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

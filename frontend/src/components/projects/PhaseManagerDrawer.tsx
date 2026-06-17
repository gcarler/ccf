"use client";

import { RightPanel } from '@/components/ui/RightPanel';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
GripVertical,Plus,
Save,
Trash2
} from 'lucide-react';
import { useState } from 'react';
import type { PhaseDef } from './ProjectKanbanBoard';

interface Props {
    projectId: string;
    phases: PhaseDef[];
    onClose: () => void;
    onSaved: (phases: PhaseDef[]) => void;
}

const COLOR_PRESETS = [
    '#94a3b8', '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316',
];

export function PhaseManagerDrawer({ projectId, phases, onClose, onSaved }: Props) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [items, setItems] = useState<PhaseDef[]>(() => phases.map((p, i) => ({ ...p, order_index: i })));
    const [saving, setSaving] = useState(false);

    const handleMoveUp = (index: number) => {
        if (index === 0) return;
        const next = [...items];
        [next[index - 1], next[index]] = [next[index], next[index - 1]];
        setItems(next);
    };

    const handleMoveDown = (index: number) => {
        if (index === items.length - 1) return;
        const next = [...items];
        [next[index], next[index + 1]] = [next[index + 1], next[index]];
        setItems(next);
    };

    const handleRename = (index: number, name: string) => {
        const next = [...items];
        next[index] = { ...next[index], name };
        setItems(next);
    };

    const handleChangeColor = (index: number, color: string) => {
        const next = [...items];
        next[index] = { ...next[index], color };
        setItems(next);
    };

    const handleAdd = () => {
        const count = items.length;
        setItems([...items, {
            slug: `phase-${Date.now()}`,
            name: `Fase ${count + 1}`,
            color: COLOR_PRESETS[count % COLOR_PRESETS.length],
            order_index: count,
        }]);
    };

    const handleRemove = (index: number) => {
        if (items.length <= 1) {
            addToast('Debe haber al menos una fase', 'error');
            return;
        }
        const next = items.filter((_, i) => i !== index);
        setItems(next);
    };

    const handleSave = async () => {
        if (!token) return;
        setSaving(true);
        try {
            const payload = items.map((p, i) => ({
                name: p.name,
                slug: p.slug,
                color: p.color,
                order_index: i,
            }));
            const result = await apiFetch<PhaseDef[]>(`/projects/${projectId}/phases`, {
                method: 'PUT',
                token,
                body: payload,
            });
            onSaved(result);
            addToast('Fases actualizadas', 'success');
            onClose();
        } catch (err: any) {
            const detail = typeof err?.detail === 'string'
                ? err.detail
                : err?.detail?.detail || err?.detail?.message || (err?.detail ? JSON.stringify(err.detail) : '');
            addToast(detail || 'Error al guardar fases', 'error');
        } finally {
            setSaving(false);
        }
    };

    return (
        <RightPanel open={true} onClose={onClose} title="Gestionar Fases" width={480}>
            <div className="flex flex-col h-full">
                {/* Body */}
                <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
                    {items.map((phase, i) => (
                        <div
                            key={phase.slug}
                            className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-white/5 rounded-md border border-slate-100 dark:border-white/10 group"
                        >
                            {/* Reorder buttons */}
                            <div className="flex flex-col gap-0.5 shrink-0">
                                <button onClick={() => handleMoveUp(i)} disabled={i === 0} className="size-4 flex items-center justify-center text-slate-300 hover:text-slate-600 disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▲</span>
                                </button>
                                <button onClick={() => handleMoveDown(i)} disabled={i === items.length - 1} className="size-4 flex items-center justify-center text-slate-300 hover:text-slate-600 disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▼</span>
                                </button>
                            </div>

                            {/* Drag handle */}
                            <div className="opacity-0 group-hover:opacity-40 cursor-grab text-slate-400 shrink-0">
                                <GripVertical size={14} />
                            </div>

                            {/* Color picker trigger */}
                            <div className="relative shrink-0">
                                <div className="size-7 rounded-lg border border-slate-200 dark:border-white/10" style={{ backgroundColor: phase.color }} />
                                <select
                                    value={phase.color}
                                    onChange={e => handleChangeColor(i, e.target.value)}
                                    className="absolute inset-0 opacity-0 cursor-pointer"
                                    aria-label="Color de fase"
                                >
                                    {COLOR_PRESETS.map(c => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Name input */}
                            <input
                                type="text"
                                value={phase.name}
                                onChange={e => handleRename(i, e.target.value)}
                                className="flex-1 text-[13px] font-bold bg-transparent outline-none text-slate-800 dark:text-slate-100 placeholder:text-slate-400 border-b border-transparent focus:border-blue-500 transition-all"
                            />

                            {/* Delete */}
                            <button
                                onClick={() => handleRemove(i)}
                                className="size-7 rounded-lg flex items-center justify-center text-slate-300 hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                            >
                                <Trash2 size={12} />
                            </button>
                        </div>
                    ))}

                    {/* Add phase */}
                    <button
                        onClick={handleAdd}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-md border-2 border-dashed border-slate-200 dark:border-white/10 text-slate-400 hover:text-[hsl(var(--primary))] hover:border-blue-500/30 transition-all text-[11px] font-semibold uppercase tracking-wide"
                    >
                        <Plus size={14} /> Agregar Fase
                    </button>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 px-4 py-2.5 border-t border-slate-100 dark:border-white/5 shrink-0">
                    <button
                        onClick={onClose}
                        className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-all"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 flex items-center gap-2 hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-50 transition-all"
                    >
                        {saving ? (
                            <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <Save size={14} />
                        )}
                        Guardar
                    </button>
                </div>
            </div>
        </RightPanel>
    );
}

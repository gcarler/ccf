"use client";

import { RightPanel } from '@/components/ui/RightPanel';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { GripVertical, Plus, Save, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useProjectUpdate, type PhaseDef } from '@/context/ProjectUpdateContext';

interface Props {
    projectId: string;
    onClose: () => void;
}

const COLOR_PRESETS = [
    '#94a3b8', '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316',
];

/**
 * Drawer para gestionar fases de un proyecto. Self-sufficient desde 2026-07-16
 * (cierre de `PARCIAL-PHASES-001`): consume `phases`/`tasks`/`reloadProject`
 * directamente del ProjectUpdateContext, por lo que `page.tsx` ya no necesita
 * mantener un duplicado ni pasar callbacks. La API surface colapsa a sólo
 * `projectId` + `onClose`.
 *
 * Validación (cierra el contrato):
 *  - Al menos 1 fase (no permite save si se queda vacío).
 *  - Name no vacío en cada fase.
 *  - Slug único (case-insensitive) entre items del draft.
 *  - Pre-flight de tasks huérfanas: si al guardar alguna tarea existente
 *    quedaría con status que no existe en los slugs nuevos, el save se
 *    bloquea con mensaje claro (el backend rechaza _assert_status_in_project_phases
 *    en PATCH posteriores al cambio de fases; mejor avisar antes).
 */
export function PhaseManagerDrawer({ projectId, onClose }: Props) {
    const { token, loading: authLoading } = useAuth();
    const { addToast } = useToast();
    const { phases: ctxPhases, tasks: ctxTasks, reloadProject } = useProjectUpdate();

    const draftKey = `phaseManagerDraft:${projectId}`;
    const [items, setItems] = useState<PhaseDef[]>(() =>
        (ctxPhases ?? []).map((p, i) => ({ ...p, order_index: i })),
    );
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Restore draft from a previous abandoned session, if any. A draft is only
    // considered valid if its length matches the current phase count; otherwise
    // the project's phases have changed underneath us and we silently discard.
    useEffect(() => {
        if (typeof window === 'undefined') return;
        try {
            const raw = window.localStorage.getItem(draftKey);
            if (!raw) return;
            const parsed = JSON.parse(raw) as PhaseDef[];
            if (Array.isArray(parsed) && parsed.length === (ctxPhases?.length ?? 0)) {
                setItems(parsed);
            }
        } catch {
            /* ignore corrupt draft */
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Persist draft whenever items change so an accidental close / crash
    // doesn't lose the user's edits.
    useEffect(() => {
        if (typeof window === 'undefined') return;
        try {
            window.localStorage.setItem(draftKey, JSON.stringify(items));
        } catch {
            /* quota exceeded — skip silently */
        }
    }, [items, draftKey]);

    // Clear the draft on unmount (cancel / X / click-outside / Escape).
    useEffect(() => {
        return () => {
            try {
                if (typeof window !== 'undefined') window.localStorage.removeItem(draftKey);
            } catch { /* ignore */ }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

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

    /**
     * Validación previa al PUT. Devuelve `null` si todo OK; si no, setea el
     * mensaje de error visible y devuelve el mensaje para el toast (opcional).
     */
    const validateItems = (): string | null => {
        if (items.length === 0) {
            return 'Debe existir al menos una fase.';
        }
        const seenSlugs = new Set<string>();
        for (const item of items) {
            if (!item.name.trim()) {
                return 'Ninguna fase puede tener nombre vacío.';
            }
            const slugKey = item.slug.toLowerCase();
            if (seenSlugs.has(slugKey)) {
                return `Hay slugs duplicados ("${item.slug}"). Renombra o fusiona antes de guardar.`;
            }
            seenSlugs.add(slugKey);
        }

        // Pre-flight: ninguna tarea existente debe quedar con status fuera del nuevo set.
        const validSlugs = new Set(items.map(i => i.slug));
        const orphanTasks = (ctxTasks ?? []).filter(
            (t) => !validSlugs.has((t.status ?? 'todo').toLowerCase()),
        );
        if (orphanTasks.length > 0) {
            const sampleTitles = orphanTasks
                .slice(0, 3)
                .map((t) => `"${t.title || '(sin título)'}"`)
                .join(', ');
            const more = orphanTasks.length > 3 ? ` y ${orphanTasks.length - 3} más` : '';
            return `Hay ${orphanTasks.length} tarea(s) en estados que vas a eliminar: ${sampleTitles}${more}. Mueve esas tareas a un estado nuevo antes de guardar.`;
        }
        return null;
    };

    const handleSave = async () => {
        if (authLoading) return;
        if (!token) {
            setError('Debes iniciar sesión para guardar las fases.');
            return;
        }
        setError(null);
        const validationMsg = validateItems();
        if (validationMsg) {
            setError(validationMsg);
            addToast(validationMsg, 'error');
            return;
        }
        setSaving(true);
        try {
            const payload = items.map((p, i) => ({
                name: p.name,
                slug: p.slug,
                color: p.color,
                order_index: i,
            }));
            await apiFetch(`/projects/${projectId}/phases`, {
                method: 'PUT',
                token,
                body: payload,
            });
            try {
                if (typeof window !== 'undefined') window.localStorage.removeItem(draftKey);
            } catch { /* ignore */ }
            addToast('Fases actualizadas', 'success');
            // Refresh the context so all consumers (KanbanBoard, Gantt, MasterView...)
            // receive the new phases without page.tsx prop-drilling.
            await reloadProject();
            onClose();
        } catch (err: any) {
            setError('No se pudieron guardar las fases. Ajusta los cambios y vuelve a intentarlo.');
            const detail = typeof err?.detail === 'string'
                ? err.detail
                : err?.detail?.detail || err?.detail?.message || (err?.detail ? JSON.stringify(err.detail) : '');
            addToast(detail || 'Error al guardar fases', 'error');
            // Intentional: keep drawer open on error so user can fix and retry;
            // localStorage draft is preserved.
        } finally {
            setSaving(false);
        }
    };

    const handleCancel = () => {
        try {
            if (typeof window !== 'undefined') window.localStorage.removeItem(draftKey);
        } catch { /* ignore */ }
        onClose();
    };

    return (
        <RightPanel open={true} onClose={onClose} title="Gestionar Fases" width={480}>
            <div className="flex flex-col h-full">
                {error && (
                    <div className="mx-3 mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
                        <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
                    </div>
                )}
                {/* Body */}
                <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
                    {items.map((phase, i) => (
                        <div
                            key={phase.slug}
                            className="flex items-center gap-3 p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md border border-[hsl(var(--border))] dark:border-white/10 group"
                        >
                            {/* Reorder buttons */}
                            <div className="flex flex-col gap-0.5 shrink-0">
                                <button onClick={() => handleMoveUp(i)} disabled={i === 0} className="size-4 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▲</span>
                                </button>
                                <button onClick={() => handleMoveDown(i)} disabled={i === items.length - 1} className="size-4 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▼</span>
                                </button>
                            </div>

                            {/* Drag handle */}
                            <div className="opacity-0 group-hover:opacity-40 cursor-grab text-[hsl(var(--text-secondary))] shrink-0">
                                <GripVertical size={14} />
                            </div>

                            {/* Color picker trigger */}
                            <div className="relative shrink-0">
                                <div className="size-7 rounded-lg border border-[hsl(var(--border))] dark:border-white/10" style={{ backgroundColor: phase.color }} />
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
                                className="flex-1 text-[13px] font-bold bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] border-b border-transparent focus:border-blue-500 transition-all"
                            />

                            {/* Slug (read-only, derived) */}
                            <code className="hidden md:inline text-[9px] font-mono text-[hsl(var(--text-secondary))] opacity-60 truncate max-w-[120px]" title={phase.slug}>
                                {phase.slug}
                            </code>

                            {/* Delete */}
                            <button
                                onClick={() => handleRemove(i)}
                                className="size-7 rounded-lg flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                            >
                                <Trash2 size={12} />
                            </button>
                        </div>
                    ))}

                    {/* Add phase */}
                    <button
                        onClick={handleAdd}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-md border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-blue-500/30 transition-all text-[11px] font-semibold uppercase tracking-wide"
                    >
                        <Plus size={14} /> Agregar Fase
                    </button>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 px-4 py-2.5 border-t border-[hsl(var(--border))] dark:border-white/5 shrink-0">
                    <button
                        onClick={handleCancel}
                        className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md transition-all"
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

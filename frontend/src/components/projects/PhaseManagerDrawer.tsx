"use client";

import { RightPanel } from '@/components/ui/RightPanel';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { PHASE_COLOR_OPTIONS, DEFAULT_PHASE_COLOR } from '@/lib/projects/palette';
import { Plus, Save, ShieldCheck, Layers, Sparkles, Trash2, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useProjectUpdate, type PhaseDef } from '@/context/ProjectUpdateContext';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';

interface Props {
    projectId: string;
    onClose: () => void;
}

const COLOR_PRESETS = PHASE_COLOR_OPTIONS.map((option) => option.value);

const PMI_LIFECYCLE_PRESETS: Array<{
    id: 'predictive' | 'hybrid' | 'agile';
    testId: string;
    label: string;
    subtitle: string;
    phases: string[];
}> = [
    {
        id: 'predictive',
        testId: 'phase-preset-predictive',
        label: 'Predictivo PMI (5 Fases)',
        subtitle: 'Cascada secuencial Stage-Gate',
        phases: ['Inicio', 'Planificación', 'Ejecución', 'Monitoreo y Control', 'Cierre'],
    },
    {
        id: 'hybrid',
        testId: 'phase-preset-hybrid',
        label: 'Híbrido Stage-Gate',
        subtitle: 'Gobernanza por hitos + entregas iterativas',
        phases: ['Descubrimiento', 'Diseño y Línea Base', 'Construcción Iterativa', 'Validación QA', 'Despliegue'],
    },
    {
        id: 'agile',
        testId: 'phase-preset-agile',
        label: 'Flujo Adaptativo',
        subtitle: 'Kanban continuo con Definition of Done',
        phases: ['Backlog', 'En Análisis', 'En Progreso', 'En Revisión DoD', 'Completado'],
    },
];

function buildUniqueSlug(name: string, existingSlugs: Set<string>): string {
    const base = name
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'phase';
    let candidate = base;
    let suffix = 2;
    while (existingSlugs.has(candidate.toLowerCase())) {
        candidate = `${base}-${suffix}`;
        suffix += 1;
    }
    return candidate;
}

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
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

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
            color: COLOR_PRESETS[count % COLOR_PRESETS.length] ?? DEFAULT_PHASE_COLOR,
            order_index: count,
        }]);
    };

    const handleApplyPreset = (presetPhases: string[]) => {
        setItems((current) => {
            const existingNames = new Set(
                current.map((item) => item.name.trim().toLowerCase()),
            );
            const existingSlugs = new Set(
                current.map((item) => item.slug.toLowerCase()),
            );
            const next = [...current];
            for (const phaseName of presetPhases) {
                const normalizedName = phaseName.trim().toLowerCase();
                if (existingNames.has(normalizedName)) continue;
                const slug = buildUniqueSlug(phaseName, existingSlugs);
                existingNames.add(normalizedName);
                existingSlugs.add(slug.toLowerCase());
                const index = next.length;
                next.push({
                    slug,
                    name: phaseName,
                    color: COLOR_PRESETS[index % COLOR_PRESETS.length] ?? DEFAULT_PHASE_COLOR,
                    order_index: index,
                });
            }
            return next;
        });
    };

    const handleRemove = (index: number) => {
        if (items.length <= 1) {
            addToast('Debe haber al menos una fase', 'error');
            return;
        }
        const phase = items[index];
        if (!phase) return;
        const linkedTaskCount = (ctxTasks ?? []).filter(
            task => (task.status ?? '').toLowerCase() === phase.slug.toLowerCase(),
        ).length;
        if (linkedTaskCount > 0) {
            const message = linkedTaskCount === 1
                ? 'Mueve la tarea de esta fase antes de eliminarla.'
                : `Mueve las ${linkedTaskCount} tareas de esta fase antes de eliminarla.`;
            setError(message);
            addToast(message, 'error');
            return;
        }
        setConfirmAction({
            title: 'Eliminar fase del borrador',
            description: `¿Confirmas quitar “${phase.name}” del borrador de fases? Esta fase aún no se eliminará del proyecto hasta que guardes los cambios.`,
            destructive: true,
            confirmLabel: 'Eliminar fase',
            onConfirm: () => {
                setItems(current => current.filter(item => item.slug !== phase.slug));
                setConfirmAction(null);
            },
        });
    };

    const allTasks = ctxTasks ?? [];
    const validSlugsSet = new Set(items.map((item) => item.slug.toLowerCase()));
    const orphanTasks = allTasks.filter(
        (t) => !validSlugsSet.has((t.status ?? 'todo').toLowerCase()),
    );
    const orphanTasksCount = orphanTasks.length;

    const phaseCounts = items.map((phase) => ({
        phase,
        count: allTasks.filter(
            (task) => (task.status ?? '').toLowerCase() === phase.slug.toLowerCase(),
        ).length,
    }));

    const bottleneckEntry = phaseCounts.reduce<{ name: string; count: number } | null>(
        (acc, curr) => {
            if (curr.count === 0) return acc;
            if (!acc || curr.count > acc.count) {
                return { name: curr.phase.name, count: curr.count };
            }
            return acc;
        },
        null,
    );

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
        } catch (err: unknown) {
            setError('No se pudieron guardar las fases. Ajusta los cambios y vuelve a intentarlo.');
            const detail = typeof err === 'object' && err !== null && 'detail' in err
                ? typeof (err as { detail: unknown }).detail === 'string'
                    ? (err as { detail: string }).detail
                    : (err as { detail: { detail?: string; message?: string } }).detail?.detail
                        || (err as { detail: { detail?: string; message?: string } }).detail?.message
                        || (err as { detail: unknown }).detail ? JSON.stringify((err as { detail: unknown }).detail) : ''
                : '';
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
        <RightPanel
            open={true}
            onClose={onClose}
            title="Gestionar Fases"
            width="w-full sm:w-[85vw] lg:w-[68vw] xl:w-[60vw] max-w-none"
            resizeStorageKey="workspace:project_tools_width"
            resizeDefaultWidth={960}
        >
            <div className="flex flex-col h-full">
                {error && (
                    <div className="mx-3 mt-3 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-[hsl(var(--warning))]">
                        <p className="text-xs font-bold uppercase tracking-wide">{error}</p>
                    </div>
                )}
                {/* Body */}
                <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-3">
                    {/* Banner Ejecutivo de Gobernanza Stage-Gate PMI §2.4 */}
                    <div
                        data-testid="phase-manager-pmi-summary"
                        className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 space-y-2.5"
                    >
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                                <span className="p-1.5 rounded-md bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
                                    <ShieldCheck size={15} />
                                </span>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                                        Gobernanza de Ciclo de Vida & Stage-Gates (PMI §2.4)
                                    </p>
                                    <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                                        Control de integridad de fases, carga de paquetes WBS y prevención de estados huérfanos.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-2">
                                <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Fases Configuradas
                                </p>
                                <p className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                                    {items.length}
                                </p>
                            </div>
                            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-2">
                                <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Paquetes WBS
                                </p>
                                <p className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                                    {allTasks.length}
                                </p>
                            </div>
                            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-2">
                                <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Fase Cuello de Botella
                                </p>
                                <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5 truncate">
                                    {bottleneckEntry ? `${bottleneckEntry.name} (${bottleneckEntry.count})` : 'Sin carga'}
                                </p>
                            </div>
                            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-2">
                                <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Riesgo de Huérfanos
                                </p>
                                {orphanTasksCount === 0 ? (
                                    <p className="text-xs font-bold text-[hsl(var(--success))] mt-0.5">
                                        0 huérfanos
                                    </p>
                                ) : (
                                    <p className="text-xs font-bold text-[hsl(var(--warning))] mt-0.5 flex items-center gap-1">
                                        <AlertTriangle size={12} />
                                        {orphanTasksCount} huérfano(s)
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Selector Rápido de Presets de Ciclo de Vida PMI */}
                    <div
                        data-testid="phase-manager-pmi-presets"
                        className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 space-y-2"
                    >
                        <div className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            <Sparkles size={13} className="text-[hsl(var(--primary))]" />
                            <span>Plantillas de Ciclo de Vida PMI (Adición Segura 1-Clic)</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                            {PMI_LIFECYCLE_PRESETS.map((preset) => (
                                <button
                                    key={preset.id}
                                    type="button"
                                    data-testid={preset.testId}
                                    onClick={() => handleApplyPreset(preset.phases)}
                                    className="flex flex-col items-start text-left rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary)/0.5)] hover:bg-[hsl(var(--primary)/0.05)] p-2.5 transition-all"
                                >
                                    <span className="text-xs font-bold text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                        <Layers size={12} className="text-[hsl(var(--primary))]" />
                                        {preset.label}
                                    </span>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5">
                                        {preset.subtitle}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 content-start">
                    {items.map((phase, i) => {
                        const linkedCount = phaseCounts[i]?.count ?? 0;
                        return (
                        <div
                            key={phase.slug}
                            className="flex items-center gap-3 p-3 bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] group"
                        >
                            {/* Reorder buttons */}
                            <div className="flex flex-col gap-0.5 shrink-0">
                                <button type="button" onClick={() => handleMoveUp(i)} disabled={i === 0} aria-label={`Mover fase ${phase.name} arriba`} className="size-4 flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▲</span>
                                </button>
                                <button type="button" onClick={() => handleMoveDown(i)} disabled={i === items.length - 1} aria-label={`Mover fase ${phase.name} abajo`} className="size-4 flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] disabled:opacity-20 disabled:cursor-not-allowed">
                                    <span className="font-semibold leading-none">▼</span>
                                </button>
                            </div>

                            {/* Color picker trigger */}
                            <div className="relative shrink-0">
                                <div className="size-7 rounded-lg border border-[hsl(var(--border))]" style={{ backgroundColor: phase.color }} />
                                <select
                                    value={phase.color}
                                    onChange={e => handleChangeColor(i, e.target.value)}
                                    className="absolute inset-0 opacity-0 cursor-pointer"
                                    aria-label={`Color de fase ${phase.name}`}
                                >
                                    {PHASE_COLOR_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>{option.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Name input + Metrics */}
                            <div className="flex-1 min-w-0">
                                <input
                                    type="text"
                                    value={phase.name}
                                    onChange={e => handleRename(i, e.target.value)}
                                    aria-label={`Nombre de fase ${phase.name}`}
                                    className="w-full text-base font-bold bg-transparent outline-none text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] border-b border-transparent focus:border-[hsl(var(--primary))] transition-all"
                                />
                                <div
                                    data-testid={`phase-card-metrics-${phase.slug}`}
                                    className="flex items-center gap-1.5 mt-1 text-2xs"
                                >
                                    <span className="font-medium text-[hsl(var(--muted-foreground))]">
                                        {linkedCount} paquete(s)
                                    </span>
                                    <span
                                        className={
                                            linkedCount > 0
                                                ? 'px-1.5 py-0.5 rounded font-bold uppercase tracking-wider bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]'
                                                : 'px-1.5 py-0.5 rounded font-bold uppercase tracking-wider bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                                        }
                                    >
                                        {linkedCount > 0 ? 'En uso' : 'Libre'}
                                    </span>
                                </div>
                            </div>

                            {/* Slug (read-only, derived) */}
                            <code className="hidden md:inline text-2xs font-mono text-[hsl(var(--muted-foreground))] opacity-60 truncate max-w-[120px]" title={phase.slug}>
                                {phase.slug}
                            </code>

                            {/* Delete */}
                                <button
                                    type="button"
                                    onClick={() => handleRemove(i)}
                                    aria-label={`Eliminar fase ${phase.name}`}
                                    className="size-7 rounded-lg flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-all shrink-0"
                            >
                                <Trash2 size={12} />
                            </button>
                        </div>
                        );
                    })}
                    </div>

                    {/* Add phase */}
                    <button
                        type="button"
                        onClick={handleAdd}
                        className="w-full flex items-center justify-center gap-2 py-3 rounded-md border-2 border-dashed border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--primary)/0.3)] transition-all text-xs font-semibold uppercase tracking-wide"
                    >
                        <Plus size={14} /> Agregar Fase
                    </button>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-2 px-4 py-2.5 border-t border-[hsl(var(--border))] shrink-0">
                    <button
                        onClick={handleCancel}
                        className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] rounded-md transition-all"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] flex items-center gap-2 hover:bg-[hsl(var(--primary)/0.9)] active:scale-95 disabled:opacity-50 transition-all"
                    >
                        {saving ? (
                            <div className="size-4 border-2 border-[hsl(var(--primary-foreground)/0.3)] border-t-[hsl(var(--primary-foreground))] rounded-full animate-spin" />
                        ) : (
                            <Save size={14} />
                        )}
                        Guardar
                    </button>
                </div>
            </div>
            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </RightPanel>
    );
}

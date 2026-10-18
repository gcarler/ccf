"use client";

import { useState, useRef, useMemo, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, ChevronRight, GitBranch, ListChecks, Plus, UserX, X } from 'lucide-react';
import clsx from 'clsx';

export interface Activity {
    id: string;
    title: string;
    completed: boolean;
    assignee?: { name: string; color?: string };
    children?: Activity[];
}

type PmiActivityFilter = 'ALL' | 'PENDING' | 'COMPLETED' | 'UNASSIGNED';

const PMI_ACTIVITY_FILTERS: { key: PmiActivityFilter; label: string }[] = [
    { key: 'ALL', label: 'Todas' },
    { key: 'PENDING', label: 'Pendientes' },
    { key: 'COMPLETED', label: 'Completadas' },
    { key: 'UNASSIGNED', label: 'Sin Responsable' },
];

/** Pasos canónicos del ciclo PHVA/PDCA (PMI §6.2 — Definir las Actividades). */
const PMI_PDCA_PRESETS: { key: 'plan' | 'do' | 'check' | 'act'; label: string; text: string }[] = [
    {
        key: 'plan',
        label: 'Plan',
        text: '[Planificar] Definir alcance técnico y criterios de aceptación',
    },
    {
        key: 'do',
        label: 'Do',
        text: '[Hacer] Construir e integrar entregable del paquete',
    },
    {
        key: 'check',
        label: 'Check',
        text: '[Verificar] Ejecutar pruebas QA y validar evidencia DoD',
    },
    {
        key: 'act',
        label: 'Act',
        text: '[Actuar] Documentar lecciones aprendidas y cierre',
    },
];

export interface ActivityPmiStats {
    totalCount: number;
    completedCount: number;
    completionPct: number;
    unassignedPendingCount: number;
    maxDepth: number;
}

/** Diagnóstico recursivo de descomposición de actividades (PMI §6.2). */
export function computeActivityPmiStats(activities: Activity[]): ActivityPmiStats {
    let totalCount = 0;
    let completedCount = 0;
    let unassignedPendingCount = 0;
    let maxDepth = 0;

    const visit = (nodes: Activity[], depth: number) => {
        for (const node of nodes) {
            totalCount += 1;
            maxDepth = Math.max(maxDepth, depth);
            if (node.completed) completedCount += 1;
            else if (!node.assignee?.name) unassignedPendingCount += 1;
            if (node.children?.length) visit(node.children, depth + 1);
        }
    };
    visit(activities, 1);

    return {
        totalCount,
        completedCount,
        completionPct: totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0,
        unassignedPendingCount,
        maxDepth,
    };
}

/** Filtra el árbol conservando nodos que cumplen o que tienen descendientes que cumplen. */
export function filterActivityTree(
    activities: Activity[],
    predicate: (a: Activity) => boolean,
): Activity[] {
    const result: Activity[] = [];
    for (const node of activities) {
        const filteredChildren = node.children
            ? filterActivityTree(node.children, predicate)
            : [];
        if (predicate(node) || filteredChildren.length > 0) {
            result.push({ ...node, children: filteredChildren });
        }
    }
    return result;
}

export function toggleActivity(activities: Activity[], id: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, completed: !a.completed };
        if (a.children) return { ...a, children: toggleActivity(a.children, id) };
        return a;
    });
}

export function addChild(activities: Activity[], parentId: string, newItem: Activity): Activity[] {
    return activities.map(a => {
        if (a.id === parentId) return { ...a, children: [...(a.children ?? []), newItem] };
        if (a.children) return { ...a, children: addChild(a.children, parentId, newItem) };
        return a;
    });
}

export function updateTitle(activities: Activity[], id: string, title: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, title };
        if (a.children) return { ...a, children: updateTitle(a.children, id, title) };
        return a;
    });
}

function ActivityItem({
    activity,
    depth = 0,
    onToggle,
    onAddChild,
    onUpdateTitle,
    onDelete,
}: {
    activity: Activity;
    depth?: number;
    onToggle: (id: string) => void;
    onAddChild: (parentId: string) => void;
    onUpdateTitle: (id: string, title: string) => void;
    onDelete: (id: string) => void;
}) {
    const [expanded, setExpanded] = useState(depth === 0);
    const [editing, setEditing] = useState(false);
    const [titleVal, setTitleVal] = useState(activity.title);
    const hasChildren = (activity.children?.length ?? 0) > 0;
    const inputRef = useRef<HTMLInputElement>(null);
    const cancelEditRef = useRef(false);

    useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

    return (
        <div>
            <div
                className={clsx(
                    'group flex items-center gap-1.5 py-1.5 px-2 rounded-lg transition-colors hover:bg-[hsl(var(--surface-1))] relative',
                )}
                style={{ paddingLeft: depth * 20 + 8 }}
            >
                {depth > 0 && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-[hsl(var(--border))]"
                        style={{ left: depth * 20 - 4 }}
                    />
                )}

                {hasChildren ? (
                    <button
                        type="button"
                        onClick={() => setExpanded(v => !v)}
                        aria-expanded={expanded}
                        aria-label={`${expanded ? 'Contraer' : 'Expandir'} sub-actividades de ${activity.title}`}
                        className="size-4 flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors shrink-0"
                    >
                        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </button>
                ) : <span aria-hidden="true" className="size-4 shrink-0" />}

                <button
                    type="button"
                    onClick={() => onToggle(activity.id)}
                    aria-pressed={activity.completed}
                    aria-label={activity.completed ? `Marcar como pendiente: ${activity.title}` : `Completar actividad: ${activity.title}`}
                    className={clsx(
                        'size-4 rounded border-2 flex items-center justify-center shrink-0 transition-all',
                        activity.completed
                            ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]'
                            : 'border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]'
                    )}
                >
                    {activity.completed && <Check size={9} strokeWidth={3} />}
                </button>

                {editing ? (
                    <input
                        ref={inputRef}
                        aria-label={`Editar actividad: ${activity.title}`}
                        value={titleVal}
                        onChange={e => setTitleVal(e.target.value)}
                        onBlur={() => {
                            if (cancelEditRef.current) {
                                cancelEditRef.current = false;
                            } else {
                                onUpdateTitle(activity.id, titleVal);
                            }
                            setEditing(false);
                        }}
                        onKeyDown={e => {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                inputRef.current?.blur();
                            }
                            if (e.key === 'Escape') {
                                e.preventDefault();
                                cancelEditRef.current = true;
                                setTitleVal(activity.title);
                                inputRef.current?.blur();
                            }
                        }}
                        className="flex-1 text-sm bg-transparent outline-none border-b border-[hsl(var(--primary))] text-[hsl(var(--foreground))]"
                    />
                ) : (
                    <button
                        type="button"
                        onClick={() => setEditing(true)}
                        aria-label={`Editar actividad: ${activity.title}`}
                        className={clsx(
                            'flex-1 text-left text-sm font-medium cursor-text select-none truncate',
                            activity.completed
                                ? 'line-through text-[hsl(var(--muted-foreground))]'
                                : 'text-[hsl(var(--foreground))]'
                        )}
                    >
                        {activity.title}
                    </button>
                )}

                {activity.assignee && (
                    <div
                        title={activity.assignee.name}
                        className="size-5 rounded-full flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))] shrink-0"
                        style={{ backgroundColor: activity.assignee.color ?? 'hsl(var(--primary))' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                <button
                    type="button"
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    aria-label={`Añadir sub-actividad a ${activity.title}`}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>

                <button
                    type="button"
                    onClick={() => onDelete(activity.id)}
                    aria-label={`Eliminar actividad: ${activity.title}`}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-all"
                    title="Eliminar actividad"
                >
                    <X size={10} strokeWidth={2.5} />
                </button>
            </div>

            <AnimatePresence initial={false}>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                    >
                        {activity.children!.map(child => (
                            <ActivityItem
                                key={child.id}
                                activity={child}
                                depth={depth + 1}
                                onToggle={onToggle}
                                onAddChild={onAddChild}
                                onUpdateTitle={onUpdateTitle}
                                onDelete={onDelete}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default function TaskActivitySection({
    activities,
    newActivityTitle,
    onNewActivityTitleChange,
    onAddTopLevel,
    onToggle,
    onAddChild,
    onUpdateTitle,
    onDelete,
}: {
    activities: Activity[];
    newActivityTitle: string;
    onNewActivityTitleChange: (v: string) => void;
    onAddTopLevel: () => void;
    onToggle: (id: string) => void;
    onAddChild: (parentId: string) => void;
    onUpdateTitle: (id: string, title: string) => void;
    onDelete: (id: string) => void;
}) {
    const [pmiFilter, setPmiFilter] = useState<PmiActivityFilter>('ALL');

    const pmiStats = useMemo(() => computeActivityPmiStats(activities), [activities]);
    const visibleActivities = useMemo(() => {
        if (pmiFilter === 'ALL') return activities;
        const predicate = (a: Activity): boolean => {
            if (pmiFilter === 'PENDING') return !a.completed;
            if (pmiFilter === 'COMPLETED') return a.completed;
            return !a.completed && !a.assignee?.name;
        };
        return filterActivityTree(activities, predicate);
    }, [activities, pmiFilter]);

    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))]">
            <div className="flex items-center justify-between mb-3">
                <h3 id="task-activities-heading" className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                    <Check size={11} /> Actividades
                    <span className="px-1.5 py-0.5 bg-[hsl(var(--surface-2))] rounded text-[hsl(var(--muted-foreground))] font-bold text-2xs">
                        {activities.length}
                    </span>
                </h3>
            </div>

            {activities.length > 0 && (
                <div
                    data-testid="task-activities-pmi-summary"
                    className="mb-3 space-y-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] px-3 py-2"
                >
                    <div className="flex items-center justify-between flex-wrap gap-1 text-2xs">
                        <span className="inline-flex items-center gap-1 font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            <ListChecks size={11} className="text-[hsl(var(--primary))]" />
                            Descomposición de Actividades PMI
                        </span>
                        <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                            Nivel de descomposición máx.:{' '}
                            <span className="font-bold text-[hsl(var(--foreground))]">Nivel {pmiStats.maxDepth}</span>
                        </span>
                    </div>

                    <div className="flex items-center justify-between flex-wrap gap-1 text-2xs text-[hsl(var(--muted-foreground))]">
                        <span>
                            Total Nodos: <span className="font-bold text-[hsl(var(--foreground))]">{pmiStats.totalCount}</span>{' '}
                            · Completadas:{' '}
                            <span className="font-bold text-[hsl(var(--foreground))]">{pmiStats.completedCount}</span>
                        </span>
                        <span
                            title="Actividades pendientes sin responsable asignado"
                            className={clsx(
                                "inline-flex items-center gap-1 font-medium",
                                pmiStats.unassignedPendingCount > 0
                                    ? "text-[hsl(var(--warning))]"
                                    : "text-[hsl(var(--muted-foreground))]",
                            )}
                        >
                            <UserX size={11} aria-hidden="true" />
                            Brechas sin Responsable: {pmiStats.unassignedPendingCount}
                        </span>
                    </div>

                    <div className="space-y-1">
                        <div className="flex items-center justify-between text-2xs">
                            <span className="text-[hsl(var(--muted-foreground))]">Avance de Actividades:</span>
                            <span className="font-bold text-[hsl(var(--foreground))]">{pmiStats.completionPct}%</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-[hsl(var(--surface-3))] overflow-hidden">
                            <div
                                className={clsx(
                                    "h-full rounded-full transition-all duration-300",
                                    pmiStats.completionPct >= 100
                                        ? "bg-[hsl(var(--success))]"
                                        : "bg-[hsl(var(--primary))]",
                                )}
                                style={{ width: `${Math.min(100, pmiStats.completionPct)}%` }}
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* Filtro jerárquico de actividades PMI */}
            {activities.length > 0 && (
                <div
                    data-testid="task-activities-pmi-filter"
                    className="mb-2 flex flex-wrap items-center gap-1"
                    role="group"
                    aria-label="Filtrar actividades PMI"
                >
                    {PMI_ACTIVITY_FILTERS.map((option) => {
                        const isActive = pmiFilter === option.key;
                        return (
                            <button
                                key={option.key}
                                type="button"
                                aria-pressed={isActive}
                                onClick={() => setPmiFilter(option.key)}
                                className={clsx(
                                    "rounded-md border px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide transition-colors",
                                    isActive
                                        ? "border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"
                                        : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] opacity-70 hover:opacity-100",
                                )}
                            >
                                {option.label}
                            </button>
                        );
                    })}
                </div>
            )}

            <div className="space-y-0.5">
                {visibleActivities.map(a => (
                    <ActivityItem
                        key={a.id}
                        activity={a}
                        depth={0}
                        onToggle={onToggle}
                        onAddChild={onAddChild}
                        onUpdateTitle={onUpdateTitle}
                        onDelete={onDelete}
                    />
                ))}
            </div>
            {visibleActivities.length === 0 && activities.length > 0 && (
                <p className="mt-2 rounded-md border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] px-2.5 py-2 text-center text-2xs text-[hsl(var(--muted-foreground))]">
                    No hay actividades del nivel PMI seleccionado.
                </p>
            )}

            {/* Asistente 1-Clic de pasos canónicos PMI / PHVA */}
            <div
                data-testid="task-activities-pmi-presets"
                className="mt-2 flex flex-wrap items-center gap-1 pl-2"
            >
                <GitBranch size={11} className="text-[hsl(var(--muted-foreground))] shrink-0" aria-hidden="true" />
                <span className="text-2xs text-[hsl(var(--muted-foreground))]">Pasos PHVA:</span>
                {PMI_PDCA_PRESETS.map((preset) => (
                    <button
                        key={preset.key}
                        type="button"
                        data-testid={`task-activity-preset-${preset.key}`}
                        onClick={() => onNewActivityTitleChange(preset.text)}
                        aria-label={`Prefijar actividad: ${preset.text}`}
                        className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] transition-colors hover:border-[hsl(var(--primary)/0.35)] hover:bg-[hsl(var(--primary)/0.12)] hover:text-[hsl(var(--primary))]"
                    >
                        {preset.label}
                    </button>
                ))}
            </div>

            <div className="flex items-center gap-2 mt-2 pl-2">
                <Plus size={13} className="text-[hsl(var(--muted-foreground))] shrink-0" />
                <input
                    type="text"
                    aria-label="Añadir actividad"
                    value={newActivityTitle}
                    onChange={e => onNewActivityTitleChange(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && onAddTopLevel()}
                    placeholder="Añadir actividad..."
                    className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
                />
                {newActivityTitle.trim() && (
                    <button
                        type="button"
                        aria-label="Añadir actividad"
                        onClick={onAddTopLevel}
                        className="px-2 py-1 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold hover:bg-[hsl(var(--primary))] transition-all"
                    >
                        + Añadir
                    </button>
                )}
            </div>
        </section>
    );
}

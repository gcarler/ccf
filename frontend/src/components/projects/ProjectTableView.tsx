"use client";

import { useMemo, useRef, useState, useEffect } from 'react';
import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';
import clsx from 'clsx';
import { Star, ShieldCheck, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectUserFavorite } from '@/types/projects';
import { getStatusOption, getPriorityOption } from '@/lib/projects/constants';
import { TaskStatusBadge, TaskPriorityBadge } from './badges';

type TaskWithOptionalProgress = ProjectTaskRecord & {
    progress?: number | null;
};

type PmiTableFilter = 'ALL' | 'RACI_GAP' | 'OVERDUE' | 'CRITICAL';

function isTaskCompleted(task: TaskWithOptionalProgress): boolean {
    const st = (task.status ?? '').toLowerCase();
    const rawProgress = Number(task.progress ?? task.progress_pct ?? task.physical_progress_pct ?? 0);
    return st === 'completed' || st === 'done' || rawProgress >= 100;
}

function getTaskRule050100Score(task: TaskWithOptionalProgress): number {
    if (isTaskCompleted(task)) return 100;
    const st = (task.status ?? '').toLowerCase();
    const rawProgress = Number(task.progress ?? task.progress_pct ?? task.physical_progress_pct ?? 0);
    if (st && st !== 'todo' && st !== 'pending' && st !== 'backlog') {
        return Math.max(50, Number.isFinite(rawProgress) ? rawProgress : 0);
    }
    return 0;
}

function TitleRenderer({ value, data }: { value: string; data: { id?: string; status?: string } }) {
    const st = data?.status === 'completed';
    return (
        <div className="flex items-center gap-2.5">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                st ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]' : 'border-[hsl(var(--border))]')}>
                {st && <span className="text-2xs font-bold">✓</span>}
            </div>
            <span className="text-base font-bold text-[hsl(var(--foreground))] truncate">{value}</span>
        </div>
    );
}

function StatusRenderer({ value }: { value: string }) {
    const opt = getStatusOption(value?.toLowerCase());
    return <TaskStatusBadge value={value} className="max-w-full" title={opt.label} />;
}

function PriorityRenderer({ value }: { value: string }) {
    const opt = getPriorityOption(value?.toLowerCase());
    return <TaskPriorityBadge value={value} className="max-w-full" title={opt.label} />;
}

function AssigneeRenderer({ value, assigneeMap }: { value: string | null | undefined; assigneeMap?: Record<string, string> }) {
    if (!value) return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;
    const name = (assigneeMap && assigneeMap[value]) || value;
    return (
        <span
            className="text-xs font-bold text-[hsl(var(--foreground))]"
            title={name}
        >
            {name}
        </span>
    );
}

function DateRenderer({ value }: { value: string }) {
    if (!value) return <span className="text-[hsl(var(--muted-foreground))] text-xs">—</span>;
    return <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">{new Date(value).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' })}</span>;
}

function ProgressRenderer({
    data,
}: {
    value?: unknown;
    data?: { status?: string; progress?: number | null; progress_pct?: number | null; physical_progress_pct?: number | null };
}) {
    const st = (data?.status ?? '').toLowerCase();
    const isDone = st === 'completed' || st === 'done';
    const raw = Number(data?.progress ?? data?.progress_pct ?? data?.physical_progress_pct ?? 0);
    const pct = isDone ? 100 : Number.isFinite(raw) ? Math.max(0, Math.min(100, Math.round(raw))) : 0;
    return (
        <span
            className={clsx(
                'text-xs font-bold',
                pct >= 100
                    ? 'text-[hsl(var(--success))]'
                    : pct > 0
                      ? 'text-[hsl(var(--primary))]'
                      : 'text-[hsl(var(--muted-foreground))]'
            )}
        >
            {pct}%
        </span>
    );
}

function BudgetRenderer({ value }: { value?: number | string | null }) {
    const numeric = Number(value ?? 0);
    if (!Number.isFinite(numeric) || numeric <= 0) {
        return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;
    }
    return (
        <span className="text-xs font-bold text-[hsl(var(--foreground))]">
            ${numeric.toLocaleString('es-CO')}
        </span>
    );
}

const PMI_FILTER_OPTIONS: Array<{ id: PmiTableFilter; label: string }> = [
    { id: 'ALL', label: 'Todas' },
    { id: 'RACI_GAP', label: 'Sin Responsable' },
    { id: 'OVERDUE', label: 'Vencidas' },
    { id: 'CRITICAL', label: 'Críticas / Urgentes' },
];

export default function ProjectTableView({ tasks, projectId }: { tasks: ProjectTaskRecord[]; projectId?: string }) {
    const gridRef = useRef<AgGridTableRef>(null);
    const { token } = useAuth();
    const [onlyFavorites, setOnlyFavorites] = useState(false);
    const [pmiFilter, setPmiFilter] = useState<PmiTableFilter>('ALL');
    const [favoriteTaskIds, setFavoriteTaskIds] = useState<Set<string>>(new Set());
    const [assigneeMap, setAssigneeMap] = useState<Record<string, string>>({});

    const effectiveProjectId = projectId || tasks[0]?.project_id;
    const todayIso = useMemo(() => new Date().toISOString().slice(0, 10), []);

    useEffect(() => {
        let active = true;
        if (!token) return;
        apiFetch<Array<{ id: string; nombre_completo?: string; first_name?: string; last_name?: string; username?: string; user?: { id?: string; username?: string } }>>(
            '/projects/assignee-candidates?limit=1000',
            { token }
        )
            .then(data => {
                if (!active || !Array.isArray(data)) return;
                const map: Record<string, string> = {};
                for (const p of data) {
                    const fullName = [p.first_name, p.last_name].filter(Boolean).join(' ').trim();
                    const name = p.nombre_completo || fullName || p.user?.username || p.username || p.id;
                    if (p.id) map[p.id] = name;
                    if (p.user?.id) map[p.user.id] = name;
                }
                setAssigneeMap(map);
            })
            .catch(() => {});
        return () => { active = false; };
    }, [token]);

    useEffect(() => {
        let active = true;
        if (!effectiveProjectId || !token) return;
        apiFetch<(string | ProjectUserFavorite)[]>(`/projects/${effectiveProjectId}/favorites?entity_type=task`, { token })
            .then(favs => {
                if (active && Array.isArray(favs)) {
                    setFavoriteTaskIds(new Set(favs.map(f => typeof f === 'string' ? f : f.entity_id)));
                }
            })
            .catch(() => {});
        return () => { active = false; };
    }, [effectiveProjectId, token]);

    const pmiMetrics = useMemo(() => {
        const typedTasks = tasks as TaskWithOptionalProgress[];
        const totalCount = typedTasks.length;
        const weightedProgress =
            totalCount > 0
                ? Math.round(
                      typedTasks.reduce((acc, task) => acc + getTaskRule050100Score(task), 0) / totalCount
                  )
                : 0;
        const totalBac = typedTasks.reduce(
            (acc, task) => acc + (Number.isFinite(Number(task.budget_allocated ?? 0)) ? Number(task.budget_allocated ?? 0) : 0),
            0
        );
        const raciGapsCount = typedTasks.filter(
            (task) => !isTaskCompleted(task) && !task.assignee_id
        ).length;
        const overdueCount = typedTasks.filter(
            (task) =>
                !isTaskCompleted(task) &&
                Boolean(task.due_date) &&
                String(task.due_date).slice(0, 10) < todayIso
        ).length;

        return {
            weightedProgress,
            totalBac,
            raciGapsCount,
            overdueCount,
        };
    }, [tasks, todayIso]);

    const displayedTasks = useMemo(() => {
        return (tasks as TaskWithOptionalProgress[]).filter((t) => {
            if (onlyFavorites && !favoriteTaskIds.has(t.id)) {
                return false;
            }
            if (pmiFilter === 'RACI_GAP') {
                return !isTaskCompleted(t) && !t.assignee_id;
            }
            if (pmiFilter === 'OVERDUE') {
                return (
                    !isTaskCompleted(t) &&
                    Boolean(t.due_date) &&
                    String(t.due_date).slice(0, 10) < todayIso
                );
            }
            if (pmiFilter === 'CRITICAL') {
                const prio = (t.priority ?? '').toLowerCase();
                return prio === 'urgent' || prio === 'high';
            }
            return true;
        });
    }, [tasks, onlyFavorites, favoriteTaskIds, pmiFilter, todayIso]);

    const colDefs = useMemo<ColDef[]>(() => [
        { field: 'title',    headerName: 'Tarea',        flex: 2, cellRenderer: TitleRenderer },
        { field: 'status',   headerName: 'Estado',       width: 140, cellRenderer: StatusRenderer },
        {
            field: 'assignee_id',
            headerName: 'Responsable',
            width: 160,
            cellRenderer: (params: { value: string | null | undefined }) => (
                <AssigneeRenderer value={params.value} assigneeMap={assigneeMap} />
            ),
        },
        { field: 'due_date', headerName: 'Entrega',      width: 120, cellRenderer: DateRenderer },
        { field: 'priority', headerName: 'Prioridad',    width: 120, cellRenderer: PriorityRenderer },
        { field: 'progress', headerName: 'Avance PMI',   width: 120, cellRenderer: ProgressRenderer },
        { field: 'budget_allocated', headerName: 'BAC Paquete', width: 130, cellRenderer: BudgetRenderer },
    ], [assigneeMap]);

    // Inline height is dynamic (based on row count) and cannot be expressed with
    // static Tailwind classes. It is intentionally kept as an inline style.
    const height = Math.min(Math.max(displayedTasks.length * 36 + 40, 200), 600);

    return (
        <div className="flex flex-col gap-2">
            {/* Resumen Ejecutivo PMI §6.6 & §7.4 de Paquetes de Trabajo */}
            <div
                data-testid="project-table-pmi-summary"
                className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]"
            >
                <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2">
                    <div className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        <ShieldCheck size={12} className="text-[hsl(var(--primary))]" />
                        <span>Avance Ponderado (0/50/100)</span>
                    </div>
                    <p className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                        {pmiMetrics.weightedProgress}%
                    </p>
                </div>

                <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2">
                    <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        BAC Paquetes
                    </p>
                    <p className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                        ${pmiMetrics.totalBac.toLocaleString('es-CO')}
                    </p>
                </div>

                <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2">
                    <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        Brechas RACI (Sin Responsable)
                    </p>
                    <p
                        className={clsx(
                            'text-sm font-bold mt-0.5',
                            pmiMetrics.raciGapsCount > 0
                                ? 'text-[hsl(var(--warning))]'
                                : 'text-[hsl(var(--success))]'
                        )}
                    >
                        {pmiMetrics.raciGapsCount}
                    </p>
                </div>

                <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2">
                    <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        Vencidas
                    </p>
                    <p
                        className={clsx(
                            'text-sm font-bold mt-0.5 flex items-center gap-1',
                            pmiMetrics.overdueCount > 0
                                ? 'text-[hsl(var(--destructive))]'
                                : 'text-[hsl(var(--success))]'
                        )}
                    >
                        {pmiMetrics.overdueCount > 0 && <AlertTriangle size={12} />}
                        {pmiMetrics.overdueCount}
                    </p>
                </div>
            </div>

            <div className="flex items-center justify-between gap-2 flex-wrap px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                <div className="flex items-center gap-2 flex-wrap">
                    <button
                        type="button"
                        onClick={() => setOnlyFavorites(prev => !prev)}
                        className={clsx(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border',
                            onlyFavorites
                                ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.3)] shadow-xs'
                                : 'text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]'
                        )}
                        title="Filtrar por tareas favoritas"
                    >
                        <Star size={13} className={clsx(onlyFavorites ? 'fill-current text-[hsl(var(--warning))]' : '')} />
                        <span>Solo Mis Favoritas</span>
                        {favoriteTaskIds.size > 0 && (
                            <span className={clsx(
                                'px-1.5 py-0.5 rounded-full text-2xs font-bold',
                                onlyFavorites
                                    ? 'bg-[hsl(var(--warning))] text-[hsl(var(--background))]'
                                    : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]'
                            )}>
                                {favoriteTaskIds.size}
                            </span>
                        )}
                    </button>

                    <div
                        data-testid="project-table-pmi-filter"
                        className="inline-flex items-center gap-1 flex-wrap"
                    >
                        {PMI_FILTER_OPTIONS.map((opt) => {
                            const active = pmiFilter === opt.id;
                            return (
                                <button
                                    key={opt.id}
                                    type="button"
                                    onClick={() => setPmiFilter(opt.id)}
                                    className={clsx(
                                        'px-2.5 py-1 rounded-lg text-2xs font-bold uppercase tracking-wider transition-all border',
                                        active
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:text-[hsl(var(--foreground))]'
                                    )}
                                >
                                    {opt.label}
                                </button>
                            );
                        })}
                    </div>
                </div>
                <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                    {displayedTasks.length} de {tasks.length} tareas
                </span>
            </div>

            <div className="min-w-0 rounded-lg overflow-hidden border border-[hsl(var(--border))] shadow-sm" style={{ height }}>
                <AgGridTable
                    ref={gridRef}
                    density="compact"
                    rowData={displayedTasks}
                    columnDefs={colDefs}
                    defaultColDef={{ resizable: true, sortable: true, suppressMovable: false, minWidth: 96 }}
                    getRowId={(p) => String(p.data.id)}
                    suppressCellFocus
                />
            </div>
        </div>
    );
}


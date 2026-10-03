"use client";

import { useMemo, useRef, useState, useEffect } from 'react';
import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';
import clsx from 'clsx';
import { Star } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectUserFavorite } from '@/types/projects';
import { getStatusOption, getPriorityOption } from '@/lib/projects/constants';
import { TaskStatusBadge, TaskPriorityBadge } from './badges';

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

function AssigneeRenderer({ value }: { value: string | null | undefined }) {
    if (!value) return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;
    return (
        <span
            className="text-xs font-bold text-[hsl(var(--foreground))]"
            title={value}
        >
            {String(value).replace(/-/g, '').slice(0, 8)}
        </span>
    );
}

function DateRenderer({ value }: { value: string }) {
    if (!value) return <span className="text-[hsl(var(--muted-foreground))] text-xs">—</span>;
    return <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">{new Date(value).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' })}</span>;
}

export default function ProjectTableView({ tasks, projectId }: { tasks: ProjectTaskRecord[]; projectId?: string }) {
    const gridRef = useRef<AgGridTableRef>(null);
    const { token } = useAuth();
    const [onlyFavorites, setOnlyFavorites] = useState(false);
    const [favoriteTaskIds, setFavoriteTaskIds] = useState<Set<string>>(new Set());

    const effectiveProjectId = projectId || tasks[0]?.project_id;

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

    const displayedTasks = useMemo(() => {
        if (!onlyFavorites) return tasks;
        return tasks.filter(t => favoriteTaskIds.has(t.id));
    }, [tasks, onlyFavorites, favoriteTaskIds]);

    const colDefs = useMemo<ColDef[]>(() => [
        { field: 'title',    headerName: 'Tarea',        flex: 2, cellRenderer: TitleRenderer },
        { field: 'status',   headerName: 'Estado',       width: 140, cellRenderer: StatusRenderer },
        { field: 'assignee_id', headerName: 'Responsable', width: 130, cellRenderer: AssigneeRenderer },
        { field: 'due_date', headerName: 'Entrega',      width: 120, cellRenderer: DateRenderer },
        { field: 'priority', headerName: 'Prioridad',    width: 120, cellRenderer: PriorityRenderer },
    ], []);

    // Inline height is dynamic (based on row count) and cannot be expressed with
    // static Tailwind classes. It is intentionally kept as an inline style.
    const height = Math.min(Math.max(displayedTasks.length * 36 + 40, 200), 600);

    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
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
                            'px-1.5 py-0.2 rounded-full text-3xs font-bold',
                            onlyFavorites
                                ? 'bg-[hsl(var(--warning))] text-[hsl(var(--background))]'
                                : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]'
                        )}>
                            {favoriteTaskIds.size}
                        </span>
                    )}
                </button>
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


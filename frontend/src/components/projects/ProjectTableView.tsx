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

export default function ProjectTableView({ tasks, projectId }: { tasks: ProjectTaskRecord[]; projectId?: string }) {
    const gridRef = useRef<AgGridTableRef>(null);
    const { token } = useAuth();
    const [onlyFavorites, setOnlyFavorites] = useState(false);
    const [favoriteTaskIds, setFavoriteTaskIds] = useState<Set<string>>(new Set());
    const [assigneeMap, setAssigneeMap] = useState<Record<string, string>>({});

    const effectiveProjectId = projectId || tasks[0]?.project_id;

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

    const displayedTasks = useMemo(() => {
        if (!onlyFavorites) return tasks;
        return tasks.filter(t => favoriteTaskIds.has(t.id));
    }, [tasks, onlyFavorites, favoriteTaskIds]);

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
    ], [assigneeMap]);

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
                            'px-1.5 py-0.5 rounded-full text-2xs font-bold',
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


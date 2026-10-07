"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { STATUS_LABELS, getValidStatus, type TaskStatus } from '@/lib/projects/constants';
import { getAllAssignedProjectTasks, getAllProjects } from '@/lib/projects/api';
import { DSSkeleton } from '@/design';
import { CheckCircle2, FolderOpen, Layout } from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';
import { useSearchParams } from 'next/navigation';
import {
    flattenProjectTasks,
    isTaskOverdue,
    normalizeTaskRow,
    type TaskScope,
    type TaskStatusFilter,
    type TaskViewItem,
} from './taskList';

const STATUS_FLOW: TaskStatus[] = ['todo', 'in_progress', 'review', 'completed'];
// `as const` preserves the literal 'all' union; without it, TS widens the
// array elements to `string` and the setStatus call site (line 80) fails
// typecheck because the state union is narrower than `string`.
const STATUS_FILTERS: TaskStatusFilter[] = ['all', 'todo', 'in_progress', 'review', 'completed', 'overdue'];
const PROJECT_TASK_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];
const PROJECT_TASK_VIEW_OPTIONS: { value: ViewType; label: string }[] = [
    { value: 'list', label: 'Lista' },
    { value: 'table', label: 'Tabla' },
    { value: 'grid', label: 'Tarjetas' },
    { value: 'board', label: 'Tablero' },
    { value: 'kanban', label: 'Kanban' },
    { value: 'calendar', label: 'Calendario' },
    { value: 'gantt', label: 'Gantt' },
    { value: 'wiki', label: 'Wiki' },
];

function normalizeSearchText(value: string): string {
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
}

function formatStatusFilter(value: TaskStatusFilter): string {
    if (value === 'all') return 'Todas';
    if (value === 'overdue') return 'Vencidas';
    return STATUS_LABELS[value as TaskStatus];
}

export default function ProjectsTasksPage() {
    const { token, loading: authLoading } = useAuth();
    const searchParams = useSearchParams();
    const taskScope: TaskScope = searchParams?.get('scope') === 'all' ? 'all' : 'mine';
    const [tasks, setTasks] = useState<TaskViewItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<TaskStatusFilter>('all');
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');
    const [loadAttempt, setLoadAttempt] = useState(0);
    const loadedTaskScope = useRef<TaskScope>(taskScope);
    const taskRequestSequence = useRef(0);

    useEffect(() => {
        const requestId = ++taskRequestSequence.current;
        const controller = new AbortController();
        const load = async () => {
            setLoading(true);
            if (!token) {
                if (requestId !== taskRequestSequence.current) return;
                setLoading(false);
                setTasks([]);
                setError('Debes iniciar sesión para ver las tareas de proyecto.');
                return;
            }
            try {
                setError(null);
                if (taskScope === 'all') {
                    const projects = await getAllProjects(token, { cache: 'no-store', signal: controller.signal });
                    if (requestId !== taskRequestSequence.current) return;
                    setTasks(flattenProjectTasks(projects));
                } else {
                    const data = await getAllAssignedProjectTasks(token, { cache: 'no-store', signal: controller.signal });
                    if (requestId !== taskRequestSequence.current) return;
                    setTasks(data.map((row) => normalizeTaskRow(row)));
                }
                loadedTaskScope.current = taskScope;
            } catch {
                if (controller.signal.aborted || requestId !== taskRequestSequence.current) return;
                if (loadedTaskScope.current !== taskScope) setTasks([]);
                setError('No se pudieron cargar las tareas de proyecto.');
                toast.error('Error al cargar tareas');
            } finally {
                if (!controller.signal.aborted && requestId === taskRequestSequence.current) setLoading(false);
            }
        };
        if (!authLoading) load();
        return () => {
            controller.abort();
            if (taskRequestSequence.current === requestId) taskRequestSequence.current += 1;
        };
    }, [authLoading, loadAttempt, taskScope, token]);

    useEffect(() => {
        const view = searchParams?.get('view');
        if (!view) return;
        const allowedViews: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];
        if (allowedViews.includes(view as ViewType)) {
            setViewType(view as ViewType);
        }
    }, [searchParams]);

    const filtered = useMemo(() => {
        const terms = normalizeSearchText(search).split(/\s+/).filter(Boolean);
        return tasks.filter((task) => {
            const matchesStatus = status === 'all'
                || (status === 'overdue' ? isTaskOverdue(task) : task.status === status);
            if (!matchesStatus || terms.length === 0) return matchesStatus;
            const searchableText = normalizeSearchText([
                task.title,
                task.project_title ?? '',
                task.status,
                task.priority ?? '',
            ].join(' '));
            return terms.every((term) => searchableText.includes(term));
        });
    }, [tasks, status, search]);

    const groupedTasks = STATUS_FLOW.map((value) => ({
        id: value,
        label: value,
        rows: filtered.filter((task) => task.status === value),
    }));
    const calendarEvents = filtered.map((task) => ({
        id: task.id,
        title: task.title,
        date: (task.due_date || task.start_date || new Date().toISOString()).split('T')[0],
        color: task.status === 'completed' ? 'emerald' as const : task.priority === 'high' ? 'rose' as const : 'blue' as const,
        location: task.status,
    }));
    const ganttItems = filtered.map((task) => ({
        id: task.id,
        title: task.title,
        subtitle: `${task.status} · ${task.priority || 'normal'}`,
        start_date: task.start_date || task.due_date || new Date().toISOString(),
        end_date: task.due_date || task.start_date || new Date().toISOString(),
        color: task.status === 'completed' ? 'emerald' as const : task.priority === 'high' ? 'rose' as const : 'blue' as const,
        progress: task.status === 'completed' ? 100 : task.status === 'review' ? 75 : task.status === 'in_progress' ? 50 : 20,
    }));

    const moveForward = async (task: TaskViewItem) => {
        const index = STATUS_FLOW.indexOf(getValidStatus(task.status));
        const nextStatus = STATUS_FLOW[Math.min(index + 1, STATUS_FLOW.length - 1)];
        if (!nextStatus || nextStatus === task.status) return;
        try {
            const updated = await apiFetch<TaskViewItem>(`/projects/tasks/${task.id}`, {
                method: 'PATCH',
                token,
                body: { status: nextStatus },
            });
            setTasks((prev) => prev.map((row) => (row.id === task.id ? updated : row)));
        } catch {
            toast.error('Error al cambiar estado de tarea');
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: taskScope === 'all' ? 'Todas las tareas' : 'Mis tareas', icon: CheckCircle2 }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={PROJECT_TASK_VIEWS}
            onSearch={setSearch}
            searchValue={search}
        >
            {error && (
                <div role="alert" className="mx-4 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-[hsl(var(--warning))]">
                    <p className="text-xs font-bold uppercase tracking-wide">{error} {tasks.length > 0 ? 'Se conservan los resultados anteriores.' : ''}</p>
                    <button
                        type="button"
                        onClick={() => setLoadAttempt((attempt) => attempt + 1)}
                        disabled={loading}
                        className="rounded-md border border-[hsl(var(--warning)/0.4)] px-3 py-1.5 text-xs font-semibold transition-colors hover:bg-[hsl(var(--warning)/0.1)] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        Reintentar
                    </button>
                </div>
            )}

            <div className="grid grid-cols-1 gap-2 border-b border-[hsl(var(--border))] px-3 py-3 sm:hidden">
                <label className="sr-only" htmlFor="projects-mobile-view">Vista de tareas</label>
                <select
                    id="projects-mobile-view"
                    aria-label="Vista de tareas"
                    value={viewType}
                    onChange={(event) => setViewType(event.target.value as ViewType)}
                    className="h-10 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 text-sm text-[hsl(var(--foreground))]"
                >
                    {PROJECT_TASK_VIEW_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                </select>
                <label className="sr-only" htmlFor="projects-mobile-search">Buscar tareas</label>
                <input
                    id="projects-mobile-search"
                    type="search"
                    aria-label="Buscar tareas"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar tareas..."
                    className="h-10 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30"
                />
            </div>

            <div className="px-3 py-3 border-b border-[hsl(var(--border))] flex flex-wrap gap-2">
                {STATUS_FILTERS.map((value) => (
                    <button
                        key={value}
                        onClick={() => setStatus(value)}
                        className={clsx(
                            'px-3 py-1 rounded-full text-2xs uppercase tracking-wide font-black border transition-colors',
                            status === value
                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                                : 'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'
                        )}
                    >
                        {formatStatusFilter(value)}
                    </button>
                ))}
            </div>

            <section aria-label="Resultados de tareas" className="flex-1 overflow-y-auto p-4">
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <DSSkeleton key={idx} rounded="lg" className="h-20" />)}</div>
                ) : !error && filtered.length === 0 ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] p-4 text-center text-[hsl(var(--muted-foreground))]">
                        {taskScope === 'all'
                            ? 'No hay tareas en el portafolio para este filtro.'
                            : 'No hay tareas asignadas para este filtro.'}
                    </div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] overflow-hidden">
                        <table className="w-full text-left">
                            <thead className="bg-[hsl(var(--surface-2))]">
                                <tr>
                                    <th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Tarea</th>
                                    {taskScope === 'all' && (
                                        <th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden md:table-cell">Proyecto</th>
                                    )}
                                    <th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden md:table-cell">Estado</th>
                                    <th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hidden lg:table-cell">Prioridad</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[hsl(var(--border))]">
                                {filtered.map((task) => (
                                    <tr key={task.id} className="hover:bg-[hsl(var(--surface-2))]">
                                        <td className="px-3 py-2 text-sm font-medium text-[hsl(var(--foreground))]">{task.title}</td>
                                        {taskScope === 'all' && (
                                            <td className="px-3 py-2 hidden md:table-cell text-xs text-[hsl(var(--muted-foreground))]">{task.project_title || 'Sin proyecto'}</td>
                                        )}
                                        <td className="px-3 py-2 hidden md:table-cell text-xs text-[hsl(var(--muted-foreground))]">{task.status}</td>
                                        <td className="px-3 py-2 hidden lg:table-cell text-xs text-[hsl(var(--muted-foreground))]">{task.priority}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                        {filtered.map((task) => (
                            <article key={task.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                                <h3 className="font-bold text-[hsl(var(--foreground))]">{task.title}</h3>
                                {taskScope === 'all' && (
                                    <p className="mt-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{task.project_title || 'Sin proyecto'}</p>
                                )}
                                <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">{task.status} · {task.priority}</p>
                            </article>
                        ))}
                    </div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
                        {groupedTasks.map((group) => (
                            <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-3">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{group.label}</span>
                                    <span className="text-2xs font-bold text-[hsl(var(--muted-foreground))]">{group.rows.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {group.rows.map((task) => <div key={task.id} className="rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-2 text-sm font-medium">{task.title}</div>)}
                                </div>
                            </section>
                        ))}
                    </div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de tareas de proyecto" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Tareas de proyecto" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Tareas de proyecto" storageKey="wiki_projects_tasks" />
                ) : (
                    <div className="space-y-3">
                        {filtered.map((task) => (
                            <article key={task.id} className="rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                                <div className="flex items-center justify-between gap-3">
                                    <div>
                                        <h3 className="font-bold text-[hsl(var(--foreground))]">{task.title}</h3>
                                        <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">Estado: {task.status} · Prioridad: {task.priority}</p>
                                        {taskScope === 'all' && (
                                            <p className="mt-1 inline-flex items-center gap-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                                                <FolderOpen size={10} /> {task.project_title || 'Sin proyecto'}
                                            </p>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => moveForward(task)}
                                        className="px-3 py-1 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs uppercase tracking-wide font-black"
                                    >
                                        Siguiente estado
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </section>
        </ProjectsShell>
    );
}

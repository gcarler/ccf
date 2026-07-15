"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { STATUS_LABELS, getValidStatus, type TaskStatus } from '@/lib/projects/constants';
import { DSSkeleton } from '@/design/components/DSSkeleton';
import type { ProjectTaskRecord } from '@/types/projects';
import { CheckCircle2, Layout } from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';
import { useSearchParams } from 'next/navigation';

const STATUS_FLOW: TaskStatus[] = ['todo', 'in_progress', 'review', 'completed'];
// `as const` preserves the literal 'all' union; without it, TS widens the
// array elements to `string` and the setStatus call site (line 80) fails
// typecheck because the state union is narrower than `string`.
const STATUS_FILTERS = ['all', 'todo', 'in_progress', 'review', 'completed'] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
const PROJECT_TASK_VIEWS: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

function formatStatusFilter(value: StatusFilter): string {
    return value === 'all' ? 'Todas' : STATUS_LABELS[value as TaskStatus];
}

export default function ProjectsTasksPage() {
    const { token } = useAuth();
    const searchParams = useSearchParams();
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState<StatusFilter>('all');
    const [viewType, setViewType] = useState<ViewType>('list');

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectTaskRecord[]>('/projects/tasks', { token, cache: 'no-store' });
                setTasks(Array.isArray(data) ? data : []);
            } catch (error) {
                toast.error("Error inesperado");
                toast.error('Error al cargar tareas');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

    useEffect(() => {
        const view = searchParams?.get('view');
        if (!view) return;
        const allowedViews: ViewType[] = ['list', 'table', 'grid', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];
        if (allowedViews.includes(view as ViewType)) {
            setViewType(view as ViewType);
        }
    }, [searchParams]);

    const filtered = useMemo(() => {
        if (status === 'all') return tasks;
        return tasks.filter((task) => task.status === status);
    }, [tasks, status]);

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

    const moveForward = async (task: ProjectTaskRecord) => {
        const index = STATUS_FLOW.indexOf(getValidStatus(task.status));
        const nextStatus = STATUS_FLOW[Math.min(index + 1, STATUS_FLOW.length - 1)];
        if (!nextStatus || nextStatus === task.status) return;
        try {
            const updated = await apiFetch<ProjectTaskRecord>(`/projects/tasks/${task.id}`, {
                method: 'PATCH',
                token,
                body: { status: nextStatus },
            });
            setTasks((prev) => prev.map((row) => (row.id === task.id ? updated : row)));
        } catch (error) {
            toast.error("Error inesperado");
            toast.error('Error al cambiar estado de tarea');
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mis tareas', icon: CheckCircle2 }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={PROJECT_TASK_VIEWS}
        >

            <div className="px-3 py-3 border-b border-[hsl(var(--border))] dark:border-white/10 flex flex-wrap gap-2">
                {STATUS_FILTERS.map((value) => (
                    <button
                        key={value}
                        onClick={() => setStatus(value as StatusFilter)}
                        className={clsx(
                            'px-3 py-1 rounded-full text-[10px] uppercase tracking-wide font-black border transition-colors',
                            status === value
                                ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]'
                                : 'border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                        )}
                    >
                        {formatStatusFilter(value)}
                    </button>
                ))}
            </div>

            <main className="flex-1 overflow-y-auto p-4">
                {loading ? (
                    <div className="space-y-3">{[1, 2, 3, 4].map((idx) => <DSSkeleton key={idx} rounded="lg" className="h-20" />)}</div>
                ) : filtered.length === 0 ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 text-center text-[hsl(var(--text-secondary))]">No hay tareas para este filtro.</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                        <table className="w-full text-left">
                            <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                                <tr>
                                    <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tarea</th>
                                    <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Estado</th>
                                    <th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">Prioridad</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                {filtered.map((task) => (
                                    <tr key={task.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]">
                                        <td className="px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">{task.title}</td>
                                        <td className="px-3 py-2 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{task.status}</td>
                                        <td className="px-3 py-2 hidden lg:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{task.priority}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                        {filtered.map((task) => (
                            <article key={task.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5">
                                <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{task.title}</h3>
                                <p className="text-xs text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">{task.status} · {task.priority}</p>
                            </article>
                        ))}
                    </div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
                        {groupedTasks.map((group) => (
                            <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{group.rows.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {group.rows.map((task) => <div key={task.id} className="rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-2 text-sm font-medium">{task.title}</div>)}
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
                            <article key={task.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5">
                                <div className="flex items-center justify-between gap-3">
                                    <div>
                                        <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{task.title}</h3>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">Estado: {task.status} · Prioridad: {task.priority}</p>
                                    </div>
                                    <button
                                        onClick={() => moveForward(task)}
                                        className="px-3 py-1 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] uppercase tracking-wide font-black"
                                    >
                                        Siguiente estado
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </main>
        </ProjectsShell>
    );
}

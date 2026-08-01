"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectPortfolioSummaryRow, ProjectWorkloadSummaryRow, ProjectRecord, ProjectTaskRecord } from '@/types/projects';
import { BarChart3, Layout, MoreHorizontal } from 'lucide-react';
import { DSSkeleton } from '@/design';
import { toast } from 'sonner';

function taskColor(task: ProjectTaskRecord, todayKey: string): 'blue' | 'emerald' | 'amber' | 'rose' | 'sky' {
    if (task.status === 'completed') return 'emerald';
    if (task.priority === 'urgent') return 'rose';
    const due = task.due_date ? task.due_date.slice(0, 10) : null;
    if (due && due < todayKey) return 'rose';
    if (due === todayKey) return 'amber';
    if (task.priority === 'high') return 'sky';
    return 'blue';
}

export default function ProjectsMorePage() {
    const { token, loading: authLoading } = useAuth();
    const [summary, setSummary] = useState<ProjectPortfolioSummaryRow[]>([]);
    const [workload, setWorkload] = useState<ProjectWorkloadSummaryRow[]>([]);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const load = async () => {
            if (!token) {
                setLoading(false);
                setSummary([]);
                setWorkload([]);
                setProjects([]);
                setError('Debes iniciar sesión para ver el resumen de proyectos.');
                return;
            }
            try {
                setError(null);
                const [summaryRows, workloadRows, projectRows] = await Promise.all([
                    apiFetch<ProjectPortfolioSummaryRow[]>('/projects/summary', { token, cache: 'no-store' }),
                    apiFetch<ProjectWorkloadSummaryRow[]>('/projects/workload', { token, cache: 'no-store' }),
                    apiFetch<ProjectRecord[]>('/projects', { token, cache: 'no-store' }).catch(() => []),
                ]);
                setSummary(Array.isArray(summaryRows) ? summaryRows : []);
                setWorkload(Array.isArray(workloadRows) ? workloadRows : []);
                setProjects(Array.isArray(projectRows) ? projectRows : []);
            } catch (error) {
                setSummary([]);
                setWorkload([]);
                setProjects([]);
                setError('No se pudo cargar el resumen de proyectos.');
                toast.error("Error inesperado");
                toast.error('Error al cargar resumen');
            } finally {
                setLoading(false);
            }
        };
        if (!authLoading) load();
    }, [authLoading, token]);

    const metrics = useMemo(() => {
        const totals = summary.reduce(
            (acc, row) => {
                acc.projects += row.total_projects;
                acc.tasks += row.total_tasks;
                acc.done += row.completed_tasks;
                if (row.project_status === 'planning') acc.planning += row.total_projects;
                if (row.project_status === 'active') acc.active += row.total_projects;
                return acc;
            },
            { projects: 0, tasks: 0, done: 0, planning: 0, active: 0 }
        );
        const overloaded = workload.filter((row) => row.overdue_tasks > 0).length;
        return {
            ...totals,
            overloaded,
        };
    }, [summary, workload]);

    // Eventos de calendario y gantt construidos desde tareas reales (F3):
    // antes se fabricaban con ``Date.now() + index * 86400000`` y títulos
    // "Responsable <UUID>". Ahora se usan ``due_date``/``start_date`` y el
    // título real de cada tarea, con el proyecto como contexto.
    const calendarEvents = useMemo(() => {
        const todayKey = new Date().toISOString().slice(0, 10);
        const events: Array<{ id: string | number; title: string; date: string; color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'sky'; location?: string }> = [];
        for (const project of projects) {
            for (const task of project.tasks ?? []) {
                const date = (task.due_date || task.start_date || '').slice(0, 10);
                if (!date) continue;
                events.push({
                    id: task.id,
                    title: task.title,
                    date,
                    color: taskColor(task, todayKey),
                    location: project.title,
                });
            }
        }
        return events.sort((a, b) => a.date.localeCompare(b.date));
    }, [projects]);

    const ganttItems = useMemo(() => {
        const items: Array<{ id: string | number; title: string; subtitle?: string; start_date: string; end_date: string; color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'sky'; progress?: number }> = [];
        for (const project of projects) {
            for (const task of project.tasks ?? []) {
                const start = (task.start_date || task.due_date || '').slice(0, 10);
                const end = (task.due_date || task.start_date || '').slice(0, 10);
                if (!start || !end) continue;
                items.push({
                    id: task.id,
                    title: task.title,
                    subtitle: project.title,
                    start_date: start,
                    end_date: end,
                    color: task.status === 'completed' ? 'emerald' : task.status === 'review' ? 'amber' : 'blue',
                    progress: task.status === 'completed' ? 100 : 0,
                });
            }
        }
        return items.sort((a, b) => a.start_date.localeCompare(b.start_date));
    }, [projects]);

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mas', icon: MoreHorizontal }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
        >
            <main className="flex-1 overflow-y-auto p-3">
                {error && (
                    <div className="mb-3 rounded-lg border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                        <p className="text-xs font-bold uppercase tracking-wide">{error}</p>
                    </div>
                )}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">{[1, 2, 3].map((idx) => <DSSkeleton key={idx} className="h-32 rounded-lg" />)}</div>
                ) : !error && summary.length === 0 && workload.length === 0 && projects.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <BarChart3 size={48} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-4" />
                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Sin datos de resumen</h3>
                        <p className="text-sm text-[hsl(var(--text-secondary))] mt-1 max-w-md">Aún no hay suficiente información de proyectos para mostrar métricas.</p>
                    </div>
                ) : viewType === 'list' ? (
                    <div className="space-y-3">{summary.map((row) => <article key={row.project_status} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5"><h3 className="font-bold uppercase">{row.project_status}</h3><p className="text-sm text-[hsl(var(--text-secondary))] mt-1">{row.total_projects} proyectos · {row.total_tasks} tareas · {row.completed_tasks} completadas</p></article>)}</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto"><table className="w-full min-w-[480px] text-left"><thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5"><tr><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Proyectos</th><th className="px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tareas</th></tr></thead><tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">{summary.map((row) => <tr key={row.project_status}><td className="px-3 py-2 text-sm font-medium">{row.project_status}</td><td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{row.total_projects}</td><td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{row.total_tasks}</td></tr>)}</tbody></table></div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">{summary.map((row) => <section key={row.project_status} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3"><p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{row.project_status}</p><p className="text-xl font-bold mt-2">{row.total_projects}</p><p className="text-sm text-[hsl(var(--text-secondary))] mt-1">{row.total_tasks} tareas</p></section>)}</div>
                ) : viewType === 'calendar' ? (
                    <UniversalCalendarView events={calendarEvents} title="Calendario de carga" />
                ) : viewType === 'gantt' ? (
                    <UniversalGanttView items={ganttItems} moduleName="Carga de proyectos" />
                ) : viewType === 'wiki' ? (
                    <UniversalWikiView moduleName="Resumen de proyectos" storageKey="wiki_projects_more" />
                ) : (
                    <>
                        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <MetricCard label="Proyectos" value={metrics.projects} />
                            <MetricCard label="Tareas" value={metrics.tasks} />
                            <MetricCard label="Tareas completadas" value={metrics.done} />
                        </section>
                        <section className="mt-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                            <h3 className="font-bold flex items-center gap-2"><BarChart3 size={16} /> Estado de pipeline</h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] mt-2">En planificacion: {metrics.planning} · Activos: {metrics.active}</p>
                            <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">Responsables con tareas vencidas: {metrics.overloaded}</p>
                        </section>
                    </>
                )}
            </main>
        </ProjectsShell>
    );
}

function MetricCard({ label, value }: { label: string; value: number }) {
    return (
        <article className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
            <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">{value}</p>
        </article>
    );
}

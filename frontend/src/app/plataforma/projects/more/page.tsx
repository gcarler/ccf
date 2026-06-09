"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectPortfolioSummaryRow, ProjectWorkloadSummaryRow } from '@/types/projects';
import { BarChart3, Layout, MoreHorizontal } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';
import { toast } from 'sonner';

export default function ProjectsMorePage() {
    const { token } = useAuth();
    const [summary, setSummary] = useState<ProjectPortfolioSummaryRow[]>([]);
    const [workload, setWorkload] = useState<ProjectWorkloadSummaryRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const [summaryRows, workloadRows] = await Promise.all([
                    apiFetch<ProjectPortfolioSummaryRow[]>('/projects/summary', { token, cache: 'no-store' }),
                    apiFetch<ProjectWorkloadSummaryRow[]>('/projects/workload', { token, cache: 'no-store' }),
                ]);
                setSummary(Array.isArray(summaryRows) ? summaryRows : []);
                setWorkload(Array.isArray(workloadRows) ? workloadRows : []);
            } catch (error) {
                console.error(error);
                toast.error('Error al cargar resumen');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

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
    const calendarEvents = workload.map((row, index) => ({ id: row.assignee_id || index, title: `Responsable ${row.assignee_id ?? index + 1}`, date: new Date(Date.now() + index * 86400000).toISOString().split('T')[0], color: row.overdue_tasks > 0 ? 'rose' as const : 'emerald' as const, location: `${row.open_tasks + row.in_review} tareas activas` }));
    const ganttItems = workload.map((row, index) => {
        const date = new Date(Date.now() + index * 86400000).toISOString();
        const activeTasks = row.open_tasks + row.in_review;
        return { id: row.assignee_id || index, title: `Responsable ${row.assignee_id ?? index + 1}`, subtitle: `${activeTasks} tareas activas`, start_date: date, end_date: date, color: row.overdue_tasks > 0 ? 'rose' as const : 'emerald' as const, progress: activeTasks > 0 ? Math.max(10, 100 - Math.min(90, row.overdue_tasks * 10)) : 100 };
    });

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mas', icon: MoreHorizontal }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
        >
            <main className="flex-1 overflow-y-auto p-3">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">{[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-32 rounded-lg" />)}</div>
                ) : summary.length === 0 && workload.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <BarChart3 size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                        <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300">Sin datos de resumen</h3>
                        <p className="text-sm text-slate-500 mt-1 max-w-md">Aún no hay suficiente información de proyectos para mostrar métricas.</p>
                    </div>
                ) : viewType === 'list' ? (
                    <div className="space-y-3">{summary.map((row) => <article key={row.project_status} className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5"><h3 className="font-bold uppercase">{row.project_status}</h3><p className="text-sm text-slate-500 mt-1">{row.total_projects} proyectos · {row.total_tasks} tareas · {row.completed_tasks} completadas</p></article>)}</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-50 dark:bg-white/5"><tr><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Estado</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Proyectos</th><th className="px-3 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-400">Tareas</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/5">{summary.map((row) => <tr key={row.project_status}><td className="px-3 py-2 text-sm font-medium">{row.project_status}</td><td className="px-3 py-2 text-[11px] text-slate-500">{row.total_projects}</td><td className="px-3 py-2 text-[11px] text-slate-500">{row.total_tasks}</td></tr>)}</tbody></table></div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">{summary.map((row) => <section key={row.project_status} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{row.project_status}</p><p className="text-xl font-bold mt-2">{row.total_projects}</p><p className="text-sm text-slate-500 mt-1">{row.total_tasks} tareas</p></section>)}</div>
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
                        <section className="mt-3 rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-slate-50 dark:bg-white/5">
                            <h3 className="font-bold flex items-center gap-2"><BarChart3 size={16} /> Estado de pipeline</h3>
                            <p className="text-sm text-slate-500 mt-2">En planificacion: {metrics.planning} · Activos: {metrics.active}</p>
                            <p className="text-sm text-slate-500 mt-1">Responsables con tareas vencidas: {metrics.overloaded}</p>
                        </section>
                    </>
                )}
            </main>
        </ProjectsShell>
    );
}

function MetricCard({ label, value }: { label: string; value: number }) {
    return (
        <article className="rounded-lg border border-slate-200 dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p>
            <p className="text-xl font-bold text-slate-800 dark:text-white mt-1">{value}</p>
        </article>
    );
}


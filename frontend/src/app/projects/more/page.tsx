"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import type { ProjectPortfolioSummaryRow, ProjectWorkloadSummaryRow } from '@/types/projects';
import { BarChart3, Layout, MoreHorizontal } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

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
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mas', icon: MoreHorizontal }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
            />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-32 rounded-3xl" />)}</div>
                ) : viewType === 'list' ? (
                    <div className="space-y-4">{summary.map((row) => <article key={row.project_status} className="rounded-2xl border border-slate-200 dark:border-white/10 p-5 bg-white dark:bg-white/5"><h3 className="font-black uppercase">{row.project_status}</h3><p className="text-sm text-slate-500 mt-2">{row.total_projects} proyectos · {row.total_tasks} tareas · {row.completed_tasks} completadas</p></article>)}</div>
                ) : viewType === 'table' ? (
                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden"><table className="w-full text-left"><thead className="bg-slate-50 dark:bg-white/5"><tr><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Estado</th><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Proyectos</th><th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Tareas</th></tr></thead><tbody className="divide-y divide-slate-100 dark:divide-white/5">{summary.map((row) => <tr key={row.project_status}><td className="px-4 py-3 text-sm font-bold">{row.project_status}</td><td className="px-4 py-3 text-[11px] text-slate-500">{row.total_projects}</td><td className="px-4 py-3 text-[11px] text-slate-500">{row.total_tasks}</td></tr>)}</tbody></table></div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">{summary.map((row) => <section key={row.project_status} className="rounded-2xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-4"><p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{row.project_status}</p><p className="text-3xl font-black mt-3">{row.total_projects}</p><p className="text-sm text-slate-500 mt-2">{row.total_tasks} tareas</p></section>)}</div>
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
                        <section className="mt-6 rounded-3xl border border-slate-200 dark:border-white/10 p-6 bg-slate-50 dark:bg-white/5">
                            <h3 className="font-black flex items-center gap-2"><BarChart3 size={16} /> Estado de pipeline</h3>
                            <p className="text-sm text-slate-500 mt-3">En planificacion: {metrics.planning} · Activos: {metrics.active}</p>
                            <p className="text-sm text-slate-500 mt-1">Responsables con tareas vencidas: {metrics.overloaded}</p>
                        </section>
                    </>
                )}
            </main>
        </div>
    );
}

function MetricCard({ label, value }: { label: string; value: number }) {
    return (
        <article className="rounded-3xl border border-slate-200 dark:border-white/10 p-6 bg-white dark:bg-white/5">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
            <p className="text-4xl font-black text-slate-800 dark:text-white mt-2">{value}</p>
        </article>
    );
}


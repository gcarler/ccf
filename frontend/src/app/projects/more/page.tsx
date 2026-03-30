"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ProjectPortfolioSummaryRow, ProjectWorkloadSummaryRow } from '@/types/projects';
import { BarChart3, Layout, MoreHorizontal } from 'lucide-react';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectsMorePage() {
    const { token } = useAuth();
    const [summary, setSummary] = useState<ProjectPortfolioSummaryRow[]>([]);
    const [workload, setWorkload] = useState<ProjectWorkloadSummaryRow[]>([]);
    const [loading, setLoading] = useState(true);

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

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Mas', icon: MoreHorizontal }]}
                viewType="grid"
                setViewType={() => {}}
            />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{[1, 2, 3].map((idx) => <Skeleton key={idx} className="h-32 rounded-3xl" />)}</div>
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

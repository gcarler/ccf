"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import type { CourseSummary, DashboardMetrics, PilotReadiness } from '@/types/academy';
import { GraduationCap, AlertTriangle, ShieldCheck, Download, Filter, Plus } from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';
import { DSMetric, DSCard, DSBadge } from '@/design';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { useWikiDocument } from '@/hooks/useWikiDocument';

import WorkspaceLayout from '@/components/WorkspaceLayout';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';

export default function CoordinationConsole() {
    const { token, isAuthenticated } = useAuth();
    const router = useRouter();
    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [readiness, setReadiness] = useState<PilotReadiness | null>(null);
    const [courses, setCourses] = useState<CourseSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [modalityFilter, setModalityFilter] = useState<'all' | 'formal' | 'non_formal'>('all');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('academy_coordination_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('academy_coordination_wiki_notes', {
        title: 'Wiki de coordinacion academica',
    });

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        const load = async () => {
            try {
                setLoading(true);
                const [metricsData, readinessData, coursesData] = await Promise.all([
                    apiFetch<DashboardMetrics>(`/academy/dashboard/metrics`, { token, cache: 'no-store' }),
                    apiFetch<PilotReadiness>(`/academy/dashboard/pilot-readiness`, { token, cache: 'no-store' }),
                    apiFetch<CourseSummary[]>(`/academy/courses/?modality=formal&published_only=false`, { token, cache: 'no-store' }),
                ]);
                setMetrics(metricsData);
                setReadiness(readinessData);
                setCourses(Array.isArray(coursesData) ? coursesData : []);
            } catch (err) {
                console.error(err);
                toast.error('No pudimos sincronizar los datos de coordinación');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token, isAuthenticated]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('academy_coordination_view', viewType);
        }
    }, [viewType]);

    const readinessPerc = readiness?.readiness_score != null ? Math.round(readiness.readiness_score * 100) : 0;
    const filteredCourses = useMemo(() => {
        return courses.filter((course) => {
            const matchesSearch = course.title.toLowerCase().includes(search.toLowerCase());
            const matchesModality = modalityFilter === 'all' || course.modality === (modalityFilter === 'formal' ? 'formal' : 'non_formal');
            return matchesSearch && matchesModality;
        });
    }, [courses, search, modalityFilter]);

    const downloadSnapshot = () => {
        const payload = JSON.stringify({ metrics, readiness, courses }, null, 2);
        const blob = new Blob([payload], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'ccf-academy-report.json';
        link.click();
        URL.revokeObjectURL(url);
        toast.success('Reporte descargado');
    };

    if (loading) {
        return (
            <WorkspaceLayout sidebarTitle="Academia">
                <div className="p-4 space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-lg" />)}
                    </div>
                    <Skeleton className="h-[400px] rounded-lg" />
                </div>
            </WorkspaceLayout>
        );
    }

    return (
        <WorkspaceLayout 
            sidebarTitle="Academia"
            allowedRoles={['admin', 'coordinador', 'staff']}
        >
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0f1114]">
                <WorkspaceToolbar
                    breadcrumbs={[
                        { label: 'Academia', icon: GraduationCap },
                        { label: 'Coordinación', icon: ShieldCheck },
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={['grid', 'table', 'list', 'wiki']}
                    rightActions={
                        <div className="flex items-center gap-3">
                            <button 
                                onClick={() => router.push('/plataforma/academy/coordination/courses/new')}
                                className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
                            >
                                <Plus size={14} /> Nuevo Programa
                            </button>
                            <div className="h-4 w-px bg-slate-200 dark:bg-white/10 mx-1" />
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                Alistamiento: {readinessPerc}%
                            </span>
                        </div>
                    }
                />

                <main className="flex-1 overflow-y-auto p-4 p-4 space-y-3">
                    {metrics && viewType === 'grid' && (
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <DSMetric label="Cursos totales" value={String(metrics.total_courses ?? 0)} trend="+4 cohortes" tone="blue" />
                            <DSMetric label="Inscripciones" value={String(metrics.total_enrollments ?? 0)} trend="Semana actual" tone="emerald" />
                            <DSMetric label="Formales aprobados" value={String(metrics.approved_formal_enrollments ?? 0)} trend="Actas activas" tone="amber" />
                        </section>
                    )}

                    {readiness && viewType === 'grid' && (
                        <section className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-4 shadow-[var(--shadow-floating)]">
                            <header className="flex items-center justify-between mb-3">
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-500 mb-2">Checklist de alistamiento</p>
                                    <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Piloto Academia Faro</h2>
                                </div>
                                <div className="text-right">
                                    <div className="size-8 rounded-full border-4 border-blue-500/20 flex items-center justify-center relative">
                                        <svg className="absolute inset-0 rotate-[-90deg]">
                                            <circle cx="40" cy="40" r="36" fill="transparent" stroke="currentColor" strokeWidth="4" className="text-blue-500" strokeDasharray={226} strokeDashoffset={226 - (226 * readinessPerc / 100)} />
                                        </svg>
                                        <span className="text-xl font-bold text-blue-600">{readinessPerc}%</span>
                                    </div>
                                </div>
                            </header>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {readiness.checklist.map((item) => (
                                    <article key={item.key} className={clsx(
                                        'rounded-lg border p-3 flex items-center gap-4 transition-all group hover:scale-[1.01]',
                                        item.completed 
                                            ? 'border-emerald-100 dark:border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-500/5' 
                                            : 'border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02]'
                                    )}>
                                        <div className={clsx(
                                            'size-10 rounded-md flex items-center justify-center transition-transform group-hover:rotate-12',
                                            item.completed ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' : 'bg-slate-200 dark:bg-white/10 text-slate-500'
                                        )}>
                                            {item.completed ? <ShieldCheck size={20} /> : <AlertTriangle size={20} />}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{item.label}</p>
                                            <p className={clsx("text-[10px] font-bold uppercase tracking-wide mt-1", item.completed ? 'text-emerald-600' : 'text-slate-400')}>
                                                {item.completed ? 'Verificado por IA' : 'Acción Requerida'}
                                            </p>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </section>
                    )}

                    {viewType === 'wiki' && (
                        <section className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-4 shadow-[var(--shadow-floating)] space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">Manual Operativo de Coordinación</h3>
                                <DSBadge tone="blue" label="Autosave activo" />
                            </div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta políticas de cohortes, apertura/cierre de cursos, certificación y actas..."
                                className="w-full min-h-[400px] bg-slate-50/50 dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/5 p-3 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-4 focus:ring-blue-500/5 transition-all"
                            />
                        </section>
                    )}

                    {(viewType === 'grid' || viewType === 'table' || viewType === 'list') && (
                        <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
                            <header className="p-4 border-b border-slate-100 dark:border-white/5 space-y-3">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div>
                                        <DSBadge tone="blue" label="Gestión de Cohortes" />
                                        <h3 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight mt-2">Programas Académicos</h3>
                                    </div>
                                    <button 
                                        onClick={downloadSnapshot}
                                        className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide px-3 py-2.5 rounded-md border-2 border-slate-100 dark:border-white/5 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-all active:scale-95"
                                    >
                                        <Download size={14} /> Exportar Auditoría
                                    </button>
                                </div>
                                
                                <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                                    <div className="flex-1 relative group">
                                        <Filter size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-blue-500" />
                                        <input
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            placeholder="Filtrar por nombre del curso o cohorte..."
                                            className="w-full bg-slate-50 dark:bg-white/5 border-2 border-transparent focus:border-blue-500/20 rounded-lg py-3 pl-12 pr-4 text-sm font-bold outline-none transition-all shadow-inner"
                                        />
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex bg-slate-100 dark:bg-white/5 p-1 rounded-lg border border-slate-200 dark:border-white/10">
                                            {(['all', 'formal', 'non_formal'] as const).map((m) => (
                                                <button
                                                    key={m}
                                                    onClick={() => setModalityFilter(m)}
                                                    className={clsx(
                                                        "px-4 py-2 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all",
                                                        modalityFilter === m 
                                                            ? "bg-white dark:bg-white/10 text-blue-600 shadow-lg shadow-blue-500/5" 
                                                            : "text-slate-400 hover:text-slate-600"
                                                    )}
                                                >
                                                    {m === 'all' ? 'Todos' : m === 'formal' ? 'Formal' : 'No Formal'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </header>

                            {filteredCourses.length > 0 ? (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead className="bg-slate-50/50 dark:bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                            <tr>
                                                <th className="px-4 py-1.5">Curso / Programa</th>
                                                <th className="px-4 py-1.5">Cohorte Activa</th>
                                                <th className="px-4 py-1.5">Modalidad</th>
                                                <th className="px-4 py-1.5">Certificado</th>
                                                <th className="px-4 py-1.5 text-right">Control</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                            {filteredCourses.map((course) => (
                                                <tr key={course.id} className="group hover:bg-slate-50 dark:hover:bg-white/[0.01] transition-colors">
                                                    <td className="px-4 py-2">
                                                        <div 
                                                            className="font-bold text-slate-900 dark:text-white cursor-pointer group-hover:text-blue-600 transition-colors"
                                                            onClick={() => router.push(`/academy/courses/${course.id}`)}
                                                        >
                                                            {course.title}
                                                        </div>
                                                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mt-1">ID: {course.id}</div>
                                                    </td>
                                                    <td className="px-4 py-2">
                                                        <span className="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-full font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide">
                                                            {course.cohort_name || 'Sin cohorte'}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-2">
                                                        <DSBadge 
                                                            tone={course.modality === 'formal' ? 'amber' : 'emerald'} 
                                                            label={course.modality === 'formal' ? 'ACADÉMICO' : 'LIBRE'} 
                                                        />
                                                    </td>
                                                    <td className="px-4 py-2">
                                                        <div className="flex items-center gap-2">
                                                            <div className={clsx("size-2 rounded-full", course.certificate_type ? 'bg-emerald-500' : 'bg-amber-500')} />
                                                            <span className="text-xs font-bold text-slate-500">{course.certificate_type || 'Por definir'}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-2 text-right">
                                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-all">
                                                            <button
                                                                onClick={() => router.push(`/academy/courses/${course.id}/lessons`)}
                                                                className="px-4 py-2 rounded-md text-[9px] font-semibold uppercase tracking-wide bg-blue-600 text-white shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
                                                            >
                                                                Lecciones
                                                            </button>
                                                            <button
                                                                onClick={() => router.push(`/academy/courses/${course.id}/edit`)}
                                                                className="px-4 py-2 rounded-md text-[9px] font-semibold uppercase tracking-wide border-2 border-slate-100 dark:border-white/5 text-slate-500 hover:bg-white dark:hover:bg-white/10 transition-all active:scale-95"
                                                            >
                                                                Config
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <div className="py-1.5">
                                    <EmptyState 
                                        icon={GraduationCap}
                                        title="No se encontraron programas"
                                        description="Ajusta los filtros o crea un nuevo programa académico para comenzar."
                                        onAction={() => router.push('/plataforma/academy/coordination/courses/new')}
                                        actionLabel="Nuevo Programa"
                                    />
                                </div>
                            )}
                        </DSCard>
                    )}
                </main>
            </div>
        </WorkspaceLayout>
    );
}


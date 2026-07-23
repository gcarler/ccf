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
        const ctrl = new AbortController();
        const load = async () => {
            try {
                setLoading(true);
                const [metricsData, readinessData, coursesData] = await Promise.all([
                    apiFetch<DashboardMetrics>(`/academy/dashboard/metrics`, { token, cache: 'no-store', signal: ctrl.signal }),
                    apiFetch<PilotReadiness>(`/academy/dashboard/pilot-readiness`, { token, cache: 'no-store', signal: ctrl.signal }),
                    apiFetch<CourseSummary[]>(`/academy/courses/?modality=formal&published_only=false`, { token, cache: 'no-store', signal: ctrl.signal }),
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
        return () => ctrl.abort();
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
            allowedPermissions={['academy:manage']}
        >
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))]">
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
                                className="inline-flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
                            >
                                <Plus size={14} /> Nuevo Programa
                            </button>
                            <div className="h-4 w-px bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                Alistamiento: {readinessPerc}%
                            </span>
                        </div>
                    }
                />

                <main className="flex-1 overflow-y-auto p-4 space-y-3">
                    {metrics && viewType === 'grid' && (
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <DSMetric label="Cursos totales" value={String(metrics.total_courses ?? 0)} trend="+4 cohortes" tone="blue" />
                            <DSMetric label="Inscripciones" value={String(metrics.total_enrollments ?? 0)} trend="Semana actual" tone="emerald" />
                            <DSMetric label="Formales aprobados" value={String(metrics.approved_formal_enrollments ?? 0)} trend="Actas activas" tone="amber" />
                        </section>
                    )}

                    {readiness && viewType === 'grid' && (
                        <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 shadow-[var(--shadow-floating)]">
                            <header className="flex items-center justify-between mb-3">
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mb-2">Checklist de alistamiento</p>
                                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Piloto Academia CCF</h2>
                                </div>
                                <div className="text-right">
                                    <div className="size-8 rounded-full border-4 border-blue-500/20 flex items-center justify-center relative">
                                        <svg className="absolute inset-0 rotate-[-90deg]">
                                            <circle cx="40" cy="40" r="36" fill="transparent" stroke="currentColor" strokeWidth="4" className="text-[hsl(var(--primary))]" strokeDasharray={226} strokeDashoffset={226 - (226 * readinessPerc / 100)} />
                                        </svg>
                                        <span className="text-xl font-bold text-[hsl(var(--primary))]">{readinessPerc}%</span>
                                    </div>
                                </div>
                            </header>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {readiness.checklist.map((item) => (
                                    <article key={item.key} className={clsx(
                                        'rounded-lg border p-3 flex items-center gap-4 transition-all group hover:scale-[1.01]',
                                        item.completed 
                                            ? 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))]' 
                                            : 'border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]'
                                    )}>
                                        <div className={clsx(
                                            'size-10 rounded-md flex items-center justify-center transition-transform group-hover:rotate-12',
                                            item.completed ? 'bg-[hsl(var(--success))] text-white shadow-lg shadow-[hsl(var(--success))/0.2]' : 'bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))]'
                                        )}>
                                            {item.completed ? <ShieldCheck size={20} /> : <AlertTriangle size={20} />}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{item.label}</p>
                                            <p className={clsx("text-[10px] font-bold uppercase tracking-wide mt-1", item.completed ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--text-secondary))]')}>
                                                {item.completed ? 'Verificado por IA' : 'Acción Requerida'}
                                            </p>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </section>
                    )}

                    {viewType === 'wiki' && (
                        <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 shadow-[var(--shadow-floating)] space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Manual Operativo de Coordinación</h3>
                                <DSBadge tone="blue" label="Autosave activo" />
                            </div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta políticas de cohortes, apertura/cierre de cursos, certificación y actas..."
                                className="w-full min-h-[400px] bg-[hsl(var(--surface-1))]/50 dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/5 transition-all"
                            />
                        </section>
                    )}

                    {(viewType === 'grid' || viewType === 'table' || viewType === 'list') && (
                        <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
                            <header className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 space-y-3">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div>
                                        <DSBadge tone="blue" label="Gestión de Cohortes" />
                                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight mt-2">Programas Académicos</h3>
                                    </div>
                                    <button 
                                        onClick={downloadSnapshot}
                                        className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide px-3 py-2.5 rounded-md border-2 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all active:scale-95"
                                    >
                                        <Download size={14} /> Exportar Auditoría
                                    </button>
                                </div>
                                
                                <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                                    <div className="flex-1 relative group">
                                        <Filter size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] transition-colors group-focus-within:text-[hsl(var(--primary))]" />
                                        <input
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            placeholder="Filtrar por nombre del curso o cohorte..."
                                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border-2 border-transparent focus:border-blue-500/20 rounded-lg py-3 pl-12 pr-4 text-sm font-bold outline-none transition-all shadow-inner"
                                        />
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10">
                                            {(['all', 'formal', 'non_formal'] as const).map((m) => (
                                                <button
                                                    key={m}
                                                    onClick={() => setModalityFilter(m)}
                                                    className={clsx(
                                                        "px-4 py-2 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all",
                                                        modalityFilter === m 
                                                            ? "bg-[hsl(var(--bg-primary))] dark:bg-white/10 text-[hsl(var(--primary))] shadow-lg shadow-blue-500/5" 
                                                            : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]"
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
                                        <thead className="bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                            <tr>
                                                <th className="px-4 py-1.5">Curso / Programa</th>
                                                <th className="px-4 py-1.5">Cohorte Activa</th>
                                                <th className="px-4 py-1.5">Modalidad</th>
                                                <th className="px-4 py-1.5">Certificado</th>
                                                <th className="px-4 py-1.5 text-right">Control</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                            {filteredCourses.map((course) => (
                                                <tr key={course.id} className="group hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.01] transition-colors">
                                                    <td className="px-4 py-2">
                                                        <div 
                                                            className="font-bold text-[hsl(var(--text-primary))] dark:text-white cursor-pointer group-hover:text-[hsl(var(--primary))] transition-colors"
                                                            onClick={() => router.push(`/plataforma/academy/courses/${course.id}`)}
                                                        >
                                                            {course.title}
                                                        </div>
                                                        <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">ID: {course.id}</div>
                                                    </td>
                                                    <td className="px-4 py-2">
                                                        <span className="px-3 py-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-wide">
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
                                                            <div className={clsx("size-2 rounded-full", course.certificate_type ? 'bg-[hsl(var(--success))]' : 'bg-[hsl(var(--warning))]')} />
                                                            <span className="text-xs font-bold text-[hsl(var(--text-secondary))]">{course.certificate_type || 'Por definir'}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-2 text-right">
                                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-all">
                                                            <button
                                                                onClick={() => router.push(`/plataforma/academy/courses/${course.id}/lessons`)}
                                                                className="px-4 py-2 rounded-md text-[9px] font-semibold uppercase tracking-wide bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all"
                                                            >
                                                                Lecciones
                                                            </button>
                                                            <button
                                                                onClick={() => router.push(`/plataforma/academy/courses/${course.id}/edit`)}
                                                                className="px-4 py-2 rounded-md text-[9px] font-semibold uppercase tracking-wide border-2 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10 transition-all active:scale-95"
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

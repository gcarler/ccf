"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import type { CourseSummary, DashboardMetrics, PilotReadiness } from '@/types/academy';
import { GraduationCap, Target, AlertTriangle, BarChart3, Loader2, Users, ShieldCheck, Download, Filter } from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

export default function CoordinationConsole() {
    const { token, user, isAuthenticated } = useAuth();
    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [readiness, setReadiness] = useState<PilotReadiness | null>(null);
    const [courses, setCourses] = useState<CourseSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [modalityFilter, setModalityFilter] = useState<'all' | 'formal' | 'non_formal'>('all');

    const isCoordination = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'staff'].includes(role);
    }, [user?.role]);

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

    const readinessPerc = readiness ? Math.round(readiness.readiness_score * 100) : 0;
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

    return (
        <div className="flex flex-col h-full bg-[#f5f7fb] dark:bg-[#0f1114] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Coordinación', icon: ShieldCheck },
                ]}
                viewType="grid"
                setViewType={() => {}}
                rightActions={
                    <span className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-500">
                        Estado general: {readinessPerc}%
                    </span>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                {!isCoordination && (
                    <div className="border border-rose-300 bg-rose-100 text-rose-800 rounded-3xl px-6 py-4 text-sm font-semibold">
                        Esta consola está restringida al equipo académico. Tus permisos actuales son "{user?.role || 'estudiante'}".
                    </div>
                )}

                {loading && (
                    <div className="flex items-center gap-3 text-slate-500 text-sm"><Loader2 className="animate-spin" /> Preparando tableros ejecutivos...</div>
                )}

                {metrics && (
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <CoordStat icon={Users} label="Cursos totales" value={metrics.total_courses} tone="blue" />
                        <CoordStat icon={BarChart3} label="Inscripciones" value={metrics.total_enrollments} tone="emerald" />
                        <CoordStat icon={Target} label="Formal aprobados" value={metrics.approved_formal_enrollments} tone="amber" />
                    </section>
                )}

                {readiness && (
                    <section className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl p-6">
                        <header className="flex items-center justify-between mb-6">
                            <div>
                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Checklist de alistamiento</p>
                                <h2 className="text-2xl font-black text-slate-900 dark:text-white">Piloto Academia Faro</h2>
                            </div>
                            <div className="text-right">
                                <p className="text-sm text-slate-500 font-semibold">Readiness</p>
                                <p className="text-4xl font-black text-blue-600">{readinessPerc}%</p>
                            </div>
                        </header>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {readiness.checklist.map((item) => (
                                <article key={item.key} className={clsx('rounded-2xl border p-4 flex items-center gap-4', item.completed ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50')}>
                                    <div className={clsx('size-10 rounded-xl flex items-center justify-center', item.completed ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600')}>
                                        {item.completed ? '✓' : '!'}
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-slate-900 dark:text-white">{item.label}</p>
                                        <p className="text-[11px] font-black uppercase tracking-widest text-slate-400">{item.completed ? 'Completado' : 'Pendiente'}</p>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                )}

                {readiness && readiness.checklist.some((item) => !item.completed) && (
                    <section className="rounded-[2rem] border border-amber-200 bg-amber-50/70 p-6 text-amber-800 flex items-center gap-4">
                        <AlertTriangle size={32} />
                        <div>
                            <p className="text-sm font-semibold">Pendientes críticos</p>
                            <p className="text-xs uppercase tracking-[0.3em] font-black">{readiness.checklist.filter((item) => !item.completed).length} ítems requieren acción</p>
                        </div>
                    </section>
                )}

                {courses.length > 0 && (
                    <section className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl">
                        <header className="px-6 py-5 border-b border-slate-100 dark:border-white/5 space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Cohortes formales</p>
                                    <h3 className="text-xl font-black text-slate-900 dark:text-white">Seguimiento de actas y certificados</h3>
                                </div>
                                <button onClick={downloadSnapshot} className="inline-flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.3em] px-3 py-2 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5">
                                    <Download size={14} /> Reporte
                                </button>
                            </div>
                            <div className="flex flex-col lg:flex-row lg:items-center lg:gap-4 gap-3">
                                <div className="flex items-center gap-2 flex-1">
                                    <div className="rounded-2xl bg-slate-100 dark:bg-white/5 px-3 py-2 flex items-center gap-2 flex-1">
                                        <Filter size={16} className="text-slate-400" />
                                        <input
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            placeholder="Buscar curso"
                                            className="bg-transparent flex-1 text-sm outline-none"
                                        />
                                    </div>
                                    <select
                                        value={modalityFilter}
                                        onChange={(e) => setModalityFilter(e.target.value as 'all' | 'formal' | 'non_formal')}
                                        className="rounded-2xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                                    >
                                        <option value="all">Todas las modalidades</option>
                                        <option value="formal">Formal</option>
                                        <option value="non_formal">No formal</option>
                                    </select>
                                </div>
                                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">{filteredCourses.length} resultados</span>
                            </div>
                        </header>
                        <div className="overflow-x-auto hide-scrollbar">
                            <table className="min-w-full text-sm">
                                <thead className="text-left text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                                    <tr>
                                        <th className="px-6 py-4">Curso</th>
                                        <th className="px-6 py-4">Cohorte</th>
                                        <th className="px-6 py-4">Modalidad</th>
                                        <th className="px-6 py-4">Certificado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredCourses.map((course) => (
                                        <tr key={course.id} className="border-t border-slate-100 dark:border-white/5">
                                            <td className="px-6 py-4 font-semibold text-slate-900 dark:text-white">{course.title}</td>
                                            <td className="px-6 py-4 text-slate-500">{course.cohort_name || 'Sin asignar'}</td>
                                            <td className="px-6 py-4">{course.modality === 'formal' ? 'Formal' : 'No formal'}</td>
                                            <td className="px-6 py-4 text-slate-500">{course.certificate_type || 'Pendiente'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}

function CoordStat({ icon: Icon, label, value, tone }: { icon: any; label: string; value: number | string; tone: 'blue' | 'emerald' | 'amber' }) {
    const styles = {
        blue: 'bg-blue-500/10 text-blue-600 border-blue-500/30',
        emerald: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30',
        amber: 'bg-amber-500/10 text-amber-600 border-amber-500/30',
    };
    return (
        <div className="rounded-[2.5rem] bg-white dark:bg-[#111418] border border-slate-200 dark:border-white/5 shadow-sm p-6 flex items-center gap-4">
            <div className={clsx('size-12 rounded-2xl flex items-center justify-center border', styles[tone])}>
                <Icon size={22} />
            </div>
            <div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 mb-1">{label}</p>
                <p className="text-2xl font-black text-slate-900 dark:text-white">{value}</p>
            </div>
        </div>
    );
}

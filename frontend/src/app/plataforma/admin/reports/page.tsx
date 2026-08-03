"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import {
    TrendingUp,
    PieChart,
    DollarSign,
    ArrowUpRight,
    Download,
    Bell,
    Users,
    GraduationCap,
    BookOpen,
    Target,
    Filter,
    Calendar,
    ChevronDown,
    Activity,
    Zap,
    BrainCircuit,
    Layers
} from 'lucide-react';
import clsx from 'clsx';

type ReportTab = 'academic' | 'financial' | 'operational';

interface CoursePerf { course_id: number | null; enrollments: number; certificates: number; approvals: number; }
type CoursePerfRow = CoursePerf;
interface WarehouseSummary { total_events?: number; by_event?: { event_name: string; count: number }[]; error?: string; }
interface AcademyMetrics {
    active_students?: number;
    completion_rate?: number;
    certificates_issued?: number;
    top_courses?: { title?: string; count?: number }[];
    formal_stats?: Record<string, unknown>;
    no_formal_stats?: Record<string, unknown>;
}

interface BiData {
    warehouse: WarehouseSummary | null;
    courses: CoursePerfRow[];
    academy: AcademyMetrics | null;
}

const EMPTY_BI: BiData = { warehouse: null, courses: [], academy: null };

function csvCell(value: string | number): string {
    const s = String(value);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function exportReportsCsv(bi: BiData, activeTab: ReportTab): void {
    const lines: string[] = [];
    const push = (row: (string | number)[]) => lines.push(row.map(csvCell).join(','));
    const stamp = new Date().toISOString().slice(0, 10);
    push(['CCF - Reporte BI', activeTab, stamp]);

    if (activeTab === 'academic') {
        push([]);
        push(['Curso', 'Inscripciones', 'Certificados', 'Aprobaciones']);
        const rows = bi.courses.length > 0
            ? bi.courses
            : [{ course_id: null, enrollments: bi.academy?.active_students ?? 0, certificates: bi.academy?.certificates_issued ?? 0, approvals: 0 }];
        rows.forEach((c) => push([String(c.course_id ?? '-'), c.enrollments, c.certificates, c.approvals]));
    } else {
        push([]);
        push(['Tipo de Evento', 'Conteo']);
        (bi.warehouse?.by_event ?? []).forEach((ev) => push([ev.event_name, ev.count]));
        push(['TOTAL', bi.warehouse?.total_events ?? 0]);
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bi-reporte-${activeTab}-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function AdvancedBIReports() {
    const { isAuthenticated, token } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<ReportTab>('academic');
    const [bi, setBi] = useState<BiData>(EMPTY_BI);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const controller = new AbortController();
        const fetchAnalytics = async () => {
            if (!token) return;
            setLoading(true);
            try {
                const [warehouse, courses, academy] = await Promise.allSettled([
                    apiFetch<WarehouseSummary>('/analytics/events/summary/warehouse', { token, signal: controller.signal }),
                    apiFetch<{ courses: CoursePerfRow[] }>('/analytics/academy/performance', { token, signal: controller.signal }),
                    apiFetch<AcademyMetrics>('/analytics/dashboard-metrics', { token, signal: controller.signal }),
                ]);
                setBi({
                    warehouse: warehouse.status === 'fulfilled' ? warehouse.value : null,
                    courses: courses.status === 'fulfilled' ? (courses.value?.courses ?? []) : [],
                    academy: academy.status === 'fulfilled' ? academy.value : null,
                });
            } catch (e) {
                console.error('BI Analytics fetch failed', e);
            } finally {
                setLoading(false);
            }
        };
        fetchAnalytics();
        return () => controller.abort();
    }, [token]);

    const academyCompletion = bi.academy?.completion_rate ?? 0;
    const formalCompletion = typeof bi.academy?.formal_stats?.completion_rate === 'number' ? bi.academy.formal_stats.completion_rate : (bi.academy?.completion_rate ?? 0);
    const noFormalCompletion = typeof bi.academy?.no_formal_stats?.completion_rate === 'number' ? bi.academy.no_formal_stats.completion_rate : 0;
    const activeStudents = bi.academy?.active_students ?? 0;
    const certificates = bi.academy?.certificates_issued ?? 0;
    const totalEvents = bi.warehouse?.total_events ?? 0;
    const topCourses = bi.academy?.top_courses ?? [];
    const courseBars = topCourses.length > 0
        ? topCourses.slice(0, 12)
        : [...Array(12)].map(() => ({ title: '', count: 0 }));
    const maxCourse = Math.max(1, ...courseBars.map(c => c.count ?? 0));

    if (!isAuthenticated) return null;

    const tabs = [
        { id: 'academic', label: 'Académico', icon: GraduationCap },
        { id: 'financial', label: 'Financiero', icon: DollarSign },
        { id: 'operational', label: 'Operativo', icon: Activity },
    ];

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Gestión Central', icon: Bell },
                { label: 'Inteligencia de Negocios', icon: BrainCircuit }
            ]}
        >
            <AdminHero
                eyebrow="Business Intelligence"
                title="Centro de Análisis Avanzado"
                description="Visualiza el impacto real de la plataforma a través de métricas cruzadas. Optimus BI analiza tendencias de retención, ingresos y efectividad académica."
                tags={['BI Core', 'Machine Learning', 'Real-time']}
                watchers={['Dirección General', 'Comité Académico']}
                primaryAction={{ label: 'Exportar Reporte Full', icon: Download, onClick: () => window.print() }}
                secondaryAction={{ label: 'Configurar Alertas', icon: Zap, onClick: () => router.push('/plataforma/admin/settings/system') }}
            />

            {/* Sub-navigation Tabs */}
            <div className="flex flex-wrap items-center gap-4 mb-3 bg-[hsl(var(--surface-2))]/50 dark:bg-white/5 p-2 rounded-lg w-fit border border-[hsl(var(--border))] dark:border-white/10">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as ReportTab)}
                        className={clsx(
                            "flex items-center gap-3 px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide transition-all active:scale-95",
                            activeTab === tab.id
                                ? "bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--primary))] text-[hsl(var(--primary))] dark:text-white shadow-xl shadow-[hsl(var(--info)/10%)]"
                                : "text-[hsl(var(--text-secondary))] hover:bg-white/50 dark:hover:bg-white/5"
                        )}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                {/* Main Insight Card */}
                <div className="lg:col-span-8 space-y-3">
                    <section className="relative overflow-hidden rounded-lg bg-[hsl(var(--bg-muted))] border border-white/5 p-4 text-white shadow-2xl group min-h-[400px] flex flex-col justify-between">
                        <div className="absolute top-0 right-0 -mr-24 -mt-24 size-96 bg-[hsl(var(--info))]/20 rounded-full blur-[100px] group-hover:bg-[hsl(var(--info))]/30 transition-all duration-1000" />

                        <div className="relative z-10 flex justify-between items-start">
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="px-3 py-1 bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] border border-[hsl(var(--info)/100%)]/30 rounded-full text-2xs font-semibold uppercase tracking-wide flex items-center gap-2">
                                        <Layers size={12} /> Perspectiva de {activeTab}
                                    </div>
                                    <span className="text-[hsl(var(--text-secondary))] text-2xs font-bold uppercase tracking-wide">Actulizado hace 2 min</span>
                                </div>
                                <h3 className="text-lg font-bold tracking-tighter leading-none mb-2">Indicador de Eficacia</h3>
                                <p className="text-[hsl(var(--text-secondary))] text-sm font-medium max-w-md">Análisis predictivo basado en el comportamiento del último trimestre.</p>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                                <span className="text-xl font-bold text-white tracking-tighter">
                                    {loading ? '—' : `${(academyCompletion * 100).toFixed(1)}%`}
                                </span>
                                <div className="flex items-center gap-1.5 text-[hsl(var(--success))] text-2xs font-semibold uppercase tracking-wide">
                                    <TrendingUp size={14} /> Tasa de finalización
                                </div>
                            </div>
                        </div>

                        {/* Custom Chart Illustration — real top courses */}
                        <div className="relative z-10 h-48 flex items-end gap-4 mt-3">
                            {courseBars.map((c, i) => {
                                const h = c.count ? Math.max(8, Math.round((c.count / maxCourse) * 100)) : 0;
                                return (
                                    <div key={i} className="flex-1 flex flex-col items-center gap-3 group/bar">
                                        <div
                                            style={{ height: `${h}%` }}
                                            className={clsx(
                                                "w-full rounded-t-2xl transition-all duration-700 relative",
                                                i === courseBars.length - 1 ? "bg-[hsl(var(--primary))] shadow-[0_0_30px_rgba(59,130,246,0.5)]" : "bg-white/10 opacity-30 group-hover/bar:opacity-60"
                                            )}
                                        >
                                            {c.count ? <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] px-3 py-1.5 rounded-lg font-semibold shadow-xl whitespace-nowrap">{c.count} insc.</div> : null}
                                        </div>
                                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase text-[10px] max-w-full truncate">{c.title || '—'}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* Secondary Metrics Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 space-y-3 shadow-xl">
                            <div className="flex justify-between items-center">
                                <div className="size-7 rounded-lg bg-info-soft dark:bg-[hsl(var(--info))]/30 text-[hsl(var(--primary))] flex items-center justify-center">
                                    <Users size={24} />
                                </div>
                                <button className="p-2 hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"><ChevronDown size={18} /></button>
                            </div>
                            <div>
                                <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Estudiantes Activos</p>
                                <h4 className="text-lg font-bold tracking-tight">{loading ? '—' : activeStudents} activos</h4>
                            </div>
                            <div className="space-y-3">
                                <div className="flex justify-between text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <span>Formal</span>
                                    <span>{loading ? '—' : `${Math.round(formalCompletion * 100)}%`} compl.</span>
                                </div>
                                <div className="h-2 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-[hsl(var(--primary))] w-[92%]" />
                                </div>
                                <div className="flex justify-between text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <span>No Formal</span>
                                    <span>{loading ? '—' : `${Math.round(noFormalCompletion * 100)}%`} compl.</span>
                                </div>
                                <div className="h-2 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-[hsl(var(--surface-2))] w-[64%]" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 space-y-3 shadow-xl">
                            <div className="flex justify-between items-center">
                                <div className="size-7 rounded-lg bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] flex items-center justify-center">
                                    <Target size={24} />
                                </div>
                                <button className="p-2 hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"><Filter size={18} /></button>
                            </div>
                            <div>
                                <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Certificados Emitidos</p>
                                <h4 className="text-lg font-bold tracking-tight">{loading ? '—' : certificates} emitidos</h4>
                            </div>
                            <div className="p-4 bg-[hsl(var(--success-muted))] rounded-lg border border-[hsl(var(--success)/0.3)]">
                                <p className="text-2xs font-bold text-[hsl(var(--success))] leading-relaxed uppercase tracking-wider">
                                    Optimus AI: &quot;Reducción del 15% en costos operativos mediante automatización de actas.&quot;
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Sidebar BI Tools */}
                <aside className="lg:col-span-4 space-y-3">
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 shadow-2xl space-y-3">
                        <div className="flex items-center gap-3">
                            <BrainCircuit size={20} className="text-[hsl(var(--primary))]" />
                            <h4 className="text-lg font-semibold uppercase tracking-wide tracking-tighter">Acciones BI</h4>
                        </div>

                        <div className="space-y-4">
                            <button className="w-full flex items-center justify-between p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-transparent hover:border-[hsl(var(--info)/100%)]/30 transition-all group">
                                <div className="flex items-center gap-4 text-left">
                                    <div className="size-10 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] shadow-sm group-hover:scale-110 transition-transform">
                                        <Calendar size={18} />
                                    </div>
                                    <div>
                                        <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">Ventana de Eventos</p>
                                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))]">Últimos 7 días · {totalEvents} eventos</p>
                                    </div>
                                </div>
                                <ArrowUpRight size={16} className="text-[hsl(var(--text-secondary))]" />
                            </button>

                            <button className="w-full flex items-center justify-between p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-transparent hover:border-[hsl(var(--info)/100%)]/30 transition-all group">
                                <div className="flex items-center gap-4 text-left">
                                    <div className="size-10 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] shadow-sm group-hover:scale-110 transition-transform">
                                        <BookOpen size={18} />
                                    </div>
                                    <div>
                                        <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">Segmento</p>
                                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))]">Modalidad Formal</p>
                                    </div>
                                </div>
                                <ArrowUpRight size={16} className="text-[hsl(var(--text-secondary))]" />
                            </button>
                        </div>

                        <div className="pt-8 border-t border-[hsl(var(--border))] dark:border-white/5">
                            <div className="flex items-center justify-between mb-3">
                                <h5 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Eventos por tipo</h5>
                                <PieChart size={14} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            <div className="relative size-10 mx-auto mb-3">
                                <svg className="size-full -rotate-90 drop-shadow-2xl" viewBox="0 0 36 36">
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="rgba(59,130,246,0.1)" strokeWidth="4" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="hsl(var(--info))" strokeWidth="4" strokeDasharray="65 100" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="hsl(var(--text-primary))" strokeWidth="4" strokeDasharray="35 100" strokeDashoffset="-65" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">{loading ? '—' : totalEvents}</span>
                                    <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Eventos</span>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {(bi.warehouse?.by_event ?? []).slice(0, 4).map((ev) => {
                                    const pct = totalEvents > 0 ? Math.round((ev.count / totalEvents) * 100) : 0;
                                    return (
                                        <div key={ev.event_name} className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <div className="size-2 rounded-full bg-[hsl(var(--primary))]" />
                                                <span className="text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-[10rem] truncate">{ev.event_name}</span>
                                            </div>
                                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">{pct}%</span>
                                        </div>
                                    );
                                })}
                                {!loading && (bi.warehouse?.by_event?.length ?? 0) === 0 && (
                                    <p className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">Sin eventos registrados en el warehouse.</p>
                                )}
                            </div>
                        </div>

                        <button
                            onClick={() => exportReportsCsv(bi, activeTab)}
                            className="w-full py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] active:scale-95 transition-all"
                        >
                            Exportar Reporte CSV
                        </button>
                    </div>
                </aside>
            </div>
        </AdminShell>
    );
}

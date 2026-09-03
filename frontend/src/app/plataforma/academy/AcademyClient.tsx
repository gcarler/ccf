"use client";

import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import EmptyState from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design';
import { DSChart } from '@/design';

import { apiFetch } from '@/lib/http';
import { GraduationCap, TrendingUp, AlertTriangle, Sparkles, BookOpen, CheckCircle2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import type { DashboardMetrics } from '@/types/academy';

type DashboardCard = NonNullable<DashboardMetrics['cards']>[number] & { color?: 'blue' | 'emerald' | 'amber' };
type AcademyDashboard = Omit<DashboardMetrics, 'cards'> & { cards: DashboardCard[] };

interface AvailableCourse {
    id: string;
    slug?: string;
    title: string;
    description?: string;
    duration_hours?: number;
    modality?: string;
    lessons?: unknown[];
}

function dashboardFromProfile(profile: { enrollments_count: number; certificates_count: number; total_progress: number }): AcademyDashboard {
    return {
        total_courses: profile.enrollments_count,
        formal_courses: 0,
        non_formal_courses: 0,
        total_enrollments: profile.enrollments_count,
        completed_enrollments: 0,
        approved_formal_enrollments: 0,
        approved_non_formal_enrollments: 0,
        cards: [
            { title: 'Mis cursos', value: String(profile.enrollments_count), trend: '', tone: 'blue', color: 'blue' },
            { title: 'Mi progreso', value: `${Math.round(profile.total_progress)}%`, trend: '', tone: 'emerald', color: 'emerald' },
            { title: 'Certificados', value: String(profile.certificates_count), trend: '', tone: 'amber', color: 'amber' },
        ],
        enrollment_trends: [],
        top_courses: [],
    };
}

export default function AcademyClient() {
    const { token, user, hasModuleAccess } = useAuth();
    const router = useRouter();
    const [dashboard, setDashboard] = useState<AcademyDashboard | null>(null);
    const [availableCourses, setAvailableCourses] = useState<AvailableCourse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [enrollingId, setEnrollingId] = useState<string | null>(null);

    const loadData = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const fetchOpts = { token, cache: 'no-store' as RequestCache, signal };
            let data: AcademyDashboard;
            if (hasModuleAccess('academy', 'manage')) {
                data = await apiFetch<AcademyDashboard>('/academy/dashboard/metrics', fetchOpts);
                setDashboard({ ...data, cards: data.cards ?? [] });
            } else {
                const profile = await apiFetch<{ enrollments_count: number; certificates_count: number; total_progress: number }>('/academy/me/profile', fetchOpts);
                setDashboard(dashboardFromProfile(profile as { enrollments_count: number; certificates_count: number; total_progress: number }));

                // Si es estudiante, cargar catálogo de cursos disponibles
                try {
                    const courses = await apiFetch<AvailableCourse[]>('/academy/courses', fetchOpts);
                    setAvailableCourses(Array.isArray(courses) ? courses : []);
                } catch {
                    // ignore courses fetch errors
                }
            }
        } catch (err: unknown) {
            // AbortError es esperado al desmontar; no se muestra al usuario.
            if (err instanceof DOMException && err.name === 'AbortError') return;
            // I-06 (cierre 2026-07-24): error extraction type-safe sin cast frágil.
            // ``err instanceof Error`` cubre ``Error`` estándar; el shape HTTP
            // ``{detail: string}`` del backend se extrae con ``in`` narrowing.
            let message = 'Error al cargar métricas de la Academia';
            if (err instanceof Error && err.message) {
                message = err.message;
            } else if (
                err && typeof err === 'object' &&
                'detail' in err &&
                typeof (err as { detail?: unknown }).detail === 'string'
            ) {
                message = (err as { detail: string }).detail;
            }
            setError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [hasModuleAccess, token]);

    useEffect(() => {
        const controller = new AbortController();
        loadData(controller.signal);
        return () => controller.abort();
    }, [loadData]);

    if (loading && !dashboard) {
        return (
            <div className="p-8 text-center text-[hsl(var(--text-secondary))] font-black animate-pulse uppercase tracking-wide">
                Cargando Dashboard Pro...
            </div>
        );
    }

    if (error && !dashboard) {
        return (
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] p-4">
                <EmptyState
                    title="No pudimos cargar el dashboard"
                    description={error}
                    icon={AlertTriangle}
                    actionLabel="Reintentar"
                    onAction={loadData}
                />
            </div>
        );
    }

    if (!dashboard) {
        return (
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] p-4">
                <EmptyState
                    title="Sin métricas disponibles"
                    description="Cuando haya cursos publicados verás aquí las estadísticas."
                    icon={TrendingUp}
                    actionLabel="Reintentar"
                    onAction={loadData}
                />
            </div>
        );
    }

    const handleEnroll = async (courseId: string, courseTitle: string) => {
        if (!token || !user) return;
        setEnrollingId(courseId);
        try {
            await apiFetch('/academy/enrollments/', {
                method: 'POST',
                token,
                body: { persona_id: user.id, course_id: courseId },
            });
            toast.success(`¡Te has matriculado en "${courseTitle}" con éxito!`);
            router.push(`/plataforma/academy/course/${courseId}`);
        } catch {
            toast.error('Error al matricular en el curso.');
            setEnrollingId(null);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Dashboard Inteligente', icon: TrendingUp },
                ]}
                rightActions={
                    <button onClick={() => router.push('/plataforma/academy/curriculum')} className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-2xs font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:scale-105 transition-all">
                        Ver Malla Curricular
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-3 space-y-5">
                {/* Onboarding para Nuevos Estudiantes / Buscadores con 0 cursos */}
                {!hasModuleAccess('academy', 'manage') && dashboard.total_courses === 0 && (
                    <section className="bg-gradient-to-br from-blue-950/40 via-blue-900/20 to-[hsl(var(--surface-1))] border border-blue-500/30 rounded-2xl p-6 shadow-xl space-y-5">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4">
                            <div className="flex items-center gap-3.5">
                                <div className="size-12 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center shadow-inner">
                                    <Sparkles size={26} />
                                </div>
                                <div>
                                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 mb-1 border border-emerald-500/30">
                                        <CheckCircle2 size={12} /> Acceso Gratuito Habilitado
                                    </div>
                                    <h2 className="text-xl font-black text-white">¡Bienvenido a tu Formación Ministerial CCF!</h2>
                                    <p className="text-xs text-blue-200/80">Selecciona el curso en el que deseas comenzar tu crecimiento hoy mismo:</p>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {availableCourses.map((course) => (
                                <div
                                    key={course.id}
                                    className="bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 hover:border-blue-500/50 rounded-xl p-4 flex flex-col justify-between transition-all hover:shadow-lg hover:scale-[1.01] group"
                                >
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="text-2xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                                {course.modality || 'Gratuito'}
                                            </span>
                                            <span className="text-2xs text-[hsl(var(--text-secondary))] font-medium flex items-center gap-1">
                                                <BookOpen size={12} /> {course.duration_hours || 8} hrs
                                            </span>
                                        </div>
                                        <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white text-base group-hover:text-blue-400 transition-colors line-clamp-1">
                                            {course.title}
                                        </h3>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 leading-relaxed">
                                            {course.description || course.title}
                                        </p>
                                    </div>

                                    <div className="pt-4 mt-2 border-t border-white/5">
                                        <button
                                            type="button"
                                            onClick={() => handleEnroll(course.id, course.title)}
                                            disabled={enrollingId === course.id}
                                            className="w-full py-2.5 px-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
                                        >
                                            {enrollingId === course.id ? 'Matriculando...' : 'Comenzar Ahora →'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Metricas Principales sin recuadros, números 3x más grandes con efecto hover gradiente */}
                <section className="grid grid-cols-2 lg:grid-cols-4 gap-6 py-3 px-1">
                    {dashboard.cards.map((card, idx) => {
                        const gradients = [
                            'group-hover:from-[hsl(var(--primary))] group-hover:via-[hsl(var(--info))] group-hover:to-[hsl(var(--accent))]',
                            'group-hover:from-emerald-400 group-hover:via-teal-300 group-hover:to-cyan-400',
                            'group-hover:from-amber-400 group-hover:via-orange-400 group-hover:to-pink-400',
                            'group-hover:from-[hsl(var(--warning))] group-hover:via-[hsl(var(--accent))] group-hover:to-[hsl(var(--danger))]'
                        ];
                        const grad = gradients[idx % gradients.length];
                        return (
                            <div key={card.title} className="group cursor-pointer select-none space-y-1">
                                <p className={`text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-[hsl(var(--text-primary))] dark:text-white ${grad} group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:text-transparent group-hover:scale-105 group-hover:drop-shadow-[0_0_18px_rgba(99,102,241,0.35)] transition-all duration-300 origin-left`}>
                                    {card.value}
                                </p>
                                <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-primary))] dark:group-hover:text-white transition-colors">
                                    {card.title}
                                </p>
                                {card.trend !== undefined && (
                                    <p className="text-2xs font-semibold text-emerald-500 flex items-center gap-1">
                                        ↑ {card.trend}% crecimiento
                                    </p>
                                )}
                            </div>
                        );
                    })}
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {/* Tendencia de Matriculas */}
                    <div className="lg:col-span-2">
                        <DSCard>
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Tendencia de Crecimiento</h3>
                                    <p className="text-xl font-bold text-white italic">Inscripciones Mensuales</p>
                                </div>
                                <div className="size-10 rounded-md bg-[hsl(var(--info))]/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                    <TrendingUp size={20} />
                                </div>
                            </div>
                            {dashboard.enrollment_trends?.length ? (
                                <DSChart type="area" data={dashboard.enrollment_trends} color="hsl(var(--info))" height={250} />
                            ) : (
                                <p className="py-12 text-center text-sm text-[hsl(var(--text-secondary))]">Aún no hay historial de inscripciones.</p>
                            )}
                        </DSCard>
                    </div>

                    {/* Top Cursos */}
                    <div className="space-y-3">
                        <DSCard>
                            <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Cursos Top Performance</h3>
                            <div className="space-y-4">
                                {dashboard.top_courses?.map((course) => (
                                    <div key={course.title} className="flex items-center justify-between group">
                                        <div className="flex items-center gap-3">
                                            <div className="size-2 rounded-full bg-[hsl(var(--primary))]" />
                                            <span className="text-xs font-bold text-[hsl(var(--text-secondary))] group-hover:text-white transition-colors">{course.title}</span>
                                        </div>
                                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{course.count} Est.</span>
                                    </div>
                                ))}
                            </div>
                            {!dashboard.top_courses?.length && <p className="text-sm text-[hsl(var(--text-secondary))]">Sin cursos con inscripciones todavía.</p>}
                        </DSCard>
                    </div>
                </div>
            </main>
        </div>
    );
}

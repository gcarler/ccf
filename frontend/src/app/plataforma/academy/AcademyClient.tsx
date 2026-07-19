"use client";

import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import EmptyState from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design/components/DSCard';
import { DSChart } from '@/design/components/DSChart';
import { DSMetric } from '@/design/components/DSMetric';
import { apiFetch } from '@/lib/http';
import {
GraduationCap,
Sparkles,
TrendingUp,
AlertTriangle,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback,useEffect,useState } from 'react';
import { toast } from 'sonner';
import type { DashboardMetrics } from '@/types/academy';

interface DashboardCard {
    title: string;
    value: string;
    trend: string;
    color: string;
}

interface AcademyDashboard extends Omit<DashboardMetrics, 'cards'> {
    cards?: DashboardCard[];
    enrollment_trends?: { label: string; value: number }[];
    top_courses?: { title: string; count: number }[];
}

export default function AcademyClient() {
    const { token } = useAuth();
    const router = useRouter();
    const [dashboard, setDashboard] = useState<AcademyDashboard | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // ACAD-CRIT-002: conectamos al endpoint del propio módulo (AcademyManager)
    // para obtener `cards`, `enrollment_trends` y `top_courses` reales.
    // Si el usuario no tiene `academy:manage` (caso 99%), cae al endpoint genérico
    // `/dashboard/academy` que sigue entregando métricas a cualquier rol con `academy:read`.
    const loadData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<any>('/academy/dashboard/metrics', { token });
            setDashboard(data);
        } catch (err: any) {
            const status = err?.status ?? err?.response?.status;
            if (status === 403 || status === 404) {
                // Fallback operativo: estudiantes no son Manager pero tienen derecho a un resumen.
                try {
                    const fallback = await apiFetch<any>('/dashboard/academy', { token });
                    setDashboard(fallback);
                    return;
                } catch (fallbackErr: any) {
                    const message =
                        fallbackErr?.detail || fallbackErr?.message ||
                        'Error al cargar métricas de la Academia';
                    setError(message);
                    toast.error(message);
                    return;
                }
            }
            const message =
                err?.detail || err?.message || 'Error al cargar métricas de la Academia';
            setError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadData();
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
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] p-4">
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
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] p-4">
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

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Dashboard Inteligente', icon: TrendingUp },
                ]}
                rightActions={
                    <button onClick={() => router.push('/plataforma/academy/curriculum')} className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                        Ver Malla Curricular
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-3 space-y-3">
                {/* Metricas Principales */}
                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {dashboard?.cards?.map((card, idx) => (
                        <DSMetric 
                            key={idx}
                            label={card.title} 
                            value={card.value} 
                            trend={card.trend} 
                            tone={card.color as 'blue' | 'emerald' | 'amber'} 
                        />
                    ))}
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {/* Tendencia de Matriculas */}
                    <div className="lg:col-span-2">
                        <DSCard>
                            <div className="flex items-center justify-between mb-3">
                                <div>
                                    <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Tendencia de Crecimiento</h3>
                                    <p className="text-xl font-bold text-white italic">Inscripciones Mensuales</p>
                                </div>
                                <div className="size-10 rounded-md bg-blue-500/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                    <TrendingUp size={20} />
                                </div>
                            </div>
                            <DSChart type="area" data={dashboard?.enrollment_trends} color="#3b82f6" height={250} />
                        </DSCard>
                    </div>

                    {/* Top Cursos */}
                    <div className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Cursos Top Performance</h3>
                            <div className="space-y-4">
                                {dashboard?.top_courses?.map((course, idx) => (
                                    <div key={idx} className="flex items-center justify-between group">
                                        <div className="flex items-center gap-3">
                                            <div className="size-2 rounded-full bg-[hsl(var(--primary))]" />
                                            <span className="text-xs font-bold text-[hsl(var(--text-secondary))] group-hover:text-white transition-colors">{course.title}</span>
                                        </div>
                                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{course.count} Est.</span>
                                    </div>
                                ))}
                            </div>
                        </DSCard>

                        {/* Optimus Coach Card */}
                        <div className="p-3 bg-gradient-to-br from-blue-600 to-sky-700 rounded-2xl text-white space-y-4 shadow-2xl shadow-blue-500/20 border border-white/10 relative overflow-hidden">
                            <div className="absolute -right-4 -top-4 size-10 bg-white/10 rounded-full blur-3xl" />
                            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide relative z-10">
                                <Sparkles size={14} className="animate-pulse" /> Optimus Intelligence
                            </div>
                            <p className="text-sm font-bold leading-relaxed opacity-95 italic relative z-10">
                                &quot;Detectamos un aumento del 15% en el compromiso tras el nuevo módulo de Teología. 5 participantes están listos para certificación.&quot;
                            </p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    GraduationCap, 
    BookOpen, 
    CheckCircle2, 
    Clock, 
    TrendingUp, 
    Plus, 
    Search,
    ChevronRight,
    Sparkles,
    Calendar,
    Settings,
    FileText,
    Users
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

export default function AcademyClient() {
    const { token, user } = useAuth();
    const router = useRouter();
    const [courses, setCourses] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [aiInsights, setAiInsights] = useState<any[]>([]);

    useEffect(() => {
        if (!token) return;
        const loadData = async () => {
            try {
                setLoading(true);
                const [coursesData, statsData, aiRes] = await Promise.all([
                    apiFetch<any[]>('/academy/courses', { token }),
                    apiFetch<any>('/academy/dashboard/metrics', { token }).catch(() => null),
                    apiFetch<any[]>('/api/agents/analytics/insights', { token }).catch(() => [])
                ]);
                setCourses(coursesData);
                setStats(statsData);
                setAiInsights((aiRes as any[] || []).filter(i => i.insight_type === 'academy_insight'));
            } catch (err) {
                toast.error('Error al cargar datos de la Academia');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [token]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Dashboard', icon: TrendingUp },
                ]}
                rightActions={
                    <button onClick={() => router.push('/academy/curriculum')} className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                        Ver Malla Curricular
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <DSMetric label="Cursos Activos" value={String(courses.length)} trend="En catálogo" tone="blue" />
                    <DSMetric label="Matrículas" value={String(stats?.total_enrollments || 0)} trend="Total histórico" tone="emerald" />
                    <DSMetric label="Completados" value={String(stats?.approved_formal_enrollments || 0)} trend="Ruta Formal" tone="amber" />
                    <DSMetric label="Certificados" value="12" trend="Emitidos" tone="violet" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Mis Cursos en Curso</h3>
                            <div className="space-y-4">
                                {courses.slice(0, 3).map(course => (
                                    <div key={course.id} className="p-4 rounded-2xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all cursor-pointer" onClick={() => router.push(`/academy/course/${course.id}`)}>
                                        <div className="flex items-center gap-4">
                                            <div className="size-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-600 font-black text-xs">
                                                {course.title.charAt(0)}
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold text-slate-800 dark:text-white">{course.title}</p>
                                                <p className="text-[10px] text-slate-400 uppercase font-black">{course.modality}</p>
                                            </div>
                                        </div>
                                        <ChevronRight size={18} className="text-slate-200 group-hover:text-blue-500 transition-all" />
                                    </div>
                                ))}
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <div className="p-6 bg-blue-600 rounded-[2.5rem] text-white space-y-4 shadow-xl shadow-blue-500/20 border border-white/10">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em]">
                                <Sparkles size={14} /> Optimus Coach
                            </div>
                            <p className="text-[11px] font-bold leading-relaxed opacity-90 italic">
                                &quot;Has completado el 60% de Teología Sistemática. ¡Sigue así! Tu próxima lección te espera.&quot;
                            </p>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    );
}

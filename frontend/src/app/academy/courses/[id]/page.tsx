"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    GraduationCap, 
    ShieldCheck, 
    BookOpen, 
    ArrowLeft,
    FileText,
    Calendar,
    ChevronRight
} from 'lucide-react';
import { DSBadge } from '@/design/components/DSBadge';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

interface CourseStats {
    total_enrolled: number;
    completion_rate: number;
    average_grade: number;
    active_sessions: number;
}

export default function CourseCoordinationPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    
    const [course, setCourse] = useState<any>(null);
    const [stats, setStats] = useState<CourseStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !isAuthenticated || !id) return;
        
        const loadData = async () => {
            try {
                setLoading(true);
                const [courseData, statsData] = await Promise.all([
                    apiFetch<any>(`/academy/courses/${id}`, { token }),
                    Promise.resolve({
                        total_enrolled: 42,
                        completion_rate: 85,
                        average_grade: 92,
                        active_sessions: 3
                    })
                ]);
                setCourse(courseData);
                setStats(statsData);
            } catch (err) {
                console.error(err);
                toast.error('No se pudo cargar la información del programa');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [id, token, isAuthenticated]);

    if (loading) return (
        <div className="flex items-center justify-center h-full p-3 text-slate-500 font-semibold uppercase tracking-wide animate-pulse">
            Sincronizando Malla Curricular...
        </div>
    );

    if (!course) return (
        <div className="flex flex-col items-center justify-center h-full p-3 text-center space-y-4">
            <h2 className="text-lg font-black text-rose-500 uppercase">Programa no encontrado</h2>
            <button onClick={() => router.back()} className="text-sm font-semibold text-blue-600 uppercase tracking-wide flex items-center gap-2">
                <ArrowLeft size={14} /> Volver a Coordinación
            </button>
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Coordinación', icon: ShieldCheck, href: '/academy/coordination' },
                    { label: course.title, icon: BookOpen },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => router.push(`/academy/courses/${id}/manage`)}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all"
                        >
                            Gestionar Cohorte
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="space-y-2">
                        <DSBadge tone={course.modality === 'formal' ? 'violet' : 'emerald'} label={course.modality === 'formal' ? 'RUTA FORMAL' : 'RUTA NO FORMAL'} />
                        <h1 className="text-lg font-black text-slate-900 dark:text-white tracking-tight leading-none uppercase">
                            {course.title}
                        </h1>
                        <p className="text-slate-500 font-bold uppercase tracking-wide text-xs flex items-center gap-2">
                            <span className="text-blue-600">{course.code}</span> • {course.cohort_name || 'Sin cohorte activa'}
                        </p>
                    </div>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <DSMetric label="Inscritos" value={String(stats?.total_enrolled ?? 0)} trend="+5 esta semana" tone="blue" />
                    <DSMetric label="Finalización" value={`${stats?.completion_rate ?? 0}%`} trend="Target 90%" tone="emerald" />
                    <DSMetric label="Promedio" value={String(stats?.average_grade ?? 0)} trend="Sobre 100" tone="amber" />
                    <DSMetric label="Lecciones" value={String(course.lessons_count ?? 0)} trend="Activas" tone="violet" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Estado de Alistamiento Académico</h3>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="size-8 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-600">
                                            <Calendar size={20} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">Periodo de Inscripción</p>
                                            <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wide">Abierto hasta 30 Mayo, 2026</p>
                                        </div>
                                    </div>
                                    <DSBadge tone="emerald" label="ACTIVO" />
                                </div>
                                
                                <div className="h-px bg-slate-100 dark:bg-white/5" />

                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="size-8 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-600">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">Malla Curricular</p>
                                            <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wide">9 de 10 lecciones con contenido</p>
                                        </div>
                                    </div>
                                    <DSBadge tone="amber" label="REVISIÓN" />
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Actas y Certificación</h3>
                            <div className="p-4 text-center bg-slate-50 dark:bg-white/5 rounded-md border border-dashed border-slate-200 dark:border-white/10">
                                <ShieldCheck size={48} className="mx-auto text-slate-300 mb-4" />
                                <h4 className="text-sm font-semibold text-slate-800 dark:text-white uppercase tracking-wide">Sin actas de cierre emitidas</h4>
                                <p className="text-[11px] text-slate-500 mt-2 font-medium">Las actas se generan automáticamente al finalizar el periodo académico del programa formal.</p>
                            </div>
                        </DSCard>
                    </div>

                    <div className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Acciones de Control</h3>
                            <div className="space-y-3">
                                <button className="w-full flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-white/5 hover:bg-blue-600 hover:text-white transition-all group text-left">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide">Ver Reporte de Asistencia</span>
                                    <ChevronRight size={14} className="text-slate-400 group-hover:text-white" />
                                </button>
                                <button className="w-full flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-white/5 hover:bg-blue-600 hover:text-white transition-all group text-left">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide">Auditar Evaluaciones</span>
                                    <ChevronRight size={14} className="text-slate-400 group-hover:text-white" />
                                </button>
                                <button className="w-full flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-white/5 hover:bg-blue-600 hover:text-white transition-all group text-left">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide">Lista de Espera</span>
                                    <ChevronRight size={14} className="text-slate-400 group-hover:text-white" />
                                </button>
                            </div>
                        </DSCard>

                        <div className="bg-indigo-600 rounded-md p-4 text-white space-y-4 shadow-xl shadow-indigo-500/20">
                            <h4 className="text-sm font-semibold uppercase tracking-tight">Optimus Coach</h4>
                            <p className="text-[11px] text-indigo-100 font-medium leading-relaxed">
                                Este curso tiene un 15% más de participación que el promedio. Recomiendo abrir una segunda cohorte para el próximo periodo.
                            </p>
                            <button className="text-[10px] font-semibold uppercase tracking-wide px-4 py-2 bg-white/20 rounded-md hover:bg-white/30 transition-all">
                                Ver Análisis IA
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

// Minimal apiFetch mock to satisfy types if needed or use real one
import { apiFetch } from '@/lib/http';

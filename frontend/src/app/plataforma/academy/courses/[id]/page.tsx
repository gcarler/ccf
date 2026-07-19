"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    GraduationCap, 
    ShieldCheck, 
    BookOpen, 
    ArrowLeft,
    FileText,
    Calendar
} from 'lucide-react';
import { DSBadge } from '@/design/components/DSBadge';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

interface CourseStats {
    total_enrolled: number;
    completion_rate: number;
    average_grade: number;
}

interface CourseDetail {
    id: string;
    title: string;
    code: string;
    modality: string;
    cohort_name?: string | null;
    lesson_count: number;
    is_published: boolean;
}

interface CourseStudent {
    progress_percent: number;
    average_grade: number;
}

export default function CourseCoordinationPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    
    const [course, setCourse] = useState<CourseDetail | null>(null);
    const [stats, setStats] = useState<CourseStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !isAuthenticated || !id) return;
        
        const ctrl = new AbortController();
        const loadData = async () => {
            try {
                setLoading(true);
                const [courseData, students] = await Promise.all([
                    apiFetch<CourseDetail>(`/academy/courses/${id}`, { token, signal: ctrl.signal }),
                    apiFetch<CourseStudent[]>(`/academy/admin/courses/${id}/students`, { token, signal: ctrl.signal }),
                ]);
                const totalEnrolled = students.length;
                const completed = students.filter((student) => student.progress_percent >= 100).length;
                const graded = students.filter((student) => Number.isFinite(student.average_grade));
                setCourse(courseData);
                setStats({
                    total_enrolled: totalEnrolled,
                    completion_rate: totalEnrolled ? Math.round((completed / totalEnrolled) * 100) : 0,
                    average_grade: graded.length
                        ? Math.round(graded.reduce((sum, student) => sum + student.average_grade, 0) / graded.length)
                        : 0,
                });
            } catch {
                toast.error('No se pudo cargar la información del programa');
            } finally {
                setLoading(false);
            }
        };
        loadData();
        return () => ctrl.abort();
    }, [id, token, isAuthenticated]);

    if (loading) return (
        <div className="flex items-center justify-center h-full p-3 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">
            Sincronizando Malla Curricular...
        </div>
    );

    if (!course) return (
        <div className="flex flex-col items-center justify-center h-full p-3 text-center space-y-4">
            <h2 className="text-lg font-bold text-rose-500 uppercase">Programa no encontrado</h2>
            <button onClick={() => router.back()} className="text-sm font-semibold text-[hsl(var(--primary))] uppercase tracking-wide flex items-center gap-2">
                <ArrowLeft size={14} /> Volver a Coordinación
            </button>
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <h1 className="sr-only">{course.title}</h1>
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Coordinación', icon: ShieldCheck, href: '/plataforma/academy/coordination' },
                    { label: course.title, icon: BookOpen },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => router.push(`/plataforma/academy/courses/${id}/manage`)}
                            className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all"
                        >
                            Gestionar Cohorte
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="space-y-2">
                        <DSBadge tone={course.modality === 'formal' ? 'blue' : 'emerald'} label={course.modality === 'formal' ? 'RUTA FORMAL' : 'RUTA NO FORMAL'} />
                        <p aria-hidden="true" className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight leading-none uppercase">
                            {course.title}
                        </p>
                        <p className="text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide text-xs flex items-center gap-2">
                            <span className="text-[hsl(var(--primary))]">{course.code}</span> • {course.cohort_name || 'Sin cohorte activa'}
                        </p>
                    </div>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <DSMetric label="Inscritos" value={String(stats?.total_enrolled ?? 0)} trend="+5 esta semana" tone="blue" />
                    <DSMetric label="Finalización" value={`${stats?.completion_rate ?? 0}%`} trend="Target 90%" tone="emerald" />
                    <DSMetric label="Promedio" value={String(stats?.average_grade ?? 0)} trend="Sobre 100" tone="amber" />
                    <DSMetric label="Lecciones" value={String(course.lesson_count)} trend="Publicadas" tone="blue" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Estado de Alistamiento Académico</h3>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="size-8 rounded-md bg-blue-500/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                            <Calendar size={20} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Periodo de Inscripción</p>
                                            <p className="text-[11px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{course.is_published ? 'Visible para estudiantes' : 'Borrador interno'}</p>
                                        </div>
                                    </div>
                                    <DSBadge tone={course.is_published ? 'emerald' : 'amber'} label={course.is_published ? 'PUBLICADO' : 'BORRADOR'} />
                                </div>
                                
                                <div className="h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />

                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="size-8 rounded-md bg-amber-500/10 flex items-center justify-center text-amber-600">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Malla Curricular</p>
                                            <p className="text-[11px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{course.lesson_count} lecciones registradas</p>
                                        </div>
                                    </div>
                                    <DSBadge tone="amber" label="REVISIÓN" />
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Actas y Certificación</h3>
                            <div className="p-4 text-center bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/10">
                                <ShieldCheck size={48} className="mx-auto text-[hsl(var(--text-secondary))] mb-4" />
                                <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide">Sin actas de cierre emitidas</h4>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-2 font-medium">Las actas se generan automáticamente al finalizar el periodo académico del programa formal.</p>
                            </div>
                        </DSCard>
                    </div>

                </div>
            </main>
        </div>
    );
}

"use client";

import React, { useMemo } from 'react';
import { Bell, BookOpen, ChevronRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import AdminHero from '@/components/admin/AdminHero';

export default function StudentGrades() {
    const { isAuthenticated } = useAuth();
    const { enrollments, loading } = useStudentEnrollments();

    const approvedGrades = enrollments.filter((en) => typeof en.final_grade === 'number');
    const averageGrade = useMemo(() => {
        if (!approvedGrades.length) return 0;
        const total = approvedGrades.reduce((acc, curr) => acc + (curr.final_grade || 0), 0);
        return Math.round((total / approvedGrades.length) * 10) / 10;
    }, [approvedGrades]);

    const completionRate = useMemo(() => {
        if (!enrollments.length) return 0;
        const completed = enrollments.filter((en) => en.progress_percent >= 100 || en.approved).length;
        return Math.round((completed / enrollments.length) * 100);
    }, [enrollments]);

    if (!isAuthenticated) return null;

    return (
        <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="Calificaciones"
                title="Mis calificaciones"
                description="Consolida tus promedios por nivel: Fundamentos, Intermedio y Avanzado."
                tags={['Promedio', 'Asistencia', 'Logros']}
                watchers={['Equipo Académico', 'Optimus Brain']}
                primaryAction={{ label: 'Configurar alertas', icon: Bell, onClick: () => {} }}
            />

            <section className="relative overflow-hidden rounded-[2.5rem] bg-primary p-8 text-white shadow-2xl shadow-primary/30 border border-white/10">
                <div className="relative flex flex-wrap gap-8 justify-between items-center">
                    <div>
                        <span className="text-[10px] font-black uppercase tracking-widest text-primary bg-white px-3 py-1.5 rounded-xl shadow-sm">
                            Resumen del {new Date().getFullYear()}
                        </span>
                        <h2 className="text-3xl font-black tracking-tight leading-none mt-4">Progreso Académico</h2>
                        <p className="text-white/80 text-sm mt-2 font-medium">
                            {enrollments.length ? 'Información en tiempo real de tus materias inscritas.' : 'Empieza un curso para ver tus métricas aquí.'}
                        </p>
                    </div>
                    <div className="flex gap-6">
                        <MetricCard label="Promedio general" value={averageGrade ? `${averageGrade}/10` : '—'} />
                        <MetricCard label="Cursos aprobados" value={`${completionRate}%`} />
                    </div>
                </div>
            </section>

            <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] shadow-xl p-6 space-y-6">
                {loading ? (
                    <div className="px-6 py-12 text-center text-slate-400 text-sm font-semibold uppercase tracking-widest">
                        Cargando materias...
                    </div>
                ) : enrollments.length === 0 ? (
                    <div className="px-6 py-16 text-center text-slate-400 space-y-3">
                        <BookOpen className="w-12 h-12 mx-auto text-slate-300" />
                        <p className="text-lg font-bold text-slate-800 dark:text-white">Aún no tienes calificaciones</p>
                        <p className="text-sm">Inscríbete a un curso para ver tus notas y progreso aquí.</p>
                    </div>
                ) : (
                    <div className="px-2 flex flex-col gap-4">
                        <h3 className="text-slate-900 dark:text-white text-xl font-bold mb-2">Materias inscritas</h3>
                        {enrollments.map((enrollment) => (
                            <article key={enrollment.id} className="bg-slate-50 dark:bg-white/5 rounded-[2rem] p-6 border border-slate-100 dark:border-white/10 flex flex-col gap-4 shadow-xl transition-all">
                                <div className="flex items-center gap-4">
                                    <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                                        <BookOpen size={24} />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-xs text-slate-400 uppercase tracking-widest font-bold mb-1">
                                            {enrollment.course.modality === 'formal' ? 'Programa formal' : 'Ruta no formal'}
                                        </p>
                                        <h4 className="text-slate-900 dark:text-white text-lg font-bold leading-tight">{enrollment.course.title}</h4>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-primary text-2xl font-black">
                                            {typeof enrollment.final_grade === 'number' ? enrollment.final_grade.toFixed(1) : '--'}
                                            <span className="text-xs text-slate-400 font-bold">/10</span>
                                        </p>
                                        <p className="text-[9px] text-slate-500 uppercase font-black tracking-widest mt-1">Calificación</p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-3 items-center text-sm">
                                    <StatusPill label="Progreso" value={`${Math.round(enrollment.progress_percent)}%`} highlight={enrollment.progress_percent >= 70} />
                                    <StatusPill label="Asistencia" value={`${Math.round(enrollment.attendance_percent)}%`} highlight={enrollment.attendance_percent >= 75} />
                                    <StatusPill label="Estado" value={enrollment.approved ? 'Aprobado' : 'En curso'} highlight={enrollment.approved} />
                                </div>
                                <div className="h-px bg-slate-200 dark:bg-white/10"></div>
                                <div className="flex items-center justify-between text-xs uppercase tracking-widest font-black text-slate-500">
                                    <span>ID inscripción #{enrollment.id}</span>
                                    <button className="text-primary flex items-center gap-1 hover:translate-x-1 transition-transform">
                                        Ver detalle <ChevronRight size={14} />
                                    </button>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function MetricCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="bg-white/15 rounded-2xl px-6 py-4 border border-white/20 text-center">
            <p className="text-[10px] font-black uppercase tracking-widest text-white/70">{label}</p>
            <p className="text-2xl font-black text-white mt-1">{value}</p>
        </div>
    );
}

function StatusPill({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div
            className={`px-3 py-1.5 rounded-lg border text-[10px] font-black uppercase tracking-widest ${
                highlight
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-white/5 text-slate-400 border-white/10'
            }`}
        >
            <span className="text-slate-500 mr-1">{label}</span>
            {value}
        </div>
    );
}


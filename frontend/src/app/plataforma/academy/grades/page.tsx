"use client";

import React, { useMemo } from 'react';
import { Bell, BookOpen, ChevronRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import AdminHero from '@/components/admin/AdminHero';
import { useRouter } from 'next/navigation';

export default function StudentGrades() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
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
        <div className="space-y-3 px-4 py-1.5">
            <AdminHero
                eyebrow="Calificaciones"
                title="Mis calificaciones"
                description="Consolida tus promedios por nivel: Fundamentos, Intermedio y Avanzado."
                tags={['Promedio', 'Asistencia', 'Logros']}
                watchers={['Equipo Academico', 'Optimus Brain']}
                primaryAction={{ label: 'Configurar alertas', icon: Bell, onClick: () => router.push('/plataforma/account') }}
            />

            <section className="relative overflow-hidden rounded-lg bg-[hsl(var(--primary))] p-4 text-[hsl(var(--primary-foreground))] shadow-2xl border border-[hsl(var(--primary)/0.2)]">
                <div className="relative flex flex-wrap gap-4 justify-between items-center">
                    <div>
                        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] px-3 py-1.5 rounded-lg shadow-sm">
                            Resumen del {new Date().getFullYear()}
                        </span>
                        <h2 className="text-xl font-bold tracking-tight leading-none mt-3">Progreso Academico</h2>
                        <p className="text-[hsl(var(--primary-foreground)/0.8)] text-sm mt-2 font-medium">
                            {enrollments.length ? 'Informacion en tiempo real de tus materias inscritas.' : 'Empieza un curso para ver tus metricas aqui.'}
                        </p>
                    </div>
                    <div className="flex gap-4">
                        <MetricCard label="Promedio general" value={averageGrade ? `${averageGrade}/10` : '—'} />
                        <MetricCard label="Cursos aprobados" value={`${completionRate}%`} />
                    </div>
                </div>
            </section>

            <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-xl p-4 space-y-3">
                {loading ? (
                    <div className="px-4 py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm font-semibold uppercase tracking-wide">
                        Cargando materias...
                    </div>
                ) : enrollments.length === 0 ? (
                    <div className="px-4 py-1.5 text-center text-[hsl(var(--text-secondary))] space-y-3">
                        <BookOpen className="w-12 h-8 mx-auto text-[hsl(var(--text-secondary))]" />
                        <p className="text-sm font-bold text-[hsl(var(--foreground))]">Aun no tienes calificaciones</p>
                        <p className="text-sm">Inscribete a un curso para ver tus notas y progreso aqui.</p>
                    </div>
                ) : (
                    <div className="px-2 flex flex-col gap-4">
                        <h3 className="text-[hsl(var(--foreground))] text-base font-bold mb-2">Materias inscritas</h3>
                        {enrollments.map((enrollment) => (
                            <article key={enrollment.id} className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))] flex flex-col gap-4 shadow-xl transition-all">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
                                        <BookOpen size={24} />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-xs text-[hsl(var(--text-secondary))] uppercase tracking-wide font-bold mb-1">
                                            {enrollment.course.modality === 'formal' ? 'Programa formal' : 'Ruta no formal'}
                                        </p>
                                        <h4 className="text-[hsl(var(--foreground))] text-sm font-bold leading-tight">{enrollment.course.title}</h4>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-[hsl(var(--primary))] text-lg font-bold">
                                            {typeof enrollment.final_grade === 'number' ? enrollment.final_grade.toFixed(1) : '--'}
                                            <span className="text-xs text-[hsl(var(--text-secondary))] font-bold">/10</span>
                                        </p>
                                        <p className="text-2xs text-[hsl(var(--text-secondary))] uppercase font-bold tracking-wide mt-1">Calificacion</p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-3 items-center text-sm">
                                    <StatusPill label="Progreso" value={`${Math.round(enrollment.progress_percent)}%`} highlight={enrollment.progress_percent >= 70} />
                                    <StatusPill label="Asistencia" value={`${Math.round(enrollment.attendance_percent)}%`} highlight={enrollment.attendance_percent >= 75} />
                                    <StatusPill label="Estado" value={enrollment.approved ? 'Aprobado' : 'En curso'} highlight={enrollment.approved} />
                                </div>
                                <div className="h-px bg-[hsl(var(--border))]"></div>
                                <div className="flex items-center justify-between text-xs uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))]">
                                    <span>ID inscripcion #{enrollment.id}</span>
                                    <button className="text-[hsl(var(--primary))] flex items-center gap-1 hover:translate-x-1 transition-transform">
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
        <div className="bg-[hsl(var(--primary-foreground)/0.15)] rounded-lg px-3 py-1.5 border border-[hsl(var(--primary-foreground)/0.2)] text-center">
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground)/0.7)]">{label}</p>
            <p className="text-lg font-bold text-[hsl(var(--primary-foreground))] mt-1">{value}</p>
        </div>
    );
}

function StatusPill({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
    return (
        <div
            className={`px-3 py-1.5 rounded-lg border text-2xs font-semibold uppercase tracking-wide ${
                highlight
                    ? 'bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.3)]'
                    : 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]'
            }`}
        >
            <span className="text-[hsl(var(--text-secondary))] mr-1">{label}</span>
            {value}
        </div>
    );
}

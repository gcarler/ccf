"use client";

import clsx from 'clsx';
import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BookOpen, CheckCircle, Link as LinkIcon, PlusCircle, Calendar } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';

const filters = ['Todos', 'En progreso', 'Finalizados'];

export default function StudentCurriculum() {
    const router = useRouter();
    const { isAuthenticated } = useAuth();
    const { enrollments, loading, error } = useStudentEnrollments();
    const [activeFilter, setActiveFilter] = useState('Todos');

    const filtered = useMemo(() => {
        if (activeFilter === 'En progreso') {
            return enrollments.filter((en) => !en.approved);
        }
        if (activeFilter === 'Finalizados') {
            return enrollments.filter((en) => en.approved || en.certificate_issued);
        }
        return enrollments;
    }, [enrollments, activeFilter]);

    const summary = useMemo(() => {
        const formal = enrollments.filter((en) => en.course.modality === 'formal').length;
        const informal = enrollments.length - formal;
        const avgProgress = enrollments.length
            ? Math.round(enrollments.reduce((acc, en) => acc + en.progress_percent, 0) / enrollments.length)
            : 0;
        return { formal, informal, avgProgress };
    }, [enrollments]);

    if (!isAuthenticated) return null;

    return (
        <div className="space-y-3 px-4 py-1.5">
            <AdminHero
                eyebrow="Currículo"
                title="Organizador curricular"
                description="Administra tus rutas según el nivel de formación (fundamentos, intermedio, avanzado)."
                tags={['Fundamentos', 'Intermedio', 'Avanzado']}
                watchers={['Coordinación Académica', 'Optimus Brain']}
                primaryAction={{ label: 'Editar plan', icon: LinkIcon, onClick: () => router.push('/plataforma/academy/coordination') }}
                secondaryAction={{ label: 'Ver cronograma', icon: Calendar, onClick: () => router.push('/plataforma/academy/schedule') }}
            />
            <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-xl overflow-hidden">
                <div className="flex overflow-x-auto hide-scrollbar gap-3 p-4 border-b border-[hsl(var(--border))]">
                    {filters.map((filter) => (
                        <CommunityToolbarChip
                            key={filter}
                            label={filter}
                            active={activeFilter === filter}
                            variant={activeFilter === filter ? 'solid' : 'outline'}
                            onClick={() => setActiveFilter(filter)}
                        />
                    ))}
                </div>
                <div className="px-4 py-2 flex items-center justify-between">
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))]">{activeFilter}</h2>
                    <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] px-3 py-1 rounded-full">
                        {filtered.length} cursos
                    </span>
                </div>
                <div className="px-4 pb-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <SummaryCard label="Formal" value={summary.formal} tone="blue" />
                    <SummaryCard label="No formal" value={summary.informal} tone="blue" />
                    <SummaryCard label="Avg progreso" value={`${summary.avgProgress}%`} tone="emerald" />
                </div>
                {loading && <p className="px-4 pb-6 text-sm text-[hsl(var(--text-secondary))]">Sincronizando tus cursos...</p>}
                {error && <p className="px-4 pb-6 text-sm text-[hsl(var(--danger))]">{error}</p>}
                {!loading && filtered.length === 0 && (
                    <div className="px-4 py-1.5 text-center text-[hsl(var(--text-secondary))] space-y-3">
                        <BookOpen className="w-12 h-8 mx-auto text-[hsl(var(--text-secondary))]" />
                        <p className="text-sm font-bold text-[hsl(var(--foreground))]">No encontramos cursos en esta categoría</p>
                        <p className="text-sm">Inscríbete a una nueva cohorte para ampliar tu plan de estudios.</p>
                    </div>
                )}
                <div className="px-4 pb-8 space-y-4">
                        {filtered.map((enrollment) => (
                            <article
                                key={enrollment.id}
                                onClick={() => router.push(`/plataforma/academy/course/${enrollment.course.id}`)}
                                className="bg-[hsl(var(--surface-2))] rounded-md p-3 border border-[hsl(var(--border))] flex items-center gap-4 group cursor-pointer hover:shadow-lg transition-all"
                            >
                                <div className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors p-2">
                                    <BookOpen size={20} />
                                </div>
                                <div className="flex-1">
                                    <div
                                        className={clsx(
                                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-2xs font-semibold uppercase tracking-wide mb-3 border',
                                            enrollment.approved
                                                ? 'text-[hsl(var(--success))] border-[hsl(var(--success)/25%)] bg-[hsl(var(--success)/0.1)]'
                                                : 'text-[hsl(var(--warning))] border-[hsl(var(--warning)/25%)] bg-[hsl(var(--warning)/0.1)]'
                                        )}
                                    >
                                        {enrollment.approved ? <CheckCircle size={12} /> : <LinkIcon size={12} />}
                                        {enrollment.approved ? 'Completado' : 'En curso'}
                                    </div>
                                    <h3 className="text-sm font-bold text-[hsl(var(--foreground))] leading-tight mb-1 group-hover:text-[hsl(var(--primary))] transition-colors">
                                        {enrollment.course.title}
                                    </h3>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">{enrollment.course.modality === 'formal' ? 'Programa formal' : 'Taller no formal'}</p>
                                </div>
                                <div className="w-20 h-20 rounded-lg border border-[hsl(var(--border))] flex flex-col items-center justify-center bg-[hsl(var(--surface-1))]">
                                    <p className="text-[hsl(var(--foreground))] text-sm font-semibold">{Math.round(enrollment.progress_percent)}%</p>
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] uppercase tracking-wide">Progreso</p>
                                </div>
                            </article>
                        ))}
                    <Link href="/plataforma/academy" className="bg-[hsl(var(--primary)/0.05)] rounded-md p-4 border-2 border-dashed border-[hsl(var(--primary)/0.2)] flex flex-col items-center justify-center gap-3 group hover:border-[hsl(var(--primary)/0.5)] hover:bg-[hsl(var(--primary)/0.1)] transition-all cursor-pointer">
                        <div className="text-[hsl(var(--primary)/0.5)] group-hover:text-[hsl(var(--primary))] transition-colors">
                            <PlusCircle size={32} />
                        </div>
                        <p className="text-[hsl(var(--primary))] font-bold text-xs uppercase tracking-wide">Añadir nueva materia</p>
                    </Link>
                </div>
            </div>
        </div>
    );
}

function SummaryCard({ label, value, tone }: { label: string; value: string | number; tone: 'blue' | 'sky' | 'emerald' }) {
    const colors: Record<'blue' | 'sky' | 'emerald', string> = {
        blue: 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]',
        sky: 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]',
        emerald: 'bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]',
    };
    return (
        <div className={`rounded-lg border border-[hsl(var(--border))] px-4 py-1.5 flex items-center justify-between ${colors[tone]}`}>
            <span className="text-2xs font-semibold uppercase tracking-wide">{label}</span>
            <span className="text-sm font-semibold">{value}</span>
        </div>
    );
}

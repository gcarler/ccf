"use client";

import clsx from 'clsx';
import React, { useMemo, useState } from 'react';
import { BookOpen, CheckCircle, Link as LinkIcon, PlusCircle, Calendar } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';

const filters = ['Todos', 'En progreso', 'Finalizados'];

export default function StudentCurriculum() {
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
        <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="Currículo"
                title="Organizador curricular"
                description="Administra tus rutas según el nivel de formación (fundamentos, intermedio, avanzado)."
                tags={['Fundamentos', 'Intermedio', 'Avanzado']}
                watchers={['Coordinación Académica', 'Optimus Brain']}
                primaryAction={{ label: 'Editar plan', icon: LinkIcon, onClick: () => {} }}
                secondaryAction={{ label: 'Ver cronograma', icon: Calendar, onClick: () => {} }}
            />
            <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl overflow-hidden">
                <div className="flex overflow-x-auto hide-scrollbar gap-3 p-6 border-b border-slate-100 dark:border-white/5">
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
                <div className="px-6 py-4 flex items-center justify-between">
                    <h2 className="text-2xl font-black text-slate-900 dark:text-white">{activeFilter}</h2>
                    <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 bg-slate-100 dark:bg-white/5 px-3 py-1 rounded-full">
                        {filtered.length} cursos
                    </span>
                </div>
                <div className="px-6 pb-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <SummaryCard label="Formal" value={summary.formal} tone="blue" />
                    <SummaryCard label="No formal" value={summary.informal} tone="violet" />
                    <SummaryCard label="Avg progreso" value={`${summary.avgProgress}%`} tone="emerald" />
                </div>
                {loading && <p className="px-6 pb-6 text-sm text-slate-500">Sincronizando tus cursos...</p>}
                {error && <p className="px-6 pb-6 text-sm text-rose-400">{error}</p>}
                {!loading && filtered.length === 0 && (
                    <div className="px-6 py-16 text-center text-slate-400 space-y-3">
                        <BookOpen className="w-12 h-12 mx-auto text-slate-300" />
                        <p className="text-lg font-bold text-slate-800 dark:text-white">No encontramos cursos en esta categoría</p>
                        <p className="text-sm">Inscríbete a una nueva cohorte para ampliar tu plan de estudios.</p>
                    </div>
                )}
                <div className="px-6 pb-8 space-y-4">
                        {filtered.map((enrollment) => (
                            <article key={enrollment.id} className="bg-slate-50 dark:bg-white/5 rounded-[2rem] p-5 border border-slate-100 dark:border-white/10 flex items-center gap-4 group">
                                <div className="text-slate-400 group-hover:text-primary transition-colors p-2">
                                    <BookOpen size={20} />
                                </div>
                                <div className="flex-1">
                                    <div
                                        className={clsx(
                                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest mb-3 border',
                                            enrollment.approved
                                                ? 'text-emerald-500 border-emerald-200 bg-emerald-50'
                                                : 'text-amber-500 border-amber-200 bg-amber-50'
                                        )}
                                    >
                                        {enrollment.approved ? <CheckCircle size={12} /> : <LinkIcon size={12} />}
                                        {enrollment.approved ? 'Completado' : 'En curso'}
                                    </div>
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-tight mb-1 group-hover:text-primary transition-colors">
                                        {enrollment.course.title}
                                    </h3>
                                    <p className="text-xs text-slate-500 font-medium">{enrollment.course.modality === 'formal' ? 'Programa formal' : 'Taller no formal'}</p>
                                </div>
                                <div className="w-20 h-20 rounded-2xl border border-slate-200 dark:border-white/10 flex flex-col items-center justify-center bg-white dark:bg-black/20">
                                    <p className="text-slate-900 dark:text-white text-lg font-black">{Math.round(enrollment.progress_percent)}%</p>
                                    <p className="text-[9px] text-slate-500 uppercase tracking-widest">Progreso</p>
                                </div>
                            </article>
                        ))}
                    <Link href="/academy" className="bg-primary/5 rounded-[2rem] p-6 border-2 border-dashed border-primary/20 flex flex-col items-center justify-center gap-3 group hover:border-primary/50 hover:bg-primary/10 transition-all cursor-pointer">
                        <div className="text-primary/50 group-hover:text-primary transition-colors">
                            <PlusCircle size={32} />
                        </div>
                        <p className="text-primary font-bold text-xs uppercase tracking-widest">Añadir nueva materia</p>
                    </Link>
                </div>
            </div>
        </div>
    );
}

function SummaryCard({ label, value, tone }: { label: string; value: string | number; tone: 'blue' | 'violet' | 'emerald' }) {
    const colors: Record<'blue' | 'violet' | 'emerald', string> = {
        blue: 'bg-blue-50 text-blue-600 dark:bg-blue-500/10',
        violet: 'bg-violet-50 text-violet-600 dark:bg-violet-500/10',
        emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10',
    };
    return (
        <div className={`rounded-2xl border border-slate-100 dark:border-white/5 px-4 py-3 flex items-center justify-between ${colors[tone]}`}>
            <span className="text-[10px] font-black uppercase tracking-[0.3em]">{label}</span>
            <span className="text-lg font-black">{value}</span>
        </div>
    );
}

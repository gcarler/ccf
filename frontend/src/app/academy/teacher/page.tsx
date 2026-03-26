"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import { AssignmentSubmissionReview } from '@/types/academy';
import {
    GraduationCap,
    ClipboardList,
    CheckCircle2,
    XCircle,
    Loader2,
    FileText,
    ArrowRight,
    Award,
    Shield,
    MessageCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

export default function TeacherWorkspace() {
    const { token, user, isAuthenticated } = useAuth();
    const [submissions, setSubmissions] = useState<AssignmentSubmissionReview[]>([]);
    const [loading, setLoading] = useState(true);
    const [gradingId, setGradingId] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'pending' | 'history'>('pending');

    const isStaff = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'docente', 'staff'].includes(role);
    }, [user?.role]);

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        loadSubmissions();
    }, [token, isAuthenticated]);

    const loadSubmissions = async () => {
        try {
            setLoading(true);
            const data = await apiFetch<AssignmentSubmissionReview[]>(`/academy/admin/submissions?limit=50`, {
                token,
                cache: 'no-store',
            });
            setSubmissions(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            toast.error('No pudimos cargar las entregas pendientes');
        } finally {
            setLoading(false);
        }
    };

    const pending = submissions.filter((submission) => submission.grade == null);
    const graded = submissions.filter((submission) => submission.grade != null);

    const handleQuickGrade = async (submission: AssignmentSubmissionReview, decision: 'approve' | 'review') => {
        if (!token) return;
        setGradingId(submission.id);
        const grade = decision === 'approve' ? 95 : 60;
        const feedback = decision === 'approve'
            ? 'Excelente trabajo, sigue así.'
            : 'Por favor ajusta los requisitos antes de volver a enviar.';
        try {
            await apiFetch<AssignmentSubmissionReview>(
                `/academy/admin/submissions/${submission.id}/grade?grade=${grade}&feedback=${encodeURIComponent(feedback)}`,
                { method: 'PATCH', token }
            );
            toast.success(decision === 'approve' ? 'Calificación registrada' : 'Solicitud de ajustes enviada');
            await loadSubmissions();
        } catch (err) {
            console.error(err);
            toast.error('No se pudo registrar la calificación');
        } finally {
            setGradingId(null);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#121417] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Panel Docente', icon: ClipboardList },
                ]}
                viewType="grid"
                setViewType={() => {}}
                rightActions={
                    <span className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                        {pending.length} revisiones pendientes
                    </span>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                {!isStaff && (
                    <div className="border border-amber-300 bg-amber-100 text-amber-800 rounded-3xl px-6 py-4 text-sm font-semibold">
                        Este panel está reservado para docentes y coordinación. Solicita permisos al administrador.
                    </div>
                )}

                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <TeacherStat icon={Award} label="Entregas pendientes" value={pending.length} tone="blue" />
                    <TeacherStat icon={Shield} label="Revisadas" value={graded.length} tone="emerald" />
                    <TeacherStat icon={MessageCircle} label="Feedback promedio" value={graded.length ? 'En curso' : 'N/A'} tone="amber" />
                </section>

                 <section className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl">
                     <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between px-6 py-5 border-b border-slate-100 dark:border-white/5 gap-3">
                         <div>
                             <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Flujo de revisiones</p>
                             <h2 className="text-2xl font-black text-slate-800 dark:text-white">Entregas de estudiantes</h2>
                         </div>
                        <div className="flex items-center gap-3">
                            <div className="rounded-2xl bg-slate-900/5 dark:bg-white/5 border border-slate-200 dark:border-white/10 p-1 flex gap-1">
                                {[
                                    { id: 'pending', label: 'Pendientes' },
                                    { id: 'history', label: 'Historial' },
                                ].map((option) => (
                                    <button
                                        key={option.id}
                                        onClick={() => setViewMode(option.id as 'pending' | 'history')}
                                        className={`px-3 py-1.5 rounded-xl text-[11px] font-black uppercase tracking-[0.3em] ${
                                            viewMode === option.id ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white' : 'text-slate-400'
                                        }`}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={loadSubmissions}
                                className="inline-flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.3em] px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5"
                            >
                                Actualizar
                                <ArrowRight size={14} />
                            </button>
                        </div>
                     </header>
                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                        {loading && (
                            <div className="flex items-center gap-3 px-6 py-8 text-slate-500">
                                <Loader2 className="animate-spin" size={18} /> Sincronizando con el LMS...
                            </div>
                        )}
                        {!loading && viewMode === 'pending' && pending.length === 0 && (
                            <div className="px-6 py-12 text-center text-slate-500 text-sm">
                                No hay entregas pendientes por ahora. Disfruta un café ☕
                            </div>
                        )}
                        {viewMode === 'pending' && pending.map((submission) => (
                            <article key={submission.id} className="px-6 py-6 flex flex-col lg:flex-row lg:items-center gap-6">
                                <div className="flex-1 min-w-0 space-y-2">
                                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-500">{submission.lesson_title}</p>
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-tight">
                                        {submission.student_name}
                                    </h3>
                                    <p className="text-sm text-slate-500 line-clamp-2">{submission.comment || 'Sin comentarios adicionales'}</p>
                                    <div className="flex items-center gap-4 text-[11px] font-black uppercase tracking-widest text-slate-400">
                                        <span>Entrega #{submission.id}</span>
                                        <span>{new Date(submission.submitted_at).toLocaleString()}</span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <a
                                        href={submission.file_url}
                                        target="_blank"
                                        className="inline-flex items-center gap-2 px-4 py-2 rounded-2xl border border-slate-200 dark:border-white/10 text-[11px] font-black uppercase tracking-[0.3em] hover:bg-slate-50 dark:hover:bg-white/5"
                                        rel="noreferrer"
                                    >
                                        <FileText size={14} /> Ver archivo
                                    </a>
                                    <button
                                        disabled={gradingId === submission.id}
                                        onClick={() => handleQuickGrade(submission, 'approve')}
                                        className={clsx(
                                            'inline-flex items-center gap-2 px-4 py-2 rounded-2xl text-[11px] font-black uppercase tracking-[0.3em] bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600 transition-all',
                                            gradingId === submission.id && 'opacity-50 cursor-wait'
                                        )}
                                    >
                                        <CheckCircle2 size={14} /> Aprobar
                                    </button>
                                    <button
                                        disabled={gradingId === submission.id}
                                        onClick={() => handleQuickGrade(submission, 'review')}
                                        className={clsx(
                                            'inline-flex items-center gap-2 px-4 py-2 rounded-2xl text-[11px] font-black uppercase tracking-[0.3em] bg-rose-500 text-white shadow-lg shadow-rose-500/20 hover:bg-rose-600 transition-all',
                                            gradingId === submission.id && 'opacity-50 cursor-wait'
                                        )}
                                    >
                                        <XCircle size={14} /> Revisar
                                    </button>
                                </div>
                            </article>
                        ))}
                        {viewMode === 'history' && (
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm">
                                    <thead>
                                        <tr className="text-left text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                                            <th className="px-6 py-3">Lección</th>
                                            <th className="px-6 py-3">Estudiante</th>
                                            <th className="px-6 py-3">Nota</th>
                                            <th className="px-6 py-3">Fecha</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {graded.length === 0 && (
                                            <tr>
                                                <td colSpan={4} className="px-6 py-6 text-slate-500 text-center">Aún no hay historial</td>
                                            </tr>
                                        )}
                                        {graded.map((submission) => (
                                            <tr key={`graded-${submission.id}`} className="border-t border-slate-100 dark:border-white/5">
                                                <td className="px-6 py-4 font-semibold text-slate-900 dark:text-white">{submission.lesson_title}</td>
                                                <td className="px-6 py-4 text-slate-400">{submission.student_name}</td>
                                                <td className="px-6 py-4">{submission.grade?.toFixed(1) ?? 'N/A'}</td>
                                                <td className="px-6 py-4 text-slate-400">{new Date(submission.submitted_at).toLocaleDateString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </section>

                {graded.length > 0 && (
                    <section className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-slate-50/70 dark:bg-white/5 p-6">
                        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 mb-4">Últimas calificaciones</p>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {graded.slice(0, 3).map((submission) => (
                                <div key={submission.id} className="bg-white dark:bg-[#121417] rounded-2xl border border-slate-100 dark:border-white/10 p-4 shadow-sm">
                                    <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">{submission.lesson_title}</p>
                                    <h4 className="text-lg font-bold text-slate-800 dark:text-white">{submission.student_name}</h4>
                                    <p className="text-sm text-slate-500">Nota: {submission.grade?.toFixed(1)}</p>
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
}

function TeacherStat({ icon: Icon, label, value, tone }: { icon: any; label: string; value: number | string; tone: 'blue' | 'emerald' | 'amber' }) {
    const toneClasses = {
        blue: 'bg-blue-50 text-blue-600 dark:bg-blue-500/10',
        emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10',
        amber: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10',
    };
    return (
        <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] p-6 flex items-center gap-4 shadow-sm">
            <div className={clsx('size-12 rounded-2xl flex items-center justify-center', toneClasses[tone])}>
                <Icon size={22} />
            </div>
            <div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 mb-1">{label}</p>
                <p className="text-2xl font-black text-slate-900 dark:text-white">{value}</p>
            </div>
        </div>
    );
}

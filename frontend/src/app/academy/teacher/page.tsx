"use client";

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import { AssignmentSubmissionReview } from '@/types/academy';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import {
    GraduationCap,
    ClipboardList,
    CheckCircle2,
    XCircle,
    Loader2,
    FileText,
    Shield,
    Users,
    BookOpen,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';
import { useWikiDocument } from '@/hooks/useWikiDocument';

import WorkspaceLayout from '@/components/WorkspaceLayout';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { DSMetric, DSCard, DSBadge } from '@/design';

export default function TeacherWorkspace() {
    const { token, user, isAuthenticated } = useAuth();
    const router = useRouter();
    const [submissions, setSubmissions] = useState<AssignmentSubmissionReview[]>([]);
    const [courses, setCourses] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [gradingId, setGradingId] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'pending' | 'history' | 'courses'>('courses');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('academy_teacher_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('academy_teacher_wiki_notes', {
        title: 'Wiki docente',
    });

    const isStaff = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'docente', 'staff'].includes(role);
    }, [user?.role]);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [subRes, courseRes] = await Promise.all([
                apiFetch<AssignmentSubmissionReview[]>(`/academy/admin/submissions?limit=50`, {
                    token,
                    cache: 'no-store',
                }),
                apiFetch<any[]>(`/academy/courses/`, { token })
            ]);
            setSubmissions(Array.isArray(subRes) ? subRes : []);
            setCourses(Array.isArray(courseRes) ? courseRes : []);
        } catch (err) {
            console.error(err);
            toast.error('No pudimos cargar los datos del panel');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        loadData();
    }, [token, isAuthenticated, loadData]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('academy_teacher_view', viewType);
        }
    }, [viewType]);

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
            await loadData();
        } catch (err) {
            console.error(err);
            toast.error('No se pudo registrar la calificación');
        } finally {
            setGradingId(null);
        }
    };

    if (loading) {
        return (
            <WorkspaceLayout sidebarTitle="Academia">
                <div className="p-4 space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-lg" />)}
                    </div>
                    <Skeleton className="h-[400px] rounded-lg" />
                </div>
            </WorkspaceLayout>
        );
    }

    return (
        <WorkspaceLayout 
            sidebarTitle="Academia"
            allowedRoles={['admin', 'coordinador', 'docente', 'staff']}
        >
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0f1114]">
                <WorkspaceToolbar
                    breadcrumbs={[
                        { label: 'Academia', icon: GraduationCap },
                        { label: 'Panel Docente', icon: ClipboardList },
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={['grid', 'table', 'list', 'wiki']}
                    rightActions={
                        <div className="flex items-center gap-3">
                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                {pending.length} revisiones pendientes
                            </span>
                            <div className="h-4 w-px bg-slate-200 dark:bg-white/10 mx-1" />
                            <button 
                                onClick={loadData}
                                className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors text-slate-400 hover:text-blue-500"
                            >
                                <Loader2 size={16} className={clsx(loading && 'animate-spin')} />
                            </button>
                        </div>
                    }
                />

                <main className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-8">
                    {!isStaff && (
                        <div className="p-4 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-500/20 rounded-2xl">
                            <p className="text-sm font-bold text-amber-800 dark:text-amber-400 flex items-center gap-2">
                                <Shield size={18} /> Acceso Restringido
                            </p>
                            <p className="text-xs text-amber-700 dark:text-amber-400/70 mt-1">Este panel está reservado para docentes y coordinación. Solicita permisos al administrador.</p>
                        </div>
                    )}

                    {viewType === 'grid' && (
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <DSMetric label="Entregas pendientes" value={String(pending.length)} tone="blue" trend="Acción inmediata" />
                            <DSMetric label="Revisadas" value={String(graded.length)} tone="emerald" trend="Esta semana" />
                            <DSMetric label="Feedback promedio" value={graded.length ? 'Nivel Alto' : 'N/A'} tone="amber" trend="Calidad docente" />
                        </section>
                    )}

                    {viewType === 'wiki' && (
                        <section className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-8 shadow-[var(--shadow-floating)] space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight">Guía de Evaluación y Rúbricas</h3>
                                <DSBadge tone="blue" label="Privado Docentes" />
                            </div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta rúbricas, criterios de aprobación, política de feedback y tiempos de respuesta..."
                                className="w-full min-h-[400px] bg-slate-50/50 dark:bg-black/20 rounded-[1.5rem] border border-slate-100 dark:border-white/5 p-6 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-4 focus:ring-blue-500/5 transition-all"
                            />
                        </section>
                    )}

                    {(viewType === 'grid' || viewType === 'table' || viewType === 'list') && (
                        <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
                            <header className="p-8 border-b border-slate-100 dark:border-white/5 space-y-6">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div>
                                        <DSBadge tone="blue" label="Workspace Académico" />
                                        <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight mt-2">Control de Entregas</h3>
                                    </div>
                                    <div className="flex bg-slate-100 dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10 self-start md:self-center">
                                        {(['courses', 'pending', 'history'] as const).map((m) => (
                                            <button
                                                key={m}
                                                onClick={() => setViewMode(m)}
                                                className={clsx(
                                                    "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                                    viewMode === m 
                                                        ? "bg-white dark:bg-white/10 text-blue-600 shadow-lg shadow-blue-500/5" 
                                                        : "text-slate-400 hover:text-slate-600"
                                                )}
                                            >
                                                {m === 'courses' ? 'Mis Cursos' : m === 'pending' ? 'Pendientes' : 'Historial'}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </header>

                            <div className="min-h-[400px]">
                                {viewMode === 'courses' && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 p-8 gap-6">
                                        {courses.length === 0 && (
                                            <div className="col-span-full py-20">
                                                <EmptyState 
                                                    icon={BookOpen}
                                                    title="Sin cursos asignados"
                                                    description="Actualmente no tienes cursos bajo tu supervisión. Contacta con coordinación."
                                                />
                                            </div>
                                        )}
                                        {courses.map(course => (
                                            <div key={course.id} className="p-6 rounded-lg border-2 border-slate-50 dark:border-white/5 bg-white dark:bg-white/5 group hover:border-blue-500/30 transition-all hover:shadow-xl hover:shadow-blue-500/5">
                                                <div className="flex justify-between items-start mb-6">
                                                    <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-[9px] font-black uppercase tracking-widest text-blue-600">{course.code}</span>
                                                    <DSBadge tone="emerald" label={course.modality} />
                                                </div>
                                                <h4 className="text-xl font-black text-slate-800 dark:text-white mb-4 tracking-tight leading-none">{course.title}</h4>
                                                <div className="flex items-center gap-4 mb-8">
                                                    <div className="flex items-center gap-2 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                                                        <Users size={14} className="text-blue-500" /> {course.students_count || 0} Alumnos
                                                    </div>
                                                    <div className="flex items-center gap-2 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
                                                        <BookOpen size={14} className="text-blue-500" /> {course.lessons_count || 0} Lecciones
                                                    </div>
                                                </div>
                                                <button 
                                                    onClick={() => router.push(`/academy/courses/${course.id}/manage`)}
                                                    className="w-full py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[1.2rem] text-[10px] font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-lg"
                                                >
                                                    Gestionar Programa
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {viewMode === 'pending' && (
                                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                                        {pending.length === 0 && (
                                            <div className="py-32">
                                                <EmptyState 
                                                    icon={CheckCircle2}
                                                    title="¡Todo al día!"
                                                    description="No hay entregas pendientes de revisión por ahora. Disfruta un café ☕"
                                                />
                                            </div>
                                        )}
                                        {pending.map((submission) => (
                                            <article key={submission.id} className="p-8 flex flex-col lg:flex-row lg:items-center gap-8 group hover:bg-slate-50 dark:hover:bg-white/[0.01] transition-colors">
                                                <div className="flex-1 min-w-0 space-y-3">
                                                    <div className="flex items-center gap-2">
                                                        <DSBadge tone="blue" label={submission.lesson_title} />
                                                        <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest">Entrega #{submission.id}</span>
                                                    </div>
                                                    <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tight leading-none">
                                                        {submission.student_name}
                                                    </h3>
                                                    <p className="text-sm text-slate-500 line-clamp-2 font-medium bg-slate-100/50 dark:bg-black/20 p-4 rounded-xl italic">&quot;{submission.comment || 'Sin comentarios adicionales'}&quot;</p>
                                                    <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                                        <div className="flex items-center gap-2"><Loader2 size={12} className="text-amber-500" /> Pendiente</div>
                                                        <div className="size-1 rounded-full bg-slate-200" />
                                                        <div>{new Date(submission.submitted_at).toLocaleString()}</div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <a
                                                        href={submission.file_url}
                                                        target="_blank"
                                                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border-2 border-slate-100 dark:border-white/5 text-[10px] font-black uppercase tracking-widest hover:bg-white dark:hover:bg-white/5 transition-all active:scale-95"
                                                        rel="noreferrer"
                                                    >
                                                        <FileText size={14} /> Abrir
                                                    </a>
                                                    <button
                                                        disabled={gradingId === submission.id}
                                                        onClick={() => handleQuickGrade(submission, 'approve')}
                                                        className={clsx(
                                                            'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest bg-emerald-500 text-white shadow-xl shadow-emerald-500/20 hover:scale-105 active:scale-95 transition-all',
                                                            gradingId === submission.id && 'opacity-50 cursor-wait'
                                                        )}
                                                    >
                                                        <CheckCircle2 size={14} /> Aprobar
                                                    </button>
                                                    <button
                                                        disabled={gradingId === submission.id}
                                                        onClick={() => handleQuickGrade(submission, 'review')}
                                                        className={clsx(
                                                            'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest bg-rose-500 text-white shadow-xl shadow-rose-500/20 hover:scale-105 active:scale-95 transition-all',
                                                            gradingId === submission.id && 'opacity-50 cursor-wait'
                                                        )}
                                                    >
                                                        <XCircle size={14} /> Revisar
                                                    </button>
                                                </div>
                                            </article>
                                        ))}
                                    </div>
                                )}

                                {viewMode === 'history' && (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left">
                                            <thead className="bg-slate-50/50 dark:bg-white/[0.02] text-[10px] font-black uppercase tracking-widest text-slate-400">
                                                <tr>
                                                    <th className="px-8 py-4">Lección / Estudiante</th>
                                                    <th className="px-8 py-4">Nota Final</th>
                                                    <th className="px-8 py-4">Fecha Revisión</th>
                                                    <th className="px-8 py-4 text-right">Estado</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                                {graded.length === 0 && (
                                                    <tr>
                                                        <td colSpan={4} className="py-20 text-center">
                                                            <EmptyState icon={ClipboardList} title="Historial vacío" description="Aún no has calificado ninguna entrega." />
                                                        </td>
                                                    </tr>
                                                )}
                                                {graded.map((submission) => (
                                                    <tr key={submission.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.01] transition-colors">
                                                        <td className="px-8 py-5">
                                                            <div className="font-black text-slate-900 dark:text-white uppercase tracking-tight">{submission.student_name}</div>
                                                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{submission.lesson_title}</div>
                                                        </td>
                                                        <td className="px-8 py-5">
                                                            <span className="text-lg font-black text-slate-900 dark:text-white">{submission.grade?.toFixed(1) ?? 'N/A'}</span>
                                                        </td>
                                                        <td className="px-8 py-5 text-xs text-slate-500 font-medium">{new Date(submission.submitted_at).toLocaleDateString()}</td>
                                                        <td className="px-8 py-5 text-right">
                                                            <DSBadge tone="emerald" label="REVISADO" />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </DSCard>
                    )}
                </main>
            </div>
        </WorkspaceLayout>
    );
}


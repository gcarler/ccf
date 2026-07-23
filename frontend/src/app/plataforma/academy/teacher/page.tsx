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
    const [gradingId, setGradingId] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'pending' | 'history' | 'courses'>('courses');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('academy_teacher_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('academy_teacher_wiki_notes', {
        title: 'Wiki docente',
    });

    const isStaff = useMemo(() => {
        const role = (user?.role || '').toLowerCase();
        return ['admin', 'coordinador', 'docente', 'staff'].includes(role);
    }, [user?.role]);

    const loadData = useCallback(async (signal?: AbortSignal) => {
        try {
            setLoading(true);
            const [subRes, courseRes] = await Promise.all([
                apiFetch<AssignmentSubmissionReview[]>(`/academy/admin/submissions?limit=50`, {
                    token,
                    cache: 'no-store',
                    signal,
                }),
                apiFetch<any[]>(`/academy/courses/`, { token, signal })
            ]);
            setSubmissions(Array.isArray(subRes) ? subRes : []);
            setCourses(Array.isArray(courseRes) ? courseRes : []);
        } catch (err) {
            if ((err as Error).name === 'AbortError') return;
            console.error(err);
            toast.error('No pudimos cargar los datos del panel');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        const ctrl = new AbortController();
        loadData(ctrl.signal);
        return () => ctrl.abort();
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
            allowedPermissions={['academy:edit', 'academy:manage']}
        >
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))]">
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
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                {pending.length} revisiones pendientes
                            </span>
                            <div className="h-4 w-px bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />
                            <button 
                                onClick={() => loadData()}
                                className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg transition-colors text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]"
                            >
                                <Loader2 size={16} className={clsx(loading && 'animate-spin')} />
                            </button>
                        </div>
                    }
                />

                <main className="flex-1 overflow-y-auto p-4 space-y-3">
                    {!isStaff && (
                        <div className="p-4 bg-[hsl(var(--warning)/0.08)] border border-[hsl(var(--warning)/0.3)] rounded-lg">
                            <p className="text-sm font-bold text-[hsl(var(--warning))] flex items-center gap-2">
                                <Shield size={18} /> Acceso Restringido
                            </p>
                            <p className="text-xs text-[hsl(var(--warning))] mt-1">Este panel está reservado para docentes y coordinación. Solicita permisos al administrador.</p>
                        </div>
                    )}

                    {viewType === 'grid' && (
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <DSMetric label="Entregas pendientes" value={String(pending.length)} tone="blue" trend="Acción inmediata" />
                            <DSMetric label="Revisadas" value={String(graded.length)} tone="emerald" trend="Esta semana" />
                            <DSMetric label="Feedback promedio" value={graded.length ? 'Nivel Alto' : 'N/A'} tone="amber" trend="Calidad docente" />
                        </section>
                    )}

                    {viewType === 'wiki' && (
                        <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 shadow-[var(--shadow-floating)] space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Guía de Evaluación y Rúbricas</h3>
                                <DSBadge tone="blue" label="Privado Docentes" />
                            </div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta rúbricas, criterios de aprobación, política de feedback y tiempos de respuesta..."
                                className="w-full min-h-[400px] bg-[hsl(var(--surface-1))]/50 dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/5 transition-all"
                            />
                        </section>
                    )}

                    {(viewType === 'grid' || viewType === 'table' || viewType === 'list') && (
                        <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
                            <header className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 space-y-3">
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div>
                                        <DSBadge tone="blue" label="Workspace Académico" />
                                        <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight mt-2">Control de Entregas</h3>
                                    </div>
                                    <div className="flex bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 self-start md:self-center">
                                        {(['courses', 'pending', 'history'] as const).map((m) => (
                                            <button
                                                key={m}
                                                onClick={() => setViewMode(m)}
                                                className={clsx(
                                                    "px-4 py-2 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all",
                                                    viewMode === m 
                                                        ? "bg-[hsl(var(--bg-primary))] dark:bg-white/10 text-[hsl(var(--primary))] shadow-lg shadow-blue-500/5" 
                                                        : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]"
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
                                    <div className="grid grid-cols-1 md:grid-cols-2 p-4 gap-3">
                                        {courses.length === 0 && (
                                            <div className="col-span-full py-1.5">
                                                <EmptyState 
                                                    icon={BookOpen}
                                                    title="Sin cursos asignados"
                                                    description="Actualmente no tienes cursos bajo tu supervisión. Contacta con coordinación."
                                                />
                                            </div>
                                        )}
                                        {courses.map(course => (
                                            <div key={course.id} className="p-3 rounded-lg border-2 border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 group hover:border-blue-500/30 transition-all hover:shadow-xl hover:shadow-blue-500/5">
                                                <div className="flex justify-between items-start mb-3">
                                                    <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 rounded-lg text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">{course.code}</span>
                                                    <DSBadge tone="emerald" label={course.modality} />
                                                </div>
                                                <h4 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white mb-4 tracking-tight leading-none">{course.title}</h4>
                                                <div className="flex items-center gap-4 mb-3">
                                                    <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] text-[10px] font-bold uppercase tracking-wide">
                                                        <Users size={14} className="text-[hsl(var(--primary))]" /> {course.students_count || 0} Alumnos
                                                    </div>
                                                    <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] text-[10px] font-bold uppercase tracking-wide">
                                                        <BookOpen size={14} className="text-[hsl(var(--primary))]" /> {course.lessons_count || 0} Lecciones
                                                    </div>
                                                </div>
                                                <button 
                                                    onClick={() => router.push(`/plataforma/academy/courses/${course.id}/manage`)}
                                                    className="w-full py-3 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg text-[10px] font-semibold uppercase tracking-wide hover:scale-105 active:scale-95 transition-all shadow-lg"
                                                >
                                                    Gestionar Programa
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {viewMode === 'pending' && (
                                    <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                        {pending.length === 0 && (
                                            <div className="py-1.5">
                                                <EmptyState 
                                                    icon={CheckCircle2}
                                                    title="¡Todo al día!"
                                                    description="No hay entregas pendientes de revisión por ahora. Disfruta un café ☕"
                                                />
                                            </div>
                                        )}
                                        {pending.map((submission) => (
                                            <article key={submission.id} className="p-4 flex flex-col lg:flex-row lg:items-center gap-3 group hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.01] transition-colors">
                                                <div className="flex-1 min-w-0 space-y-3">
                                                    <div className="flex items-center gap-2">
                                                        <DSBadge tone="blue" label={submission.lesson_title} />
                                                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Entrega #{submission.id}</span>
                                                    </div>
                                                    <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight leading-none">
                                                        {submission.student_name}
                                                    </h3>
                                                    <p className="text-sm text-[hsl(var(--text-secondary))] line-clamp-2 font-medium bg-[hsl(var(--surface-2))]/50 dark:bg-black/20 p-4 rounded-md italic">&quot;{submission.comment || 'Sin comentarios adicionales'}&quot;</p>
                                                    <div className="flex items-center gap-4 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                        <div className="flex items-center gap-2"><Loader2 size={12} className="text-amber-500" /> Pendiente</div>
                                                        <div className="size-1 rounded-full bg-[hsl(var(--surface-3))]" />
                                                        <div>{new Date(submission.submitted_at).toLocaleString()}</div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <a
                                                        href={submission.file_url}
                                                        target="_blank"
                                                        className="inline-flex items-center gap-2 px-3 py-2.5 rounded-md border-2 border-[hsl(var(--border))] dark:border-white/5 text-[10px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 transition-all active:scale-95"
                                                        rel="noopener noreferrer"
                                                    >
                                                        <FileText size={14} /> Abrir
                                                    </a>
                                                    <button
                                                        disabled={gradingId === submission.id}
                                                        onClick={() => handleQuickGrade(submission, 'approve')}
                                                        className={clsx(
                                                            'inline-flex items-center gap-2 px-3 py-2.5 rounded-md text-[10px] font-semibold uppercase tracking-wide bg-[hsl(var(--success))] text-white shadow-xl shadow-[hsl(var(--success))/0.2] hover:scale-105 active:scale-95 transition-all',
                                                            gradingId === submission.id && 'opacity-50 cursor-wait'
                                                        )}
                                                    >
                                                        <CheckCircle2 size={14} /> Aprobar
                                                    </button>
                                                    <button
                                                        disabled={gradingId === submission.id}
                                                        onClick={() => handleQuickGrade(submission, 'review')}
                                                        className={clsx(
                                                            'inline-flex items-center gap-2 px-3 py-2.5 rounded-md text-[10px] font-semibold uppercase tracking-wide bg-[hsl(var(--destructive))] text-white shadow-xl shadow-[hsl(var(--destructive))/0.2] hover:scale-105 active:scale-95 transition-all',
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
                                            <thead className="bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                <tr>
                                                    <th className="px-4 py-1.5">Lección / Estudiante</th>
                                                    <th className="px-4 py-1.5">Nota Final</th>
                                                    <th className="px-4 py-1.5">Fecha Revisión</th>
                                                    <th className="px-4 py-1.5 text-right">Estado</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                                {graded.length === 0 && (
                                                    <tr>
                                                        <td colSpan={4} className="py-1.5 text-center">
                                                            <EmptyState icon={ClipboardList} title="Historial vacío" description="Aún no has calificado ninguna entrega." />
                                                        </td>
                                                    </tr>
                                                )}
                                                {graded.map((submission) => (
                                                    <tr key={submission.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.01] transition-colors">
                                                        <td className="px-4 py-2">
                                                            <div className="font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{submission.student_name}</div>
                                                            <div className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">{submission.lesson_title}</div>
                                                        </td>
                                                        <td className="px-4 py-2">
                                                            <span className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{submission.grade?.toFixed(1) ?? 'N/A'}</span>
                                                        </td>
                                                        <td className="px-4 py-2 text-xs text-[hsl(var(--text-secondary))] font-medium">{new Date(submission.submitted_at).toLocaleDateString()}</td>
                                                        <td className="px-4 py-2 text-right">
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

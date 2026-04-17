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
    ArrowRight,
    Award,
    Shield,
    MessageCircle,
    Users,
    BookOpen,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

export default function TeacherWorkspace() {
    const { token, user, isAuthenticated } = useAuth();
    const router = useRouter();
    const [submissions, setSubmissions] = useState<AssignmentSubmissionReview[]>([]);
    const [courses, setCourses] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [gradingId, setGradingId] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'pending' | 'history' | 'courses'>('courses');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('academy_teacher_view', 'grid'));
    const [wikiNotes, setWikiNotes] = useState('');

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
                apiFetch<any[]>(`/academy/courses/`, { token }) // In a real scenario, this would be filtered by teacher_id
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

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = window.localStorage.getItem('academy_teacher_wiki_notes');
            if (saved) setWikiNotes(saved);
        }
    }, []);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem('academy_teacher_wiki_notes', wikiNotes);
        }
    }, [wikiNotes]);



    const pending = submissions.filter((submission) => submission.grade == null);
    const graded = submissions.filter((submission) => submission.grade != null);

    const groupedByDate = useMemo(() => {
        const map: Record<string, AssignmentSubmissionReview[]> = {};
        for (const item of submissions) {
            const date = new Date(item.submitted_at);
            const key = Number.isNaN(date.getTime()) ? 'Sin fecha' : date.toISOString().slice(0, 10);
            if (!map[key]) map[key] = [];
            map[key].push(item);
        }
        return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
    }, [submissions]);

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

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#121417] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Panel Docente', icon: ClipboardList },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki']}
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

                {viewType === 'grid' && (
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <TeacherStat icon={Award} label="Entregas pendientes" value={pending.length} tone="blue" />
                    <TeacherStat icon={Shield} label="Revisadas" value={graded.length} tone="emerald" />
                    <TeacherStat icon={MessageCircle} label="Feedback promedio" value={graded.length ? 'En curso' : 'N/A'} tone="amber" />
                </section>
                )}

                {viewType === 'list' && (
                    <section className="space-y-3">
                        {submissions.map((submission) => (
                            <article key={`list-${submission.id}`} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-bold text-slate-900 dark:text-white">{submission.student_name}</p>
                                    <p className="text-xs text-slate-500">{submission.lesson_title} · {new Date(submission.submitted_at).toLocaleDateString()}</p>
                                </div>
                                <span className={clsx('text-[10px] font-black uppercase tracking-widest', submission.grade == null ? 'text-amber-500' : 'text-emerald-500')}>
                                    {submission.grade == null ? 'Pendiente' : 'Calificada'}
                                </span>
                            </article>
                        ))}
                        {submissions.length === 0 && <div className="py-10 text-center text-slate-400 text-sm">Sin entregas registradas</div>}
                    </section>
                )}

                {viewType === 'table' && (
                    <section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="text-left text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
                                    <th className="px-6 py-3">Lección</th>
                                    <th className="px-6 py-3">Estudiante</th>
                                    <th className="px-6 py-3">Estado</th>
                                    <th className="px-6 py-3">Nota</th>
                                    <th className="px-6 py-3">Fecha</th>
                                </tr>
                            </thead>
                            <tbody>
                                {submissions.map((submission) => (
                                    <tr key={`table-${submission.id}`} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-6 py-4 font-semibold text-slate-900 dark:text-white">{submission.lesson_title}</td>
                                        <td className="px-6 py-4 text-slate-400">{submission.student_name}</td>
                                        <td className="px-6 py-4 text-xs font-black uppercase tracking-widest">
                                            <span className={submission.grade == null ? 'text-amber-500' : 'text-emerald-500'}>{submission.grade == null ? 'Pendiente' : 'Calificada'}</span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-700 dark:text-slate-300">{submission.grade?.toFixed(1) ?? 'N/A'}</td>
                                        <td className="px-6 py-4 text-slate-400">{new Date(submission.submitted_at).toLocaleString()}</td>
                                    </tr>
                                ))}
                                {submissions.length === 0 && (
                                    <tr><td colSpan={5} className="px-6 py-8 text-center text-slate-400">Sin información</td></tr>
                                )}
                            </tbody>
                        </table>
                    </section>
                )}

                {(viewType === 'board' || viewType === 'kanban') && (
                    <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {[
                            { key: 'courses', label: 'Mis cursos', items: courses.map((c) => ({ id: `course-${c.id}`, title: c.title, meta: `${c.code} · ${c.students_count || 0} alumnos` })) },
                            { key: 'pending', label: 'Pendientes', items: pending.map((s) => ({ id: `pending-${s.id}`, title: s.student_name, meta: s.lesson_title })) },
                            { key: 'graded', label: 'Calificadas', items: graded.map((s) => ({ id: `graded-${s.id}`, title: s.student_name, meta: `${s.lesson_title} · ${s.grade?.toFixed(1) ?? 'N/A'}` })) },
                        ].map((column) => (
                            <div key={column.key} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                <div className="mb-3 flex items-center justify-between">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{column.label}</p>
                                    <span className="text-[10px] font-black text-slate-400">{column.items.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {column.items.map((item: any) => (
                                        <div key={item.id} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                                            <p className="text-xs font-black text-slate-800 dark:text-slate-100">{item.title}</p>
                                            <p className="text-[10px] text-slate-400">{item.meta}</p>
                                        </div>
                                    ))}
                                    {column.items.length === 0 && <div className="py-5 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">Vacío</div>}
                                </div>
                            </div>
                        ))}
                    </section>
                )}

                {viewType === 'calendar' && (
                    <section className="space-y-4">
                        {groupedByDate.map(([date, items]) => (
                            <div key={date} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                                <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{date}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {items.map((submission) => (
                                        <div key={`cal-${submission.id}`} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                                            <p className="text-sm font-black text-slate-900 dark:text-white">{submission.student_name}</p>
                                            <p className="text-[10px] text-slate-400">{submission.lesson_title}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                        {groupedByDate.length === 0 && <div className="py-10 text-center text-slate-400 text-sm">Sin agenda de entregas</div>}
                    </section>
                )}

                {viewType === 'gantt' && (
                    <section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Pipeline de revisión docente</p>
                        {submissions.map((submission) => {
                            const progress = submission.grade == null ? 55 : 100;
                            return (
                                <div key={`gantt-${submission.id}`} className="space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                        <span className="font-bold text-slate-700 dark:text-slate-300">{submission.student_name} · {submission.lesson_title}</span>
                                        <span className="font-black text-slate-400">{progress}%</span>
                                    </div>
                                    <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                        <div className={clsx('h-full', submission.grade == null ? 'bg-amber-500' : 'bg-emerald-500')} style={{ width: `${progress}%` }} />
                                    </div>
                                </div>
                            );
                        })}
                        {submissions.length === 0 && <div className="py-8 text-center text-slate-400 text-sm">Sin entregas para trazar</div>}
                    </section>
                )}

                {viewType === 'wiki' && (
                    <section className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki docente</p>
                        <textarea
                            value={wikiNotes}
                            onChange={(e) => setWikiNotes(e.target.value)}
                            placeholder="Documenta rúbricas, criterios de aprobación, política de feedback y tiempos de respuesta..."
                            className="w-full min-h-[340px] rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20"
                        />
                    </section>
                )}

                 {viewType === 'grid' && (
                 <section className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl">
                     <header className="flex flex-col lg:flex-row lg:items-center lg:justify-between px-6 py-5 border-b border-slate-100 dark:border-white/5 gap-3">
                         <div>
                             <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Flujo de revisiones</p>
                             <h2 className="text-2xl font-black text-slate-800 dark:text-white">Entregas de estudiantes</h2>
                         </div>
                        <div className="flex items-center gap-3">
                            <div className="rounded-2xl bg-slate-900/5 dark:bg-white/5 border border-slate-200 dark:border-white/10 p-1 flex gap-1">    
                                {[
                                    { id: 'courses', label: 'Mis Cursos' },
                                    { id: 'pending', label: 'Pendientes' },
                                    { id: 'history', label: 'Historial' },
                                ].map((option) => (
                                    <button
                                        key={option.id}
                                        onClick={() => setViewMode(option.id as any)}
                                        className={`px-3 py-1.5 rounded-xl text-[11px] font-black uppercase tracking-[0.3em] ${
                                            viewMode === option.id ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white' : 'text-slate-400'     
                                        }`}
                                    >
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={loadData}
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

                        {viewMode === 'courses' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 p-6 gap-6">
                                {courses.length === 0 && !loading && (
                                    <div className="col-span-full py-12 text-center text-slate-500">
                                        No tienes cursos asignados actualmente.
                                    </div>
                                )}
                                {courses.map(course => (
                                    <div key={course.id} className="p-6 rounded-[2rem] border border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 group hover:border-blue-500 transition-all">
                                        <div className="flex justify-between items-start mb-4">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-blue-500">{course.code}</span>
                                            <span className="px-2 py-1 bg-white dark:bg-slate-900 rounded-lg text-[9px] font-black uppercase tracking-widest text-slate-400 border border-slate-100 dark:border-white/5">{course.modality}</span>
                                        </div>
                                        <h4 className="text-xl font-black text-slate-800 dark:text-white mb-2">{course.title}</h4>
                                        <div className="flex items-center gap-4 mb-6">
                                            <div className="flex items-center gap-1.5 text-slate-500 text-xs">
                                                <Users size={14} /> {course.students_count || 0}
                                            </div>
                                            <div className="flex items-center gap-1.5 text-slate-500 text-xs">
                                                <BookOpen size={14} /> {course.lessons_count || 0}
                                            </div>
                                        </div>
                                        <button 
                                            onClick={() => router.push(`/academy/courses/${course.id}/manage`)}
                                            className="w-full py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 group-hover:bg-blue-600 group-hover:text-white group-hover:border-blue-600 transition-all"
                                        >
                                            Gestionar Curso
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {!loading && viewMode === 'pending' && pending.length === 0 && (                            <div className="px-6 py-12 text-center text-slate-500 text-sm">
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
                )}

                {viewType === 'grid' && graded.length > 0 && (
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


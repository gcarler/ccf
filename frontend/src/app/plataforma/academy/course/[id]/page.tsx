"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    BookOpen,
    CheckCircle2,
    PlayCircle,
    FileText,
    Clock,
    Award,
    GraduationCap,
    HelpCircle,
    Sparkles,
    Share2,
    MoreHorizontal
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import VideoPlayer from '@/components/academy/VideoPlayer';
import Skeleton from '@/components/ui/Skeleton';
import Tooltip from '@/components/ui/Tooltip';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface Lesson {
    id: string;
    title: string;
    content: string;
    content_type?: string;
    media_url?: string;
    order_index: number;
    duration_minutes: number;
    is_completed?: boolean;
}

interface Course {
    id: string;
    title: string;
    description: string;
    lessons: Lesson[];
}

export default function CourseViewPage() {
    const params = useParams();
    const id = (params?.id as string) ?? '';
    const { token } = useAuth();
    const router = useRouter();
    const { pushSidebarPanel } = useSidebarLayers();
    const [course, setCourse] = useState<Course | null>(null);
    const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
    const [loading, setLoading] = useState(true);
    const [progress] = useState<any>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchCourseData = useCallback(async () => {
        if (!token || !id) return;
        try {
            const data = await apiFetch<Course>(`/academy/courses/${id}`, { token });
            setCourse(data);
            if (data.lessons?.length) {
                const uncompleted = data.lessons.find((lesson: Lesson) => !lesson.is_completed);
                setActiveLesson(uncompleted || data.lessons[0]);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [id, token]);

    useEffect(() => {
        fetchCourseData();
    }, [fetchCourseData]);

    const handleVideoProgress = async (percent: number, currentTime: number) => {
        if (Math.floor(percent) % 5 !== 0) return;

        try {
            await apiFetch(`/academy/lessons/${activeLesson?.id}/progress`, {
                method: 'POST',
                token,
                body: { progress_percent: percent, last_position_seconds: Math.floor(currentTime) }
            });
        } catch (err) {
            console.error(err);
        }
    };

    const handleLessonComplete = async () => {
        if (!token || !activeLesson) return;

        try {
            await apiFetch(`/academy/lessons/${activeLesson.id}/progress`, {
                method: 'POST',
                token,
                body: { progress_percent: 100, last_position_seconds: 0 }
            });
            setCourse((prev) => prev ? {
                ...prev,
                lessons: prev.lessons.map((lesson) => (
                    lesson.id === activeLesson.id ? { ...lesson, is_completed: true } : lesson
                ))
            } : null);
        } catch (err) {
            console.error(err);
        }
    };

    const completionRate = course ? Math.round((course.lessons.filter((lesson) => lesson.is_completed).length / course.lessons.length) * 100) : 0;

    useEffect(() => {
        if (!course) return;

        pushSidebarPanel({
            id: `course-curriculum-${course.id}`,
            title: course.title,
            onBack: () => router.push('/plataforma/academy'),
            content: (
                <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-transparent">
                    <div className="p-4 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Tu Avance</h3>
                            <span className="font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{completionRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                            <motion.div initial={{ width: 0 }} animate={{ width: `${completionRate}%` }} className="h-full bg-[hsl(var(--primary))] shadow-sm" />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto px-2 pb-10 space-y-1">
                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4 mb-2">Contenido del Curso</p>
                        {course.lessons
                            .slice()
                            .sort((a, b) => a.order_index - b.order_index)
                            .map((lesson, idx) => {
                                const isActive = activeLesson?.id === lesson.id;
                                const isCompleted = lesson.is_completed;

                                return (
                                    <button
                                        key={lesson.id}
                                        onClick={() => setActiveLesson(lesson)}
                                        className={clsx(
                                            "w-full text-left px-4 py-1.5 rounded-lg transition-all group flex items-start gap-3.5",
                                            isActive
                                                ? "bg-blue-600/10 dark:bg-blue-500/10 border border-blue-100/50 dark:border-white/5"
                                                : "hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] border border-transparent"
                                        )}
                                    >
                                        <div
                                            className={clsx(
                                                "size-9 rounded-md flex items-center justify-center shrink-0 border transition-all",
                                                isCompleted
                                                    ? "bg-emerald-500 border-emerald-500 text-white"
                                                    : isActive
                                                        ? "bg-[hsl(var(--primary))] border-blue-600 text-white"
                                                        : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/5 text-[hsl(var(--text-secondary))]"
                                            )}
                                        >
                                            {isCompleted ? <CheckCircle2 size={16} /> : (isActive ? <PlayCircle size={16} /> : <span className="font-semibold">{idx + 1}</span>)}
                                        </div>
                                        <div className="min-w-0">
                                            <p className={clsx("font-semibold leading-tight mb-1", isActive ? "text-[hsl(var(--text-primary))] dark:text-white" : "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]")}>{lesson.title}</p>
                                            <div className="flex items-center gap-2 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                <Clock size={10} /> {lesson.duration_minutes} min
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                    </div>
                </div>
            )
        });
    }, [activeLesson, course, pushSidebarPanel, router]);

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden">
                <WorkspaceToolbar breadcrumbs={[{ label: 'Cargando curso...', icon: GraduationCap }]} />
                <div className="flex-1 flex">
                    <aside className="w-80 lg:w-96 border-r border-[hsl(var(--border))] dark:border-white/5 p-4 space-y-4"><Skeleton className="h-4 w-1/2" /><Skeleton className="h-8 w-full rounded-lg" /><Skeleton className="h-8 w-full rounded-lg" /></aside>
                    <main className="flex-1 p-4 space-y-3"><Skeleton className="aspect-video w-full rounded-lg" /><Skeleton className="h-10 w-1/2" /><Skeleton className="h-32 w-full rounded-lg" /></main>
                </div>
            </div>
        );
    }

    if (!course) return <div className="p-3 text-center font-semibold uppercase text-[hsl(var(--text-secondary))] tracking-wide">Curso no encontrado.</div>;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden font-display no-scrollbar">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Academia', icon: GraduationCap }, { label: course.title, icon: BookOpen }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki']}
                rightActions={
                    <div className="flex items-center gap-2">
                        <Tooltip content="Compartir curso"><button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"><Share2 size={18} /></button></Tooltip>
                        <Tooltip content="Ayuda"><button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"><HelpCircle size={18} /></button></Tooltip>
                        <div className="w-[1px] h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-2" />
                        <button onClick={() => router.push('/plataforma/academy')} className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 hover:bg-[hsl(var(--surface-3))] rounded-md text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] transition-all active:scale-95">Salir</button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] relative no-scrollbar">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f003_0%,_transparent_50%)] pointer-events-none" />

                {viewType === 'list' && (
 <section className="w-full p-4 lg:p-4 space-y-4">
                        {course.lessons.map((lesson) => (
                            <button key={lesson.id} onClick={() => setActiveLesson(lesson)} className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/10 p-4 text-left bg-[hsl(var(--bg-primary))] dark:bg-white/5 hover:border-blue-300 transition-all">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Lección {lesson.order_index}</p>
                                        <h3 className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{lesson.title}</h3>
                                    </div>
                                    <span className="text-xs font-bold text-[hsl(var(--text-secondary))]">{lesson.duration_minutes} min</span>
                                </div>
                            </button>
                        ))}
                    </section>
                )}

                {viewType === 'table' && (
 <section className="w-full p-4 lg:p-4">
                        <div className="overflow-x-auto rounded-md border border-[hsl(var(--border))] dark:border-white/10">
                            <table className="w-full text-left min-w-[480px]">
                                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <tr>
                                        <th className="px-4 py-2">Orden</th>
                                        <th className="px-4 py-2">Lección</th>
                                        <th className="px-4 py-2">Tipo</th>
                                        <th className="px-4 py-2">Duración</th>
                                        <th className="px-4 py-2">Estado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {course.lessons.map((lesson) => (
                                        <tr key={lesson.id} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                                            <td className="px-4 py-2 font-bold text-[hsl(var(--text-secondary))]">{lesson.order_index}</td>
                                            <td className="px-4 py-2 font-bold text-[hsl(var(--text-primary))] dark:text-white">{lesson.title}</td>
                                            <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{lesson.content_type || 'video'}</td>
                                            <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{lesson.duration_minutes} min</td>
                                            <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{lesson.is_completed ? 'Completada' : 'Pendiente'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}

                {(viewType === 'board' || viewType === 'kanban') && (
 <section className="w-full p-4 lg:p-4 grid gap-4 md:grid-cols-3">
                        {['Pendiente', 'En curso', 'Completada'].map((status) => {
                            const lessons = course.lessons.filter((lesson) => (
                                status === 'Completada' ? lesson.is_completed : status === 'En curso' ? lesson.id === activeLesson?.id && !lesson.is_completed : !lesson.is_completed && lesson.id !== activeLesson?.id
                            ));
                            return (
                                <div key={status} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))]/70 dark:bg-white/5 p-3">
                                    <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{status}</h3>
                                    <div className="space-y-3">
                                        {lessons.map((lesson) => (
                                            <button key={lesson.id} onClick={() => setActiveLesson(lesson)} className="w-full rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-black/20 p-4 text-left shadow-sm">
                                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{lesson.title}</p>
                                                <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{lesson.duration_minutes} min</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </section>
                )}

                {viewType === 'calendar' && (
                    <section className="h-full p-4">
                        <UniversalCalendarView
                            title="Calendario del curso"
                            events={course.lessons.map((lesson, index) => ({
                                id: lesson.id,
                                title: lesson.title,
                                date: new Date(Date.now() + index * 86400000).toISOString().slice(0, 10),
                                color: lesson.is_completed ? 'emerald' : 'blue'
                            }))}
                        />
                    </section>
                )}

                {viewType === 'gantt' && (
                    <section className="h-full p-4">
                        <UniversalGanttView
                            moduleName="Lecciones"
                            items={course.lessons.map((lesson, index) => {
                                const start = new Date(Date.now() + index * 86400000);
                                const end = new Date(start.getTime() + Math.max(lesson.duration_minutes, 30) * 60000);
                                return {
                                    id: lesson.id,
                                    title: lesson.title,
                                    subtitle: lesson.content_type || 'video',
                                    start_date: start.toISOString(),
                                    end_date: end.toISOString(),
                                    progress: lesson.is_completed ? 100 : 0,
                                    color: lesson.is_completed ? 'emerald' : 'blue'
                                };
                            })}
                        />
                    </section>
                )}

                {viewType === 'wiki' && (
                    <section className="p-4">
                        <UniversalWikiView moduleName={course.title} storageKey={`academy_course_${course.id}_wiki`} />
                    </section>
                )}

                {viewType === 'grid' && (
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeLesson?.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
 className="w-full p-4 lg:p-4 lg:pt-8 space-y-3 pb-4"
                    >
                        <div className="relative group/player rounded-lg overflow-hidden shadow-[var(--shadow-floating)] border border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-2))] dark:bg-black aspect-video flex items-center justify-center">
                            {(!activeLesson?.content_type || activeLesson.content_type === 'video') && (
                                <>
                                    <VideoPlayer
                                        src={activeLesson?.media_url || "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"}
                                        onProgress={handleVideoProgress}
                                        onComplete={handleLessonComplete}
                                        initialTime={progress?.last_position_seconds || 0}
                                    />
                                    <div className="absolute top-4 left-6 flex gap-2">
                                        <div className="px-3 py-1 bg-white/10 backdrop-blur-md border border-white/20 rounded-full text-[9px] font-semibold uppercase tracking-wide text-white">4K ULTRA HD</div>
                                        <div className="px-3 py-1 bg-blue-600/80 backdrop-blur-md rounded-full text-[9px] font-semibold uppercase tracking-wide text-white flex items-center gap-1.5"><Sparkles size={10} /> Optimus Enhanced</div>
                                    </div>
                                </>
                            )}
                            {activeLesson?.content_type === 'pdf' && (
                                <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center bg-[hsl(var(--surface-1))] dark:bg-black space-y-3">
                                    <FileText size={64} className="text-[hsl(var(--destructive))]" />
                                    <div>
                                        <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">Documento PDF Adjunto</h3>
                                        <p className="text-[hsl(var(--text-secondary))] text-sm mt-2">Lee el documento para completar esta lección.</p>
                                    </div>
                                    <a href={activeLesson.media_url || "#"} target="_blank" rel="noopener noreferrer" className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md font-bold uppercase tracking-wide text-xs hover:bg-[hsl(var(--primary))] transition-colors">
                                        Abrir Documento
                                    </a>
                                </div>
                            )}
                            {activeLesson?.content_type === 'quiz' && (
                                <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center bg-[hsl(var(--surface-1))] dark:bg-black space-y-3">
                                    <HelpCircle size={64} className="text-[hsl(var(--primary))]" />
                                    <div>
                                        <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">Evaluación de Conocimiento</h3>
                                        <p className="text-[hsl(var(--text-secondary))] text-sm mt-2">Responde las preguntas para avanzar a la siguiente etapa.</p>
                                    </div>
                                    <button onClick={handleLessonComplete} className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md font-bold uppercase tracking-wide text-xs hover:bg-[hsl(var(--primary)/0.85)] transition-colors shadow-lg shadow-[hsl(var(--primary)/0.3)]">
                                        Comenzar Cuestionario
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="space-y-4">
                            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                                <div className="space-y-3 max-w-2xl">
                                    <div className="flex items-center gap-3">
                                        <span className="font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-lg uppercase tracking-wide">Lección {activeLesson?.order_index}</span>
                                        <div className="size-1 rounded-full bg-[hsl(var(--surface-2))]" />
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{activeLesson?.duration_minutes} Minutos de contenido</span>
                                    </div>
                                    <h2 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">
                                        {activeLesson?.title}
                                    </h2>
                                </div>
                                <div className="flex items-center gap-3 shrink-0">
                                    <button className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all border border-[hsl(var(--border))] dark:border-white/5"><MoreHorizontal size={20} /></button>
                                    <button
                                        onClick={handleLessonComplete}
                                        disabled={activeLesson?.is_completed}
                                        className={clsx(
                                            "px-3 py-2 rounded-lg font-black text-[11px] uppercase tracking-wide transition-all active:scale-95 flex items-center gap-3 shadow-xl",
                                            activeLesson?.is_completed
                                                ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 cursor-not-allowed"
                                                : "bg-[hsl(var(--primary))] text-white shadow-blue-500/20 hover:scale-[1.02]"
                                        )}
                                    >
                                        {activeLesson?.is_completed ? 'Lección Completada' : 'Finalizar Lección'} <CheckCircle2 size={18} />
                                    </button>
                                </div>
                            </div>

                            <div className="prose prose-slate dark:prose-invert max-w-none">
                                <div className="p-3 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                                    {activeLesson?.content.split('\n').map((paragraph, index) => (
                                        <p key={index} className="mb-3 last:mb-0">{paragraph}</p>
                                    ))}
                                </div>
                            </div>

                            <section className="p-4 rounded-lg bg-gradient-to-br from-[hsl(var(--bg-muted))] to-[#1e1f21] border border-white/5 text-white flex flex-col md:flex-row items-center justify-between gap-4 group">
                                <div className="flex items-center gap-4">
                                    <div className="size-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-[hsl(var(--primary))] shadow-2xl group-hover:scale-110 transition-transform">
                                        <Award size={32} />
                                    </div>
                                    <div>
                                        <h4 className="text-base font-bold tracking-tight">Hito de Conocimiento</h4>
                                        <p className="text-[hsl(var(--text-secondary))] text-sm font-medium">Al completar esta lección, recibirás +10 XP para tu perfil pastoral.</p>
                                    </div>
                                </div>
                                <div className="flex -space-x-3">
                                    {[1, 2, 3].map((item) => <div key={item} className="size-8 rounded-full border-2 border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-center justify-center text-[10px] font-bold text-[hsl(var(--text-secondary))]">JD</div>)}
                                    <div className="size-8 rounded-full border-2 border-[hsl(var(--border))] bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-white">+12</div>
                                </div>
                            </section>
                        </div>
                    </motion.div>
                </AnimatePresence>
                )}
            </main>
        </div>
    );
}

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
    ChevronLeft,
    Layout,
    GraduationCap,
    HelpCircle,
    ChevronRight,
    Lock,
    Sparkles,
    Zap,
    Share2,
    MoreHorizontal
} from 'lucide-react';
import Link from 'next/link';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import VideoPlayer from '@/components/academy/VideoPlayer';
import Skeleton from '@/components/ui/Skeleton';
import Tooltip from '@/components/ui/Tooltip';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface Lesson {
    id: number;
    title: string;
    content: string;
    content_type?: string;
    media_url?: string;
    order_index: number;
    duration_minutes: number;
    is_completed?: boolean;
}

interface Course {
    id: number;
    title: string;
    description: string;
    lessons: Lesson[];
}

export default function CourseViewPage() {
    const params = useParams();
    const id = (params?.id as string) ?? '';
    const { token, user } = useAuth();
    const router = useRouter();
    const [course, setCourse] = useState<Course | null>(null);
    const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
    const [loading, setLoading] = useState(true);
    const [progress, setProgress] = useState<any>(null);

    const fetchCourseData = useCallback(async () => {
        if (!token || !id) return;
        try {
            const data = await apiFetch<Course>(`/academy/courses/${id}`, { token });
            setCourse(data);
            if (data && data.lessons && data.lessons.length > 0) {
                const uncompleted = data.lessons.find((l: Lesson) => !l.is_completed);
                setActiveLesson(uncompleted || data.lessons[0]);
            }
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    }, [id, token]);

    useEffect(() => { fetchCourseData(); }, [fetchCourseData]);

    const handleVideoProgress = async (percent: number, currentTime: number) => {
        if (Math.floor(percent) % 5 === 0) {
            try {
                await apiFetch(`/academy/lessons/${activeLesson?.id}/progress`, {
                    method: 'POST', token, body: { progress_percent: percent, last_position_seconds: Math.floor(currentTime) }
                });
            } catch (err) { console.error(err); }
        }
    };

    const handleLessonComplete = async () => {
        if (!token || !activeLesson) return;
        try {
            await apiFetch(`/academy/lessons/${activeLesson.id}/progress`, { method: 'POST', token, body: { progress_percent: 100, last_position_seconds: 0 } });
            setCourse(prev => prev ? { ...prev, lessons: prev.lessons.map(l => l.id === activeLesson.id ? { ...l, is_completed: true } : l) } : null);
        } catch (err) { console.error(err); }
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
                <WorkspaceToolbar breadcrumbs={[{ label: 'Cargando curso...', icon: GraduationCap }]} viewType="grid" setViewType={() => {}} />
                <div className="flex-1 flex">
                    <aside className="w-80 lg:w-96 border-r border-slate-100 dark:border-white/5 p-6 space-y-4"><Skeleton className="h-4 w-1/2" /><Skeleton className="h-12 w-full rounded-2xl" /><Skeleton className="h-12 w-full rounded-2xl" /></aside>
                    <main className="flex-1 p-12 space-y-8"><Skeleton className="aspect-video w-full rounded-[3rem]" /><Skeleton className="h-10 w-1/2" /><Skeleton className="h-32 w-full rounded-2xl" /></main>
                </div>
            </div>
        );
    }

    if (!course) return <div className="p-10 text-center font-black uppercase text-slate-400 tracking-widest">Curso no encontrado.</div>;

    // ── Push Curriculum to Sidebar Stack ──────────────────────────────────────
    const { pushSidebarPanel } = useSidebarLayers();
    const completionRate = course ? Math.round((course.lessons.filter(l => l.is_completed).length / course.lessons.length) * 100) : 0;

    useEffect(() => {
        if (!course) return;

        pushSidebarPanel({
            id: `course-curriculum-${course.id}`,
            title: course.title,
            onBack: () => router.push('/academy'),
            content: (
                <div className="flex flex-col h-full bg-white dark:bg-transparent">
                    <div className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Tu Avance</h3>
                            <span className="text-[10px] font-black text-blue-600 dark:text-blue-400">{completionRate}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                            <motion.div initial={{ width: 0 }} animate={{ width: `${completionRate}%` }} className="h-full bg-blue-600 shadow-sm" />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto px-2 pb-10 space-y-1">
                        <p className="text-[9px] font-black text-slate-300 uppercase tracking-widest px-4 mb-2">Contenido del Curso</p>
                        {course.lessons.sort((a, b) => a.order_index - b.order_index).map((lesson, idx) => {
                            const isActive = activeLesson?.id === lesson.id;
                            const isCompleted = lesson.is_completed;
                            
                            return (
                                <button
                                    key={lesson.id} onClick={() => setActiveLesson(lesson)}
                                    className={clsx(
                                        "w-full text-left px-4 py-3.5 rounded-2xl transition-all group flex items-start gap-3.5",
                                        isActive 
                                            ? "bg-blue-600/10 dark:bg-blue-500/10 border border-blue-100/50 dark:border-white/5" 
                                            : "hover:bg-slate-50 dark:hover:bg-white/5 text-slate-500 border border-transparent"
                                    )}
                                >
                                    <div className={clsx(
                                        "size-9 rounded-xl flex items-center justify-center shrink-0 border transition-all",
                                        isCompleted ? "bg-emerald-500 border-emerald-500 text-white" : 
                                        (isActive ? "bg-blue-600 border-blue-600 text-white" : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 text-slate-400")
                                    )}>
                                        {isCompleted ? <CheckCircle2 size={16} /> : (isActive ? <PlayCircle size={16} /> : <span className="text-[10px] font-black">{idx + 1}</span>)}
                                    </div>
                                    <div className="min-w-0">
                                        <p className={clsx("text-[12px] font-black leading-tight mb-1", isActive ? "text-slate-900 dark:text-white" : "text-slate-600 dark:text-slate-400")}>{lesson.title}</p>
                                        <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-widest text-slate-400">
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
    }, [course, activeLesson, completionRate, pushSidebarPanel, router]);

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden p-12">
                <Skeleton className="h-10 w-1/3 mb-10 rounded-xl" />
                <div className="flex-1 space-y-8">
                    <Skeleton className="aspect-video w-full rounded-[3rem]" />
                    <Skeleton className="h-10 w-1/2 rounded-xl" />
                </div>
            </div>
        );
    }

    if (!course) return <div className="p-10 text-center font-black uppercase text-slate-400 tracking-widest">Curso no encontrado.</div>;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display no-scrollbar">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Academia', icon: GraduationCap }, { label: course.title, icon: BookOpen }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <div className="flex items-center gap-2">
                        <Tooltip content="Compartir curso"><button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><Share2 size={18} /></button></Tooltip>
                        <Tooltip content="Ayuda"><button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><HelpCircle size={18} /></button></Tooltip>
                        <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-2" />
                        <button onClick={() => router.push('/academy')} className="flex items-center gap-2 px-4 py-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all active:scale-95">Salir</button>
                    </div>
                }
            />

            {/* Content Main 3.0 */}
            <main className="flex-1 overflow-y-auto scrollbar-thin bg-white dark:bg-[#1e1f21] relative no-scrollbar">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f003_0%,_transparent_50%)] pointer-events-none" />
                
                <AnimatePresence mode="wait">
                    <motion.div 
                        key={activeLesson?.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                        className="max-w-5xl mx-auto p-8 lg:p-16 lg:pt-8 space-y-12 pb-32"
                    >
                        {/* Dynamic Content Player Container */}
                        <div className="relative group/player rounded-[3rem] overflow-hidden shadow-[var(--shadow-floating)] border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-black aspect-video flex items-center justify-center">
                            {(!activeLesson?.content_type || activeLesson.content_type === 'video') && (
                                <>
                                    <VideoPlayer 
                                        src={activeLesson?.media_url || "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"}
                                        onProgress={handleVideoProgress}
                                        onComplete={handleLessonComplete}
                                        initialTime={progress?.last_position_seconds || 0}
                                    />
                                    <div className="absolute top-6 left-6 flex gap-2">
                                        <div className="px-3 py-1 bg-white/10 backdrop-blur-md border border-white/20 rounded-full text-[9px] font-black uppercase tracking-[0.2em] text-white">4K ULTRA HD</div>
                                        <div className="px-3 py-1 bg-blue-600/80 backdrop-blur-md rounded-full text-[9px] font-black uppercase tracking-[0.2em] text-white flex items-center gap-1.5"><Sparkles size={10} /> Optimus Enhanced</div>
                                    </div>
                                </>
                            )}
                            {activeLesson?.content_type === 'pdf' && (
                                <div className="w-full h-full flex flex-col items-center justify-center p-12 text-center bg-slate-50 dark:bg-black space-y-6">
                                    <FileText size={64} className="text-red-500" />
                                    <div>
                                        <h3 className="text-xl font-black text-slate-800 dark:text-white">Documento PDF Adjunto</h3>
                                        <p className="text-slate-500 text-sm mt-2">Lee el documento para completar esta lección.</p>
                                    </div>
                                    <a href={activeLesson.media_url || "#"} target="_blank" rel="noreferrer" className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-blue-700 transition-colors">
                                        Abrir Documento
                                    </a>
                                </div>
                            )}
                            {activeLesson?.content_type === 'quiz' && (
                                <div className="w-full h-full flex flex-col items-center justify-center p-12 text-center bg-slate-50 dark:bg-black space-y-6">
                                    <HelpCircle size={64} className="text-indigo-500" />
                                    <div>
                                        <h3 className="text-xl font-black text-slate-800 dark:text-white">Evaluación de Conocimiento</h3>
                                        <p className="text-slate-500 text-sm mt-2">Responde las preguntas para avanzar a la siguiente etapa.</p>
                                    </div>
                                    <button onClick={handleLessonComplete} className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/30">
                                        Comenzar Cuestionario
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="space-y-10">
                            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
                                <div className="space-y-3 max-w-2xl">
                                    <div className="flex items-center gap-3">
                                        <span className="text-[10px] font-black text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-lg uppercase tracking-widest">Lección {activeLesson?.order_index}</span>
                                        <div className="size-1 rounded-full bg-slate-300" />
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{activeLesson?.duration_minutes} Minutos de contenido</span>
                                    </div>
                                    <h2 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">
                                        {activeLesson?.title}
                                    </h2>
                                </div>
                                <div className="flex items-center gap-3 shrink-0">
                                    <button className="p-3 bg-slate-50 dark:bg-white/5 rounded-2xl text-slate-400 hover:text-blue-600 transition-all border border-slate-100 dark:border-white/5"><MoreHorizontal size={20} /></button>
                                    <button 
                                        onClick={handleLessonComplete}
                                        disabled={activeLesson?.is_completed}
                                        className={clsx(
                                            "px-8 py-4 rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.2em] transition-all active:scale-95 flex items-center gap-3 shadow-xl",
                                            activeLesson?.is_completed 
                                                ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 cursor-not-allowed" 
                                                : "bg-blue-600 text-white shadow-blue-500/20 hover:scale-[1.02]"
                                        )}
                                    >
                                        {activeLesson?.is_completed ? 'Lección Completada' : 'Finalizar Lección'} <CheckCircle2 size={18} />
                                    </button>
                                </div>
                            </div>

                            <div className="prose prose-slate dark:prose-invert max-w-none">
                                <div className="p-10 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 text-lg text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {activeLesson?.content.split('\n').map((para, i) => (
                                        <p key={i} className="mb-6 last:mb-0">{para}</p>
                                    ))}
                                </div>
                            </div>

                            {/* Reward Preview Card */}
                            <section className="p-8 rounded-[3rem] bg-gradient-to-br from-slate-900 to-[#1e1f21] border border-white/5 text-white flex flex-col md:flex-row items-center justify-between gap-8 group">
                                <div className="flex items-center gap-6">
                                    <div className="size-16 rounded-[1.5rem] bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-2xl group-hover:scale-110 transition-transform">
                                        <Award size={32} />
                                    </div>
                                    <div>
                                        <h4 className="text-xl font-black tracking-tight">Hito de Conocimiento</h4>
                                        <p className="text-slate-400 text-sm font-medium">Al completar esta lección, recibirás +10 XP para tu perfil pastoral.</p>
                                    </div>
                                </div>
                                <div className="flex -space-x-3">
                                    {[1,2,3].map(i => <div key={i} className="size-10 rounded-full border-2 border-slate-900 bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400">JD</div>)}
                                    <div className="size-10 rounded-full border-2 border-slate-900 bg-blue-600 flex items-center justify-center text-[10px] font-black text-white">+12</div>
                                </div>
                            </section>
                        </div>
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
}

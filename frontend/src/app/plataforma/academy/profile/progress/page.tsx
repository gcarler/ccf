"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import { apiFetch } from '@/lib/http';
import { 
    GraduationCap, 
    Award, 
    BookOpen, 
    CheckCircle2, 
    Clock, 
    Trophy, 
    Star, 
    ArrowRight,
    Search,
    BarChart3
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion } from 'framer-motion';

interface CourseProgress {
    id: number;
    title: string;
    progress_percent: number;
    status: string;
    average_grade: number;
    lessons_completed: number;
    total_lessons: number;
    last_activity: string;
    certificate_issued: boolean;
}

export default function StudentProgressPage() {
    const router = useRouter();
    const { token, user, isAuthenticated } = useAuth();
    const [progress, setProgress] = useState<CourseProgress[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [stats, setStats] = useState({
        total_courses: 0,
        completed_courses: 0,
        average_grade: 0,
        certificates: 0
    });

    useEffect(() => {
        if (!token || !isAuthenticated) return;
        const loadData = async () => {
            try {
                setLoading(true);
                // Simulamos una carga suave para la animación
                await new Promise(r => setTimeout(r, 600));
                const data = await apiFetch<CourseProgress[]>(`/academy/users/${user?.id}/progress`, { token });
                const arr = Array.isArray(data) ? data : [];
                setProgress(arr);
                
                // Calculate basic stats
                const completed = arr.filter(c => c.status === 'completed').length;
                const avg = arr.length > 0 ? arr.reduce((acc, curr) => acc + curr.average_grade, 0) / arr.length : 0;
                const certs = arr.filter(c => c.certificate_issued).length;

                setStats({
                    total_courses: arr.length,
                    completed_courses: completed,
                    average_grade: avg,
                    certificates: certs
                });
            } catch (err) {
                console.error(err);
                toast.error('No pudimos cargar tu progreso académico');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [token, isAuthenticated, user?.id]);

    if (!isAuthenticated) return null;

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden font-sans relative">
            {/* Ambient Background Glows */}
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-sky-600/5 rounded-full blur-[100px] pointer-events-none" />

            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/plataforma/academy' },
                    { label: 'Mi Progreso', icon: BarChart3 },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table', 'calendar', 'gantt']}
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-3 relative z-10">
                {viewType === 'calendar' && (
                    <UniversalCalendarView
                        title="Actividad académica"
                        events={progress.map((course) => ({
                            id: course.id,
                            title: course.title,
                            date: new Date(course.last_activity).toISOString().slice(0, 10),
                            color: course.status === 'completed' ? 'emerald' : 'blue'
                        }))}
                    />
                )}
                {viewType === 'gantt' && (
                    <UniversalGanttView
                        moduleName="Progreso académico"
                        items={progress.map((course) => ({
                            id: course.id,
                            title: course.title,
                            subtitle: course.status,
                            start_date: course.last_activity,
                            end_date: new Date(new Date(course.last_activity).getTime() + 86400000).toISOString(),
                            progress: course.progress_percent,
                            color: course.status === 'completed' ? 'emerald' : 'blue'
                        }))}
                    />
                )}
                {viewType === 'table' && (
                    <div className="overflow-hidden rounded-md border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                <tr><th className="px-4 py-2">Curso</th><th className="px-4 py-2">Estado</th><th className="px-4 py-2">Progreso</th><th className="px-4 py-2">Nota</th></tr>
                            </thead>
                            <tbody>
                                {progress.map((course) => (
                                    <tr key={course.id} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-4 py-2 font-bold text-slate-900 dark:text-white">{course.title}</td>
                                        <td className="px-4 py-2 text-slate-500">{course.status}</td>
                                        <td className="px-4 py-2 text-slate-500">{course.progress_percent}%</td>
                                        <td className="px-4 py-2 text-slate-500">{course.average_grade.toFixed(1)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {viewType === 'list' && (
                    <div className="space-y-2">
                        {progress.map((course) => (
                            <article key={course.id} className="rounded-md border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{course.title}</h3>
                                        <p className="mt-2 text-sm text-slate-500">{course.lessons_completed}/{course.total_lessons} lecciones</p>
                                    </div>
                                    <span className="text-sm font-semibold text-blue-600">{course.progress_percent}%</span>
                                </div>
                            </article>
                        ))}
                    </div>
                )}
                {viewType === 'grid' && (
                <motion.div 
                    variants={containerVariants}
                    initial="hidden"
                    animate="show"
 className="w-full space-y-3"
                >
                    {/* Hero Section Premium */}
                    <motion.section variants={itemVariants} className="relative rounded-lg bg-[#001b48] overflow-hidden group border border-white/10 shadow-2xl">
                        <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-[0.05] mix-blend-overlay" />
                        <div className="absolute top-[-50%] right-[-10%] w-[80%] h-[200%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-400/20 via-blue-900/10 to-transparent blur-3xl pointer-events-none" />
                        
                        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between p-4 lg:p-4 gap-4">
                            <div className="space-y-3 max-w-xl">
                                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl rounded-full text-[10px] font-semibold uppercase tracking-wide text-blue-100 border border-white/10">
                                    <Trophy size={14} className="text-amber-400" /> Rendimiento Académico
                                </div>
                                <h1 className="text-xl lg:text-xl font-bold text-white tracking-tighter leading-[0.9] mb-4">
                                    Tu camino <br /> al <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-blue-500">Propósito.</span>
                                </h1>
                                <p className="text-blue-100/60 text-sm font-medium leading-relaxed">
                                    Estás en el nivel <strong>{Math.floor(stats.average_grade / 10)}</strong>. Tu constancia está dando frutos, continúa así.
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 lg:w-[400px]">
                                <HeaderStat label="Promedio" value={stats.average_grade.toFixed(1)} icon={Star} color="text-amber-400" bg="bg-amber-400/20" />
                                <HeaderStat label="Certificados" value={stats.certificates} icon={Award} color="text-emerald-400" bg="bg-emerald-400/20" />
                                <HeaderStat label="Pendientes" value={stats.total_courses - stats.completed_courses} icon={BookOpen} color="text-blue-400" bg="bg-blue-400/20" />
                                <HeaderStat label="Logros" value={stats.completed_courses} icon={CheckCircle2} color="text-sky-400" bg="bg-sky-400/20" />
                            </div>
                        </div>
                    </motion.section>

                    {/* Courses Progress List */}
                    <motion.section variants={itemVariants} className="space-y-3">
                        <div className="flex items-end justify-between px-4">
                            <div>
                                <h2 className="text-xl font-bold text-slate-800 dark:text-white tracking-tight">Detalle por Curso</h2>
                                <p className="text-slate-500 font-medium">Desglose de notas y asistencia de tus inscripciones.</p>
                            </div>
                            <div className="flex gap-2">
                                <button className="p-3 bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-lg shadow-sm"><Search size={18} className="text-slate-400" /></button>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-4">
                            {loading ? (
                                Array(3).fill(0).map((_, i) => (
                                    <div key={i} className="h-40 bg-slate-100 dark:bg-white/5 rounded-md animate-pulse" />
                                ))
                            ) : progress.length > 0 ? (
                                progress.map(course => (
                                    <div 
                                        key={course.id} 
                                        className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-lg p-4 lg:p-3 flex flex-col lg:flex-row lg:items-center justify-between gap-3 group hover:border-blue-500/30 hover:shadow-2xl hover:shadow-blue-500/5 transition-all duration-500"
                                    >
                                        <div className="flex-1 space-y-4">
                                            <div className="flex items-center gap-3">
                                                <span className={clsx(
                                                    "px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide",
                                                    course.status === 'completed' ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
                                                )}>
                                                    {course.status === 'completed' ? 'Completado' : 'En Curso'}
                                                </span>
                                                <span className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-1.5">
                                                    <BookOpen size={12} /> {course.lessons_completed} / {course.total_lessons} Lecciones
                                                </span>
                                            </div>
                                            <h3 className="text-xl font-bold text-slate-800 dark:text-white group-hover:text-blue-600 transition-colors leading-none tracking-tight">{course.title}</h3>
                                            <div className="flex items-center gap-4">
                                                <div className="flex items-center gap-2 text-slate-500">
                                                    <Clock size={14} strokeWidth={2.5} />
                                                    <span className="text-xs font-bold">Activo: {new Date(course.last_activity).toLocaleDateString()}</span>
                                                </div>
                                                {course.certificate_issued && (
                                                    <div className="flex items-center gap-2 text-amber-500 bg-amber-500/10 px-3 py-1 rounded-full">
                                                        <Award size={14} strokeWidth={2.5} />
                                                        <span className="text-[10px] font-semibold uppercase tracking-wide">Certificado Disponible</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="w-full lg:w-[400px] flex flex-col md:flex-row items-center gap-3">
                                            <div className="flex-1 w-full space-y-4">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Progreso General</span>
                                                    <span className="text-sm font-semibold text-slate-800 dark:text-white">{course.progress_percent}%</span>
                                                </div>
                                                <div className="h-3 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden p-0.5">
                                                    <motion.div 
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${course.progress_percent}%` }}
                                                        className={clsx(
                                                            "h-full rounded-full transition-all duration-1000 shadow-inner",
                                                            course.progress_percent === 100 ? "bg-emerald-500 shadow-emerald-500/20" : "bg-gradient-to-r from-blue-600 to-blue-400 shadow-blue-500/20"
                                                        )}
                                                    />
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-4 md:border-l border-slate-100 dark:border-white/5 md:pl-8 shrink-0">
                                                <div className="text-center">
                                                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Nota</p>
                                                    <p className={clsx("text-xl font-bold tracking-tighter", course.average_grade >= 70 ? "text-emerald-500" : "text-rose-500")}>
                                                        {course.average_grade.toFixed(1)}
                                                    </p>
                                                </div>
                                                <button 
                                                    onClick={() => router.push(`/academy/course/${course.id}`)}
                                                    className="size-7 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-xl shadow-slate-900/10"
                                                >
                                                    <ArrowRight size={24} strokeWidth={3} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="bg-white dark:bg-[#15171c] rounded-lg p-4 text-center space-y-3 border border-slate-100 dark:border-white/5 shadow-inner">
                                    <div className="size-10 bg-slate-100 dark:bg-white/5 rounded-md flex items-center justify-center mx-auto text-slate-300">
                                        <BookOpen size={48} />
                                    </div>
                                    <div className="max-w-md mx-auto space-y-4">
                                        <h3 className="text-lg font-bold text-slate-800 dark:text-white">Aún no tienes progreso registrado</h3>
                                        <p className="text-slate-500 font-medium">Inscríbete en un curso de nuestro catálogo para comenzar tu formación espiritual hoy mismo.</p>
                                        <button onClick={() => router.push('/academy')} className="mt-3 px-3 py-2 bg-blue-600 text-white rounded-md font-black text-xs uppercase tracking-wide shadow-2xl shadow-blue-500/30 hover:scale-105 transition-all">Explorar Catálogo</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </motion.section>
                </motion.div>
                )}
            </main>
        </div>
    );
}

function HeaderStat({ label, value, icon: Icon, color, bg }: any) {
    return (
        <div className="p-4 bg-white/5 backdrop-blur-2xl rounded-md border border-white/10 flex items-center gap-3 group hover:bg-white/10 transition-all cursor-default">
            <div className={clsx('size-9 rounded-lg flex items-center justify-center shadow-inner transition-transform group-hover:scale-110', bg, color)}>
                <Icon size={22} strokeWidth={2.5} />
            </div>
            <div>
                <p className="font-semibold text-blue-200/50 uppercase tracking-wide mb-1 leading-none">{label}</p>
                <p className="text-xl font-bold text-white tracking-tighter leading-none">{value}</p>
            </div>
        </div>
    );
}


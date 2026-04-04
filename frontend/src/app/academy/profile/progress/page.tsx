"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import { 
    GraduationCap, 
    Award, 
    BookOpen, 
    CheckCircle2, 
    Clock, 
    Trophy, 
    Star, 
    Calendar,
    ArrowRight,
    Search,
    ChevronRight,
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

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Mi Progreso', icon: BarChart3 },
                ]}
                viewType="grid"
                setViewType={() => {}}
            />

            <main className="flex-1 overflow-y-auto p-6 lg:p-10 space-y-10">
                {/* Header Section */}
                <section className="relative rounded-[3.5rem] bg-slate-900 overflow-hidden p-10 lg:p-14 text-white">
                    <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-blue-600/20 to-transparent pointer-events-none" />
                    <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-10">
                        <div className="space-y-4">
                            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl rounded-full text-[10px] font-black uppercase tracking-[0.3em] text-blue-100 border border-white/10">
                                <Trophy size={14} className="text-amber-400" /> Rendimiento Académico
                            </div>
                            <h1 className="text-5xl font-black tracking-tighter leading-none">
                                Tu camino <br /> al <span className="text-blue-400">Propósito.</span>
                            </h1>
                            <p className="text-slate-400 text-lg max-w-lg">
                                Estás en el nivel <strong>{Math.floor(stats.average_grade / 10)}</strong>. Sigue completando lecciones para obtener tu próximo certificado.
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <HeaderStat label="Promedio General" value={stats.average_grade.toFixed(1)} icon={Star} color="text-amber-400" />
                            <HeaderStat label="Certificados" value={stats.certificates} icon={Award} color="text-emerald-400" />
                            <HeaderStat label="Cursos Activos" value={stats.total_courses - stats.completed_courses} icon={BookOpen} color="text-blue-400" />
                            <HeaderStat label="Completados" value={stats.completed_courses} icon={CheckCircle2} color="text-purple-400" />
                        </div>
                    </div>
                </section>

                {/* Courses Progress List */}
                <section className="space-y-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">Detalle por Curso</h2>
                            <p className="text-slate-500 text-sm">Desglose de notas y asistencia de tus inscripciones.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                        {loading ? (
                            Array(3).fill(0).map((_, i) => (
                                <div key={i} className="h-32 bg-slate-100 dark:bg-white/5 rounded-3xl animate-pulse" />
                            ))
                        ) : progress.length > 0 ? (
                            progress.map(course => (
                                <div 
                                    key={course.id} 
                                    className="bg-white dark:bg-[#15171c] border border-slate-200 dark:border-white/5 rounded-3xl p-6 lg:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-8 group hover:border-blue-500/30 transition-all shadow-sm"
                                >
                                    <div className="flex-1 space-y-3">
                                        <div className="flex items-center gap-3">
                                            <span className={clsx(
                                                "px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                                                course.status === 'completed' ? "bg-emerald-500/10 text-emerald-500" : "bg-blue-500/10 text-blue-500"
                                            )}>
                                                {course.status === 'completed' ? 'Completado' : 'En Curso'}
                                            </span>
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                                Lección {course.lessons_completed} de {course.total_lessons}
                                            </span>
                                        </div>
                                        <h3 className="text-2xl font-black text-slate-800 dark:text-white group-hover:text-blue-600 transition-colors">{course.title}</h3>
                                        <div className="flex items-center gap-6">
                                            <div className="flex items-center gap-2">
                                                <Clock size={14} className="text-slate-400" />
                                                <span className="text-xs font-bold text-slate-500">Activo: {new Date(course.last_activity).toLocaleDateString()}</span>
                                            </div>
                                            {course.certificate_issued && (
                                                <div className="flex items-center gap-2 text-emerald-500">
                                                    <Award size={14} />
                                                    <span className="text-xs font-black uppercase tracking-widest">Certificado Disponible</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="w-full lg:w-72 space-y-4">
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Progreso del Curso</span>
                                            <span className="text-sm font-black text-slate-800 dark:text-white">{course.progress_percent}%</span>
                                        </div>
                                        <div className="h-2 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                            <motion.div 
                                                initial={{ width: 0 }}
                                                animate={{ width: `${course.progress_percent}%` }}
                                                className={clsx(
                                                    "h-full rounded-full transition-all duration-1000",
                                                    course.progress_percent === 100 ? "bg-emerald-500" : "bg-blue-600"
                                                )}
                                            />
                                        </div>
                                        <div className="flex items-center justify-between pt-2">
                                            <div className="text-center flex-1">
                                                <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Nota Actual</p>
                                                <p className={clsx("text-lg font-black", course.average_grade >= 70 ? "text-emerald-500" : "text-rose-500")}>
                                                    {course.average_grade.toFixed(1)}
                                                </p>
                                            </div>
                                            <div className="w-px h-8 bg-slate-100 dark:border-white/5" />
                                            <div className="text-center flex-1">
                                                <button 
                                                    onClick={() => router.push(`/academy/course/${course.id}`)}
                                                    className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-blue-600 hover:gap-3 transition-all"
                                                >
                                                    Continuar <ArrowRight size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="bg-white dark:bg-[#15171c] rounded-[3rem] p-16 text-center space-y-6">
                                <div className="size-20 bg-slate-100 dark:bg-white/5 rounded-full flex items-center justify-center mx-auto text-slate-300">
                                    <BookOpen size={40} />
                                </div>
                                <div className="max-w-md mx-auto space-y-2">
                                    <h3 className="text-xl font-bold text-slate-800 dark:text-white">Aún no tienes progreso registrado</h3>
                                    <p className="text-slate-500">Inscríbete en un curso de nuestro catálogo para comenzar tu formación.</p>
                                    <button onClick={() => router.push('/academy')} className="mt-4 px-8 py-3 bg-blue-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl shadow-blue-500/20">Explorar Catálogo</button>
                                </div>
                            </div>
                        )}
                    </div>
                </section>
            </main>
        </div>
    );
}

function HeaderStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="p-5 bg-white/5 backdrop-blur-2xl rounded-[2rem] border border-white/10 flex items-center gap-4 group hover:bg-white/10 transition-all">
            <div className={clsx('size-10 rounded-xl flex items-center justify-center bg-white/10', color)}>
                <Icon size={20} strokeWidth={2.5} />
            </div>
            <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">{label}</p>
                <p className="text-xl font-black text-white tracking-tighter">{value}</p>
            </div>
        </div>
    );
}

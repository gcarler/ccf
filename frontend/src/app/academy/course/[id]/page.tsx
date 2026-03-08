"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ChevronLeft,
    BookOpen,
    CheckCircle2,
    PlayCircle,
    FileText,
    Clock,
    Award,
    LayoutDashboard
} from 'lucide-react';
import Link from 'next/link';

interface Lesson {
    id: number;
    title: string;
    content: string;
    order_index: number;
    duration_minutes: number;
}

interface Course {
    id: number;
    title: string;
    description: string;
    lessons: Lesson[];
}

export default function CourseViewPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    const [course, setCourse] = useState<Course | null>(null);
    const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated) return;

        const fetchCourse = async () => {
            try {
                const res = await fetch(`http://localhost:8001/courses/${id}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setCourse(data);

                    if (data.lessons && data.lessons.length > 0) {
                        setActiveLesson(data.lessons[0]);
                    }
                }
            } catch (err) {
                console.error("Error fetching course:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchCourse();
    }, [id, token, isAuthenticated]);

    if (!isAuthenticated) return null;
    if (loading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Cargando curso...</div>;
    if (!course) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">Curso no encontrado.</div>;

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row h-screen overflow-hidden">
            {/* Sidebar with Lessons */}
            <aside className="w-full md:w-80 lg:w-96 bg-slate-900 border-r border-white/10 flex flex-col h-full overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <Link href="/academy" className="flex items-center gap-2 text-primary text-sm font-bold mb-4 hover:underline">
                        <ChevronLeft size={16} /> Volver a la Academia
                    </Link>
                    <h1 className="text-xl font-black leading-tight">{course.title}</h1>
                    <div className="flex items-center gap-2 mt-2 text-slate-400 text-xs">
                        <BookOpen size={14} /> {course.lessons?.length || 0} lecciones
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                    {course.lessons?.sort((a, b) => a.order_index - b.order_index).map((lesson) => (
                        <button
                            key={lesson.id}
                            onClick={() => setActiveLesson(lesson)}
                            className={`w-full text-left p-4 rounded-2xl border transition-all duration-300 flex items-start gap-3 group ${activeLesson?.id === lesson.id
                                ? 'bg-primary/20 border-primary/40 text-white'
                                : 'bg-white/5 border-white/5 hover:border-white/10 text-slate-400'
                                }`}
                        >
                            <div className={`mt-0.5 p-1.5 rounded-lg ${activeLesson?.id === lesson.id ? 'bg-primary text-white' : 'bg-slate-800'
                                }`}>
                                <PlayCircle size={16} />
                            </div>
                            <div className="flex-1">
                                <p className="text-sm font-bold leading-snug">{lesson.title}</p>
                                <div className="flex items-center gap-3 mt-1 text-[10px] uppercase tracking-widest font-black opacity-60">
                                    <span className="flex items-center gap-1"><Clock size={10} /> {lesson.duration_minutes}m</span>
                                </div>
                            </div>
                            {activeLesson?.id === lesson.id && <CheckCircle2 size={16} className="text-primary mt-1" />}
                        </button>
                    ))}
                </div>

                <div className="p-6 bg-slate-800/50 border-t border-white/10">
                    <button className="w-full py-4 bg-gradient-to-r from-primary to-blue-600 rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all">
                        Solicitar Certificado
                    </button>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto bg-slate-950 p-6 md:p-12">
                {activeLesson ? (
                    <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
                        <div className="bg-slate-900/40 backdrop-blur-xl border border-white/10 rounded-[2.5rem] p-8 md:p-12 shadow-2xl">
                            <div className="flex items-center gap-3 mb-6">
                                <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase tracking-widest text-slate-400">
                                    Lección Actual
                                </span>
                            </div>
                            <h2 className="text-3xl md:text-4xl font-black text-white mb-8 tracking-tight capitalize">
                                {activeLesson.title}
                            </h2>

                            <div className="prose prose-invert max-w-none prose-headings:font-black prose-p:text-slate-300 prose-p:leading-relaxed prose-p:text-lg">
                                {activeLesson.content.split('\n').map((para, i) => (
                                    <p key={i} className="mb-4">{para}</p>
                                ))}
                            </div>

                            <div className="mt-12 pt-12 border-t border-white/10 flex flex-col sm:flex-row justify-between items-center gap-6">
                                <div className="flex items-center gap-3">
                                    <Award size={32} className="text-primary" />
                                    <div>
                                        <p className="text-xs font-black uppercase tracking-widest text-slate-500">Logro</p>
                                        <p className="text-white font-bold">Completa para ganar +10 XP</p>
                                    </div>
                                </div>
                                <button className="px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-sm font-bold flex items-center gap-2 transition-all group">
                                    Marcar como completada <CheckCircle2 size={18} className="text-primary group-hover:scale-110 transition-transform" />
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <div className="w-20 h-20 bg-white/5 rounded-3xl border border-white/10 flex items-center justify-center text-slate-500 mb-6">
                            <FileText size={40} strokeWidth={1} />
                        </div>
                        <h2 className="text-2xl font-bold text-slate-300">Selecciona una lección para comenzar</h2>
                        <p className="text-slate-500 mt-2">Tu progreso se guarda automáticamente.</p>
                    </div>
                )}
            </main>
        </div>
    );
}

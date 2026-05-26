"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { 
    BookOpen, 
    FileText, 
    Plus, 
    Save, 
    Settings,
    History,
    ChevronRight,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

export default function AdminCourseContentPage() {
    const params = useParams();
    const id = (params?.id as string) || '';
    const { token } = useAuth();
    
    const [course, setCourse] = useState<any>(null);
    const [lessons, setLessons] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadData = async () => {
            try {
                setLoading(true);
                const [courseData, lessonsData] = await Promise.all([
                    apiFetch<any>(`/academy/courses/${id}`, { token }),
                    apiFetch<any[]>(`/academy/courses/${id}/lessons`, { token }).catch(() => [])
                ]);
                setCourse(courseData);
                setLessons(Array.isArray(lessonsData) ? lessonsData : []);
            } catch (err) {
                toast.error('Error al cargar contenido del curso');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [id, token]);

    if (loading) return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-slate-400">Preparando Editor de Contenidos...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Contenidos', icon: BookOpen, href: '/plataforma/admin/content/list' },
                    { label: course?.title || 'Curso', icon: FileText },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="px-4 py-2 text-slate-500 text-[10px] font-semibold uppercase tracking-wide hover:text-slate-700 transition-all">
                            Vista Previa
                        </button>
                        <button className="px-3 py-2 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Save size={14} /> Publicar Cambios
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-3">
                    <div className="lg:col-span-2 space-y-3">
                        <header className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="blue" label="PROGRAMA ACADÉMICO" />
                                <DSBadge tone="emerald" label="PUBLICADO" />
                            </div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight leading-tight uppercase">
                                {course?.title}
                            </h1>
                        </header>

                        <section className="space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Lecciones y Módulos ({lessons.length})</h3>
                                <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide hover:border-blue-500 transition-all">
                                    <Plus size={14} /> Nueva Lección
                                </button>
                            </div>

                            <div className="space-y-3">
                                {lessons.map((lesson, idx) => (
                                    <div key={lesson.id} className="group bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 flex items-center justify-between hover:border-blue-500/30 transition-all cursor-pointer">
                                        <div className="flex items-center gap-4">
                                            <span className="text-xs font-semibold text-slate-300 group-hover:text-blue-500 transition-colors">
                                                {String(idx + 1).padStart(2, '0')}
                                            </span>
                                            <div>
                                                <h4 className="text-sm font-bold text-slate-800 dark:text-white">{lesson.title}</h4>
                                                <p className="font-semibold">{lesson.modality || 'Video + PDF'}</p>
                                            </div>
                                        </div>
                                        <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-500 transition-all" />
                                    </div>
                                ))}

                                {lessons.length === 0 && (
                                    <div className="py-1.5 text-center border-2 border-dashed border-slate-100 dark:border-white/5 rounded-lg">
                                        <BookOpen size={48} className="mx-auto text-slate-100 mb-4" />
                                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">El curso no tiene contenido todavía</p>
                                    </div>
                                )}
                            </div>
                        </section>
                    </div>

                    <aside className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-4">Configuración de Obra</h3>
                            <div className="space-y-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Código de Referencia</p>
                                    <p className="text-sm font-bold">{course?.code}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sede Principal</p>
                                    <p className="text-sm font-bold">Campus Virtual / Central</p>
                                </div>
                                <div className="h-px bg-slate-100 dark:bg-white/5" />
                                <button className="w-full flex items-center justify-center gap-2 py-3 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-50 transition-all">
                                    <Settings size={14} /> Ajustes Técnicos
                                </button>
                            </div>
                        </DSCard>

                        <div className="bg-slate-900 rounded-lg p-4 text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-blue-400">
                                <History size={14} /> Control de Versiones
                            </div>
                            <p className="text-[11px] font-medium opacity-70">
                                Última edición por Admin_CCF hace 1 hora.
                            </p>
                            <button className="text-[9px] font-semibold uppercase tracking-wide text-blue-400 hover:text-blue-300">
                                Ver historial completo
                            </button>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    );
}

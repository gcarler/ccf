"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { 
    LayoutDashboard, 
    CheckCircle2, 
    Calendar, 
    MessageSquare, 
    MoreVertical,
    Play,
    Pause,
    Sparkles
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function TaskDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    
    const [task, setTask] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [isTimerRunning, setIsTimerRunning] = useState(false);

    useEffect(() => {
        if (!token || !id) return;
        const loadTask = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/projects/tasks/${id}`, { token }).catch(() => null);
                setTask(data || {
                    id,
                    title: 'Tarea del Sistema',
                    description: 'Esta tarea fue recuperada del índice global de actividades.',
                    status: 'in_progress',
                    priority: 'high',
                    due_date: '2026-05-15',
                    assignee: 'Juan Perez'
                });
            } catch (err) {
                toast.error('Error al cargar la tarea');
            } finally {
                setLoading(false);
            }
        };
        loadTask();
    }, [id, token]);

    if (loading) return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-slate-400">Sincronizando con el servidor...</div>;

    const sidebarSections = [
        {
            title: 'Tareas',
            items: [
                { id: 'tasks-list', label: 'Mis Tareas', href: '/plataforma/tasks', icon: LayoutDashboard },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Tareas" sidebarSections={sidebarSections}>
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Proyectos', icon: LayoutDashboard, href: '/plataforma/projects' },
                    { label: 'Tareas', icon: CheckCircle2, href: '/plataforma/tasks' },
                    { label: `Task-${id}`, icon: CheckCircle2 },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="p-2 text-slate-400 hover:text-blue-600 transition-all">
                            <MoreVertical size={20} />
                        </button>
                        <button className="px-3 py-2 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                            Finalizar Tarea
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full grid grid-cols-1 lg:grid-cols-3 gap-3">
                    <div className="lg:col-span-2 space-y-3">
                        <header className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone={task.priority === 'high' ? 'violet' : 'amber'} label={task.priority.toUpperCase()} />
                                <DSBadge tone="blue" label={task.status.toUpperCase()} />
                            </div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight leading-tight uppercase">
                                {task.title}
                            </h1>
                        </header>

                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-4">Descripción</h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">
                                {task.description}
                            </p>
                        </DSCard>

                        <section className="space-y-4">
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Actividad y Comentarios</h3>
                            <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 text-center py-1.5">
                                <MessageSquare size={32} className="mx-auto text-slate-200 mb-4" />
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">No hay comentarios aún</p>
                            </div>
                        </section>
                    </div>

                    <aside className="space-y-3">
                        <DSCard>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Responsable</span>
                                    <div className="flex items-center gap-2">
                                        <div className="size-6 rounded-full bg-blue-500 flex items-center justify-center font-semibold text-white">
                                            {task.assignee?.charAt(0)}
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{task.assignee}</span>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fecha Límite</span>
                                    <div className="flex items-center gap-2 text-xs font-bold text-rose-500">
                                        <Calendar size={14} /> {new Date(task.due_date).toLocaleDateString()}
                                    </div>
                                </div>
                                <div className="h-px bg-slate-100 dark:bg-white/5" />
                                <div className="space-y-4">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Seguimiento de Tiempo</p>
                                    <div className="flex items-center justify-between">
                                        <span className="text-lg font-bold text-slate-900 dark:text-white font-mono">00:45:12</span>
                                        <button 
                                            onClick={() => setIsTimerRunning(!isTimerRunning)}
                                            className={clsx(
                                                'size-10 rounded-full flex items-center justify-center transition-all',
                                                isTimerRunning ? 'bg-rose-500 text-white animate-pulse' : 'bg-emerald-500 text-white'
                                            )}
                                        >
                                            {isTimerRunning ? <Pause size={18} /> : <Play size={18} className="ml-1" />}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </DSCard>

                        <div className="p-3 bg-blue-600 rounded-lg text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide">
                                <Sparkles size={14} /> AI Context
                            </div>
                            <p className="text-[11px] font-bold leading-relaxed opacity-90">
                                Esta tarea es un prerrequisito para el hito &quot;Lanzamiento Beta&quot;. Juan, recuerda adjuntar el reporte de calidad antes de cerrar.
                            </p>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
        </WorkspaceLayout>
    );
}

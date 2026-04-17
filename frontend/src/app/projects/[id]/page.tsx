"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    LayoutDashboard, 
    CheckCircle2, 
    Users, 
    Settings, 
    Plus, 
    Search, 
    Filter,
    ArrowLeft,
    MoreHorizontal,
    ChevronRight,
    Sparkles,
    Calendar,
    Clock
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

export default function ProjectDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [project, setProject] = useState<any>(null);
    const [tasks, setTasks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadProject = async () => {
            try {
                setLoading(true);
                const [projData, tasksData] = await Promise.all([
                    apiFetch<any>(`/projects/${id}`, { token }),
                    apiFetch<any[]>(`/projects/${id}/tasks`, { token }).catch(() => [])
                ]);
                setProject(projData);
                setTasks(tasksData);
            } catch (err) {
                toast.error('Error al cargar detalle del proyecto');
            } finally {
                setLoading(false);
            }
        };
        loadProject();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Recuperando ecosistema de trabajo...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Proyectos', icon: LayoutDashboard, href: '/projects' },
                    { label: project?.title || 'Cargando...', icon: Calendar },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                            Nueva Tarea
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="space-y-4">
                    <DSBadge tone="blue" label="PROYECTO ACTIVO" />
                    <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase">
                        {project?.title}
                    </h1>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <DSMetric label="Tareas Totales" value={String(tasks.length)} trend="En curso" tone="blue" />
                    <DSMetric label="Completadas" value={String(tasks.filter(t => t.status === 'completed').length)} trend="Progreso" tone="emerald" />
                    <DSMetric label="Miembros" value="5" trend="Staff activo" tone="amber" />
                    <DSMetric label="Días Restantes" value="15" trend="Cierre: 30 Abr" tone="violet" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Lista de Actividades</h3>
                            <div className="space-y-3">
                                {tasks.map(task => (
                                    <div key={task.id} className="p-4 rounded-2xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all cursor-pointer">
                                        <div className="flex items-center gap-4">
                                            <div className="size-6 rounded-full border-2 border-slate-200 dark:border-white/10 group-hover:border-blue-500 transition-colors" />
                                            <div>
                                                <p className="text-sm font-bold text-slate-800 dark:text-white">{task.title}</p>
                                                <p className="text-[10px] text-slate-400 uppercase font-black">{task.priority} Priority</p>
                                            </div>
                                        </div>
                                        <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-500" />
                                    </div>
                                ))}
                                {tasks.length === 0 && <p className="text-xs text-slate-400 text-center py-10">No hay tareas pendientes</p>}
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                <Sparkles size={14} /> AI Forecast
                            </div>
                            <p className="text-[11px] font-medium leading-relaxed opacity-80">
                                Basado en el ritmo actual, el proyecto se completará con 2 días de retraso. Se recomienda priorizar las tareas de la ruta crítica.
                            </p>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    );
}

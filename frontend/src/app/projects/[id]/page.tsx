"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Layout, 
    Target, 
    Plus, 
    Save, 
    Trash2, 
    Calendar as CalendarIcon, 
    BarChart3,
    Settings,
    KanbanSquare
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { ProjectKanbanBoard } from '@/components/projects/ProjectKanbanBoard';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectDetailPage() {
    const params = useParams<{ id: string }>();
    const id = params?.id ?? '';
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();
    
    const [project, setProject] = useState<ProjectRecord | null>(null);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'tablero' | 'overview'>('tablero');

    useEffect(() => {
        const fetchProject = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectRecord>(`/projects/${id}`, { token, cache: 'no-store' });
                setProject(data);
                setTasks(data.tasks || []);
            } catch (err) {
                console.error(err);
                addToast('Error al cargar el proyecto', 'error');
            } finally {
                setLoading(false);
            }
        };
        fetchProject();
    }, [id, token, addToast]);

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-slate-50 dark:bg-[#1e1f21] p-10 space-y-8">
                <Skeleton className="h-10 w-1/3 rounded-xl" />
                <Skeleton className="h-64 rounded-3xl" />
            </div>
        );
    }

    if (!project) return null;

    const completedTasks = tasks.filter(t => t.status === 'done').length;
    const progress = tasks.length ? Math.round((completedTasks / tasks.length) * 100) : 0;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Portfolio', icon: Layout },
                    { label: project.title, icon: Target }
                ]}
                viewType="grid" setViewType={() => {}}
                availableViews={['grid']}
                rightActions={
                    <div className="flex gap-2">
                        <button className="p-2.5 bg-slate-100 dark:bg-white/5 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><Settings size={20} /></button>
                    </div>
                }
            />

            <main className="flex-1 flex overflow-hidden">
                {/* Left: Metadata & Settings */}
                <aside className="w-80 border-r border-slate-100 dark:border-white/5 p-8 space-y-10 overflow-y-auto scrollbar-hide shrink-0 z-10 bg-white dark:bg-[#1e1f21]">
                    <div>
                        <div className="flex items-center gap-4 mb-8">
                            <div className="size-14 rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-xl" style={{ backgroundColor: project.color || '#2563eb' }}>
                                {project.title.substring(0, 1)}
                            </div>
                            <h2 className="text-xl font-black text-slate-900 dark:text-white leading-tight pr-4">
                                {project.title}
                            </h2>
                        </div>
                        
                        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] mb-4">Progreso</h3>
                        <div className="space-y-3 mb-8">
                            <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest">
                                <span className="text-slate-400">Avance Total</span>
                                <span className="text-blue-600">{progress}%</span>
                            </div>
                            <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                                <motion.div
                                    initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 1 }}
                                    className="h-full bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.5)]"
                                />
                            </div>
                        </div>

                        <div className="space-y-4">
                            <MetaItem icon={BarChart3} label="Estado" value={project.status.toUpperCase()} />
                            <MetaItem icon={CalendarIcon} label="Creado" value={new Date(project.created_at).toLocaleDateString('es-PE')} />
                        </div>
                    </div>

                    <section className="p-6 bg-blue-50 dark:bg-blue-900/10 rounded-[2.5rem] border border-blue-100 dark:border-blue-500/20">
                        <h5 className="text-[10px] font-black uppercase tracking-widest text-blue-600 mb-2">Descripción</h5>
                        <p className="text-[12px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
                            {project.description || 'Sin descripción detallada. Completa este campo para ayudar al equipo a entender los objetivos del proyecto.'}
                        </p>
                    </section>
                </aside>

                {/* Right: Main Content (Tabs) */}
                <div className="flex-1 flex flex-col bg-slate-50/50 dark:bg-black/20">
                    <nav className="px-8 pt-6 flex gap-8 border-b border-slate-200 dark:border-white/5 bg-white dark:bg-transparent shrink-0">
                        <TabButton active={activeTab === 'tablero'} onClick={() => setActiveTab('tablero')} label="Tablero Kanban" icon={KanbanSquare} />
                        <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} label="Resumen y Equipo" icon={Layout} />
                    </nav>

                    <div className="flex-1 overflow-hidden p-8">
                        <AnimatePresence mode="wait">
                            {activeTab === 'tablero' && (
                                <motion.div key="tablero" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="h-full">
                                    <ProjectKanbanBoard 
                                        project={project} 
                                        tasks={tasks} 
                                        onTasksChange={setTasks} 
                                        onOpenTask={(task) => addToast('Abrir detalles de la tarea: ' + task.title, 'info')}
                                        onAddTask={(status) => {
                                            // Mocking task creation for testing UI interactivity
                                            const fakeId = Date.now();
                                            const newTask: ProjectTaskRecord = {
                                                id: fakeId,
                                                project_id: project.id,
                                                title: 'Nueva tarea rápida',
                                                description: '',
                                                status: status,
                                                priority: 'normal',
                                                order_index: tasks.length
                                            };
                                            setTasks([...tasks, newTask]);
                                            addToast('Tarea añadida en ' + status, 'success');
                                        }}
                                    />
                                </motion.div>
                            )}
                            
                            {activeTab === 'overview' && (
                                <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="h-full overflow-y-auto">
                                    <div className="max-w-4xl bg-white dark:bg-[#1e1f21] rounded-[3rem] p-10 border border-slate-200 dark:border-white/5 shadow-sm">
                                        <h1 className="text-3xl font-black mb-6">Muro del Proyecto</h1>
                                        <p className="text-slate-500">
                                            Aquí puedes añadir discusiones, roles de equipo y documentos importantes adjuntos al proyecto completo.
                                        </p>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </main>
        </div>
    );
}

function MetaItem({ icon: Icon, label, value }: any) {
    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 text-slate-400">
                <Icon size={16} />
                <span className="text-[11px] font-bold uppercase tracking-wider">{label}</span>
            </div>
            <span className="text-[12px] font-black uppercase text-slate-700 dark:text-slate-200">
                {value}
            </span>
        </div>
    );
}

function TabButton({ active, onClick, label, icon: Icon }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "pb-4 text-[12px] font-black flex items-center gap-2 uppercase tracking-[0.1em] transition-all relative overflow-hidden",
                active ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
            )}
        >
            <Icon size={16} />
            {label}
            {active && <motion.div layoutId="tab" className="absolute bottom-0 left-0 right-0 h-1 bg-blue-600 rounded-full" />}
        </button>
    );
}

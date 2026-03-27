"use client";

import React, { useState, useEffect } from 'react';
import { 
    CheckCircle2, 
    Circle, 
    Clock, 
    AlertCircle, 
    Plus, 
    Search, 
    Filter, 
    ChevronRight, 
    MoreHorizontal,
    Zap,
    Target,
    Calendar,
    Bot,
    Sparkles,
    Layout,
    List as ListIcon,
    LayoutGrid,
    CheckSquare
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function UserTasksPage() {
    const { token, user, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [tasks, setTasks] = useState<any[]>([]);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Quality Mock Data for Tasks
        setTasks([
            { id: 1, title: 'Llamar a nuevos visitantes (Sede Norte)', priority: 'high', category: 'CRM', due: 'Hoy', xp: 50, done: false },
            { id: 2, title: 'Completar evaluación de Fundamentos', priority: 'medium', category: 'Academia', due: 'Mañana', xp: 100, done: false },
            { id: 3, title: 'Revisar reportes de Casas de Gloria', priority: 'low', category: 'Admin', due: '30 Mar', xp: 30, done: true },
        ]);
        setLoading(false);
    }, []);

    const toggleTask = (id: number) => {
        setTasks(tasks.map(t => t.id === id ? { ...t, done: !t.done } : t));
        const task = tasks.find(t => t.id === id);
        if (!task?.done) {
            addToast(`¡Tarea completada! +${task?.xp} XP ganados`, 'success');
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Productividad', icon: Layout },
                    { label: 'Mi Centro de Tareas', icon: CheckSquare }
                ]}
                viewType={viewMode} setViewType={(v: any) => setViewMode(v)}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Nueva Tarea
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* Left: Task Content */}
                    <div className="lg:col-span-8 space-y-8 pb-20">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-4">
                            <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white uppercase">Lista de Pendientes</h2>
                            <div className="flex gap-3">
                                <div className="relative w-full md:w-64">
                                    <input placeholder="Buscar tareas..." className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-2 px-10 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all" />
                                    <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                </div>
                                <button className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400"><Filter size={18} /></button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {tasks.map((task) => (
                                <motion.div 
                                    key={task.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                    className={clsx(
                                        "p-6 bg-white dark:bg-white/5 border rounded-[2.5rem] shadow-sm transition-all group flex items-center justify-between gap-6",
                                        task.done ? "border-slate-100 opacity-60 grayscale" : "border-slate-200 dark:border-white/10 hover:shadow-xl hover:border-blue-500/20"
                                    )}
                                >
                                    <div className="flex items-center gap-6">
                                        <button 
                                            onClick={() => toggleTask(task.id)}
                                            className={clsx(
                                                "size-8 rounded-xl flex items-center justify-center transition-all active:scale-90",
                                                task.done ? "bg-emerald-500 text-white" : "bg-slate-50 dark:bg-white/10 text-slate-300 hover:text-blue-600 border border-slate-100 dark:border-white/10"
                                            )}
                                        >
                                            {task.done ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                                        </button>
                                        <div>
                                            <h4 className={clsx("text-[15px] font-black uppercase tracking-tight leading-none mb-2", task.done ? "line-through text-slate-400" : "text-slate-800 dark:text-white")}>{task.title}</h4>
                                            <div className="flex items-center gap-4 text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                                                <span className={clsx(
                                                    "px-2 py-0.5 rounded-lg",
                                                    task.priority === 'high' ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-blue-600"
                                                )}>{task.priority}</span>
                                                <span className="flex items-center gap-1.5"><Layout size={10} /> {task.category}</span>
                                                <span className="flex items-center gap-1.5"><Clock size={10} /> Vence: {task.due}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-6">
                                        {!task.done && (
                                            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-xl text-[9px] font-black uppercase tracking-widest">
                                                <Zap size={12} fill="currentColor" /> +{task.xp} XP
                                            </div>
                                        )}
                                        <button className="p-2 text-slate-200 hover:text-slate-400"><MoreHorizontal size={20} /></button>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>

                    {/* Right: Insights & Stats */}
                    <aside className="lg:col-span-4 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-10">
                            <div>
                                <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] mb-8 px-2 text-center">Resumen de Hoy</h3>
                                <div className="flex justify-around">
                                    <TaskMetric label="Pendientes" value="5" color="blue" />
                                    <div className="w-px h-12 bg-slate-100 dark:bg-white/5" />
                                    <TaskMetric label="Hechas" value="12" color="emerald" />
                                </div>
                            </div>
                            <div className="pt-10 border-t border-slate-100 dark:border-white/5 text-center">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Progreso de la Semana</p>
                                <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden mb-2">
                                    <div className="h-full bg-blue-600 w-[72%] shadow-[0_0_10px_#2563eb]" />
                                </div>
                                <span className="text-[11px] font-black text-blue-600 uppercase">72% Completado</span>
                            </div>
                        </section>

                        <section className="p-8 bg-slate-900 rounded-[3rem] text-white shadow-2xl space-y-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-blue-600/20 rounded-full blur-3xl group-hover:bg-blue-600/30 transition-all" />
                            <div className="relative z-10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <Bot size={20} className="text-blue-400" />
                                    <h4 className="text-[11px] font-black uppercase tracking-widest text-blue-400">Optimus Tasks</h4>
                                </div>
                                <p className="text-[13px] font-medium leading-relaxed italic text-slate-300">
                                    &ldquo;He detectado que las llamadas del CRM son críticas hoy. ¿Deseas que prepare los scripts de conversación automáticamente?&rdquo;
                                </p>
                                <button className="flex items-center gap-2 text-[10px] font-black text-white uppercase tracking-widest group-hover:gap-3 transition-all">
                                    Preparar Scripts <ChevronRight size={14} />
                                </button>
                            </div>
                        </section>
                    </aside>
                </div>
            </main>
        </div>
    );
}

function TaskMetric({ label, value, color }: any) {
    return (
        <div className="text-center">
            <h4 className={clsx(
                "text-3xl font-black tracking-tighter mb-1",
                color === 'blue' ? "text-blue-600" : "text-emerald-600"
            )}>{value}</h4>
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
        </div>
    );
}

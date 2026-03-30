"use client";

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
    Radio, 
    Share2, 
    Users, 
    Globe, 
    Film, 
    CheckCircle2, 
    Clock, 
    AlertCircle,
    ChevronRight,
    Zap,
    Heart,
    Trophy,
    Calendar
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord, ProjectMilestoneRecord } from '@/types/projects';

interface ProjectMasterViewProps {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
}

export function ProjectMasterView({ project, tasks }: ProjectMasterViewProps) {
    // Clasificar tareas por Nodos (Sub-proyectos)
    const nutritionTasks = tasks.filter(t => t.title.includes('[Gestión]'));
    const evangelismTasks = tasks.filter(t => t.title.includes('[Evangelismo]') || t.title.includes('Historial:'));
    const formationTasks = tasks.filter(t => t.title.includes('[Formación]'));
    const webTasks = tasks.filter(t => t.title.includes('[Web]'));

    const milestones = project.milestones || [];

    // Lógica de Salud (Basada en retrasos y tareas completadas)
    const health = useMemo(() => {
        if (!tasks.length) return 100;
        const completed = tasks.filter(t => t.status === 'done').length;
        const total = tasks.length;
        return Math.round((completed / total) * 100);
    }, [tasks]);

    return (
        <div className="space-y-10 pb-20 overflow-y-auto h-full pr-2 scrollbar-thin">
            {/* Header de Impacto con Salud del Proyecto */}
            <header className="relative p-10 rounded-[3.5rem] bg-gradient-to-br from-indigo-600 to-blue-700 text-white overflow-hidden shadow-2xl">
                <div className="absolute top-0 right-0 p-10 opacity-10">
                    <Radio size={200} />
                </div>
                
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                    <div className="max-w-2xl">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest text-indigo-100 border border-white/10">Master Dashboard</span>
                            <div className="size-2 rounded-full bg-green-400 animate-pulse" />
                            <span className="text-[10px] font-bold text-indigo-100">Ministerio El Faro</span>
                        </div>
                        <h1 className="text-5xl font-black mb-4 tracking-tight leading-none text-white">Voces de Transformación</h1>
                        <p className="text-indigo-100 text-sm font-medium leading-relaxed opacity-90">
                            {project.description || "Posicionando a la iglesia como una comunidad de sentido relevante en el ecosistema digital."}
                        </p>
                    </div>

                    {/* Widget de Salud del Proyecto */}
                    <div className="bg-white/10 backdrop-blur-xl rounded-[2.5rem] p-6 border border-white/20 flex items-center gap-6 shadow-xl">
                        <div className="relative size-20">
                            <svg className="size-full" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" r="16" fill="none" className="stroke-white/10" strokeWidth="4"></circle>
                                <circle cx="18" cy="18" r="16" fill="none" className="stroke-blue-400" strokeWidth="4" 
                                    strokeDasharray={`${health}, 100`} strokeLinecap="round"></circle>
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Heart className={clsx("size-8", health > 70 ? "text-red-400" : "text-orange-400")} fill="currentColor" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-indigo-200 block mb-1">Salud Global</span>
                            <div className="text-3xl font-black">{health}%</div>
                            <span className="text-[9px] font-bold text-indigo-300">Estado: {health > 70 ? 'Óptimo' : 'Atención Requerida'}</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Línea de Tiempo de Hitos (Milestones) */}
            <section className="px-4">
                <div className="flex items-center gap-3 mb-6">
                    <Trophy className="text-yellow-500" />
                    <h3 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight">Hitos de la Misión</h3>
                </div>
                <div className="flex flex-col md:flex-row gap-6">
                    {milestones.map((m, i) => (
                        <div key={m.id} className="flex-1 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[2.5rem] p-6 shadow-sm relative group overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                <Calendar size={60} />
                            </div>
                            <div className="flex items-start gap-4 mb-4">
                                <div className={clsx("size-10 rounded-xl flex items-center justify-center", m.is_completed ? "bg-green-100 text-green-600" : "bg-blue-100 text-blue-600")}>
                                    {m.is_completed ? <CheckCircle2 size={18} /> : <Clock size={18} />}
                                </div>
                                <div className="min-w-0">
                                    <h4 className="font-black text-slate-800 dark:text-white text-sm truncate">{m.title}</h4>
                                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
                                        {m.target_date ? new Date(m.target_date).toLocaleDateString() : 'Pendiente'}
                                    </span>
                                </div>
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed line-clamp-2">{m.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Grid de Nodos Operativos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <NodeCard 
                    title="Nodo de Nutrición" 
                    subtitle="Gestión Organizacional" 
                    icon={Share2} 
                    color="bg-orange-500" 
                    tasks={nutritionTasks}
                />
                <NodeCard 
                    title="Nodo Digital" 
                    subtitle="Plataforma Web & SEO" 
                    icon={Globe} 
                    color="bg-emerald-500" 
                    tasks={webTasks}
                />
            </div>

            {/* NODO 2: EVANGELISMO - EL HEARTBEAT DEL PROYECTO */}
            <section className="space-y-6">
                <div className="flex items-center justify-between px-4">
                    <div>
                        <h3 className="text-2xl font-black text-slate-900 dark:text-white flex items-center gap-3">
                            <Film className="text-blue-600" /> Historias que Iluminan
                        </h3>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Nodo de Puentes · 24 Proyectos Temáticos</p>
                    </div>
                    <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-2xl border border-blue-100 dark:border-blue-800 shadow-sm">
                        <Zap size={14} className="text-blue-600" fill="currentColor" />
                        <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Sello de Hijos Activo</span>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                    {evangelismTasks.filter(t => t.title.includes('Historial:')).map((task, idx) => (
                        <StoryCard key={task.id} task={task} index={idx} />
                    ))}
                </div>
            </section>

            {/* NODO 3: FORMACIÓN */}
            <section className="p-12 rounded-[3.5rem] bg-slate-900 text-white relative overflow-hidden shadow-2xl border border-white/5">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 to-indigo-600/10 opacity-50" />
                <div className="relative z-10 flex flex-col md:flex-row items-center gap-12">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-4">
                            <Users className="text-blue-400" />
                            <h3 className="text-3xl font-black text-white">Nodo de Formación</h3>
                        </div>
                        <p className="text-slate-400 text-sm mb-8 font-medium max-w-lg leading-relaxed">
                            El motor creativo y espiritual del ministerio. Espacio de ruptura y laboratorio de producción colectiva.
                        </p>
                        <div className="flex flex-wrap gap-4">
                            {formationTasks.map(t => (
                                <div key={t.id} className="px-5 py-4 bg-white/5 rounded-3xl border border-white/10 flex items-center gap-3 hover:bg-white/10 transition-colors">
                                    <CheckCircle2 size={18} className={t.status === 'done' ? 'text-green-400' : 'text-slate-600'} />
                                    <span className="text-xs font-black uppercase tracking-wider">{t.title.replace('[Formación] ', '')}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="w-full md:w-72 aspect-square bg-gradient-to-br from-blue-600 to-indigo-700 rounded-[3rem] flex flex-col items-center justify-center text-center p-8 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-10">
                            <Clock size={100} />
                        </div>
                        <Clock size={48} className="mb-6 relative z-10" />
                        <span className="text-[11px] font-black uppercase tracking-[0.3em] mb-2 text-blue-100 relative z-10">Próximo Taller</span>
                        <span className="text-3xl font-black relative z-10">Sáb. 4:00 PM</span>
                        <div className="mt-4 px-4 py-2 bg-black/20 backdrop-blur-md rounded-full relative z-10">
                            <span className="text-[10px] font-bold text-white uppercase tracking-widest">Ruptura Litúrgica</span>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}

function NodeCard({ title, subtitle, icon: Icon, color, tasks }: any) {
    return (
        <div className="p-8 rounded-[3.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-xl transition-all group relative overflow-hidden">
            <div className="flex items-center gap-4 mb-8">
                <div className={clsx("size-16 rounded-[1.8rem] flex items-center justify-center text-white shadow-xl transition-transform group-hover:scale-110", color)}>
                    <Icon size={28} />
                </div>
                <div>
                    <h4 className="text-xl font-black text-slate-900 dark:text-white leading-tight">{title}</h4>
                    <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest mt-1">{subtitle}</p>
                </div>
            </div>
            <div className="space-y-3 relative z-10">
                {tasks.map((t: any) => (
                    <div key={t.id} className="flex items-center gap-4 p-4 rounded-3xl bg-slate-50 dark:bg-black/20 border border-transparent hover:border-slate-200 dark:hover:border-white/10 transition-all cursor-pointer">
                        <div className={clsx("size-2.5 rounded-full shadow-sm", t.status === 'done' ? 'bg-green-500' : 'bg-blue-500')} />
                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-300 truncate flex-1 leading-none">{t.title.split('] ')[1] || t.title}</span>
                        <ChevronRight size={16} className="text-slate-300" />
                    </div>
                ))}
            </div>
        </div>
    );
}

function StoryCard({ task, index }: { task: ProjectTaskRecord, index: number }) {
    const title = task.title.replace('Historial: ', '');
    const completedSub = task.subtasks?.filter(s => s.status === 'done').length || 0;
    const progress = task.subtasks?.length ? Math.round((completedSub / task.subtasks.length) * 100) : 0;

    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.02 }}
            className="p-5 rounded-[2.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 hover:border-blue-500/50 hover:shadow-2xl transition-all cursor-pointer group relative overflow-hidden"
        >
            <div className="flex items-center gap-4 mb-4">
                <div className="size-10 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all shadow-sm">
                    <Film size={18} />
                </div>
                <h5 className="text-[12px] font-black text-slate-800 dark:text-white truncate uppercase tracking-widest leading-none">{title}</h5>
            </div>
            
            <div className="space-y-3">
                <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                    <span>Progreso</span>
                    <span className="text-blue-600">{progress}%</span>
                </div>
                <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                    <div className="h-full bg-blue-600 rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(37,99,235,0.4)]" style={{ width: `${progress}%` }} />
                </div>
            </div>
        </motion.div>
    );
}

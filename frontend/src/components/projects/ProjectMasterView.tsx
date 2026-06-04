"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { 
    Radio, Share2, Globe, CheckCircle2, Clock, 
    Zap, Trophy, Calendar, TrendingUp, AlertCircle,
    ArrowUpRight, BarChart3
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

interface ProjectMasterViewProps {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
}

export function ProjectMasterView({ project, tasks }: ProjectMasterViewProps) {
    const nutritionTasks = tasks.filter(t => t.title.includes('[Gestión]'));
    const webTasks = tasks.filter(t => t.title.includes('[Web]'));

    const milestones = project.milestones || [];
    
    // Uso del progreso real persistido en DB
    const dbProgress = project.progress_percent || 0;

    return (
        <div className="space-y-4 pb-4 overflow-y-auto h-full pr-2 scrollbar-thin">
            {/* 1. Header de Misión con Pulso de Salud */}
            <header className="relative p-4 rounded-lg bg-slate-900 text-white overflow-hidden shadow-2xl border border-white/5">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 to-sky-600/20" />
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Radio size={220} />
                </div>
                
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="max-w-2xl space-y-3">
                        <div className="flex items-center gap-2">
                            <span className="px-2 py-1 bg-[hsl(var(--primary))] rounded-full text-[10px] font-bold uppercase tracking-wide text-white shadow-lg shadow-blue-500/40">Misión Proactiva</span>
                            <div className="size-2 rounded-full bg-emerald-400 animate-ping" />
                            <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">Sincronizado en tiempo real</span>
                        </div>
                        <h1 className="text-xl font-bold tracking-tight leading-none text-white">{project.title}</h1>
                        <p className="text-slate-400 text-base font-medium leading-relaxed max-w-xl">
                            {project.description || "Iniciativa estratégica para la expansión del reino en el ecosistema digital."}
                        </p>
                    </div>

                    {/* Widget Bento de Salud Persistida */}
                    <div className="bg-white/5 backdrop-blur-2xl rounded-lg p-3 border border-white/10 flex items-center gap-4 shadow-2xl">
                        <div className="relative size-8">
                            <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" r="16" fill="none" className="stroke-white/5" strokeWidth="3"></circle>
                                <motion.circle
                                    cx="18" cy="18" r="16" fill="none" className="stroke-blue-500" strokeWidth="3"
                                    initial={{ strokeDasharray: "0, 100" }}
                                    animate={{ strokeDasharray: `${dbProgress}, 100` }}
                                    transition={{ duration: 1.5, ease: "easeOut" }}
                                    strokeLinecap="round"
                                ></motion.circle>
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Zap className={clsx("size-8", dbProgress > 50 ? "text-yellow-400" : "text-[hsl(var(--primary))]")} fill="currentColor" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500 block mb-0.5">Avance Real</span>
                            <div className="text-xl font-bold tracking-tighter">{dbProgress}%</div>
                            <div className="flex items-center gap-2 mt-2">
                                <div className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded text-[9px] font-semibold uppercase">Salud: Óptima</div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* 2. Analítica de Impacto (NUEVA SECCIÓN DE CALIDAD) */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <AnalyticCard title="Velocidad" value="4.2" detail="Tareas/Día" icon={TrendingUp} color="text-[hsl(var(--primary))]" />
                <AnalyticCard title="Retraso" value="0" detail="Días de lag" icon={Clock} color="text-emerald-500" />
                <AnalyticCard title="Hitos" value={`${milestones.filter(m => m.is_completed).length}/${milestones.length}`} detail="Metas logradas" icon={Trophy} color="text-yellow-500" />
                <AnalyticCard title="Riesgo" value="Bajo" detail="Sin bloqueos" icon={AlertCircle} color="text-slate-400" />
            </section>

            {/* 3. Línea de Tiempo de Hitos */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tighter flex items-center gap-2">
                        <BarChart3 className="text-[hsl(var(--primary))]" size={16} /> Hitos Estratégicos
                    </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {milestones.map((m) => (
                        <div key={m.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg p-3 hover:shadow-2xl transition-all group relative overflow-hidden">
                            <div className="flex items-start justify-between mb-3">
                                <div className={clsx("size-10 rounded-md flex items-center justify-center shadow-lg", m.is_completed ? "bg-emerald-500 text-white" : "bg-slate-100 dark:bg-white/5 text-slate-400")}>
                                    {m.is_completed ? <CheckCircle2 size={18} /> : <Calendar size={18} />}
                                </div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                    {m.target_date ? new Date(m.target_date).toLocaleDateString() : 'TBD'}
                                </span>
                            </div>
                            <h4 className="text-base font-bold text-slate-900 dark:text-white mb-1 leading-tight">{m.title}</h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{m.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* 4. Grid de Nodos Operativos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <NodeCard title="Nodo de Nutrición" icon={Share2} color="bg-orange-500" tasks={nutritionTasks} />
                <NodeCard title="Nodo Digital" icon={Globe} color="bg-[hsl(var(--primary))]" tasks={webTasks} />
            </div>
        </div>
    );
}

function AnalyticCard({ title, value, detail, icon: Icon, color }: any) {
    return (
        <div className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg shadow-sm hover:shadow-xl transition-all">
            <div className="flex items-center gap-2 mb-2">
                <div className={clsx("p-1.5 rounded-md bg-slate-50 dark:bg-white/5", color)}>
                    <Icon size={14} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{title}</span>
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white leading-none">{value}</div>
            <p className="text-[10px] font-medium text-slate-400 mt-1 uppercase tracking-tight">{detail}</p>
        </div>
    );
}

function NodeCard({ title, icon: Icon, color, tasks }: any) {
    return (
        <div className="p-3 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-2xl transition-all group">
            <div className="flex items-center gap-3 mb-3">
                <div className={clsx("size-10 rounded-md flex items-center justify-center text-white shadow-xl transition-transform group-hover:scale-110", color)}>
                    <Icon size={18} />
                </div>
                <div>
                    <h4 className="text-base font-bold text-slate-900 dark:text-white leading-tight">{title}</h4>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mt-0.5">Avance por Nodo</p>
                </div>
            </div>
            <div className="space-y-2">
                {tasks.slice(0, 4).map((t: any) => (
                    <div key={t.id} className="flex items-center gap-3 p-2 rounded-md bg-slate-50 dark:bg-black/20 border border-transparent hover:border-slate-200 transition-all cursor-pointer">
                        <div className={clsx("size-2.5 rounded-full shadow-sm", t.status === 'completed' ? "bg-emerald-500" : "bg-[hsl(var(--primary))]")} />
                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-300 truncate flex-1 leading-none">{t.title.split('] ')[1] || t.title}</span>
                        <ArrowUpRight size={14} className="text-slate-300" />
                    </div>
                ))}
            </div>
        </div>
    );
}

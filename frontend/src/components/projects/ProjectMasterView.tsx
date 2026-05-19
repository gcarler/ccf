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
        <div className="space-y-10 pb-20 overflow-y-auto h-full pr-2 scrollbar-thin">
            {/* 1. Header de Misión con Pulso de Salud */}
            <header className="relative p-12 rounded-[3.5rem] bg-slate-900 text-white overflow-hidden shadow-2xl border border-white/5">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 to-indigo-600/20" />
                <div className="absolute top-0 right-0 p-12 opacity-10">
                    <Radio size={220} />
                </div>
                
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-10">
                    <div className="max-w-2xl space-y-6">
                        <div className="flex items-center gap-3">
                            <span className="px-4 py-1.5 bg-blue-600 rounded-full text-[10px] font-black uppercase tracking-widest text-white shadow-lg shadow-blue-500/40">Misión Proactiva</span>
                            <div className="size-2 rounded-full bg-emerald-400 animate-ping" />
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Sincronizado en tiempo real</span>
                        </div>
                        <h1 className="text-6xl font-black tracking-tight leading-none text-white">{project.title}</h1>
                        <p className="text-slate-400 text-base font-medium leading-relaxed max-w-xl">
                            {project.description || "Iniciativa estratégica para la expansión del reino en el ecosistema digital."}
                        </p>
                    </div>

                    {/* Widget Bento de Salud Persistida */}
                    <div className="bg-white/5 backdrop-blur-2xl rounded-[3rem] p-8 border border-white/10 flex items-center gap-8 shadow-2xl">
                        <div className="relative size-24">
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
                                <Zap className={clsx("size-10", dbProgress > 50 ? "text-yellow-400" : "text-blue-400")} fill="currentColor" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 block mb-1">Avance Real</span>
                            <div className="text-5xl font-black tracking-tighter">{dbProgress}%</div>
                            <div className="flex items-center gap-2 mt-2">
                                <div className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded text-[9px] font-black uppercase">Salud: Óptima</div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* 2. Analítica de Impacto (NUEVA SECCIÓN DE CALIDAD) */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <AnalyticCard title="Velocidad" value="4.2" detail="Tareas/Día" icon={TrendingUp} color="text-blue-500" />
                <AnalyticCard title="Retraso" value="0" detail="Días de lag" icon={Clock} color="text-emerald-500" />
                <AnalyticCard title="Hitos" value={`${milestones.filter(m => m.is_completed).length}/${milestones.length}`} detail="Metas logradas" icon={Trophy} color="text-yellow-500" />
                <AnalyticCard title="Riesgo" value="Bajo" detail="Sin bloqueos" icon={AlertCircle} color="text-slate-400" />
            </section>

            {/* 3. Línea de Tiempo de Hitos */}
            <section className="space-y-6">
                <div className="flex items-center justify-between px-4">
                    <h3 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tighter flex items-center gap-3">
                        <BarChart3 className="text-blue-600" /> Hitos Estratégicos
                    </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {milestones.map((m) => (
                        <div key={m.id} className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] p-8 hover:shadow-2xl transition-all group relative overflow-hidden">
                            <div className="flex items-start justify-between mb-6">
                                <div className={clsx("size-12 rounded-2xl flex items-center justify-center shadow-lg", m.is_completed ? "bg-emerald-500 text-white" : "bg-slate-100 dark:bg-white/5 text-slate-400")}>
                                    {m.is_completed ? <CheckCircle2 size={24} /> : <Calendar size={24} />}
                                </div>
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                    {m.target_date ? new Date(m.target_date).toLocaleDateString() : 'TBD'}
                                </span>
                            </div>
                            <h4 className="text-lg font-black text-slate-900 dark:text-white mb-2 leading-tight">{m.title}</h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{m.description}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* 4. Grid de Nodos Operativos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <NodeCard title="Nodo de Nutrición" icon={Share2} color="bg-orange-500" tasks={nutritionTasks} />
                <NodeCard title="Nodo Digital" icon={Globe} color="bg-blue-600" tasks={webTasks} />
            </div>
        </div>
    );
}

function AnalyticCard({ title, value, detail, icon: Icon, color }: any) {
    return (
        <div className="p-6 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-3xl shadow-sm hover:shadow-xl transition-all">
            <div className="flex items-center gap-3 mb-4">
                <div className={clsx("p-2 rounded-xl bg-slate-50 dark:bg-white/5", color)}>
                    <Icon size={16} />
                </div>
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{title}</span>
            </div>
            <div className="text-3xl font-black text-slate-900 dark:text-white leading-none">{value}</div>
            <p className="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-tight">{detail}</p>
        </div>
    );
}

function NodeCard({ title, icon: Icon, color, tasks }: any) {
    return (
        <div className="p-8 rounded-[3.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-2xl transition-all group">
            <div className="flex items-center gap-4 mb-8">
                <div className={clsx("size-16 rounded-[1.8rem] flex items-center justify-center text-white shadow-xl transition-transform group-hover:scale-110", color)}>
                    <Icon size={28} />
                </div>
                <div>
                    <h4 className="text-xl font-black text-slate-900 dark:text-white leading-tight">{title}</h4>
                    <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest mt-1">Avance por Nodo</p>
                </div>
            </div>
            <div className="space-y-3">
                {tasks.slice(0, 4).map((t: any) => (
                    <div key={t.id} className="flex items-center gap-4 p-4 rounded-3xl bg-slate-50 dark:bg-black/20 border border-transparent hover:border-slate-200 transition-all cursor-pointer">
                        <div className={clsx("size-2.5 rounded-full shadow-sm", t.status === 'done' ? "bg-emerald-500" : "bg-blue-500")} />
                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-300 truncate flex-1 leading-none">{t.title.split('] ')[1] || t.title}</span>
                        <ArrowUpRight size={14} className="text-slate-300" />
                    </div>
                ))}
            </div>
        </div>
    );
}

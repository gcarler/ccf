"use client";

import React, { useState, useEffect } from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    Zap, 
    Bot, 
    Bell, 
    Clock, 
    ShieldAlert, 
    Settings2,
    ToggleLeft,
    ToggleRight,
    ArrowRight,
    Sparkles
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import DSSkeleton from '@/components/ui/Skeleton';

export default function AutomationsPage() {
    const [rules, setRules] = useState([
        { id: 1, name: 'Alerta de Sobrecarga', trigger: 'Carga > 8 tareas', active: true, icon: ShieldAlert, color: 'text-rose-500' },
        { id: 2, name: 'Recordatorio 24h', trigger: 'Cerca de deadline', active: true, icon: Bell, color: 'text-blue-500' },
        { id: 3, name: 'Detector de Estancamiento', trigger: 'Sin cambios en 3 días', active: false, icon: Clock, color: 'text-amber-500' }
    ]);

    const toggleRule = (id: number) => {
        setRules(rules.map(r => r.id === id ? { ...r, active: !r.active } : r));
    };

    return (
        <WorkspaceLayout sidebarTitle="Portfolio / Automatizaciones">
            <div className="flex flex-col h-full bg-white dark:bg-[#141517] overflow-hidden font-display animate-fade-in">
                
                {/* Header de Impacto */}
                <header className="p-12 border-b border-slate-100 dark:border-white/5 bg-slate-900 text-white relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-indigo-600/20" />
                    <div className="relative z-10 max-w-4xl">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="px-3 py-1 bg-blue-600 rounded-full text-[9px] font-black uppercase tracking-widest">Motor Optimus 3.0</div>
                            <Sparkles size={16} className="text-blue-400" />
                        </div>
                        <h1 className="text-5xl font-black tracking-tight leading-none">Cerebro de Operaciones</h1>
                        <p className="text-slate-400 font-medium mt-4 text-lg">El sistema monitorea tu ministerio en segundo plano. Configura cómo quieres que CCF reaccione ante los desafíos.</p>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto scrollbar-thin p-10 space-y-10">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {rules.map((rule, idx) => (
                            <motion.div 
                                key={rule.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="p-8 rounded-[3rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-2xl transition-all relative overflow-hidden group"
                            >
                                <div className="flex items-start justify-between mb-8">
                                    <div className={clsx("p-4 rounded-2xl bg-slate-50 dark:bg-black/20", rule.color)}>
                                        <rule.icon size={24} />
                                    </div>
                                    <button onClick={() => toggleRule(rule.id)} className="transition-transform active:scale-90">
                                        {rule.active ? <ToggleRight size={40} className="text-blue-600" /> : <ToggleLeft size={40} className="text-slate-300" />}
                                    </button>
                                </div>

                                <div className="space-y-2">
                                    <h3 className="text-xl font-black text-slate-900 dark:text-white leading-tight">{rule.name}</h3>
                                    <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">{rule.trigger}</p>
                                </div>

                                <div className="mt-8 pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                    <span className="text-[10px] font-black uppercase text-blue-600 tracking-widest flex items-center gap-2">Configurar Lógica <ArrowRight size={12} /></span>
                                    {!rule.active && <span className="px-2 py-1 bg-slate-100 dark:bg-white/5 text-slate-400 rounded-lg text-[8px] font-black uppercase tracking-widest">Inactivo</span>}
                                </div>
                            </motion.div>
                        ))}

                        {/* Card para añadir nueva automatización */}
                        <div className="p-8 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-white/5 flex flex-col items-center justify-center text-center gap-4 group cursor-pointer hover:border-blue-500/30 transition-all bg-slate-50/30 dark:bg-transparent">
                            <div className="size-14 rounded-full bg-white dark:bg-white/5 shadow-md flex items-center justify-center text-slate-400 group-hover:text-blue-600 transition-colors">
                                <Plus size={24} />
                            </div>
                            <div>
                                <h4 className="font-black text-slate-900 dark:text-white uppercase tracking-widest">Crear Regla</h4>
                                <p className="text-[10px] font-bold text-slate-400 mt-1 uppercase">Expandir Inteligencia</p>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </WorkspaceLayout>
    );
}

function Plus({ size, className }: any) {
    return <Zap size={size} className={className} />;
}

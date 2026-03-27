"use client";

import React, { useState, useEffect } from 'react';
import { 
    Zap, 
    MessageSquare, 
    Mail, 
    Smartphone, 
    Plus, 
    ChevronRight, 
    MoreHorizontal,
    Bot,
    Sparkles,
    Settings,
    ArrowRight,
    Filter,
    Clock,
    CheckCircle2,
    AlertCircle,
    Play,
    Pause,
    Save,
    Layout,
    Layers,
    Share2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function AutomationBuilder() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [automations, setAutomations] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Quality Mock Data
        setAutomations([
            { id: 1, name: 'Bienvenida Automática', trigger: 'Nuevo Registro', active: true, sent: 1240, icon: Sparkles, color: 'blue' },
            { id: 2, name: 'Recordatorio Encuentro', trigger: '3 días antes', active: true, sent: 850, icon: Calendar, color: 'purple' },
            { id: 3, name: 'Re-engagement Deserción', trigger: '15 días inactivo', active: false, sent: 12, icon: AlertCircle, color: 'rose' },
        ]);
        setLoading(false);
    }, []);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CRM Pastoral', icon: Smartphone },
                    { label: 'Automatización de Mensajes', icon: Zap }
                ]}
                viewType="list" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Crear Workflow
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                <div className="max-w-7xl mx-auto space-y-10">
                    
                    {/* Automation Designer Intro */}
                    <header className="bg-slate-900 rounded-[3rem] p-12 text-white shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-80 bg-blue-600/20 rounded-full blur-[100px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                            <div className="space-y-8">
                                <div className="flex items-center gap-4">
                                    <div className="size-14 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20"><Bot size={32} /></div>
                                    <div>
                                        <h2 className="text-3xl font-black tracking-tight leading-none mb-1 uppercase">Workflow Builder</h2>
                                        <p className="text-[10px] font-black text-blue-400 uppercase tracking-[0.3em]">Crecimiento Automatizado por Optimus</p>
                                    </div>
                                </div>
                                <p className="text-slate-400 text-sm font-medium leading-relaxed max-w-md uppercase tracking-wider">
                                    Crea secuencias inteligentes de mensajes que acompañen al creyente en cada etapa de su jornada espiritual. Ahorra tiempo y personaliza el cuidado pastoral.
                                </p>
                                <div className="flex gap-4">
                                    <button className="px-10 py-4 bg-white text-slate-900 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl hover:bg-slate-100 transition-all active:scale-95">
                                        Explorar Plantillas
                                    </button>
                                </div>
                            </div>
                            <div className="hidden lg:flex justify-end pr-10">
                                <div className="relative flex items-center gap-6">
                                    <div className="size-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center animate-pulse"><Sparkles className="text-blue-400" /></div>
                                    <ArrowRight className="text-blue-500" />
                                    <div className="size-20 rounded-3xl bg-blue-600 flex items-center justify-center shadow-2xl shadow-blue-500/40"><MessageSquare /></div>
                                    <ArrowRight className="text-blue-500" />
                                    <div className="size-20 rounded-3xl bg-white/5 border border-white/10 flex items-center justify-center"><CheckCircle2 className="text-emerald-400" /></div>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Active Automations List */}
                    <div className="space-y-6">
                        <div className="flex items-center justify-between px-4">
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest leading-none text-slate-400">Mis Automatizaciones</h3>
                            <button className="p-2 hover:bg-white rounded-lg text-slate-400"><Settings size={18} /></button>
                        </div>

                        <div className="grid grid-cols-1 gap-4 pb-20">
                            {automations.map((auto) => (
                                <motion.div 
                                    key={auto.id} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}
                                    className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all group flex flex-col md:flex-row md:items-center justify-between gap-8"
                                >
                                    <div className="flex items-center gap-6">
                                        <div className={clsx(
                                            "size-14 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12",
                                            auto.color === 'blue' ? "bg-blue-50 text-blue-600" : auto.color === 'purple' ? "bg-purple-50 text-purple-600" : "bg-rose-50 text-rose-600"
                                        )}>
                                            <auto.icon size={28} />
                                        </div>
                                        <div>
                                            <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase leading-none mb-2">{auto.name}</h4>
                                            <div className="flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                <span className="flex items-center gap-1.5"><Clock size={12} /> Trigger: {auto.trigger}</span>
                                                <span className="flex items-center gap-1.5 text-blue-600"><Share2 size={12} /> Multicanal</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-10">
                                        <div className="text-center">
                                            <p className="text-lg font-black text-slate-900 dark:text-white leading-none">{auto.sent.toLocaleString()}</p>
                                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mt-1">Impactos</p>
                                        </div>
                                        <div className="flex gap-2">
                                            <button className={clsx(
                                                "px-6 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all flex items-center gap-2",
                                                auto.active ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400"
                                            )}>
                                                {auto.active ? <Play size={12} fill="currentColor" /> : <Pause size={12} fill="currentColor" />}
                                                {auto.active ? 'Activo' : 'Pausado'}
                                            </button>
                                            <button className="p-3 bg-slate-50 dark:bg-white/5 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><MoreHorizontal size={20} /></button>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

function Calendar({ size, className }: any) { return <Clock size={size} className={className} />; }

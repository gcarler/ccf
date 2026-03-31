"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { 
    Zap, 
    Play, 
    Plus, 
    Settings, 
    MessageSquare, 
    UserPlus, 
    Calendar, 
    Clock, 
    CheckCircle2, 
    ChevronRight,
    Loader2,
    Sparkles,
    ShieldCheck,
    Bell,
    Bot,
    MoreHorizontal,
    ArrowLeft,
    Trash2
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface AutomationRule {
    id: number;
    name: string;
    trigger: string;
    action: string;
    active: boolean;
    payload: any;
}

export default function MessagingAutomations() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [rules, setRules] = useState<AutomationRule[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchRules = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<AutomationRule[]>('/admin/automations', { token, cache: 'no-store' });
            setRules(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar motor de reglas", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchRules();
    }, [isAuthenticated, fetchRules]);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .automation-aura {
                    position: relative;
                }
                .automation-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, rgba(37, 99, 235, 0.1), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .automation-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Mensajería', icon: MessageSquare }, { label: 'Automatizaciones', icon: Zap }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-3 px-8 py-3 bg-blue-600 text-white rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={18} /> Nueva Regla
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-6xl mx-auto space-y-16 relative z-10">
                    
                    {/* Header Cinematic */}
                    <header className="space-y-4">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20"
                        >
                            <Bot size={12} className="animate-pulse" /> Inteligencia Pastoral Automática
                        </motion.div>
                        <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                            El CRM que <br/> <span className="text-blue-600 italic text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-400">nunca duerme.</span>
                        </h1>
                        <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-2xl leading-relaxed">
                            Configura disparadores inteligentes para que la plataforma cuide de tu congregación automáticamente. Bienvenidas, felicitaciones y alertas de cuidado.
                        </p>
                    </header>

                    {loading ? (
                        <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                            <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Red Neuronal...
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            <AnimatePresence>
                                {rules.map((rule, i) => (
                                    <motion.div 
                                        key={rule.id}
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: i * 0.05 }}
                                        className="automation-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-10 rounded-[3.5rem] shadow-sm hover:shadow-2xl transition-all duration-500 flex flex-col gap-8 overflow-hidden"
                                        style={{ '--aura-color': rule.active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)' } as any}
                                    >
                                        <div className="flex justify-between items-start">
                                            <div className={clsx(
                                                "size-16 rounded-[1.5rem] flex items-center justify-center shadow-inner group-hover:rotate-12 transition-transform duration-500",
                                                rule.active ? "bg-blue-50 text-blue-600 dark:bg-blue-900/20" : "bg-slate-50 text-slate-400 dark:bg-white/5"
                                            )}>
                                                <Zap size={32} strokeWidth={1.5} fill={rule.active ? "currentColor" : "none"} className={rule.active ? "opacity-20" : ""} />
                                            </div>
                                            <div className={clsx(
                                                "px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-colors",
                                                rule.active ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-slate-100 text-slate-400 border-slate-200"
                                            )}>
                                                {rule.active ? 'Activa' : 'Pausada'}
                                            </div>
                                        </div>

                                        <div className="space-y-2 flex-1">
                                            <h3 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none group-hover:text-blue-600 transition-colors">{rule.name}</h3>
                                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none flex items-center gap-2">
                                                <Play size={10} className="text-blue-500" /> Disparador: {rule.trigger}
                                            </p>
                                        </div>

                                        <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 space-y-4">
                                            <div className="flex items-center gap-3 text-[10px] font-black uppercase text-slate-500 tracking-widest">
                                                <Settings size={12} /> Acción Programada
                                            </div>
                                            <p className="text-xs font-bold text-slate-700 dark:text-slate-300 italic line-clamp-2">
                                                {rule.action === 'send_whatsapp' ? 'Enviar mensaje de WhatsApp personalizado' : 'Crear tarea de seguimiento pastoral'}
                                            </p>
                                        </div>

                                        <div className="flex items-center justify-between pt-4">
                                            <button className="p-3 text-slate-300 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-white/5 rounded-xl"><Plus size={18} /></button>
                                            <div className="flex gap-2">
                                                <button className="p-3 text-slate-300 hover:text-blue-600 transition-all"><Settings size={18} /></button>
                                                <button className="p-3 text-slate-300 hover:text-rose-600 transition-all"><Trash2 size={18} /></button>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}

                                {/* Empty / Add State */}
                                <motion.div 
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[3.5rem] p-10 flex flex-col items-center justify-center text-center space-y-6 hover:border-blue-500/50 hover:bg-blue-50/50 transition-all cursor-pointer group"
                                >
                                    <div className="size-20 rounded-[2rem] bg-white dark:bg-[#0a0f16] shadow-xl flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-500">
                                        <Plus size={40} strokeWidth={1.5} />
                                    </div>
                                    <div>
                                        <p className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Nueva Regla</p>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Automatizar el Cuidado Pastoral</p>
                                    </div>
                                </motion.div>
                            </AnimatePresence>
                        </div>
                    )}

                    {/* Master IA Pulse Cinematic */}
                    <motion.section 
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="bg-slate-900 p-12 lg:p-20 rounded-[4rem] text-white relative overflow-hidden group shadow-2xl"
                    >
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-blue-600/20 rounded-full blur-[120px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10 flex flex-col lg:flex-row items-center gap-16">
                            <div className="size-32 rounded-[2.5rem] bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-[0_0_50px_rgba(37,99,235,0.4)] border-4 border-white/10 shrink-0">
                                <Zap size={64} className="text-white animate-pulse" fill="currentColor" />
                            </div>
                            <div className="space-y-8 flex-1">
                                <div className="space-y-4 text-center lg:text-left">
                                    <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-white/5 border border-white/10 rounded-full text-[10px] font-black uppercase tracking-[0.4em] text-blue-400">Estado del Motor: Óptimo</div>
                                    <h2 className="text-4xl lg:text-6xl font-black tracking-tighter leading-none uppercase">Motor de <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 italic">Respuesta Inmediata.</span></h2>
                                    <p className="text-lg text-slate-400 font-medium leading-relaxed max-w-xl italic">
                                        &ldquo;Optimus Brain monitorea cada registro. Si un miembro es detectado con inactividad, el motor dispara una alerta al pastor de zona automáticamente.&rdquo;
                                    </p>
                                </div>
                                <div className="flex flex-wrap gap-4 justify-center lg:justify-start">
                                    <button className="px-10 py-5 bg-white text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-widest shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all">Ver Logs del Servidor</button>
                                    <button className="px-10 py-5 bg-white/5 backdrop-blur-md border border-white/10 text-white rounded-[2rem] font-black text-xs uppercase tracking-widest hover:bg-white/10 transition-all">Forzar Ejecución</button>
                                </div>
                            </div>
                        </div>
                    </motion.section>
                </div>
            </main>
        </div>
    );
}

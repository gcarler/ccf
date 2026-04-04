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
    Trash2,
    Activity,
    Cpu,
    Workflow,
    History,
    Check
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
                    background: linear-gradient(45deg, var(--aura-color, rgba(37, 99, 235, 0.1)), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .automation-aura:hover::after {
                    opacity: 1;
                }
                .shimmer-active {
                    position: relative;
                    overflow: hidden;
                }
                .shimmer-active::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 50%;
                    height: 100%;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.2),
                        transparent
                    );
                    animation: shimmer-pulse 2s infinite;
                }
                @keyframes shimmer-pulse {
                    0% { left: -100%; }
                    100% { left: 200%; }
                }
                .stacked-glass {
                    background: rgba(255, 255, 255, 0.7);
                    backdrop-filter: blur(20px) saturate(180%);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                .dark .stacked-glass {
                    background: rgba(30, 31, 33, 0.8);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Centro de Mensajes', icon: MessageSquare }, 
                    { label: 'Automatización Inteligente', icon: Workflow }
                ]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-3 px-8 py-3 bg-blue-600 text-white rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700">
                        <Plus size={18} /> Nueva Regla Maestro
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-7xl mx-auto space-y-16 relative z-10">
                    
                    {/* Cinematic Executive Header */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-10">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-600/10 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20 shadow-sm"
                            >
                                <Bot size={12} className="animate-pulse" /> Optimus Rule Engine v3.9
                            </motion.div>
                            <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-none uppercase">
                                El CRM que <br/> <span className="text-blue-600 italic text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-400">nunca descansa.</span>
                            </h1>
                            <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-2xl leading-relaxed">
                                Orquestación pastoral de alto nivel. Define disparadores automáticos para cuidar de tus 608 miembros con precisión quirúrgica y calor humano.
                            </p>
                        </div>

                        {/* Quick Stats Shimmer Cards */}
                        <div className="flex gap-4">
                            <QuickStat label="Reglas Activas" value={rules.filter(r => r.active).length} icon={Zap} color="text-blue-600" />
                            <QuickStat label="Acciones/Mes" value="1.2k" icon={Activity} color="text-emerald-600" />
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-blue-600/20 blur-2xl rounded-full animate-ping" />
                                    <Cpu className="animate-spin text-blue-600 relative z-10" size={64} strokeWidth={1.5} />
                                </div>
                                Sincronizando Red Neuronal...
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                {rules.map((rule, i) => (
                                    <motion.div 
                                        key={rule.id}
                                        initial={{ opacity: 0, y: 30, scale: 0.95 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        transition={{ delay: i * 0.08, duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
                                        className="automation-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-10 rounded-[3.5rem] shadow-sm hover:shadow-2xl transition-all duration-500 flex flex-col gap-8 overflow-hidden relative"
                                        style={{ '--aura-color': rule.active ? 'rgba(37, 99, 235, 0.15)' : 'rgba(100, 116, 139, 0.15)' } as any}
                                    >
                                        <div className="absolute top-0 left-0 w-full h-1 shimmer-active opacity-0 group-hover:opacity-100 transition-opacity" />
                                        
                                        <div className="flex justify-between items-start relative z-10">
                                            <div className={clsx(
                                                "size-16 rounded-[1.8rem] flex items-center justify-center shadow-inner transition-all duration-700 group-hover:scale-110 group-hover:rotate-6",
                                                rule.active ? "bg-blue-600 text-white shadow-blue-500/20" : "bg-slate-100 text-slate-400 dark:bg-white/5"
                                            )}>
                                                <Zap size={32} strokeWidth={1.5} fill={rule.active ? "currentColor" : "none"} className={rule.active ? "opacity-30" : ""} />
                                            </div>
                                            <div className={clsx(
                                                "px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-colors relative overflow-hidden",
                                                rule.active ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-slate-50 text-slate-400 border-slate-200"
                                            )}>
                                                {rule.active && <div className="absolute inset-0 bg-emerald-400/10 animate-pulse" />}
                                                <span className="relative z-10">{rule.active ? 'Sincronizado' : 'En Pausa'}</span>
                                            </div>
                                        </div>

                                        <div className="space-y-3 flex-1 relative z-10">
                                            <h3 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none group-hover:text-blue-600 transition-colors">{rule.name}</h3>
                                            <div className="flex items-center gap-2">
                                                <Play size={12} className="text-blue-500 fill-current" />
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">{rule.trigger}</p>
                                            </div>
                                        </div>

                                        <div className="p-8 stacked-glass rounded-[2.5rem] space-y-5 relative z-10">
                                            <div className="flex items-center gap-3 text-[10px] font-black uppercase text-blue-600/60 tracking-widest">
                                                <Workflow size={14} /> Pipeline de Acción
                                            </div>
                                            <p className="text-[13px] font-bold text-slate-700 dark:text-slate-300 leading-relaxed italic">
                                                &ldquo;{rule.action === 'send_whatsapp' ? 'Disparar mensaje de WhatsApp enriquecido con variables de membresía.' : 'Generar misión pastoral prioritaria en la agenda del líder.'}&rdquo;
                                            </p>
                                        </div>

                                        <div className="flex items-center justify-between pt-4 relative z-10">
                                            <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                                <History size={14} /> Última: Hoy 14:30
                                            </div>
                                            <div className="flex gap-2">
                                                <button className="p-3 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-blue-600 hover:shadow-xl transition-all"><Settings size={18} /></button>
                                                <button className="p-3 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-rose-600 hover:shadow-xl transition-all"><Trash2 size={18} /></button>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}

                                {/* Industrial Add Card */}
                                <motion.div 
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="bg-slate-50/50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[3.5rem] p-10 flex flex-col items-center justify-center text-center space-y-8 hover:border-blue-500/50 hover:bg-blue-50/50 transition-all duration-500 cursor-pointer group"
                                >
                                    <div className="size-24 rounded-[2.2rem] bg-white dark:bg-[#0a0f16] shadow-2xl flex items-center justify-center text-slate-300 group-hover:text-blue-600 group-hover:scale-110 group-hover:rotate-90 transition-all duration-700">
                                        <Plus size={48} strokeWidth={1.5} />
                                    </div>
                                    <div className="space-y-2">
                                        <p className="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Nueva Neurona</p>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Expandir el Cerebro Ministerial</p>
                                    </div>
                                </motion.div>
                            </div>
                        )}
                    </AnimatePresence>

                    {/* AI Process cinematic card */}
                    <motion.section 
                        initial={{ opacity: 0, y: 40 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="bg-slate-900 p-12 lg:p-24 rounded-[5rem] text-white relative overflow-hidden group shadow-[0_50px_100px_-20px_rgba(0,0,0,0.5)] border border-white/5"
                    >
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-[600px] bg-blue-600/10 rounded-full blur-[150px] group-hover:bg-blue-600/20 transition-all duration-1000 animate-pulse" />
                        <div className="absolute bottom-0 left-0 p-20 opacity-5 group-hover:rotate-12 transition-all duration-1000"><Workflow size={300} /></div>
                        
                        <div className="relative z-10 flex flex-col lg:flex-row items-center gap-20">
                            <div className="relative">
                                <div className="size-48 rounded-[3.5rem] bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-[0_0_80px_rgba(37,99,235,0.5)] border-4 border-white/10 group-hover:scale-105 transition-transform duration-700">
                                    <Zap size={80} className="text-white animate-pulse" fill="currentColor" />
                                </div>
                                <div className="absolute -bottom-4 -right-4 size-16 bg-white rounded-[1.5rem] flex items-center justify-center shadow-2xl text-blue-600 border-4 border-slate-900"><CheckCircle2 size={32} /></div>
                            </div>
                            
                            <div className="space-y-10 flex-1">
                                <div className="space-y-6 text-center lg:text-left">
                                    <div className="inline-flex items-center gap-3 px-6 py-2 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-full text-[11px] font-black uppercase tracking-[0.4em] text-blue-400 shadow-2xl">
                                        <Sparkles size={16} fill="currentColor" /> Análisis de Flujo en Tiempo Real
                                    </div>
                                    <h2 className="text-5xl lg:text-7xl font-black tracking-tighter leading-none uppercase">Motor de <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 italic">Cuidado Perpetuo.</span></h2>
                                    <p className="text-xl text-slate-400 font-medium leading-relaxed max-w-2xl italic">
                                        &ldquo;Optimus Brain v3.9 procesa los eventos de la congregación cada 60 segundos. Si detecta un desvío en el crecimiento de un miembro, el motor activa el protocolo de restauración de forma inmediata.&rdquo;
                                    </p>
                                </div>
                                <div className="flex flex-wrap gap-6 justify-center lg:justify-start">
                                    <button className="px-12 py-6 bg-white text-slate-900 rounded-[2.5rem] font-black text-xs uppercase tracking-[0.3em] shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center gap-3"><Activity size={18} /> Auditoría del Motor</button>
                                    <button className="px-12 py-6 bg-white/5 backdrop-blur-md border border-white/10 text-white rounded-[2.5rem] font-black text-xs uppercase tracking-[0.3em] hover:bg-white/10 transition-all">Manual de Protocolos</button>
                                </div>
                            </div>
                        </div>
                    </motion.section>
                </div>
            </main>
        </div>
    );
}

function QuickStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="px-8 py-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[1.8rem] shadow-sm flex items-center gap-5 group hover:shadow-xl transition-all">
            <div className={clsx("size-10 rounded-xl flex items-center justify-center bg-slate-50 dark:bg-black/20", color)}>
                <Icon size={20} />
            </div>
            <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
                <p className="text-lg font-black text-slate-900 dark:text-white leading-none">{value}</p>
            </div>
        </div>
    );
}

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Award, 
    Search, 
    Filter, 
    Plus, 
    ChevronRight, 
    CheckCircle2, 
    Users, 
    Calendar, 
    Zap,
    Heart,
    Star,
    Sparkles,
    Flame,
    Navigation,
    MoreHorizontal,
    Loader2,
    Check
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const iconMap: Record<string, any> = {
    'zap': Zap,
    'flame': Flame,
    'star': Star,
    'award': Award,
    'sparkles': Sparkles,
    'heart': Heart
};

export default function SpiritualMilestones() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [milestones, setMilestones] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchMilestones = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/admin/milestones', { token, cache: 'no-store' });
            setMilestones(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar hitos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchMilestones();
    }, [isAuthenticated, fetchMilestones]);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .milestone-aura {
                    position: relative;
                }
                .milestone-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, #3b82f610), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .milestone-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Vida Espiritual', icon: Heart }, { label: 'Insignias e Hitos', icon: Award }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Nueva Insignia
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
                            <Sparkles size={12} className="animate-pulse" /> Reconocimiento del Crecimiento
                        </motion.div>
                        <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                            Consola de <br/> <span className="text-blue-600 italic">Hitos de Fe.</span>
                        </h1>
                    </header>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                                <Loader2 className="animate-spin text-blue-600" size={48} strokeWidth={1.5} /> Sincronizando Conquistas...
                            </div>
                        ) : (
                            <div className="space-y-16">
                                {/* Milestone Summary Cards */}
                                <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    {milestones.map((m, i) => {
                                        const Icon = iconMap[m.icon?.toLowerCase()] || Award;
                                        return (
                                            <motion.div 
                                                key={m.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: i * 0.05 }}
                                                className="milestone-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-10 rounded-[3.5rem] shadow-sm hover:shadow-2xl transition-all duration-500 overflow-hidden"
                                                style={{ '--aura-color': 'rgba(59, 130, 246, 0.15)' } as any}
                                            >
                                                <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-125 transition-transform duration-1000">
                                                    <Icon size={120} />
                                                </div>
                                                
                                                <div className="relative z-10 space-y-8">
                                                    <div className="size-16 rounded-[1.5rem] bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center shadow-inner group-hover:rotate-12 transition-transform duration-500">
                                                        <Icon size={32} strokeWidth={1.5} />
                                                    </div>
                                                    <div>
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-2">{m.description || 'Hito Ministerial'}</p>
                                                        <h3 className="text-3xl font-black text-slate-900 dark:text-white uppercase tracking-tighter leading-none mb-1">{m.name}</h3>
                                                        <p className="text-[11px] font-bold text-blue-500 uppercase tracking-widest">{m.count} Personas Alcanzadas</p>
                                                    </div>
                                                    <div className="pt-6 border-t border-slate-50 dark:border-white/5 flex items-center justify-between">
                                                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">+ {m.xp} XP Recompensa</span>
                                                        <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest flex items-center gap-2 hover:scale-105 transition-transform">
                                                            Gestionar <ChevronRight size={14} />
                                                        </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </section>

                                {/* Bulk Action Area Cinematic */}
                                <section className="bg-slate-900 p-12 lg:p-20 rounded-[4rem] text-white relative overflow-hidden group shadow-2xl">
                                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-blue-600/20 rounded-full blur-[120px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                                    
                                    <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                                        <div className="space-y-10">
                                            <div className="space-y-4">
                                                <div className="flex items-center gap-3 text-blue-400 font-black uppercase tracking-[0.4em] text-[10px]">
                                                    <Zap size={16} fill="currentColor" /> Optimus Brain Processing
                                                </div>
                                                <h2 className="text-4xl lg:text-6xl font-black tracking-tighter leading-none uppercase">Registro Masivo <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 italic">de Conquistas.</span></h2>
                                            </div>
                                            <p className="text-lg text-slate-400 font-medium leading-relaxed max-w-xl italic">
                                                &ldquo;Sube la nómina de vencedores y Optimus Brain se encargará de estampar los certificados digitales y actualizar las Hojas de Vida instantáneamente.&rdquo;
                                            </p>
                                            <div className="flex flex-wrap gap-4">
                                                <button className="px-10 py-5 bg-white text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-widest shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all">Iniciar Protocolo</button>
                                                <button className="px-10 py-5 bg-white/5 backdrop-blur-md border border-white/10 text-white rounded-[2rem] font-black text-xs uppercase tracking-widest hover:bg-white/10 transition-all">Ver Plantillas</button>
                                            </div>
                                        </div>
                                        <div className="hidden lg:flex justify-center relative">
                                            <div className="size-64 rounded-[4rem] border-4 border-blue-500/20 flex items-center justify-center animate-pulse">
                                                <div className="size-48 rounded-[3rem] bg-blue-600 flex items-center justify-center shadow-[0_0_50px_rgba(37,99,235,0.4)]">
                                                    <Check size={80} strokeWidth={3} className="text-white" />
                                                </div>
                                            </div>
                                            <div className="absolute -bottom-6 -right-6 p-6 bg-white rounded-[2rem] shadow-2xl text-slate-900">
                                                <Award size={40} className="text-blue-600" />
                                            </div>
                                        </div>
                                    </div>
                                </section>
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}


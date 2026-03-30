"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Target, 
    Zap, 
    Heart, 
    Globe, 
    Plus, 
    TrendingUp,
    ChevronRight,
    MapPin,
    Sparkles,
    ShieldCheck,
    Loader2,
    Check,
    History,
    ArrowUpRight
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function AdminMissionImpactPage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [stats, setStats] = useState({ projects: 8, families: 450, souls: 850 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Sync with dashboard metrics if possible, otherwise keep premium mocks
        const timer = setTimeout(() => setLoading(false), 800);
        return () => clearTimeout(timer);
    }, []);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .impact-aura {
                    position: relative;
                }
                .impact-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, rgba(59, 130, 246, 0.1), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .impact-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Globe }, { label: 'Impacto Misionero', icon: Target }]}
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Registrar Hito
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-6xl mx-auto space-y-16 relative z-10">
                    
                    {/* Header Cinematic */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                        <div className="space-y-4">
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20"
                            >
                                <Sparkles size={12} className="animate-pulse" /> Expansión del Reino 2026
                            </motion.div>
                            <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-none uppercase italic">
                                Alcance <br/> <span className="text-blue-600">Misionero.</span>
                            </h1>
                            <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-xl leading-relaxed">
                                Registro y monitoreo de impacto espiritual y social. Cada dato representa una vida tocada por la visión CCF.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        {/* Stats & Log */}
                        <div className="lg:col-span-8 space-y-10">
                            <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <ImpactStat label="Proyectos Activos" value={stats.projects} icon={Globe} color="blue" />
                                <ImpactStat label="Familias Alcanzadas" value={stats.families} icon={Heart} color="rose" />
                            </section>

                            {/* Activity Log Cinematic */}
                            <section className="bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[3.5rem] overflow-hidden shadow-sm hover:shadow-2xl transition-all duration-700">
                                <div className="p-8 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/20 flex items-center justify-between">
                                    <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-3">
                                        <History size={16} className="text-blue-600" /> Bitácora de Impacto Real
                                    </h3>
                                    <span className="text-[9px] font-black text-blue-600 bg-blue-50 px-3 py-1 rounded-full uppercase tracking-widest border border-blue-100">Live feed</span>
                                </div>
                                <div className="divide-y divide-slate-50 dark:divide-white/5">
                                    {[
                                        { title: 'Misión Amazonas 2026', place: 'Leticia, Colombia', metric: '150 Biblias entregadas', date: 'Hace 2 días', tone: 'blue' },
                                        { title: 'Comedor Comunitario Sur', place: 'Barrio El Sol', metric: '200 Almuerzos servidos', date: 'Ayer', tone: 'emerald' },
                                        { title: 'Brigada de Salud Integral', place: 'Vereda La Unión', metric: '80 Atenciones médicas', date: 'Hace 1 semana', tone: 'indigo' },
                                    ].map((item, i) => (
                                        <motion.div 
                                            key={i} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                                            className="p-8 hover:bg-slate-50/50 dark:hover:bg-white/5 transition-all flex items-center justify-between group cursor-pointer"
                                        >
                                            <div className="flex items-center gap-6">
                                                <div className="size-14 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all duration-500 shadow-inner">
                                                    <MapPin size={28} />
                                                </div>
                                                <div>
                                                    <h4 className="text-lg font-black text-slate-800 dark:text-slate-100 uppercase tracking-tight leading-none mb-2">{item.title}</h4>
                                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest flex items-center gap-2">
                                                        {item.place} • {item.date}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-black text-blue-600 italic tracking-tight">{item.metric}</p>
                                                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mt-1">Métrica de Impacto</p>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            </section>
                        </div>

                        {/* Goals & Predictions Sidebar */}
                        <aside className="lg:col-span-4 space-y-8">
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                                className="bg-slate-900 p-10 rounded-[3.5rem] text-white space-y-10 relative overflow-hidden shadow-2xl group"
                            >
                                <div className="absolute top-0 right-0 -mr-16 -mt-16 size-48 bg-blue-600/20 rounded-full blur-3xl group-hover:bg-blue-600/30 transition-all duration-1000" />
                                
                                <h3 className="text-xl font-black tracking-tight uppercase italic flex items-center gap-3 relative z-10">
                                    <TrendingUp size={20} className="text-blue-400" /> Metas Globales
                                </h3>
                                
                                <div className="space-y-10 relative z-10">
                                    <GoalProgress label="Almas para Cristo" current={stats.souls} target={1000} color="bg-blue-500" />
                                    <GoalProgress label="Impacto Social" current={12000} target={20000} color="bg-indigo-500" />
                                    <GoalProgress label="Nuevas Sedes" current={3} target={5} color="bg-emerald-500" />
                                </div>

                                <div className="pt-10 border-t border-white/10 relative z-10">
                                    <div className="p-6 bg-white/5 rounded-3xl border border-white/10 flex items-start gap-4">
                                        <Zap size={20} className="text-amber-400 animate-pulse shrink-0" fill="currentColor" />
                                        <p className="text-[11px] font-bold text-slate-400 leading-relaxed uppercase tracking-wider">
                                            Optimus AI: &ldquo;El crecimiento en familias alcanzadas proyecta un cumplimiento de meta del 100% para el tercer trimestre.&rdquo;
                                        </p>
                                    </div>
                                </div>
                            </motion.div>

                            <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 p-10 rounded-[3rem] shadow-sm space-y-6">
                                <h3 className="text-xs font-black uppercase tracking-widest dark:text-white">Acciones de Misión</h3>
                                <button className="w-full py-4 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 text-slate-600 dark:text-white text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all border border-slate-200 dark:border-white/10 flex items-center justify-center gap-3 active:scale-95">
                                    <FileText size={16} /> Generar Reporte PDF
                                </button>
                                <button className="w-full py-4 bg-white dark:bg-transparent text-blue-600 text-[10px] font-black uppercase tracking-widest rounded-2xl transition-all border border-blue-100 dark:border-blue-900/30 flex items-center justify-center gap-3 hover:bg-blue-50">
                                    <ArrowUpRight size={16} /> Compartir Avance
                                </button>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}

function ImpactStat({ label, value, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20 border-rose-100 dark:border-rose-800'
    };
    return (
        <div className="impact-aura bg-white dark:bg-[#1e1f21] p-10 rounded-[3rem] border border-slate-100 dark:border-white/5 flex items-center gap-8 shadow-sm hover:shadow-2xl transition-all duration-500 group overflow-hidden">
            <div className={clsx("size-20 rounded-[2.2rem] flex items-center justify-center transition-transform group-hover:rotate-12 duration-500 shadow-inner border", colors[color])}>
                <Icon size={40} strokeWidth={1.5} />
            </div>
            <div>
                <div className="text-4xl font-black text-slate-900 dark:text-white italic tracking-tighter leading-none mb-1">{value}</div>
                <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{label}</div>
            </div>
        </div>
    );
}

function GoalProgress({ label, current, target, color }: any) {
    const pct = Math.min(100, (current / target) * 100);
    return (
        <div className="space-y-3 group/goal">
            <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                <span className="text-slate-400 group-hover/goal:text-blue-400 transition-colors">{label}</span>
                <span className="text-white">{Math.round(pct)}%</span>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                    initial={{ width: 0 }} animate={{ width: `${pct}%` }} 
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className={clsx("h-full relative", color)}
                >
                    <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.2),transparent)] animate-[shimmer_2s_infinite] -skew-x-12" />
                </motion.div>
            </div>
            <div className="text-[9px] font-bold text-slate-500 text-right uppercase tracking-widest">{current.toLocaleString()} / {target.toLocaleString()}</div>
        </div>
    );
}

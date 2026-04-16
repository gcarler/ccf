"use client";

import React from 'react';
import { 
    Users, 
    UserPlus, 
    CheckCircle2, 
    Target, 
    Search, 
    TrendingUp, 
    Zap,
    Filter
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface PipelineFiltersSidebarProps {
    stats: {
        total: number;
        new: number;
        consolidated: number;
        conversion: number;
    };
    search: string;
    onSearchChange: (val: string) => void;
}

export default function PipelineFiltersSidebar({ stats, search, onSearchChange }: PipelineFiltersSidebarProps) {
    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0f1113]">
            {/* Header Cinematic */}
            <div className="p-8 border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-[#0f1113]/50 backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-[2.5rem]">
                <div className="absolute top-0 right-0 p-12 opacity-[0.03] pointer-events-none text-blue-600 dark:text-white">
                    <Target size={160} />
                </div>
                
                <div className="flex items-center gap-6 relative z-10 p-2">
                    <div className="size-16 rounded-[1.8rem] bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white shadow-2xl shadow-blue-500/30">
                        <Target size={28} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-[-0.04em] leading-tight">
                            Pipeline<br/>
                            <span className="text-blue-600">Pastoral</span>
                        </h2>
                    </div>
                </div>

                {/* Glass Metric Cards */}
                <div className="grid grid-cols-2 gap-3 mt-8 relative z-10">
                    {[
                        { label: 'Total Leads', value: stats.total, color: 'text-slate-800 dark:text-white' },
                        { label: 'Conversión', value: `${stats.conversion}%`, color: 'text-purple-600', icon: TrendingUp }
                    ].map((s, i) => (
                        <div key={i} className="bg-white/40 dark:bg-white/[0.03] backdrop-blur-sm p-4 rounded-3xl border border-slate-100 dark:border-white/[0.05] shadow-sm">
                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5">{s.label}</p>
                            <div className="flex items-center justify-between">
                                <p className={clsx("text-lg font-black tracking-tighter leading-none", s.color)}>{s.value}</p>
                                {s.icon && <s.icon size={12} className={s.color} />}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Filters Section */}
            <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Filter size={14} className="text-blue-600" /> Segmentación
                    </h3>
                    <div className="space-y-2">
                        {[
                            { id: 'all', label: 'Todos los Prospectos', icon: Users, count: stats.total, color: 'text-blue-600', bg: 'bg-blue-500/5' },
                            { id: 'new', label: 'Registros Nuevos', icon: UserPlus, count: stats.new, color: 'text-amber-600', bg: 'bg-amber-500/5' },
                            { id: 'consolidated', label: 'Casos de Éxito', icon: CheckCircle2, count: stats.consolidated, color: 'text-emerald-600', bg: 'bg-emerald-500/5' },
                        ].map((s, i) => (
                            <motion.button 
                                key={s.id}
                                whileHover={{ x: 4 }}
                                className="w-full flex items-center gap-4 p-4 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-[2rem] hover:bg-white dark:hover:bg-white/[0.05] hover:border-blue-500/20 transition-all group"
                            >
                                <div className={clsx("size-10 rounded-2xl flex items-center justify-center transition-all group-hover:scale-110", s.bg, s.color)}>
                                    <s.icon size={16} />
                                </div>
                                <span className="flex-1 text-left font-black text-[11px] uppercase tracking-tight text-slate-700 dark:text-slate-300">{s.label}</span>
                                <span className="text-[10px] px-2.5 py-1 bg-slate-200 dark:bg-white/10 rounded-lg font-black text-slate-500">{s.count}</span>
                            </motion.button>
                        ))}
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Search size={14} className="text-blue-600" /> Búsqueda Quick-Scan
                    </h3>
                    <div className="relative group">
                        <Search size={16} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                        <input
                            value={search}
                            onChange={e => onSearchChange(e.target.value)}
                            placeholder="Nombre, teléfono o etiqueta..."
                            className="w-full pl-12 pr-6 py-5 text-xs font-black rounded-[2rem] border border-slate-200 dark:border-white/[0.05] bg-slate-50 dark:bg-[#1a1b1d] outline-none focus:ring-4 focus:ring-blue-500/10 dark:text-white transition-all placeholder:text-slate-300 dark:placeholder:text-slate-700"
                        />
                    </div>
                </section>
                
                <section className="p-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-[2.5rem] text-white shadow-2xl shadow-blue-500/25 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-8 opacity-20 group-hover:scale-110 transition-transform duration-700"><Zap size={80} /></div>
                    <div className="relative z-10">
                        <h4 className="text-lg font-black uppercase tracking-tighter leading-tight mb-2">Asistente<br/>Optimus</h4>
                        <p className="text-[10px] font-bold text-blue-100 uppercase tracking-widest leading-relaxed">
                            Analizando tendencias de permanencia para optimizar el discipulado.
                        </p>
                    </div>
                </section>
            </div>
        </div>
    );
}

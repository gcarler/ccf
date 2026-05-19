"use client";

import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { 
    ChevronLeft, ChevronRight, Calendar, Info, 
    Clock, Zap, Layout
} from 'lucide-react';
import clsx from 'clsx';

interface GanttItem {
    id: string | number;
    title: string;
    subtitle?: string;
    start_date: string; // ISO or YYYY-MM-DD
    end_date: string;
    color?: 'blue' | 'purple' | 'emerald' | 'amber' | 'rose' | 'indigo';
    progress?: number; // 0-100
}

interface UniversalGanttViewProps {
    items: GanttItem[];
    moduleName?: string;
    onItemClick?: (item: GanttItem) => void;
    onOptimize?: () => void;
}

const COLORS = {
    blue: 'bg-blue-500 shadow-blue-500/20',
    purple: 'bg-sky-500 shadow-sky-500/20',
    emerald: 'bg-emerald-500 shadow-emerald-500/20',
    amber: 'bg-amber-500 shadow-amber-500/20',
    rose: 'bg-rose-500 shadow-rose-500/20',
    indigo: 'bg-indigo-600 shadow-indigo-500/20',
};

export default function UniversalGanttView({ items, moduleName = "Módulo", onItemClick, onOptimize }: UniversalGanttViewProps) {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const [zoom, setZoom] = useState<'day' | 'week' | 'month'>('week');
    
    // Generate scale (current month as default)
    const today = new Date();
    const days = Array.from({ length: 30 }, (_, i) => {
        const d = new Date(today);
        d.setDate(today.getDate() + i - 5); // Start 5 days ago
        return d;
    });

    const scroll = (direction: 'left' | 'right') => {
        if (!scrollContainerRef.current) return;
        const amount = direction === 'left' ? -400 : 400;
        scrollContainerRef.current.scrollBy({ left: amount, behavior: 'smooth' });
    };

    const getPosition = (dateStr: string) => {
        const date = new Date(dateStr);
        const startIndex = days.findIndex(d => d.toDateString() === date.toDateString());
        if (startIndex === -1) {
            // Check if before or after
            if (date < days[0]) return -100;
            return days.length * 160;
        }
        return startIndex * 160; // 160px per day
    };

    const getWidth = (start: string, end: string) => {
        const s = new Date(start);
        const e = new Date(end);
        const diff = Math.max(1, Math.ceil((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24)));
        return (diff + 1) * 160 - 20; // gap handling
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0b0d11] rounded-[2rem] border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
            
            {/* ─── Header de Controles ─── */}
            <div className="px-6 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-white/[0.02]">
                <div className="flex items-center gap-4">
                    <div className="flex bg-white dark:bg-white/5 rounded-xl border border-slate-200 dark:border-white/10 p-1 shadow-sm">
                        <button 
                            onClick={() => setZoom('day')}
                            className={clsx("px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all", zoom === 'day' ? "bg-slate-900 text-white dark:bg-white/10" : "text-slate-400 hover:text-slate-600")}
                        >Día</button>
                        <button 
                            onClick={() => setZoom('week')}
                            className={clsx("px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all", zoom === 'week' ? "bg-slate-900 text-white dark:bg-white/10" : "text-slate-400 hover:text-slate-600")}
                        >Semana</button>
                        <button 
                            onClick={() => setZoom('month')}
                            className={clsx("px-4 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-all", zoom === 'month' ? "bg-slate-900 text-white dark:bg-white/10" : "text-slate-400 hover:text-slate-600")}
                        >Mes</button>
                    </div>
                    <div className="h-6 w-px bg-slate-200 dark:bg-white/10" />
                    <p className="text-[11px] font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                        <Layout size={14} className="text-blue-500" /> {moduleName}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5 mr-4">
                        <button onClick={() => scroll('left')} className="p-2.5 rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-400 hover:text-blue-600 transition-all shadow-sm"><ChevronLeft size={16} /></button>
                        <button onClick={() => scroll('right')} className="p-2.5 rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-400 hover:text-blue-600 transition-all shadow-sm"><ChevronRight size={16} /></button>
                    </div>
                    {onOptimize && (
                        <button
                            onClick={onOptimize}
                            className="px-6 py-2.5 bg-slate-900 dark:bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2 shadow-xl shadow-blue-500/10 hover:scale-105 transition-all"
                        >
                            <Zap size={14} /> Optimus Brain
                        </button>
                    )}
                </div>
            </div>

            {/* ─── Scroll Area ─── */}
            <div className="flex-1 overflow-hidden flex flex-col">
                {/* Timeline Header */}
                <div 
                    ref={scrollContainerRef}
                    className="flex-1 overflow-x-auto scroll-smooth scrollbar-none relative"
                >
                    <div className="min-w-max h-full flex flex-col">
                        {/* Days scale */}
                        <div className="flex border-b border-slate-100 dark:border-white/5 bg-white dark:bg-[#0b0d11] sticky top-0 z-20">
                            {days.map((day, i) => (
                                <div key={i} className={clsx(
                                    "w-[160px] p-5 flex flex-col gap-1 border-r border-slate-100 dark:border-white/5",
                                    day.toDateString() === today.toDateString() ? "bg-blue-50/50 dark:bg-blue-500/5 text-blue-600" : "text-slate-500"
                                )}>
                                    <span className="text-[10px] font-black uppercase tracking-tighter opacity-60">
                                        {day.toLocaleDateString('es-ES', { weekday: 'long' })}
                                    </span>
                                    <span className="text-2xl font-black tracking-tighter italic leading-none">
                                        {day.getDate()} {day.toLocaleDateString('es-ES', { month: 'short' }).toUpperCase()}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Content Grid */}
                        <div className="relative flex-1 bg-slate-50/20 dark:bg-transparent min-h-[500px]">
                            {/* Vertical Grid Lines */}
                            <div className="absolute inset-0 flex">
                                {days.map((_, i) => (
                                    <div key={i} className="w-[160px] h-full border-r border-slate-100 dark:border-white/5 pointer-events-none" />
                                ))}
                            </div>

                            {/* Task/Item Bars */}
                            <div className="relative z-10 p-8 space-y-6">
                                {items.length === 0 ? (
                                    <div className="absolute inset-0 flex items-center justify-center p-20 opacity-20 select-none grayscale pointer-events-none">
                                        <div className="flex flex-col items-center gap-4">
                                            <Calendar size={120} strokeWidth={0.5} />
                                            <p className="text-[10px] font-black uppercase tracking-[0.5em]">No se detectan secuencias temporales activas</p>
                                        </div>
                                    </div>
                                ) : (
                                    items.map((item, idx) => {
                                        const pos = getPosition(item.start_date);
                                        const width = getWidth(item.start_date, item.end_date);
                                        
                                        return (
                                            <div key={item.id} className="h-14 relative group">
                                                <motion.div
                                                    initial={{ opacity: 0, x: pos - 20 }}
                                                    animate={{ opacity: 1, x: pos }}
                                                    transition={{ delay: idx * 0.05 }}
                                                    onClick={() => onItemClick?.(item)}
                                                    style={{ width: `${width}px` }}
                                                    className={clsx(
                                                        "absolute h-full rounded-2xl p-4 flex items-center justify-between cursor-pointer transition-all hover:scale-[1.02] active:scale-95 shadow-lg group-hover:shadow-2xl",
                                                        COLORS[item.color || 'blue']
                                                    )}
                                                >
                                                    <div className="flex items-center gap-3 overflow-hidden">
                                                        <div className="size-8 rounded-xl bg-white/20 flex items-center justify-center text-white shrink-0"><Clock size={16} /></div>
                                                        <div className="overflow-hidden">
                                                            <p className="text-[11px] font-black text-white uppercase tracking-tight truncate leading-none mb-1">{item.title}</p>
                                                            {item.subtitle && <p className="text-[9px] text-white/70 uppercase font-bold tracking-widest truncate">{item.subtitle}</p>}
                                                        </div>
                                                    </div>
                                                    {item.progress !== undefined && (
                                                        <div className="flex items-center gap-3 text-white/90">
                                                            <span className="text-[10px] font-black">{item.progress}%</span>
                                                            <div className="size-6 rounded-full border-2 border-white/20 flex items-center justify-center">
                                                                <div className="size-1.5 rounded-full bg-white animate-pulse" />
                                                            </div>
                                                        </div>
                                                    )}
                                                </motion.div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ─── Footer Informativo ─── */}
            <div className="px-8 py-4 border-t border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02] flex items-center justify-between">
                <div className="flex gap-6">
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-blue-500" />
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">En Curso</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-sky-500" />
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Planificado</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/20" />
                        <span className="text-[9px] font-black text-emerald-500 uppercase tracking-widest">Ejecución Exitosa</span>
                    </div>
                </div>
                <button className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-blue-600 transition-colors">
                    <Info size={14} /> Protocolo de Visualización
                </button>
            </div>
        </div>
    );
}

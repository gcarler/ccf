"use client";

import React, { useState, useEffect } from 'react';
import { 
    Calendar, 
    Users, 
    CheckCircle2, 
    Clock, 
    Plus, 
    ChevronRight, 
    MoreHorizontal,
    Music,
    Baby,
    Heart,
    Shield,
    Camera,
    Coffee,
    ArrowUpRight,
    Search,
    Filter,
    Bot,
    Zap,
    ChevronLeft
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

export default function VolunteerCalendar() {
    const { token, isAuthenticated } = useAuth();
    const [shifts, setShifts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'week' | 'list'>('week');

    useEffect(() => {
        // Quality Mock Data with day associations
        setShifts([
            { id: 1, title: 'Alabanza', dayIndex: 6, time: '08:00 AM', team: 'Alabanza', status: 'confirmed', icon: Music, color: 'blue' },
            { id: 2, title: 'Niños', dayIndex: 6, time: '10:30 AM', team: 'Generación G', status: 'pending', icon: Baby, color: 'purple' },
            { id: 3, title: 'Ujieres', dayIndex: 6, time: '08:00 AM', team: 'Hospitalidad', status: 'confirmed', icon: Coffee, color: 'amber' },
            { id: 4, title: 'Ensayo', dayIndex: 4, time: '06:30 PM', team: 'Alabanza', status: 'confirmed', icon: Music, color: 'blue' },
            { id: 5, title: 'Vigilia', dayIndex: 5, time: '08:00 PM', team: 'Oración', status: 'pending', icon: Zap, color: 'indigo' },
        ]);
        setLoading(false);
    }, []);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Servicio', icon: Heart },
                    { label: 'Calendario de Voluntariado', icon: Calendar }
                ]}
                viewType={viewMode === 'list' ? 'list' : 'grid'} 
                setViewType={(v: any) => setViewMode(v === 'grid' ? 'week' : 'list')}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Postularme
                    </button>
                }
            />

            <main className="flex-1 overflow-hidden flex flex-col p-8 lg:p-12">
                <div className="max-w-[1600px] mx-auto w-full flex-1 flex flex-col gap-8">
                    
                    {/* Header Controls */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 shrink-0">
                        <div className="flex items-center gap-6">
                            <h2 className="text-3xl font-black tracking-tighter text-slate-900 dark:text-white uppercase leading-none">Cronograma de Servicio</h2>
                            <div className="flex items-center gap-2 bg-white dark:bg-white/5 p-1 rounded-2xl border border-slate-200 dark:border-white/10 shadow-sm">
                                <button 
                                    onClick={() => setViewMode('week')}
                                    className={clsx("px-6 py-2 rounded-[0.9rem] text-[10px] font-black uppercase transition-all", 
                                    viewMode === 'week' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "text-slate-400 hover:text-slate-600")}
                                >
                                    Semana
                                </button>
                                <button 
                                    onClick={() => setViewMode('list')}
                                    className={clsx("px-6 py-2 rounded-[0.9rem] text-[10px] font-black uppercase transition-all", 
                                    viewMode === 'list' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "text-slate-400 hover:text-slate-600")}
                                >
                                    Lista
                                </button>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <button className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><ChevronLeft size={20} /></button>
                            <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-widest">23 - 29 Marzo, 2026</span>
                            <button className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><ChevronRight size={20} /></button>
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {viewMode === 'week' ? (
                            <motion.div 
                                key="week-grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                                className="flex-1 grid grid-cols-1 md:grid-cols-7 gap-4 min-h-0"
                            >
                                {DAYS.map((day, idx) => (
                                    <div key={day} className="flex flex-col gap-4 min-w-0 h-full">
                                        <div className="text-center p-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl shadow-sm shrink-0">
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1">{day}</p>
                                            <p className={clsx("text-lg font-black leading-none", idx === 6 ? "text-blue-600" : "text-slate-800 dark:text-white")}>{23 + idx}</p>
                                        </div>
                                        
                                        <div className="flex-1 bg-slate-100/30 dark:bg-black/10 rounded-[2rem] p-3 space-y-3 overflow-y-auto scrollbar-hide border-2 border-transparent hover:border-blue-500/10 transition-all">
                                            {shifts.filter(s => s.dayIndex === idx).map(shift => (
                                                <motion.div 
                                                    key={shift.id} whileHover={{ scale: 1.02 }}
                                                    className={clsx(
                                                        "p-4 rounded-2xl shadow-sm border border-transparent hover:border-white/20 transition-all cursor-pointer relative overflow-hidden group",
                                                        shift.color === 'blue' ? "bg-blue-600 text-white" : 
                                                        shift.color === 'purple' ? "bg-purple-600 text-white" : 
                                                        shift.color === 'amber' ? "bg-amber-500 text-white" : "bg-slate-800 text-white"
                                                    )}
                                                >
                                                    <div className="absolute top-0 right-0 -mr-4 -mt-4 p-6 opacity-10 group-hover:opacity-20 transition-all">
                                                        <shift.icon size={48} />
                                                    </div>
                                                    <div className="relative z-10 space-y-3">
                                                        <p className="text-[9px] font-black uppercase tracking-widest opacity-80">{shift.time}</p>
                                                        <h4 className="text-[13px] font-black uppercase leading-tight tracking-tight">{shift.title}</h4>
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex -space-x-2">
                                                                <div className="size-5 rounded-full border border-white/20 bg-white/10" />
                                                                <div className="size-5 rounded-full border border-white/20 bg-white/20" />
                                                            </div>
                                                            {shift.status === 'confirmed' && <CheckCircle2 size={14} className="text-white/80" />}
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            ))}
                                            <button className="w-full py-4 border-2 border-dashed border-slate-200 dark:border-white/5 rounded-2xl text-slate-400 hover:border-blue-500/30 hover:text-blue-500 transition-all flex items-center justify-center">
                                                <Plus size={16} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div 
                                key="list-view" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                                className="flex-1 space-y-4 overflow-y-auto scrollbar-thin pr-4 pb-20"
                            >
                                {shifts.map((shift) => (
                                    <div key={shift.id} className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all flex items-center justify-between">
                                        <div className="flex items-center gap-6">
                                            <div className={clsx("size-14 rounded-2xl flex items-center justify-center", 
                                                shift.color === 'blue' ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600")}>
                                                <shift.icon size={28} />
                                            </div>
                                            <div>
                                                <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase leading-none mb-2">{shift.title}</h4>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{shift.date} • {shift.time} • {shift.team}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <span className={clsx("px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest", 
                                                shift.status === 'confirmed' ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>
                                                {shift.status}
                                            </span>
                                            <button className="p-2 text-slate-300 hover:text-slate-600"><MoreHorizontal size={20} /></button>
                                        </div>
                                    </div>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}

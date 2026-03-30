"use client";

import React, { useEffect, useState, useMemo } from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    Calendar as CalendarIcon, 
    ChevronLeft, 
    ChevronRight, 
    Plus, 
    Filter,
    CheckCircle2,
    Clock,
    Users,
    Layers,
    Bell
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    format, 
    startOfMonth, 
    endOfMonth, 
    startOfWeek, 
    endOfWeek, 
    eachDayOfInterval, 
    isSameMonth, 
    isSameDay, 
    addMonths, 
    subMonths 
} from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

export default function GlobalCalendarPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [currentDate, setCurrentDate] = useState(new Date());
    const [events, setEvents] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchEvents = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<any[]>('/system/calendar', { token });
                setEvents(data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchEvents();
    }, [token]);

    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(currentDate), { weekStartsOn: 1 });
        const end = endOfWeek(endOfMonth(currentDate), { weekStartsOn: 1 });
        return eachDayOfInterval({ start, end });
    }, [currentDate]);

    const getEventsForDay = (day: Date) => {
        return events.filter(e => isSameDay(new Date(e.start), day));
    };

    return (
        <WorkspaceLayout sidebarTitle="Herramientas / Calendario Maestro">
            <div className="flex flex-col h-full bg-white dark:bg-[#141517] overflow-hidden font-display">
                
                {/* Header Profesional */}
                <header className="px-10 py-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/20 shrink-0">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2 bg-white dark:bg-[#1e1f21] p-1.5 rounded-2xl border border-slate-200 dark:border-white/10 shadow-sm">
                            <button onClick={() => setCurrentDate(subMonths(currentDate, 1))} className="p-2 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl text-slate-400 transition-all"><ChevronLeft size={18} /></button>
                            <button onClick={() => setCurrentDate(new Date())} className="px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:text-blue-600 transition-colors">Hoy</button>
                            <button onClick={() => setCurrentDate(addMonths(currentDate, 1))} className="p-2 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl text-slate-400 transition-all"><ChevronRight size={18} /></button>
                        </div>
                        <h2 className="text-2xl font-black text-slate-900 dark:text-white capitalize tracking-tight">
                            {format(currentDate, 'MMMM yyyy', { locale: es })}
                        </h2>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex gap-1 p-1 bg-slate-100 dark:bg-white/5 rounded-xl border border-slate-200 dark:border-white/10">
                            <ViewBtn active label="Mes" />
                            <ViewBtn active={false} label="Semana" />
                            <ViewBtn active={false} label="Día" />
                        </div>
                        <button className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 hover:scale-[1.02] active:scale-95 transition-all">
                            <Plus size={14} /> Nuevo Evento
                        </button>
                    </div>
                </header>

                {/* Grid del Calendario */}
                <div className="flex-1 overflow-hidden p-6 lg:p-10">
                    <div className="h-full border border-slate-200 dark:border-white/10 rounded-[3rem] bg-white dark:bg-[#1e1f21] overflow-hidden flex flex-col shadow-2xl shadow-black/5">
                        {/* Días de la semana */}
                        <div className="grid grid-cols-7 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/20">
                            {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map(d => (
                                <div key={d} className="py-4 text-center text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">{d}</div>
                            ))}
                        </div>

                        {/* Celdas de Días */}
                        <div className="flex-1 grid grid-cols-7 overflow-y-auto scrollbar-hide">
                            {days.map((day, idx) => {
                                const dayEvents = getEventsForDay(day);
                                return (
                                    <div 
                                        key={idx} 
                                        className={clsx(
                                            "min-h-[120px] p-4 border-r border-b border-slate-100 dark:border-white/5 relative group transition-colors hover:bg-slate-50/50 dark:hover:bg-white/[0.02]",
                                            !isSameMonth(day, currentDate) && "bg-slate-50/30 dark:bg-black/10 opacity-40"
                                        )}
                                    >
                                        <span className={clsx(
                                            "inline-flex size-7 items-center justify-center rounded-lg text-[11px] font-black transition-all",
                                            isSameDay(day, new Date()) ? "bg-blue-600 text-white shadow-lg shadow-blue-500/40 scale-110" : "text-slate-400 dark:text-slate-500 group-hover:text-slate-900 dark:group-hover:text-white"
                                        )}>
                                            {format(day, 'd')}
                                        </span>

                                        <div className="mt-3 space-y-1.5 overflow-hidden">
                                            {dayEvents.slice(0, 3).map((e: any) => (
                                                <div 
                                                    key={e.id}
                                                    onClick={() => router.push(e.href)}
                                                    className={clsx(
                                                        "px-2 py-1.5 rounded-lg border text-[9px] font-black uppercase tracking-tight flex items-center gap-2 cursor-pointer hover:scale-[1.02] active:scale-95 transition-all truncate",
                                                        e.type === 'task' ? "bg-blue-50 border-blue-100 text-blue-600 dark:bg-blue-900/20 dark:border-blue-800" :
                                                        e.type === 'crm' ? "bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:border-emerald-800" :
                                                        "bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-900/20 dark:border-rose-800"
                                                    )}
                                                >
                                                    {e.type === 'task' ? <Layers size={10} /> : e.type === 'crm' ? <Users size={10} /> : <Bell size={10} />}
                                                    <span className="truncate">{e.title}</span>
                                                </div>
                                            ))}
                                            {dayEvents.length > 3 && (
                                                <div className="text-[8px] font-black text-slate-400 pl-2 uppercase tracking-widest">
                                                    + {dayEvents.length - 3} más
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </WorkspaceLayout>
    );
}

function ViewBtn({ active, label }: any) {
    return (
        <button className={clsx(
            "px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all",
            active ? "bg-white dark:bg-[#1e1f21] text-blue-600 shadow-md" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
        )}>
            {label}
        </button>
    );
}

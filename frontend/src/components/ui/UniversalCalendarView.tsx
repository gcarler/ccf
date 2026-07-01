"use client";

import React, { useState } from 'react';
import { 
    ChevronLeft, ChevronRight, Calendar as CalendarIcon, 
    Plus, Sparkles, Maximize2
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface CalendarEvent {
    id: string | number;
    title: string;
    date: string; // YYYY-MM-DD
    time?: string;
    type?: 'permanent' | 'annual' | 'once';
    color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'sky';
    location?: string;
}

interface UniversalCalendarViewProps {
    events: CalendarEvent[];
    onDateClick?: (date: Date) => void;
    onEventClick?: (event: CalendarEvent) => void;
    onCreate?: () => void;
    title?: string;
}

const COLORS: any = {
    blue: 'bg-[hsl(var(--primary))] shadow-blue-500/20 text-white',
    sky: 'bg-sky-600 shadow-sky-500/20 text-white',
    emerald: 'bg-emerald-600 shadow-emerald-500/20 text-white',
    amber: 'bg-amber-600 shadow-amber-500/20 text-white',
    rose: 'bg-rose-600 shadow-rose-500/20 text-white',
};

const DAY_LABELS = ['DOM', 'LUN', 'MAR', 'MIE', 'JUE', 'VIE', 'SAB'];

export default function UniversalCalendarView({ events, onDateClick, onEventClick, onCreate, title = "Calendario Maestro" }: UniversalCalendarViewProps) {
    const [currentDate, setCurrentDate] = useState(new Date());
    
    // Calendar logic
    const startOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const endOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
    const daysInMonth = endOfMonth.getDate();
    const startDay = startOfMonth.getDay();

    const prevMonth = () => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() - 1)));
    const nextMonth = () => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() + 1)));

    const days: (Date | null)[] = [];
    // Previous month padding
    for (let i = 0; i < startDay; i++) {
        days.push(null);
    }
    // Days of month
    for (let i = 1; i <= daysInMonth; i++) {
        days.push(new Date(currentDate.getFullYear(), currentDate.getMonth(), i));
    }

    const getEventsForDay = (day: Date) => {
        const iso = day.toISOString().split('T')[0];
        return events.filter(e => e.date === iso);
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0b0d11] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden shadow-sm">
            
            {/* ─── Control Header ─── */}
            <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-lg bg-blue-50 dark:bg-[hsl(var(--primary))]/10 flex items-center justify-center text-[hsl(var(--primary))] border border-blue-100/50 dark:border-[hsl(var(--primary))]/20">
                        <CalendarIcon size={28} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold tracking-tighter text-[hsl(var(--text-primary))] dark:text-white uppercase italic leading-none">{title}</h2>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{currentDate.toLocaleString('es-ES', { month: 'long', year: 'numeric' })}</span>
                            <Sparkles size={12} className="text-amber-500" />
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1.5 rounded-lg gap-1">
                        <button onClick={prevMonth} className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm"><ChevronLeft size={18} /></button>
                        <button onClick={() => setCurrentDate(new Date())} className="px-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors">Hoy</button>
                        <button onClick={nextMonth} className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm"><ChevronRight size={18} /></button>
                    </div>
                    {onCreate && (
                        <button
                            onClick={onCreate}
                            className="p-4 bg-[hsl(var(--bg-muted))] dark:bg-white/10 text-white rounded-lg shadow-xl shadow-black/20 hover:scale-105 transition-all"
                        >
                            <Plus size={20} />
                        </button>
                    )}
                </div>
            </div>

            {/* ─── Calendar Grid ─── */}
            <div className="flex-1 overflow-hidden flex flex-col p-3 p-4">
                {/* Labels */}
                <div className="grid grid-cols-7 gap-1 mb-4">
                    {DAY_LABELS.map(label => (
                        <div key={label} className="py-3 text-center font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{label}</div>
                    ))}
                </div>

                {/* Days Grid */}
                <div className="flex-1 grid grid-cols-7 gap-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg p-1 overflow-hidden border border-[hsl(var(--border))] dark:border-white/5">
                    {days.map((day, idx) => {
                        if (!day) return <div key={`empty-${idx}`} className="bg-white/40 dark:bg-black/20" />;
                        
                        const dayEvents = getEventsForDay(day);
                        const isToday = day.toDateString() === new Date().toDateString();

                        return (
                            <motion.div 
                                key={day.toISOString()}
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: idx * 0.005 }}
                                onClick={() => onDateClick?.(day)}
                                className={clsx(
                                    "min-h-[140px] p-4 flex flex-col gap-3 transition-all cursor-pointer group relative overflow-hidden",
                                    isToday ? "bg-blue-50/50 dark:bg-[hsl(var(--primary))]/10" : "bg-[hsl(var(--bg-primary))] dark:bg-[#0b0d11] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]"
                                )}
                            >
                                <div className="flex items-center justify-between relative z-10">
                                    <span className={clsx(
                                        "text-xl font-bold italic tracking-tighter leading-none",
                                        isToday ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-primary))] dark:group-hover:text-white"
                                    )}>
                                        {day.getDate()}
                                    </span>
                                    {isToday && <div className="size-2 rounded-full bg-[hsl(var(--primary))] animate-ping" />}
                                </div>

                                <div className="space-y-1.5 overflow-hidden">
                                    {dayEvents.slice(0, 3).map((ev) => (
                                        <button
                                            key={ev.id}
                                            onClick={(e) => { e.stopPropagation(); onEventClick?.(ev); }}
                                            className={clsx(
                                                "w-full text-left p-2 rounded-md text-[10px] font-semibold uppercase tracking-tight truncate transition-all hover:scale-[1.03] active:scale-95",
                                                COLORS[ev.color || 'blue']
                                            )}
                                        >
                                            {ev.title}
                                        </button>
                                    ))}
                                    {dayEvents.length > 3 && (
                                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-2">+{dayEvents.length - 3} más</p>
                                    )}
                                </div>

                                {/* Hover effect background */}
                                <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-10 transition-opacity">
                                    <Maximize2 size={60} className="text-[hsl(var(--primary))]" />
                                </div>
                            </motion.div>
                        );
                    })}
                </div>
            </div>

            {/* ─── Summary Footer ─── */}
            <div className="px-4 py-1.5 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                <div className="flex gap-3">
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-[hsl(var(--primary))]" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Servicios Centrales</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-emerald-600" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Eventos de Red</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-amber-600" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Consejería Especial</span>
                    </div>
                </div>
                <div className="flex items-center gap-4 text-[hsl(var(--text-secondary))] text-[10px] font-semibold uppercase tracking-wide">
                    <span>Vistas:</span>
                    <button className="text-[hsl(var(--primary))]">Mes</button>
                    <button className="hover:text-[hsl(var(--text-secondary))]">Semana</button>
                    <button className="hover:text-[hsl(var(--text-secondary))]">Día</button>
                </div>
            </div>
        </div>
    );
}

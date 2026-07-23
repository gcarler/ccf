"use client";

import React, { useState } from 'react';
import { 
    ChevronLeft, ChevronRight, Calendar as CalendarIcon, 
    Plus, Sparkles, Maximize2
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export interface CalendarEvent {
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
    onEventMove?: (event: CalendarEvent, date: Date) => void;
    onCreate?: () => void;
    title?: string;
}

const COLORS: any = {
    blue: 'bg-[hsl(var(--primary))] shadow-[hsl(var(--primary))/0.2] text-white',
    sky: 'bg-[hsl(var(--info))] shadow-[hsl(var(--info))/0.2] text-white',
    emerald: 'bg-[hsl(var(--success))] shadow-[hsl(var(--success))/0.2] text-white',
    amber: 'bg-[hsl(var(--warning))] shadow-[hsl(var(--warning))/0.2] text-white',
    rose: 'bg-[hsl(var(--danger))] shadow-[hsl(var(--danger))/0.2] text-white',
};

const DAY_LABELS = ['DOM', 'LUN', 'MAR', 'MIE', 'JUE', 'VIE', 'SAB'];

function toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

export default function UniversalCalendarView({ events, onDateClick, onEventClick, onEventMove, onCreate, title = "Calendario Maestro" }: UniversalCalendarViewProps) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [draggedEvent, setDraggedEvent] = useState<CalendarEvent | null>(null);
    const [dragOverDay, setDragOverDay] = useState<Date | null>(null);
    const dragOverCounts = React.useRef<Record<string, number>>({});
    
    // Calendar logic
    const startOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const endOfMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
    const daysInMonth = endOfMonth.getDate();
    const startDay = startOfMonth.getDay();

    const prevMonth = () => setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
    const nextMonth = () => setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));

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
        const iso = toDateKey(day);
        return events.filter(e => e.date?.slice(0, 10) === iso);
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden shadow-sm">
            
            {/* ─── Control Header ─── */}
            <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-lg bg-info-soft dark:bg-[hsl(var(--info)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] border border-[hsl(var(--info)/0.2)] dark:border-[hsl(var(--info)/0.2)]">
                        <CalendarIcon size={28} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold tracking-tighter text-[hsl(var(--text-primary))] dark:text-white uppercase italic leading-none">{title}</h2>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{currentDate.toLocaleString('es-ES', { month: 'long', year: 'numeric' })}</span>
                            <Sparkles size={12} className="text-[hsl(var(--warning))]" />
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
                                onDragOver={(e) => e.preventDefault()}
                                onDragEnter={(e) => {
                                    e.preventDefault();
                                    const key = day.toDateString();
                                    dragOverCounts.current[key] = (dragOverCounts.current[key] ?? 0) + 1;
                                    // Force re-render to apply highlight
                                    setDragOverDay(day);
                                }}
                                onDragLeave={() => {
                                    const key = day.toDateString();
                                    dragOverCounts.current[key] = Math.max(0, (dragOverCounts.current[key] ?? 0) - 1);
                                    if (dragOverCounts.current[key] === 0) {
                                        setDragOverDay((prev) => (prev?.toDateString() === key ? null : prev));
                                    }
                                }}
                                onDrop={(e) => {
                                    e.preventDefault();
                                    if (draggedEvent) {
                                        onEventMove?.(draggedEvent, day);
                                    }
                                    setDraggedEvent(null);
                                    dragOverCounts.current = {};
                                    setDragOverDay(null);
                                }}
                                className={clsx(
                                    "min-h-[140px] p-4 flex flex-col gap-3 transition-all cursor-pointer group relative overflow-hidden",
                                    isToday ? "bg-info-soft dark:bg-[hsl(var(--primary))]/10" : "bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]",
                                    dragOverDay?.toDateString() === day.toDateString() && "ring-2 ring-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--primary))]/10"
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
                                            draggable
                                            onClick={(e) => { e.stopPropagation(); onEventClick?.(ev); }}
                                            onDragStart={(e) => {
                                                e.stopPropagation();
                                                setDraggedEvent(ev);
                                                e.dataTransfer.effectAllowed = 'move';
                                            }}
                                            onDragEnd={() => {
                                                setDraggedEvent(null);
                                                dragOverCounts.current = {};
                                                setDragOverDay(null);
                                            }}
                                            className={clsx(
                                                "w-full text-left p-2 rounded-md text-[10px] font-semibold uppercase tracking-tight truncate transition-all hover:scale-[1.03] active:scale-95 cursor-move",
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
                        <div className="size-2 rounded-full bg-[hsl(var(--success))]" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Eventos de Red</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-[hsl(var(--warning))]" />
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

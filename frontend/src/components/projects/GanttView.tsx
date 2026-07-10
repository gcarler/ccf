"use client";

import React, { useMemo, useRef, useState } from 'react';
import { 
    format, 
    addDays, 
    startOfMonth, 
    endOfMonth, 
    eachDayOfInterval, 
    isSameDay, 
    differenceInDays,
    startOfDay,
    addMonths,
    subMonths
} from 'date-fns';
import { es } from 'date-fns/locale';
import { 
    ChevronLeft, 
    ChevronRight, 
    Calendar as CalendarIcon,
    Plus
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface GanttViewProps {
    tasks: any[];
    onTaskClick: (task: any) => void;
}

export default function GanttView({ tasks, onTaskClick }: GanttViewProps) {
    const [viewDate, setViewDate] = useState(new Date());
    const timelineRef = useRef<HTMLDivElement>(null);

    const days = useMemo(() => {
        const start = startOfMonth(viewDate);
        const end = endOfMonth(addMonths(viewDate, 1)); // Show 2 months for context
        return eachDayOfInterval({ start, end });
    }, [viewDate]);

    // Auto-scroll to today on mount and when month changes
    React.useEffect(() => {
        if (!timelineRef.current || days.length === 0) return;
        const todayOffset = differenceInDays(startOfDay(new Date()), startOfDay(days[0]));
        const scrollX = Math.max(0, todayOffset * dayWidth - 200);
        timelineRef.current.scrollTo({ left: scrollX, behavior: 'smooth' });
    }, [days]);

    const months = useMemo(() => {
        const result: any[] = [];
        let current = startOfMonth(viewDate);
        result.push({ date: current, days: eachDayOfInterval({ start: current, end: endOfMonth(current) }) });
        current = addMonths(current, 1);
        result.push({ date: current, days: eachDayOfInterval({ start: current, end: endOfMonth(current) }) });
        return result;
    }, [viewDate]);

    const dayWidth = 40; // Pixels per day

    const getTaskStyles = (task: any) => {
        const startRaw = task.start_date || task.created_at || new Date().toISOString();
        const endRaw = task.due_date;
        
        const startDate = new Date(startRaw);
        const endDate = endRaw ? new Date(endRaw) : addDays(startDate, 3);
        
        const duration = Math.max(1, differenceInDays(endDate, startDate));
        
        const offsetDays = differenceInDays(startOfDay(startDate), startOfDay(days[0]));
        const left = offsetDays * dayWidth;
        const width = duration * dayWidth;

        // Color by status/priority (aligned with backend phase slugs)
        const colorMap: Record<string, string> = {
            todo:        'bg-[hsl(var(--surface-2))] shadow-slate-500/20',
            in_progress: 'bg-[hsl(var(--primary))] shadow-blue-500/25',
            review:      'bg-amber-500 shadow-amber-500/20',
            completed:   'bg-emerald-500 shadow-emerald-500/25',
        };

        const prioMap: Record<string, string> = {
            urgent: 'bg-rose-600 shadow-rose-500/25',
            high:   'bg-orange-500 shadow-orange-500/25',
        };
        const barColor = task.priority ? (prioMap[task.priority] ?? null) : null;
        const barClass = barColor ?? colorMap[task.status ?? ''] ?? 'bg-[hsl(var(--primary))] shadow-blue-500/20';

        return { left, width, barClass };
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden select-none">
            {/* Gantt Header Control */}
            <div className="h-10 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between px-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 shrink-0">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 bg-[hsl(var(--bg-primary))] dark:bg-black/20 p-0.5 rounded-md border border-[hsl(var(--border))] dark:border-white/10 shadow-sm">
                        <button onClick={() => setViewDate(subMonths(viewDate, 1))} className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded text-[hsl(var(--text-secondary))] transition-all"><ChevronLeft size={14} /></button>
                        <button onClick={() => setViewDate(new Date())} className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors">Hoy</button>
                        <button onClick={() => setViewDate(addMonths(viewDate, 1))} className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded text-[hsl(var(--text-secondary))] transition-all"><ChevronRight size={14} /></button>
                    </div>
                    <span className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide">
                        {format(viewDate, 'MMMM yyyy', { locale: es })}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-2 py-1 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm">
                        <CalendarIcon size={12} /> Día
                    </button>
                    <button className="flex items-center gap-1.5 px-2 py-1 bg-[hsl(var(--surface-2))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Semana</button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Task Sidebar */}
                <aside className="w-72 border-r border-[hsl(var(--border))] dark:border-white/5 flex flex-col shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] z-20 shadow-[10px_0_30px_rgba(0,0,0,0.02)]">
                    <div className="h-10 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-3 bg-[hsl(var(--surface-1))]/30 dark:bg-white/5">
                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre de Tarea</span>
                    </div>
                    <div className="flex-1 overflow-y-auto scrollbar-none">
                        {tasks.map((task) => (
                            <div
                                key={task.id}
                                onClick={() => onTaskClick(task)}
                                className="h-8 flex items-center px-3 border-b border-[hsl(var(--border))] dark:border-white/5 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-colors cursor-pointer group"
                            >
                                <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate group-hover:text-[hsl(var(--primary))] transition-colors">{task.title}</span>
                            </div>
                        ))}
                        <button className="w-full h-8 flex items-center gap-2 px-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors text-[10px] font-bold uppercase tracking-wide">
                            <Plus size={14} /> Nuevo
                        </button>
                    </div>
                </aside>

                {/* Timeline Grid */}
                <div className="flex-1 overflow-x-auto scrollbar-thin relative bg-[hsl(var(--surface-1))]/20 dark:bg-[#1a1b1d]" ref={timelineRef}>
                    {/* Month/Day Header */}
                    <div className="sticky top-0 z-10">
                        <div className="h-10 flex border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21]">
                            {months.map((m, i) => (
                                <div 
                                    key={i} 
                                    style={{ width: m.days.length * dayWidth }}
                                    className="h-full flex items-center px-4 border-r border-[hsl(var(--border))] dark:border-white/5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide"
                                >
                                    {format(m.date, 'MMMM yyyy', { locale: es })}
                                </div>
                            ))}
                        </div>
                        <div className="h-10 flex bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border-b border-[hsl(var(--border))] dark:border-white/5">
                            {days.map((day) => (
                                <div 
                                    key={day.toISOString()} 
                                    style={{ width: dayWidth }}
                                    className={clsx(
                                        "h-full flex items-center justify-center shrink-0 border-r border-[hsl(var(--border))] dark:border-white/5 text-[10px] font-bold",
                                        isSameDay(day, new Date()) ? "bg-blue-500/10 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]"
                                    )}
                                >
                                    {format(day, 'd')}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Task Rows */}
                    <div className="relative" style={{ width: days.length * dayWidth }}>
                        {/* Grid Lines Overlay */}
                        <div className="absolute inset-0 flex pointer-events-none">
                            {days.map((_, i) => (
                                <div key={i} style={{ width: dayWidth }} className="h-full border-r border-[hsl(var(--border))]/50 dark:border-white/5 shrink-0" />
                            ))}
                        </div>

                        {/* Today Marker */}
                        <div 
                            className="absolute top-0 bottom-0 w-[2px] bg-[hsl(var(--primary))] z-30 shadow-[0_0_10px_rgba(59,130,246,0.5)]"
                            style={{ left: differenceInDays(startOfDay(new Date()), startOfDay(days[0])) * dayWidth + (dayWidth/2) }}
                        >
                            <div className="size-2 rounded-full bg-[hsl(var(--primary))] absolute -left-[3px] -top-1" />
                        </div>

                        {/* Bars */}
                        <div className="relative pt-0">
                            {tasks.map((task, idx) => {
                                const { left, width, barClass } = getTaskStyles(task);
                                return (
                                    <div key={task.id} className="h-8 flex items-center relative border-b border-[hsl(var(--border))]/50 dark:border-white/5">
                                        <motion.div
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            style={{ left, width }}
                                            onClick={() => onTaskClick(task)}
                                            className={clsx(
                                                'absolute h-5 rounded-md shadow-lg cursor-pointer group/bar flex items-center px-2 gap-1.5 overflow-hidden',
                                                barClass
                                            )}
                                        >
                                            {/* Progress Shimmer */}
                                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover/bar:animate-shimmer" />
                                            
                                            <div className="flex-1 min-w-0 flex items-center gap-1.5 relative z-10">
                                                <div className="size-3 rounded bg-white/20 flex items-center justify-center shrink-0">
                                                    <CheckCircle size={8} className="text-white" />
                                                </div>
                                                <span className="text-[10px] font-bold text-white truncate uppercase tracking-wide">{task.title}</span>
                                            </div>
                                            
                                            {/* End Handle */}
                                            <div className="w-1.5 h-4 rounded-full bg-white/30 shrink-0 opacity-0 group-hover/bar:opacity-100 transition-opacity" />
                                        </motion.div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function CheckCircle({ size, className }: any) {
    return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M20 6 9 17l-5-5"/></svg>;
}

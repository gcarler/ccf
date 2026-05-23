"use client";

import React, { useState, useMemo } from 'react';
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
    subMonths,
    isToday
} from 'date-fns';
import { es } from 'date-fns/locale';
import { 
    ChevronLeft, 
    ChevronRight, 
    Plus, 
    Clock,
    CheckCircle2,
    Users,
    AlignLeft
} from 'lucide-react';
import * as Popover from '@radix-ui/react-popover';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface CalendarProps {
    tasks: any[];
    onTaskClick: (task: any) => void;
}

export default function ProjectCalendarView({ tasks, onTaskClick }: CalendarProps) {
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);

    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(currentMonth), { weekStartsOn: 1 });
        const end = endOfWeek(endOfMonth(currentMonth), { weekStartsOn: 1 });
        return eachDayOfInterval({ start, end });
    }, [currentMonth]);

    const getTasksForDay = (day: Date) => {
        return tasks.filter(task => {
            const dateStr = task.due_date || task.dueDate;
            return dateStr && isSameDay(new Date(dateStr), day);
        });
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            {/* Calendar Header */}
            <div className="h-10 border-b border-slate-100 dark:border-white/5 flex items-center justify-between px-3 bg-slate-50/50 dark:bg-white/5 shrink-0">
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 bg-white dark:bg-black/20 p-0.5 rounded-md border border-slate-200 dark:border-white/10 shadow-sm">
                        <button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded text-slate-500 transition-all"><ChevronLeft size={14} /></button>
                        <button onClick={() => setCurrentMonth(new Date())} className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 hover:text-blue-600 transition-colors">Hoy</button>
                        <button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded text-slate-500 transition-all"><ChevronRight size={14} /></button>
                    </div>
                    <h3 className="text-sm font-bold text-slate-800 dark:text-white uppercase tracking-tighter">
                        {format(currentMonth, 'MMMM yyyy', { locale: es })}
                    </h3>
                </div>
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-blue-600 shadow-md">Mes</button>
                    <button className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-bold uppercase tracking-wide text-slate-400">Semana</button>
                </div>
            </div>

            {/* Weekday Labels */}
            <div className="grid grid-cols-7 border-b border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] z-10">
                {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map(day => (
                    <div key={day} className="py-2 text-center text-[10px] font-black text-slate-400 uppercase tracking-widest">{day}</div>
                ))}
            </div>

            {/* Calendar Grid */}
            <div className="flex-1 overflow-y-auto scrollbar-thin grid grid-cols-7 grid-rows-5 lg:grid-rows-6">
                {days.map((day, idx) => {
                    const dayTasks = getTasksForDay(day);
                    const dayKey = format(day, 'yyyy-MM-dd');
                    return (
                        <Popover.Root key={idx} open={openPopoverDay === dayKey} onOpenChange={(open) => setOpenPopoverDay(open ? dayKey : null)}>
                            <Popover.Trigger asChild>
                                <div 
                                    className={clsx(
                                        "min-h-[80px] p-1.5 border-r border-b border-slate-50 dark:border-white/5 transition-colors relative group cursor-pointer",
                                        !isSameMonth(day, currentMonth) ? "bg-slate-50/50 dark:bg-black/10" : "bg-white dark:bg-[#1e1f21]",
                                        isToday(day) && "bg-blue-50/20 dark:bg-blue-500/5",
                                        openPopoverDay === dayKey && "ring-2 ring-inset ring-blue-500/50"
                                    )}
                                >
                                    <header className="flex justify-between items-center mb-2">
                                        <span className={clsx(
                                            "size-6 flex items-center justify-center text-[11px] font-black rounded-full transition-all",
                                            isToday(day) ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200"
                                        )}>
                                            {format(day, 'd')}
                                        </span>
                                        <button
                                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 transition-all"
                                            aria-label={`Añadir evento el ${format(day, 'd MMM')}`}
                                        >
                                            <Plus size={12} />
                                        </button>
                                    </header>

                                    <div className="space-y-1 overflow-y-auto max-h-[80px] scrollbar-none">
                                        {dayTasks.map(task => (
                                            <motion.div
                                                key={task.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onTaskClick(task);
                                                }}
                                                className={clsx(
                                                    "px-2 py-1 rounded-lg text-[10px] font-bold border cursor-pointer transition-all truncate shadow-sm",
                                                    task.status === 'COMPLETADA'
                                                        ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-900/30 text-emerald-600 dark:text-emerald-400"
                                                        : "bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-900/30 text-blue-600 dark:text-blue-400"
                                                )}
                                            >
                                                <div className="flex items-center gap-1.5 truncate">
                                                    {task.status === 'COMPLETADA' ? <CheckCircle2 size={10} /> : <div className="size-1.5 rounded-full bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]" />}
                                                    {task.title}
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            </Popover.Trigger>
                            
                            <Popover.Portal>
                                <Popover.Content 
                                    side="right" 
                                    align="start" 
                                    sideOffset={8}
                                    className="z-[60] w-[340px] bg-white dark:bg-[#25262b] rounded-lg shadow-2xl shadow-black/10 dark:shadow-black/40 border border-slate-100 dark:border-white/10 p-3 font-display flex flex-col gap-3 animate-in fade-in zoom-in-95 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <div className="flex flex-col gap-1">
                                        <input
                                            autoFocus
                                            type="text"
                                            placeholder="Añade un título..."
                                            className="w-full text-base font-medium bg-transparent border-none outline-none placeholder:text-slate-400 text-slate-800 dark:text-white mb-2"
                                        />
                                        <div className="flex gap-2 text-[11px] font-bold uppercase tracking-wide">
                                            <button className="flex-1 py-1 bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 rounded-md border border-blue-100 dark:border-blue-500/20">Evento</button>
                                            <button className="flex-1 py-1 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md transition-colors">Tarea</button>
                                        </div>
                                    </div>

                                    <div className="flex flex-col gap-3">
                                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0">
                                                <Clock size={14} className="text-slate-400" />
                                            </div>
                                            <div className="flex flex-col text-[12px]">
                                                <span className="font-semibold">{format(day, 'EEEE, d MMMM', { locale: es })}</span>
                                                <span className="text-slate-400 text-[11px]">Todo el día • Seleccionar hora</span>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0">
                                                <Users size={14} className="text-slate-400" />
                                            </div>
                                            <input type="text" placeholder="Añadir invitados" className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400" />
                                        </div>

                                        <div className="flex items-start gap-3 text-slate-600 dark:text-slate-300">
                                            <div className="size-8 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center shrink-0 mt-1">
                                                <AlignLeft size={14} className="text-slate-400" />
                                            </div>
                                            <textarea 
                                                rows={2} 
                                                placeholder="Añadir descripción..." 
                                                className="text-[12px] bg-transparent outline-none w-full placeholder:text-slate-400 py-2 resize-none" 
                                            />
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-white/10">
                                        <button
                                            onClick={() => setOpenPopoverDay(null)}
                                            className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md transition-colors"
                                        >
                                            Cerrar
                                        </button>
                                        <button
                                            onClick={() => setOpenPopoverDay(null)}
                                            className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 rounded-md transition-all active:scale-95"
                                        >
                                            Guardar
                                        </button>
                                    </div>
                                </Popover.Content>
                            </Popover.Portal>
                        </Popover.Root>
                    );
                })}
            </div>
        </div>
    );
}

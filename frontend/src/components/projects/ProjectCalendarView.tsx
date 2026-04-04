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
    addDays,
    isToday
} from 'date-fns';
import { es } from 'date-fns/locale';
import { 
    ChevronLeft, 
    ChevronRight, 
    Plus, 
    MoreHorizontal, 
    Calendar as CalendarIcon,
    Clock,
    CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface CalendarProps {
    tasks: any[];
    onTaskClick: (task: any) => void;
    onAddTask?: (status: string, date?: string, title?: string) => void;
}

export default function ProjectCalendarView({ tasks, onTaskClick, onAddTask }: CalendarProps) {
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [addingForDay, setAddingForDay] = useState<Date | null>(null);
    const [newTaskTitle, setNewTaskTitle] = useState('');

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
            <div className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center justify-between px-6 bg-slate-50/50 dark:bg-white/5 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 bg-white dark:bg-black/20 p-1 rounded-xl border border-slate-200 dark:border-white/10 shadow-sm">
                        <button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-500 transition-all"><ChevronLeft size={16} /></button>
                        <button onClick={() => setCurrentMonth(new Date())} className="px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:text-blue-600 transition-colors">Hoy</button>
                        <button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-500 transition-all"><ChevronRight size={16} /></button>
                    </div>
                    <h3 className="text-[15px] font-black text-slate-800 dark:text-white uppercase tracking-tighter">
                        {format(currentMonth, 'MMMM yyyy', { locale: es })}
                    </h3>
                </div>
                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-blue-600 shadow-md">Mes</button>
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-400">Semana</button>
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
                    return (
                        <div 
                            key={idx}
                            className={clsx(
                                "min-h-[120px] p-2 border-r border-b border-slate-50 dark:border-white/5 transition-colors relative group",
                                !isSameMonth(day, currentMonth) ? "bg-slate-50/50 dark:bg-black/10" : "bg-white dark:bg-[#1e1f21]",
                                isToday(day) && "bg-blue-50/20 dark:bg-blue-500/5"
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
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setAddingForDay(day);
                                        setNewTaskTitle('');
                                    }}
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 transition-all"
                                    aria-label={`Add task on ${format(day, 'd MMM')}`}
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
                                        onClick={() => onTaskClick(task)}
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

                                {/* Inline add for this day */}
                                {addingForDay && isSameDay(addingForDay, day) && (
                                    <div
                                        className="mt-1"
                                        onClick={e => e.stopPropagation()}
                                    >
                                        <input
                                            autoFocus
                                            type="text"
                                            value={newTaskTitle}
                                            onChange={e => setNewTaskTitle(e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter' && newTaskTitle.trim()) {
                                                    onAddTask?.('todo', format(day, 'yyyy-MM-dd'), newTaskTitle);
                                                    setAddingForDay(null);
                                                    setNewTaskTitle('');
                                                }
                                                if (e.key === 'Escape') {
                                                    setAddingForDay(null);
                                                    setNewTaskTitle('');
                                                }
                                            }}
                                            placeholder="Nueva tarea..."
                                            className="w-full text-[10px] px-1.5 py-1 rounded-md border border-blue-300 dark:border-blue-700 bg-white dark:bg-[#1e1f21] text-slate-800 dark:text-slate-200 outline-none placeholder:text-slate-400"
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

"use client";

import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import {
    ChevronLeft, ChevronRight, Plus, Search, Settings2,
    Star, Flag, Clock, Users, Bell, Layers, RefreshCw,
    StickyNote, CalendarDays, ChevronDown, X, Workflow,
    Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    format, startOfWeek, endOfWeek, eachDayOfInterval,
    isSameDay, addWeeks, subWeeks, addDays, isToday,
    startOfMonth, endOfMonth, eachWeekOfInterval, addMonths, subMonths,
    isSameMonth, getHours, getMinutes
} from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import type { ProjectTaskRecord } from '@/types/projects';

// ── Constants ────────────────────────────────────────────────────────────────
const HOURS = Array.from({ length: 24 }, (_, i) => i);   // 0..23
const HOUR_HEIGHT = 60; // px per hour

type ViewMode = 'semana' | 'mes' | 'dia';

interface CalEvent {
    id: string;
    title: string;
    start: Date;
    end?: Date;
    color: string;
    type: 'task' | 'event' | 'reminder';
    allDay?: boolean;
    priority?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function minutesToTop(date: Date) {
    return (getHours(date) * 60 + getMinutes(date)) * (HOUR_HEIGHT / 60);
}
function formatHour(h: number) {
    if (h === 0) return '12 am';
    if (h === 12) return '12 pm';
    return h < 12 ? `${h} am` : `${h - 12} pm`;
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PlanificadorPage() {
    const { token } = useAuth();
    const [viewMode, setViewMode] = useState<ViewMode>('semana');
    const [currentDate, setCurrentDate] = useState(new Date());
    const [events, setEvents] = useState<CalEvent[]>([]);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [nowLine, setNowLine] = useState<number>(minutesToTop(new Date()));
    const [showViewDropdown, setShowViewDropdown] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Fetch tasks for pending list and calendar events
    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const sysCal = await apiFetch<any[]>('/system/calendar', { token }).catch(() => []);
                if (Array.isArray(sysCal)) {
                    setEvents(sysCal.map(e => ({
                        id: e.id,
                        title: e.title,
                        start: new Date(e.start),
                        end: e.end ? new Date(e.end) : undefined,
                        color: e.type === 'task' ? '#7c3aed' : e.type === 'crm' ? '#10b981' : '#ef4444',
                        type: e.type,
                        allDay: e.allDay ?? false,
                    })));
                }
            } catch { }
            // Tasks: try my-tasks or fallback to empty
            try {
                const taskData = await apiFetch<ProjectTaskRecord[]>('/projects/tasks', { token }).catch(() => []);
                if (Array.isArray(taskData)) setTasks(taskData.slice(0, 30));
            } catch { }
        };
        load();
    }, [token]);

    // Live clock line
    useEffect(() => {
        const tick = () => setNowLine(minutesToTop(new Date()));
        tick();
        const t = setInterval(tick, 60_000);
        return () => clearInterval(t);
    }, []);

    // Scroll to 8am on mount
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = HOUR_HEIGHT * 8 - 40;
        }
    }, [viewMode]);

    // Week days
    const weekDays = useMemo(() => {
        const start = startOfWeek(currentDate, { weekStartsOn: 0 });
        return eachDayOfInterval({ start, end: addDays(start, 6) });
    }, [currentDate]);

    // Events for each day
    const getEventsForDay = useCallback((day: Date) =>
        events.filter(e => !e.allDay && isSameDay(e.start, day)),
        [events]
    );
    const getAllDayForDay = useCallback((day: Date) =>
        events.filter(e => e.allDay && isSameDay(e.start, day)),
        [events]
    );

    // Nav
    const prev = () => {
        if (viewMode === 'semana') setCurrentDate(d => subWeeks(d, 1));
        else if (viewMode === 'mes') setCurrentDate(d => subMonths(d, 1));
        else setCurrentDate(d => addDays(d, -1));
    };
    const next = () => {
        if (viewMode === 'semana') setCurrentDate(d => addWeeks(d, 1));
        else if (viewMode === 'mes') setCurrentDate(d => addMonths(d, 1));
        else setCurrentDate(d => addDays(d, 1));
    };

    return (
        <WorkspaceLayout sidebarTitle="Planificador">
            <div className="flex h-full bg-white dark:bg-[#1e1f21] font-display overflow-hidden">

                {/* ── LEFT SIDE PANEL (ClickUp Planificador style) ──────────────── */}
                <aside className="w-[230px] shrink-0 border-r border-slate-100 dark:border-white/5 flex flex-col overflow-hidden">
                    {/* Panel header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-white/5 shrink-0">
                        <h2 className="text-[13px] font-bold text-slate-800 dark:text-white">Planificador</h2>
                        <button className="flex items-center gap-0.5 px-1.5 py-1 rounded-lg text-[11px] font-medium text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                            <Plus size={13} />
                            <ChevronDown size={11} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-4 px-3">
                        {/* Prioridades */}
                        <PanelSection title="Prioridades">
                            <div className="bg-slate-50 dark:bg-white/[0.03] rounded-xl p-4 text-center border border-dashed border-slate-200 dark:border-white/5">
                                <Flag size={18} className="text-slate-300 mx-auto mb-2" />
                                <p className="text-[11px] text-slate-400 leading-snug">
                                    Prioriza una tarea para verla aparecer aquí.
                                </p>
                            </div>
                            <button className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[11px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                                <Plus size={12} /> Añadir prioridad
                            </button>
                        </PanelSection>

                        {/* Reunión con */}
                        <PanelSection title="Reunión con">
                            <div className="relative">
                                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300" />
                                <input
                                    placeholder="Buscar personas..."
                                    className="w-full pl-8 pr-3 py-1.5 text-[11px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none placeholder:text-slate-300 dark:placeholder:text-slate-600 text-slate-700 dark:text-slate-300"
                                />
                            </div>
                        </PanelSection>

                        {/* Asignadas a mí */}
                        <PanelSection title="Asignadas a mí" collapsible>
                            <div />
                        </PanelSection>

                        {/* Hoy y Con atraso */}
                        <PanelSection title="Hoy y Con atraso" collapsible>
                            <div />
                        </PanelSection>

                        {/* Tareas pendientes */}
                        <PanelSection title="Tareas pendientes">
                            {/* Filter bar */}
                            <div className="flex items-center gap-1.5 mb-2">
                                <button className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-slate-500 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                                    <Workflow size={10} />
                                    Lista personal
                                </button>
                                <button className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5">
                                    <Settings2 size={11} />
                                </button>
                                <input
                                    placeholder="Buscar..."
                                    className="flex-1 min-w-0 px-2 py-1 text-[10px] bg-transparent border border-slate-200 dark:border-white/10 rounded-lg outline-none placeholder:text-slate-300 text-slate-600 dark:text-slate-300"
                                />
                            </div>

                            {/* Task list */}
                            {tasks.length === 0 ? (
                                <div className="bg-slate-50 dark:bg-white/[0.03] rounded-xl p-4 text-center border border-dashed border-slate-200 dark:border-white/5">
                                    <p className="text-[11px] text-slate-400">
                                        Ninguna tarea coincide con estos filtros.
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-0.5 max-h-[300px] overflow-y-auto scrollbar-thin">
                                    {tasks.slice(0, 15).map(t => (
                                        <div key={t.id}
                                            className="flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer group"
                                        >
                                            <Circle size={13} className="text-slate-300 shrink-0 group-hover:text-blue-400 transition-colors" />
                                            <span className="text-[11px] text-slate-600 dark:text-slate-300 truncate">{t.title}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </PanelSection>
                    </div>
                </aside>

                {/* ── MAIN CALENDAR ─────────────────────────────────────────────── */}
                <div className="flex-1 flex flex-col overflow-hidden">

                    {/* Calendar header */}
                    <header className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-slate-100 dark:border-white/5">
                        {/* Nav */}
                        <div className="flex items-center gap-1.5">
                            <button onClick={prev} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 transition-colors">
                                <ChevronLeft size={17} />
                            </button>
                            <button onClick={next} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 transition-colors">
                                <ChevronRight size={17} />
                            </button>
                            <button
                                onClick={() => setCurrentDate(new Date())}
                                className="px-3 py-1 rounded-lg text-[11px] font-bold text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 transition-colors"
                            >
                                Hoy
                            </button>
                            <h2 className="text-[15px] font-bold text-slate-800 dark:text-white ml-1 capitalize">
                                {viewMode === 'semana'
                                    ? format(currentDate, 'MMMM yyyy', { locale: es })
                                    : viewMode === 'mes'
                                        ? format(currentDate, 'MMMM yyyy', { locale: es })
                                        : format(currentDate, "EEEE d 'de' MMMM", { locale: es })
                                }
                            </h2>
                        </div>

                        {/* Right actions */}
                        <div className="flex items-center gap-1">
                            <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                                <StickyNote size={13} />
                                Notas IA
                            </button>
                            <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                            <button className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors" title="Sincronizar">
                                <RefreshCw size={14} />
                            </button>
                            <button className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors" title="Configuración">
                                <Settings2 size={14} />
                            </button>

                            {/* View mode selector */}
                            <div className="relative ml-1">
                                <button
                                    onClick={() => setShowViewDropdown(v => !v)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                                >
                                    {viewMode === 'semana' ? 'Semana' : viewMode === 'mes' ? 'Mes' : 'Día'}
                                    <ChevronDown size={12} />
                                </button>
                                <AnimatePresence>
                                    {showViewDropdown && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -4 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -4 }}
                                            className="absolute right-0 top-full mt-1.5 w-32 bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl overflow-hidden z-50"
                                        >
                                            {(['semana', 'mes', 'dia'] as ViewMode[]).map(v => (
                                                <button key={v}
                                                    onClick={() => { setViewMode(v); setShowViewDropdown(false); }}
                                                    className={clsx(
                                                        'w-full text-left px-3 py-2 text-[12px] font-medium transition-colors',
                                                        viewMode === v
                                                            ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600'
                                                            : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                                                    )}>
                                                    {v === 'semana' ? 'Semana' : v === 'mes' ? 'Mes' : 'Día'}
                                                </button>
                                            ))}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            <button className="flex items-center gap-1.5 px-3 py-1.5 ml-1 rounded-lg text-[11px] font-bold bg-blue-600 text-white shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                                <Plus size={13} /> Evento
                            </button>
                        </div>
                    </header>

                    {/* ── WEEK VIEW ──────────────────────────────────────────────── */}
                    {viewMode === 'semana' && (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            {/* Day headers */}
                            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5">
                                {/* Time gutter spacer */}
                                <div className="w-16 shrink-0" />
                                {/* COT timezone label */}
                                <div className="w-[40px] shrink-0 flex items-end pb-2 pl-1">
                                    <span className="text-[9px] font-bold text-slate-300 uppercase tracking-widest rotate-0">COT</span>
                                </div>
                                {weekDays.map((day, i) => (
                                    <div key={i} className="flex-1 min-w-0 flex flex-col items-center py-2 border-l border-slate-100 dark:border-white/5 first:border-l-0">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                            {format(day, 'EEE', { locale: es })}
                                        </span>
                                        <span className={clsx(
                                            'size-8 flex items-center justify-center rounded-full text-[15px] font-bold mt-0.5 transition-colors',
                                            isToday(day)
                                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                                                : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                                        )}>
                                            {format(day, 'd')}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {/* All-day row */}
                            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5 min-h-[28px]">
                                <div className="w-16 shrink-0 flex items-center justify-end pr-2">
                                    <span className="text-[9px] text-slate-300 dark:text-slate-600 font-bold">Todo el día</span>
                                </div>
                                <div className="w-[40px] shrink-0" />
                                {weekDays.map((day, i) => {
                                    const dayAllDay = getAllDayForDay(day);
                                    return (
                                        <div key={i} className="flex-1 border-l border-slate-100 dark:border-white/5 px-1 py-0.5 first:border-l-0">
                                            {dayAllDay.map(e => (
                                                <div key={e.id} className="truncate text-[10px] font-bold rounded px-1.5 py-0.5 text-white"
                                                    style={{ backgroundColor: e.color }}>
                                                    {e.title}
                                                </div>
                                            ))}
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Timed grid */}
                            <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
                                <div className="flex">
                                    {/* Time gutter */}
                                    <div className="w-16 shrink-0 relative" style={{ height: HOUR_HEIGHT * 24 }}>
                                        {HOURS.map(h => (
                                            <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-2 pt-0"
                                                style={{ top: h * HOUR_HEIGHT - 7 }}>
                                                {h > 0 && (
                                                    <span className="text-[9px] text-slate-300 dark:text-slate-600 font-bold select-none">
                                                        {formatHour(h)}
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>

                                    {/* Plus icon column */}
                                    <div className="w-[40px] shrink-0 relative" style={{ height: HOUR_HEIGHT * 24 }}>
                                        {HOURS.map(h => (
                                            <div key={h} className="absolute left-0 right-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity"
                                                style={{ top: h * HOUR_HEIGHT, height: HOUR_HEIGHT }}>
                                                <button className="size-5 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-sm hover:scale-110 transition-transform">
                                                    <Plus size={11} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Day columns */}
                                    {weekDays.map((day, colIdx) => {
                                        const dayEvents = getEventsForDay(day);
                                        const today = isToday(day);
                                        return (
                                            <div key={colIdx} className="flex-1 min-w-0 relative border-l border-slate-100 dark:border-white/5 first:border-l-0"
                                                style={{ height: HOUR_HEIGHT * 24 }}>
                                                {/* Hour lines */}
                                                {HOURS.map(h => (
                                                    <div key={h} className="absolute left-0 right-0 border-t border-slate-100 dark:border-white/[0.04]"
                                                        style={{ top: h * HOUR_HEIGHT }} />
                                                ))}

                                                {/* Today highlight column */}
                                                {today && (
                                                    <div className="absolute inset-0 bg-blue-50/30 dark:bg-blue-500/[0.03] pointer-events-none" />
                                                )}

                                                {/* Now line */}
                                                {today && (
                                                    <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                                                        <div className="relative flex items-center">
                                                            <div className="size-2.5 rounded-full bg-red-500 shadow-sm shadow-red-400 -ml-1.5 shrink-0" />
                                                            <div className="flex-1 h-px bg-red-500 opacity-70" />
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Events */}
                                                {dayEvents.map(e => {
                                                    const top = minutesToTop(e.start);
                                                    const durationMins = e.end
                                                        ? (e.end.getTime() - e.start.getTime()) / 60000
                                                        : 60;
                                                    const height = Math.max(20, durationMins * (HOUR_HEIGHT / 60));
                                                    return (
                                                        <div key={e.id}
                                                            className="absolute left-1 right-1 rounded-lg px-2 py-1 overflow-hidden cursor-pointer hover:brightness-95 transition-all z-20 shadow-sm"
                                                            style={{ top, height, backgroundColor: e.color + '22', borderLeft: `3px solid ${e.color}` }}
                                                        >
                                                            <p className="text-[10px] font-bold truncate" style={{ color: e.color }}>
                                                                {format(e.start, 'h:mm a')} · {e.title}
                                                            </p>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── MONTH VIEW ─────────────────────────────────────────────── */}
                    {viewMode === 'mes' && <MonthView currentDate={currentDate} events={events} />}

                    {/* ── DAY VIEW ───────────────────────────────────────────────── */}
                    {viewMode === 'dia' && (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            {/* Day header */}
                            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5 px-6 py-2">
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide capitalize">
                                    {format(currentDate, "EEEE d 'de' MMMM", { locale: es })}
                                </span>
                            </div>
                            {/* Day timed grid */}
                            <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
                                <div className="flex" style={{ height: HOUR_HEIGHT * 24 }}>
                                    <div className="w-20 shrink-0 relative">
                                        {HOURS.map(h => (
                                            <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-3"
                                                style={{ top: h * HOUR_HEIGHT - 7 }}>
                                                {h > 0 && <span className="text-[9px] text-slate-300 font-bold">{formatHour(h)}</span>}
                                            </div>
                                        ))}
                                    </div>
                                    <div className="flex-1 relative">
                                        {HOURS.map(h => (
                                            <div key={h} className="absolute left-0 right-0 border-t border-slate-100 dark:border-white/[0.04]"
                                                style={{ top: h * HOUR_HEIGHT }} />
                                        ))}
                                        {isToday(currentDate) && (
                                            <div className="absolute left-0 right-0 z-10" style={{ top: nowLine }}>
                                                <div className="flex items-center">
                                                    <div className="size-2.5 rounded-full bg-red-500 -ml-1.5 shrink-0" />
                                                    <div className="flex-1 h-px bg-red-500" />
                                                </div>
                                            </div>
                                        )}
                                        {getEventsForDay(currentDate).map(e => {
                                            const top = minutesToTop(e.start);
                                            const h = Math.max(24, ((e.end?.getTime() ?? e.start.getTime() + 3600000) - e.start.getTime()) / 60000 * (HOUR_HEIGHT / 60));
                                            return (
                                                <div key={e.id} className="absolute left-1 right-4 rounded-xl px-3 py-2 shadow-md cursor-pointer"
                                                    style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `4px solid ${e.color}` }}>
                                                    <p className="text-[11px] font-bold" style={{ color: e.color }}>{e.title}</p>
                                                    <p className="text-[10px] text-slate-400">{format(e.start, 'h:mm a')}</p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Bottom search bar */}
                    <div className="shrink-0 border-t border-slate-100 dark:border-white/5 px-4 py-2">
                        <div className="max-w-lg mx-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                            <Search size={14} className="text-slate-300 shrink-0" />
                            <input
                                placeholder="Busca eventos, compañeros de equipo, comandos..."
                                className="flex-1 text-[12px] bg-transparent outline-none text-slate-600 dark:text-slate-300 placeholder:text-slate-300 dark:placeholder:text-slate-600"
                            />
                            <div className="size-5 rounded-full bg-violet-600 flex items-center justify-center shrink-0">
                                <span className="text-[8px] text-white font-black">✦</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </WorkspaceLayout>
    );
}

// ── Month View ────────────────────────────────────────────────────────────────
function MonthView({ currentDate, events }: { currentDate: Date; events: CalEvent[] }) {
    const days = useMemo(() => {
        const start = startOfWeek(startOfMonth(currentDate), { weekStartsOn: 0 });
        const end = endOfWeek(endOfMonth(currentDate), { weekStartsOn: 0 });
        return eachDayOfInterval({ start, end });
    }, [currentDate]);

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* Day of week headers */}
            <div className="grid grid-cols-7 shrink-0 border-b border-slate-100 dark:border-white/5">
                {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(d => (
                    <div key={d} className="py-2.5 text-center text-[10px] font-black uppercase tracking-widest text-slate-400">
                        {d}
                    </div>
                ))}
            </div>
            {/* Day cells */}
            <div className="flex-1 grid grid-cols-7 overflow-y-auto scrollbar-hide">
                {days.map((day, idx) => {
                    const dayEvents = events.filter(e => isSameDay(e.start, day));
                    const inMonth = isSameMonth(day, currentDate);
                    return (
                        <div key={idx} className={clsx(
                            'min-h-[100px] p-2 border-r border-b border-slate-100 dark:border-white/5 group transition-colors cursor-pointer hover:bg-slate-50/50 dark:hover:bg-white/[0.02]',
                            !inMonth && 'opacity-30'
                        )}>
                            <span className={clsx(
                                'inline-flex size-6 items-center justify-center rounded-full text-[11px] font-bold transition-all',
                                isToday(day)
                                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-400'
                                    : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-white'
                            )}>
                                {format(day, 'd')}
                            </span>
                            <div className="mt-1 space-y-0.5">
                                {dayEvents.slice(0, 2).map(e => (
                                    <div key={e.id} className="truncate text-[9px] font-bold rounded px-1 py-0.5 text-white"
                                        style={{ backgroundColor: e.color }}>
                                        {e.title}
                                    </div>
                                ))}
                                {dayEvents.length > 2 && (
                                    <span className="text-[9px] text-slate-400 font-bold pl-0.5">+{dayEvents.length - 2} más</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Panel Section ─────────────────────────────────────────────────────────────
function PanelSection({
    title, children, collapsible
}: {
    title: string;
    children: React.ReactNode;
    collapsible?: boolean;
}) {
    const [open, setOpen] = useState(true);
    return (
        <div className="space-y-1.5">
            <div
                onClick={() => collapsible && setOpen(v => !v)}
                className={clsx('flex items-center justify-between', collapsible && 'cursor-pointer')}
            >
                <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                    {title}
                </span>
                {collapsible && (
                    <ChevronDown size={11} className={clsx('text-slate-300 transition-transform', !open && '-rotate-90')} />
                )}
            </div>
            {open && <div className="space-y-1.5">{children}</div>}
        </div>
    );
}

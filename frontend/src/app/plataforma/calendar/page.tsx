"use client";

import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import {
    ChevronLeft, ChevronRight, Plus, Search, Settings2,
    Flag, RefreshCw, StickyNote, ChevronDown, Workflow,
    Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    format, startOfWeek, endOfWeek, eachDayOfInterval,
    isSameDay, addWeeks, subWeeks, addDays, isToday,
    startOfMonth, endOfMonth, addMonths, subMonths,
    isSameMonth, getHours, getMinutes
} from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useCreation } from '@/context/CreationContext';
import type { ProjectTaskRecord } from '@/types/projects';
import InlineEventPopover from '@/components/calendar/InlineEventPopover';
import { toast } from 'sonner';

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
    type: 'task' | 'agenda_event' | 'evangelism_event' | 'reminder';
    allDay?: boolean;
    priority?: string;
    href?: string;
}

const EVENT_TYPE_META: Record<CalEvent['type'], { label: string; chip: string }> = {
    task: {
        label: 'Tarea',
        chip: 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300',
    },
    agenda_event: {
        label: 'Agenda simple',
        chip: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300',
    },
    evangelism_event: {
        label: 'Evangelismo',
        chip: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
    },
    reminder: {
        label: 'Recordatorio',
        chip: 'bg-slate-50 text-slate-700 dark:bg-white/10 dark:text-slate-300',
    },
};

const CALENDAR_EVENT_TYPES: CalEvent['type'][] = ['agenda_event', 'evangelism_event', 'task'];

function getEventTypeColor(eventType: CalEvent['type']) {
    if (eventType === 'task') return '#7c3aed';
    if (eventType === 'evangelism_event') return '#10b981';
    return '#ef4444';
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
    const { token, user } = useAuth();
    const { openModal } = useCreation();
    const router = useRouter();
    const role = (user?.role || '').toLowerCase();
    const canAccessEvangelism = role === 'admin' || role === 'pastor';
    const [viewMode, setViewMode] = useState<ViewMode>('semana');
    const [currentDate, setCurrentDate] = useState(new Date());
    const [events, setEvents] = useState<CalEvent[]>([]);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [nowLine, setNowLine] = useState<number>(minutesToTop(new Date()));
    const [showViewDropdown, setShowViewDropdown] = useState(false);
    const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);
    const [activeTypes, setActiveTypes] = useState<CalEvent['type'][]>(['task', 'agenda_event', 'evangelism_event']);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const saved = window.localStorage.getItem('calendar_active_event_types');
        if (!saved) return;
        try {
            const parsed = JSON.parse(saved);
            if (Array.isArray(parsed) && parsed.every((value) => ['task', 'agenda_event', 'evangelism_event', 'reminder'].includes(value))) {
                setActiveTypes(parsed as CalEvent['type'][]);
            }
        } catch {
            window.localStorage.removeItem('calendar_active_event_types');
        }
    }, []);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        window.localStorage.setItem('calendar_active_event_types', JSON.stringify(activeTypes));
    }, [activeTypes]);

    const visibleEvents = useMemo(
        () => events.filter((event) => activeTypes.includes(event.type)),
        [activeTypes, events]
    );
    const isCalendarFullyVisible = activeTypes.length === CALENDAR_EVENT_TYPES.length;

    const todayVisibleEvents = useMemo(
        () => visibleEvents.filter((event) => isSameDay(event.start, new Date())),
        [visibleEvents]
    );

    const upcomingVisibleEvents = useMemo(
        () => [...visibleEvents]
            .filter((event) => event.start.getTime() >= Date.now())
            .sort((a, b) => a.start.getTime() - b.start.getTime())
            .slice(0, 3),
        [visibleEvents]
    );

    const eventTypeCounts = useMemo(() => {
        return visibleEvents.reduce<Record<CalEvent['type'], number>>((acc, event) => {
            acc[event.type] = (acc[event.type] || 0) + 1;
            return acc;
        }, {
            task: 0,
            agenda_event: 0,
            evangelism_event: 0,
            reminder: 0,
        });
    }, [visibleEvents]);

    const fetchSystemCalendar = useCallback(async () => {
        if (!token) return;
        try {
            const sysCal = await apiFetch<any[]>('/system/calendar', { token }).catch(() => []);
            if (Array.isArray(sysCal)) {
                setEvents(sysCal.map(e => ({
                    id: e.id,
                    title: e.title,
                    start: new Date(e.start),
                    end: e.end ? new Date(e.end) : undefined,
                    color: getEventTypeColor(e.type),
                    type: e.type,
                    allDay: e.allDay ?? false,
                    href: e.href,
                })));
            }
        } catch { }
    }, [token]);

    const handleEventClick = useCallback((event: CalEvent) => {
        if (event.href) {
            router.push(event.href);
        }
    }, [router]);

    const fetchTasks = useCallback(async () => {
        if (!token) return;
        try {
            const taskData = await apiFetch<ProjectTaskRecord[]>('/projects/tasks', { token }).catch(() => []);
            if (Array.isArray(taskData)) setTasks(taskData.slice(0, 30));
        } catch { }
    }, [token]);

    const toggleTypeFilter = useCallback((eventType: CalEvent['type']) => {
        setActiveTypes((prev) => (
            prev.includes(eventType)
                ? prev.filter((item) => item !== eventType)
                : [...prev, eventType]
        ));
    }, []);

    const handleSaveInlineEvent = async (data: { title: string; type: 'event'|'task'; description: string; location: string; date: Date }) => {
        try {
            if (data.type === 'task') {
                const projs = await apiFetch<any[]>('/projects', { token }).catch(() => []);
                if (!projs || projs.length === 0) {
                    toast.error('Se requiere un proyecto para crear una tarea');
                    return;
                }
                await apiFetch(`/projects/${projs[0].id}/tasks`, {
                    method: 'POST', token,
                    body: { title: data.title, description: data.description, status: 'todo', priority: 'normal', due_date: data.date.toISOString() }
                });
            } else {
                await apiFetch('/agenda/events', {
                    method: 'POST', token,
                    body: { 
                        title: data.title, 
                        description: data.description, 
                        start_at: data.date.toISOString(),
                        end_at: data.date.toISOString(),
                        location: data.location,
                        is_all_day: true,
                    }
                });
            }

            // Refetch to get real IDs and synced data
            await fetchSystemCalendar();
            if (data.type === 'task') await fetchTasks();
            
            toast.success(data.type === 'task' ? 'Tarea creada' : 'Evento creado', {
                description: data.title
            });
        } catch (e: any) {
            toast.error('Error al guardar', { description: e.message || 'Error desconocido' });
        }
    };

    // Fetch tasks for pending list and calendar events
    useEffect(() => {
        fetchSystemCalendar();
        fetchTasks();
    }, [fetchSystemCalendar, fetchTasks]);

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
        events.filter(e => !e.allDay && activeTypes.includes(e.type) && isSameDay(e.start, day)),
        [activeTypes, events]
    );
    const getAllDayForDay = useCallback((day: Date) =>
        events.filter(e => e.allDay && activeTypes.includes(e.type) && isSameDay(e.start, day)),
        [activeTypes, events]
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

                {/* ── MAIN CALENDAR ─────────────────────────────────────────────── */}
                <div className="flex-1 flex flex-col overflow-hidden">

                    {/* Calendar header */}
                    <header className="shrink-0 flex items-center justify-between px-3 py-3 border-b border-slate-100 dark:border-white/5">
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
                            <div className="ml-1 flex items-center gap-2">
                                <h2 className={clsx(
                                    "text-sm font-bold capitalize transition-colors",
                                    isCalendarFullyVisible ? "text-slate-800 dark:text-white" : "text-amber-600 dark:text-amber-400"
                                )}>
                                {viewMode === 'semana'
                                    ? format(currentDate, 'MMMM yyyy', { locale: es })
                                    : viewMode === 'mes'
                                        ? format(currentDate, 'MMMM yyyy', { locale: es })
                                        : format(currentDate, "EEEE d 'de' MMMM", { locale: es })
                                }
                                </h2>
                                <span className={clsx(
                                    "rounded-full px-2 py-1 text-[9px] font-semibold uppercase tracking-wide",
                                    isCalendarFullyVisible
                                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
                                        : "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
                                )}>
                                    {isCalendarFullyVisible ? "Completo" : "Filtrado"}
                                </span>
                            </div>
                        </div>

                        {/* Right actions */}
                        <div className="flex items-center gap-1">
                            <div className="mr-2 flex items-center gap-1">
                                {CALENDAR_EVENT_TYPES.map((eventType) => (
                                    <button
                                        key={eventType}
                                        onClick={() => toggleTypeFilter(eventType)}
                                        className={clsx(
                                            "rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-all",
                                            activeTypes.includes(eventType)
                                                ? EVENT_TYPE_META[eventType].chip
                                                : "bg-slate-100 text-slate-400 dark:bg-white/5 dark:text-slate-500"
                                        )}
                                    >
                                        {EVENT_TYPE_META[eventType].label} ({eventTypeCounts[eventType]})
                                    </button>
                                ))}
                            </div>
                            <div className="hidden md:flex items-center rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/5 dark:text-slate-300">
                                {visibleEvents.length} visibles
                            </div>
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
                                            className="absolute right-0 top-full mt-1.5 w-32 bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50"
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

                            <button 
                                onClick={() => openModal('event')}
                                className="flex items-center gap-1.5 px-3 py-1.5 ml-1 rounded-lg text-[11px] font-bold bg-blue-600 text-white shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"
                            >
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
                                    <span className="text-[9px] font-bold text-slate-300 uppercase tracking-wide rotate-0">COT</span>
                                </div>
                                {weekDays.map((day, i) => (
                                    <div key={i} className="flex-1 min-w-0 flex flex-col items-center py-2 border-l border-slate-100 dark:border-white/5 first:border-l-0">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                            {format(day, 'EEE', { locale: es })}
                                        </span>
                                        <span className={clsx(
                                            'size-8 flex items-center justify-center rounded-full text-sm font-bold mt-0.5 transition-colors',
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
                                                <div
                                                    key={e.id}
                                                    onClick={() => handleEventClick(e)}
                                                    className="truncate cursor-pointer rounded px-1.5 py-0.5 text-white"
                                                    style={{ backgroundColor: e.color }}
                                                >
                                                    <div className="flex items-center gap-1">
                                                        <span className="text-[8px] font-semibold uppercase tracking-wide opacity-80">
                                                            {EVENT_TYPE_META[e.type].label}
                                                        </span>
                                                        <span className="truncate text-[10px] font-bold">{e.title}</span>
                                                    </div>
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



                                    {/* Day columns */}
                                    {weekDays.map((day, colIdx) => {
                                        const dayEvents = getEventsForDay(day);
                                        const today = isToday(day);
                                        const dayKey = format(day, 'yyyy-MM-dd');
                                        return (
                                            <InlineEventPopover 
                                                key={colIdx}
                                                open={openPopoverDay === dayKey}
                                                onOpenChange={(open) => setOpenPopoverDay(open ? dayKey : null)}
                                                day={day}
                                                onSave={handleSaveInlineEvent}
                                            >
                                                <div className="flex-1 min-w-0 relative border-l border-slate-100 dark:border-white/5 first:border-l-0 cursor-pointer group"
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
                                                                onClick={(evt) => { evt.stopPropagation(); handleEventClick(e); }}
                                                                className="absolute left-1 right-1 rounded-lg px-2 py-1 overflow-hidden cursor-pointer hover:brightness-95 transition-all z-20 shadow-sm"
                                                                style={{ top, height, backgroundColor: e.color + '22', borderLeft: `3px solid ${e.color}` }}
                                                            >
                                                                <div className="mb-1">
                                                                    <span className={clsx("inline-flex rounded-full px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide", EVENT_TYPE_META[e.type].chip)}>
                                                                        {EVENT_TYPE_META[e.type].label}
                                                                    </span>
                                                                </div>
                                                                <p className="text-[10px] font-bold truncate" style={{ color: e.color }}>
                                                                    {format(e.start, 'h:mm a')} · {e.title}
                                                                </p>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </InlineEventPopover>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── MONTH VIEW ─────────────────────────────────────────────── */}
                    {viewMode === 'mes' && <MonthView currentDate={currentDate} events={events} onSave={handleSaveInlineEvent} onEventClick={handleEventClick} />}

                    {/* ── DAY VIEW ───────────────────────────────────────────────── */}
                    {viewMode === 'dia' && (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            {/* Day header */}
                            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5 px-3 py-2">
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
                                    <InlineEventPopover 
                                        open={openPopoverDay === format(currentDate, 'yyyy-MM-dd')}
                                        onOpenChange={(open) => setOpenPopoverDay(open ? format(currentDate, 'yyyy-MM-dd') : null)}
                                        day={currentDate}
                                        onSave={handleSaveInlineEvent}
                                    >
                                        <div className="flex-1 relative cursor-pointer">
                                            {HOURS.map(h => (
                                                <div key={h} className="absolute left-0 right-0 border-t border-slate-100 dark:border-white/[0.04]"
                                                    style={{ top: h * HOUR_HEIGHT }} />
                                            ))}
                                            {isToday(currentDate) && (
                                                <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
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
                                                    <div key={e.id} 
                                                        onClick={(evt) => { evt.stopPropagation(); handleEventClick(e); }}
                                                        className="absolute left-1 right-4 rounded-md px-3 py-2 shadow-md cursor-pointer hover:brightness-95 transition-all"
                                                        style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `4px solid ${e.color}` }}>
                                                        <div className="mb-1">
                                                            <span className={clsx("inline-flex rounded-full px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide", EVENT_TYPE_META[e.type].chip)}>
                                                                {EVENT_TYPE_META[e.type].label}
                                                            </span>
                                                        </div>
                                                        <p className="text-[11px] font-bold" style={{ color: e.color }}>{e.title}</p>
                                                        <p className="text-[10px] text-slate-400">{format(e.start, 'h:mm a')}</p>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </InlineEventPopover>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Bottom search bar */}
                    <div className="shrink-0 border-t border-slate-100 dark:border-white/5 px-4 py-2">
                        <div className="max-w-lg mx-auto flex items-center gap-2 px-4 py-2 rounded-md bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                            <Search size={14} className="text-slate-300 shrink-0" />
                            <input
                                placeholder="Busca eventos, compañeros de equipo, comandos..."
                                className="flex-1 text-[12px] bg-transparent outline-none text-slate-600 dark:text-slate-300 placeholder:text-slate-300 dark:placeholder:text-slate-600"
                            />
                            <div className="size-5 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
                                <span className="font-semibold">✦</span>
                            </div>
                        </div>
                    </div>
                </div>
{/* ── RIGHT SIDE PANEL ──────────────── */}
                <aside className="w-[230px] shrink-0 border-l border-slate-100 dark:border-white/5 flex flex-col overflow-hidden">
                    {/* Panel header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-white/5 shrink-0">
                        <h2 className="text-[13px] font-bold text-slate-800 dark:text-white">Planificador</h2>
                        <button className="flex items-center gap-0.5 px-1.5 py-1 rounded-lg text-[11px] font-medium text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                            <Plus size={13} />
                            <ChevronDown size={11} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-4 px-3">
                        {/* Resumen de hoy */}
                        <PanelSection title="Hoy">
                            <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3 space-y-3">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Eventos visibles</p>
                                        <p className="text-lg font-bold text-slate-900 dark:text-white">{todayVisibleEvents.length}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Hoy</p>
                                        <p className="text-[11px] font-bold text-slate-600 dark:text-slate-300">{format(new Date(), 'dd MMM', { locale: es })}</p>
                                    </div>
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    {CALENDAR_EVENT_TYPES.map((eventType) => (
                                        <div key={eventType} className="rounded-md bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 px-2 py-2 text-center">
                                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">{EVENT_TYPE_META[eventType].label}</p>
                                            <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">
                                                {todayVisibleEvents.filter((event) => event.type === eventType).length}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    <button
                                        onClick={() => setActiveTypes([...CALENDAR_EVENT_TYPES])}
                                        className="rounded-md border border-slate-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                                    >
                                        Limpiar filtros
                                    </button>
                                    <button
                                        onClick={() => router.push('/plataforma/agenda/events')}
                                        className="rounded-md bg-blue-600 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-blue-700"
                                    >
                                        Agenda simple
                                    </button>
                                    {canAccessEvangelism && (
                                        <button
                                            onClick={() => router.push('/plataforma/evangelism/events')}
                                            className="rounded-md bg-emerald-600 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-emerald-700"
                                        >
                                            Evangelismo
                                        </button>
                                    )}
                                </div>
                                <div className="flex items-center justify-between rounded-md border border-dashed border-slate-200 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                                    <span>Estado de filtros</span>
                                    <span className={clsx(
                                        "rounded-full px-2 py-1",
                                        activeTypes.length === CALENDAR_EVENT_TYPES.length
                                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
                                            : "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
                                    )}>
                                        {activeTypes.length === CALENDAR_EVENT_TYPES.length ? "Todos visibles" : `${activeTypes.length} activos`}
                                    </span>
                                </div>
                            </div>
                        </PanelSection>

                        {/* Próximos */}
                        <PanelSection title="Próximos">
                            <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                {upcomingVisibleEvents.length === 0 ? (
                                    <p className="text-[11px] text-slate-400">No hay eventos visibles próximos.</p>
                                ) : upcomingVisibleEvents.map((event) => (
                                    <button
                                        key={event.id}
                                        onClick={() => handleEventClick(event)}
                                        className="flex w-full items-start gap-2 rounded-md bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-500/30 transition-all"
                                    >
                                        <span
                                            className="mt-0.5 size-2.5 rounded-full shrink-0"
                                            style={{ backgroundColor: event.color }}
                                        />
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className={clsx("rounded-full px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide", EVENT_TYPE_META[event.type].chip)}>
                                                    {EVENT_TYPE_META[event.type].label}
                                                </span>
                                                <span className="truncate text-[11px] font-bold text-slate-700 dark:text-slate-300">{event.title}</span>
                                            </div>
                                            <p className="mt-1 text-[10px] text-slate-400">
                                                {format(event.start, "dd MMM, h:mm a", { locale: es })}
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </PanelSection>

                        {/* Prioridades */}
                        <PanelSection title="Prioridades">
                            <div className="bg-slate-50 dark:bg-white/[0.03] rounded-md p-4 text-center border border-dashed border-slate-200 dark:border-white/5">
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
                                <div className="bg-slate-50 dark:bg-white/[0.03] rounded-md p-4 text-center border border-dashed border-slate-200 dark:border-white/5">
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

                        {/* Leyenda */}
                        <PanelSection title="Leyenda">
                            <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                {CALENDAR_EVENT_TYPES.map((eventType) => (
                                    <button
                                        key={eventType}
                                        onClick={() => toggleTypeFilter(eventType)}
                                        className={clsx(
                                            "flex w-full items-center justify-between rounded-md px-3 py-2 text-left transition-all",
                                            activeTypes.includes(eventType)
                                                ? "bg-white dark:bg-white/5"
                                                : "opacity-50 hover:opacity-80"
                                        )}
                                    >
                                        <span className="flex items-center gap-2">
                                            <span
                                                className="size-2.5 rounded-full"
                                                style={{ backgroundColor: getEventTypeColor(eventType) }}
                                            />
                                            <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                                                {EVENT_TYPE_META[eventType].label}
                                            </span>
                                        </span>
                                        <span className={clsx("rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide", EVENT_TYPE_META[eventType].chip)}>
                                            {eventTypeCounts[eventType]}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </PanelSection>
                    </div>
                </aside>

                            </div>
        </WorkspaceLayout>
    );
}

// ── Month View ────────────────────────────────────────────────────────────────
function MonthView({
    currentDate,
    events,
    onSave,
    onEventClick,
}: {
    currentDate: Date;
    events: CalEvent[];
    onSave?: (data: any) => void;
    onEventClick: (event: CalEvent) => void;
}) {
    const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);

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
                    <div key={d} className="py-2.5 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                        {d}
                    </div>
                ))}
            </div>
            {/* Day cells */}
            <div className="flex-1 grid grid-cols-7 overflow-y-auto scrollbar-hide">
                {days.map((day, idx) => {
                    const dayEvents = events.filter(e => isSameDay(e.start, day));
                    const inMonth = isSameMonth(day, currentDate);
                    const dayKey = format(day, 'yyyy-MM-dd');
                    return (
                        <InlineEventPopover 
                            key={idx}
                            open={openPopoverDay === dayKey}
                            onOpenChange={(open) => setOpenPopoverDay(open ? dayKey : null)}
                            day={day}
                            onSave={onSave}
                        >
                            <div 
                                className={clsx(
                                'min-h-[100px] p-2 border-r border-b border-slate-100 dark:border-white/5 group transition-colors cursor-pointer hover:bg-slate-50/50 dark:hover:bg-white/[0.02]',
                                !inMonth && 'opacity-30',
                                openPopoverDay === dayKey && "ring-2 ring-inset ring-blue-500/50"
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
                                    <div
                                        key={e.id}
                                        onClick={(evt) => { evt.stopPropagation(); onEventClick(e); }}
                                        className="truncate cursor-pointer rounded px-1 py-0.5 text-white"
                                        style={{ backgroundColor: e.color }}
                                    >
                                        <div className="flex items-center gap-1">
                                            <span className="text-[7px] font-semibold uppercase tracking-wide opacity-80">
                                                {EVENT_TYPE_META[e.type].label}
                                            </span>
                                            <span className="truncate text-[9px] font-bold">{e.title}</span>
                                        </div>
                                    </div>
                                ))}
                                {dayEvents.length > 2 && (
                                    <span className="text-[9px] text-slate-400 font-bold pl-0.5">+{dayEvents.length - 2} más</span>
                                )}
                            </div>
                        </div>
                        </InlineEventPopover>
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
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
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


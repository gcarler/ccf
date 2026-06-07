"use client";

import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import type { ProjectTaskRecord } from '@/types/projects';
import {
  ChevronLeft, ChevronRight, Plus, Search, Settings2,
  Flag, RefreshCw, StickyNote, ChevronDown, Workflow,
  Circle, Loader2, CalendarDays, AlertTriangle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  format, startOfWeek, endOfWeek, eachDayOfInterval,
  isSameDay, addWeeks, subWeeks, addDays, isToday,
  getHours, getMinutes, subMonths, addMonths, subDays, startOfDay,
} from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useCreation } from '@/context/CreationContext';
import InlineEventPopover from '@/components/calendar/InlineEventPopover';
import MonthView from '@/components/calendar/MonthView';
import PanelSection from '@/components/calendar/PanelSection';
import { toast } from 'sonner';
import {
  CalEvent, ViewMode, EVENT_TYPE_META, CALENDAR_EVENT_TYPES,
  HOURS, HOUR_HEIGHT, getEventTypeColor, minutesToTop, formatHour,
} from '@/types/calendar';

// ── Main Page ───────────────────────────────────────────────────────────────
export default function PlanificadorPage() {
  const { token, user } = useAuth();
  const { openModal } = useCreation();
  const router = useRouter();
  const role = (user?.role || '').toLowerCase();
  const canAccessEvangelism = ['admin', 'administrador', 'pastor'].includes(role);

  const [viewMode, setViewMode] = useState<ViewMode>('semana');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
  const [nowLine, setNowLine] = useState<number>(minutesToTop(new Date()));
  const [showViewDropdown, setShowViewDropdown] = useState(false);
  const [showCreateDropdown, setShowCreateDropdown] = useState(false);
  const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<CalEvent['type'][]>([
    'task',
    'agenda_event',
    'evangelism_event',
    'consolidation_case',
    'consolidation_task',
    'birthday',
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Restore active types from localStorage ──────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const saved = window.localStorage.getItem('calendar_active_event_types');
    if (!saved) return;
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.every((value) => CALENDAR_EVENT_TYPES.includes(value as CalEvent['type']))) {
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

  // ── Computed ─────────────────────────────────────────────────────────────
  const visibleEvents = useMemo(
    () => events.filter((event) => activeTypes.includes(event.type)),
    [activeTypes, events],
  );
  const isCalendarFullyVisible = activeTypes.length === CALENDAR_EVENT_TYPES.length;

  const todayVisibleEvents = useMemo(
    () => visibleEvents.filter((event) => isSameDay(event.start, new Date())),
    [visibleEvents],
  );

  const upcomingVisibleEvents = useMemo(
    () => [...visibleEvents]
      .filter((event) => event.start.getTime() >= Date.now())
      .sort((a, b) => a.start.getTime() - b.start.getTime())
      .slice(0, 3),
    [visibleEvents],
  );

  const eventTypeCounts = useMemo(() => {
    return visibleEvents.reduce<Record<CalEvent['type'], number>>((acc, event) => {
      acc[event.type] = (acc[event.type] || 0) + 1;
      return acc;
    }, {
      task: 0,
      agenda_event: 0,
      evangelism_event: 0,
      consolidation_case: 0,
      consolidation_task: 0,
      birthday: 0,
      reminder: 0,
    });
  }, [visibleEvents]);

  // ── Data fetching ────────────────────────────────────────────────────────
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
    } catch { /* ignore */ }
  }, [token]);

  const fetchTasks = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch<{ tasks: ProjectTaskRecord[] }>('/projects/tasks', { token }).catch(() => null);
      if (data?.tasks) setTasks(data.tasks);
    } catch { /* ignore */ }
  }, [token]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchSystemCalendar(), fetchTasks()]);
    } catch {
      setError('No se pudieron cargar los datos del calendario.');
    } finally {
      setLoading(false);
    }
  }, [fetchSystemCalendar, fetchTasks]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Now line updater ────────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => setNowLine(minutesToTop(new Date())), 60000);
    return () => clearInterval(interval);
  }, []);

  // ── Navigation ──────────────────────────────────────────────────────────
  const prev = () => {
    if (viewMode === 'semana') setCurrentDate(d => subWeeks(d, 1));
    else if (viewMode === 'mes') setCurrentDate(d => subMonths(d, 1));
    else setCurrentDate(d => subDays(d, 1));
  };
  const next = () => {
    if (viewMode === 'semana') setCurrentDate(d => addWeeks(d, 1));
    else if (viewMode === 'mes') setCurrentDate(d => addMonths(d, 1));
    else setCurrentDate(d => addDays(d, 1));
  };

  // ── Event helpers ───────────────────────────────────────────────────────
  const handleEventClick = useCallback((event: CalEvent) => {
    if (event.href) {
      router.push(event.href);
    }
  }, [router]);

  const handleSaveInlineEvent = useCallback(async (
    data: { title: string; type: 'event' | 'task'; description: string; location: string; date: Date }
  ): Promise<void> => {
    if (!token) return;
    try {
      const startAt = startOfDay(data.date).toISOString();
      const endAt = addDays(startOfDay(data.date), 1).toISOString();
      await apiFetch<void>('/agenda/events', {
        method: 'POST',
        body: JSON.stringify({
          title: data.title,
          description: data.description,
          location: data.location,
          start_at: startAt,
          end_at: endAt,
          is_all_day: true,
        }),
        token,
      });
      await fetchSystemCalendar();
      toast.success('Evento creado');
    } catch (e: any) {
      toast.error('Error al guardar', { description: e.message || 'Error desconocido' });
    }
  }, [token, fetchSystemCalendar]);

  const toggleTypeFilter = useCallback((type: CalEvent['type']) => {
    setActiveTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type],
    );
  }, []);

  type CreationPreset = 'general' | 'meeting' | 'activity' | 'project' | 'evangelism' | 'consolidation';

  const openCreation = useCallback((kind: 'event' | 'task' | 'project', preset: CreationPreset = 'general') => {
    setShowCreateDropdown(false);
    openModal(kind, { origin: 'calendar', preset });
  }, [openModal]);

  // ── View helpers ────────────────────────────────────────────────────────
  const weekDays = useMemo(() => {
    const start = startOfWeek(currentDate, { weekStartsOn: 0 });
    return eachDayOfInterval({ start, end: endOfWeek(currentDate, { weekStartsOn: 0 }) });
  }, [currentDate]);

  const getEventsForDay = useCallback((day: Date) =>
    visibleEvents.filter(e => isSameDay(e.start, day)),
  [visibleEvents]);

  const getAllDayForDay = useCallback((day: Date) =>
    visibleEvents.filter(e => isSameDay(e.start, day) && e.allDay),
  [visibleEvents]);

  // ── Render: Loading state ───────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4">
        <div className="size-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-xs shadow-lg">
          CCF
        </div>
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
        <p className="text-[11px] text-slate-400 font-medium">Cargando calendario...</p>
      </div>
    );
  }

  // ── Render: Error state ────────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4">
        <div className="size-12 rounded-full bg-red-50 dark:bg-red-500/10 flex items-center justify-center">
          <AlertTriangle size={24} className="text-red-500" />
        </div>
        <p className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{error}</p>
        <button
          onClick={fetchAll}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20 hover:brightness-110 transition-all active:scale-95"
        >
          <RefreshCw size={13} /> Reintentar
        </button>
      </div>
    );
  }

  // ── Render: Empty state ────────────────────────────────────────────────
  if (events.length === 0 && tasks.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4">
        <div className="size-12 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center">
          <CalendarDays size={24} className="text-slate-300" />
        </div>
        <div className="text-center max-w-xs">
          <p className="text-[13px] font-bold text-slate-600 dark:text-slate-300 mb-1">
            Sin eventos aún
          </p>
          <p className="text-[11px] text-slate-400">
            No hay eventos o tareas programadas. Crea un evento para empezar.
          </p>
        </div>
        <button
          onClick={() => openCreation('event', 'general')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20 hover:brightness-110 transition-all active:scale-95"
        >
          <Plus size={13} /> Crear primer evento
        </button>
      </div>
    );
  }

  // ── Render: Main ────────────────────────────────────────────────────────
  return (
    <>
      {/* Main calendar area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Calendar header */}
        <header className="shrink-0 flex items-center justify-between px-3 py-3 border-b border-slate-100 dark:border-white/5">
          <div className="flex items-center gap-1.5">
            <button onClick={prev} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 transition-colors">
              <ChevronLeft size={17} />
            </button>
            <button onClick={next} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 transition-colors">
              <ChevronRight size={17} />
            </button>
            <h2 className="text-sm font-bold text-slate-800 dark:text-white ml-2 min-w-[140px]">
              {viewMode === 'semana'
                ? `${format(weekDays[0], 'd')} – ${format(weekDays[6], 'd MMM', { locale: es })}`
                : format(currentDate, "MMMM yyyy", { locale: es })}
            </h2>
            <button
              onClick={() => setCurrentDate(new Date())}
              className="px-2 py-1 rounded-md text-[10px] font-bold text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors border border-blue-200 dark:border-blue-500/20"
            >
              Hoy
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            {/* View switcher */}
            <div className="relative">
              <button
                onClick={() => setShowViewDropdown(v => !v)}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-bold text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/10 transition-all capitalize"
              >
                {viewMode}
                <ChevronDown size={12} />
              </button>
              <AnimatePresence>
                {showViewDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1.5 w-32 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50"
                  >
                    {(['semana', 'mes', 'dia'] as ViewMode[]).map(v => (
                      <button
                        key={v}
                        onClick={() => { setViewMode(v); setShowViewDropdown(false); }}
                        className={clsx(
                          'w-full text-left px-3 py-1.5 text-[11px] font-bold transition-colors capitalize',
                          viewMode === v
                            ? 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10'
                            : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5',
                        )}
                      >
                        {v === 'semana' ? 'Semana' : v === 'mes' ? 'Mes' : 'Día'}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="relative">
              <button
                onClick={() => setShowCreateDropdown((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 ml-1 rounded-lg text-[11px] font-bold bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
              >
                <Plus size={13} /> Crear
                <ChevronDown size={11} />
              </button>
              {showCreateDropdown && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  className="absolute right-0 top-full mt-1.5 w-44 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50"
                >
                  <button
                    onClick={() => openCreation('event', 'general')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Evento general
                  </button>
                  <button
                    onClick={() => openCreation('event', 'evangelism')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Evento evangelístico
                  </button>
                  <button
                    onClick={() => openCreation('task', 'activity')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Actividad general
                  </button>
                  <button
                    onClick={() => openCreation('task', 'consolidation')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Consolidación
                  </button>
                  <button
                    onClick={() => openCreation('event', 'meeting')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Reunión
                  </button>
                  <button
                    onClick={() => openCreation('project', 'project')}
                    className="w-full text-left px-3 py-2 text-[12px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                  >
                    Proyecto
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ── WEEK VIEW ──────────────────────────────────────────────── */}
        {viewMode === 'semana' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Day headers */}
            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5">
              <div className="w-16 shrink-0" />
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
                      ? 'bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/30'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5',
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
              <div className="flex" style={{ height: HOUR_HEIGHT * 24 }}>
                <div className="w-16 shrink-0 relative">
                  {HOURS.map(h => (
                    <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-3"
                      style={{ top: h * HOUR_HEIGHT - 7 }}>
                      {h > 0 && <span className="text-[9px] text-slate-300 font-bold">{formatHour(h)}</span>}
                    </div>
                  ))}
                </div>
                <div className="w-[40px] shrink-0" />
                {weekDays.map((day, i) => (
                  <div key={i} className="flex-1 border-l border-slate-100 dark:border-white/5 relative cursor-pointer first:border-l-0">
                    {HOURS.map(h => (
                      <div key={h} className="absolute left-0 right-0 border-t border-slate-100 dark:border-white/[0.04]"
                        style={{ top: h * HOUR_HEIGHT }} />
                    ))}
                    {isToday(day) && (
                      <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                        <div className="flex items-center">
                          <div className="size-2.5 rounded-full bg-[hsl(var(--destructive))] -ml-1.5 shrink-0" />
                          <div className="flex-1 h-px bg-[hsl(var(--destructive))]" />
                        </div>
                      </div>
                    )}
                    <InlineEventPopover
                      open={openPopoverDay === format(day, 'yyyy-MM-dd')}
                      onOpenChange={(open) => setOpenPopoverDay(open ? format(day, 'yyyy-MM-dd') : null)}
                      day={day}
                      onSave={handleSaveInlineEvent}
                    >
                      <div className="absolute inset-0">
                        {getEventsForDay(day).filter(e => !e.allDay).map(e => {
                          const top = minutesToTop(e.start);
                          const h = Math.max(24, ((e.end?.getTime() ?? e.start.getTime() + 3600000) - e.start.getTime()) / 60000 * (HOUR_HEIGHT / 60));
                          return (
                            <div key={e.id}
                              onClick={(evt) => { evt.stopPropagation(); handleEventClick(e); }}
                              className="absolute left-1 right-1 rounded-lg px-2 py-1 overflow-hidden cursor-pointer hover:brightness-95 transition-all z-20 shadow-sm"
                              style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `3px solid ${e.color}` }}
                            >
                              <p className="text-[10px] font-bold truncate" style={{ color: e.color }}>
                                {format(e.start, 'h:mm a')} · {e.title}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </InlineEventPopover>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── MONTH VIEW ─────────────────────────────────────────────── */}
        {viewMode === 'mes' && (
          <MonthView
            currentDate={currentDate}
            events={events}
            onSave={handleSaveInlineEvent}
            onEventClick={handleEventClick}
          />
        )}

        {/* ── DAY VIEW ───────────────────────────────────────────────── */}
        {viewMode === 'dia' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex shrink-0 border-b border-slate-100 dark:border-white/5 px-3 py-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide capitalize">
                {format(currentDate, "EEEE d 'de' MMMM", { locale: es })}
              </span>
            </div>
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
                          <div className="size-2.5 rounded-full bg-[hsl(var(--destructive))] -ml-1.5 shrink-0" />
                          <div className="flex-1 h-px bg-[hsl(var(--destructive))]" />
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
                          style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `4px solid ${e.color}` }}
                        >
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
            <div className="size-5 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center shrink-0">
              <span className="font-semibold">✦</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT SIDE PANEL ─────────────────────────────────────────── */}
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

              {/* Active type filters */}
              <div className="flex flex-wrap gap-1">
                {CALENDAR_EVENT_TYPES.map(type => (
                  <button
                    key={type}
                    onClick={() => toggleTypeFilter(type)}
                    className={clsx(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide transition-all',
                      activeTypes.includes(type)
                        ? EVENT_TYPE_META[type].chip
                        : 'bg-slate-100 dark:bg-white/5 text-slate-300 dark:text-slate-600 line-through',
                    )}
                  >
                    {EVENT_TYPE_META[type].label}
                  </button>
                ))}
              </div>
            </div>
          </PanelSection>

          {/* Próximos */}
          <PanelSection title="Próximos">
            {upcomingVisibleEvents.length === 0 ? (
              <div className="bg-slate-50 dark:bg-white/[0.03] rounded-md p-4 text-center border border-dashed border-slate-200 dark:border-white/5">
                <Flag size={18} className="text-slate-300 mx-auto mb-2" />
                <p className="text-[11px] text-slate-400 leading-snug">No hay próximos eventos visibles.</p>
              </div>
            ) : (
              <div className="space-y-1">
                {upcomingVisibleEvents.map(e => (
                  <div key={e.id}
                    onClick={() => handleEventClick(e)}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                  >
                    <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: e.color }} />
                    <div className="min-w-0">
                      <p className="truncate text-[11px] font-bold text-slate-700 dark:text-slate-200">{e.title}</p>
                      <p className="text-[9px] text-slate-400 font-medium">{format(e.start, 'MMM d, h:mm a')}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
                    <Circle size={13} className="text-slate-300 shrink-0 group-hover:text-[hsl(var(--primary))] transition-colors" />
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
                    'flex w-full items-center justify-between rounded-md px-3 py-2 text-left transition-all',
                    activeTypes.includes(eventType)
                      ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/5'
                      : 'opacity-50 hover:opacity-80',
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
                  <span className={clsx('rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide', EVENT_TYPE_META[eventType].chip)}>
                    {eventTypeCounts[eventType]}
                  </span>
                </button>
              ))}
            </div>
          </PanelSection>
        </div>
      </aside>
    </>
  );
}

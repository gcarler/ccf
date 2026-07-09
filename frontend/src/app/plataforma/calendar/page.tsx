"use client";

import React, { Suspense, useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import type { ProjectTaskRecord } from '@/types/projects';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Search,
  Flag,
  RefreshCw,
  ChevronDown,
  Loader2,
  AlertTriangle,
  Megaphone,
  Users,
  FolderKanban,
  User,
  LayoutGrid,
  Cake,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion';
import {
  format, startOfWeek, endOfWeek, eachDayOfInterval,
  isSameDay, addWeeks, subWeeks, addDays, isToday,
  subMonths, addMonths, subDays, startOfDay,
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
  CalEvent, CalEventType, CalendarView, ViewMode,
  EVENT_TYPE_META, VIEW_EVENT_TYPES, CALENDAR_VIEW_META,
  HOURS, HOUR_HEIGHT, getEventTypeColor, minutesToTop, formatHour,
} from '@/types/calendar';

// ── View icon map ───────────────────────────────────────────────────────────
const VIEW_ICONS: Record<CalendarView, React.ElementType> = {
  todo: LayoutGrid,
  evangelismo: Megaphone,
  crm: Users,
  proyectos: FolderKanban,
  personal: User,
  cumpleanos: Cake,
};

// ── Creation options per view ───────────────────────────────────────────────
type CreationPreset = 'general' | 'meeting' | 'activity' | 'project' | 'evangelism' | 'consolidation';

interface CreateOption {
  label: string;
  kind: 'event' | 'task' | 'project';
  preset: CreationPreset;
}

const VIEW_CREATE_OPTIONS: Record<CalendarView, CreateOption[]> = {
  todo: [
    { label: 'Evento general', kind: 'event', preset: 'general' },
    { label: 'Evento evangelístico', kind: 'event', preset: 'evangelism' },
    { label: 'Tarea de proyecto', kind: 'task', preset: 'activity' },
    { label: 'Caso de consolidación', kind: 'task', preset: 'consolidation' },
    { label: 'Reunión', kind: 'event', preset: 'meeting' },
    { label: 'Proyecto', kind: 'project', preset: 'project' },
  ],
  evangelismo: [
    { label: 'Evento evangelístico', kind: 'event', preset: 'evangelism' },
    { label: 'Reunión de estrategia', kind: 'event', preset: 'meeting' },
    { label: 'Actividad grupal', kind: 'task', preset: 'activity' },
  ],
  crm: [
    { label: 'Tarea de seguimiento', kind: 'task', preset: 'consolidation' },
    { label: 'Reunión pastoral', kind: 'event', preset: 'meeting' },
  ],
  proyectos: [
    { label: 'Tarea de proyecto', kind: 'task', preset: 'activity' },
    { label: 'Nuevo proyecto', kind: 'project', preset: 'project' },
    { label: 'Reunión de equipo', kind: 'event', preset: 'meeting' },
  ],
  personal: [
    { label: 'Evento personal', kind: 'event', preset: 'general' },
    { label: 'Recordatorio', kind: 'task', preset: 'activity' },
    { label: 'Reunión', kind: 'event', preset: 'meeting' },
  ],
  cumpleanos: [],
};

// ── Main Page ───────────────────────────────────────────────────────────────
export default function PlanificadorPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-xs shadow-lg">CCF</div>
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
        <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">Cargando calendario...</p>
      </div>
    }>
      <PlanificadorInner />
    </Suspense>
  );
}

function PlanificadorInner() {
  const { token } = useAuth();
  const { openModal } = useCreation();
  const router = useRouter();
  const searchParams = useSearchParams();

  const calendarView = (searchParams?.get('view') || 'todo') as CalendarView;
  const viewMeta = CALENDAR_VIEW_META[calendarView];
  const ViewIcon = VIEW_ICONS[calendarView];

  const [timeMode, setTimeMode] = useState<ViewMode>('semana');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [_tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
  const [nowLine, setNowLine] = useState<number>(minutesToTop(new Date()));
  const [showViewDropdown, setShowViewDropdown] = useState(false);
  const [showCreateDropdown, setShowCreateDropdown] = useState(false);
  const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<CalEventType[]>(
    VIEW_EVENT_TYPES[calendarView],
  );
  const scrollRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sync active type filters when view changes
  useEffect(() => {
    setActiveTypes(VIEW_EVENT_TYPES[calendarView]);
    setEvents([]);
  }, [calendarView]);

  // ── Data fetching ────────────────────────────────────────────────────────
  const fetchCalendar = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch<any[]>(
        `/system/calendar?view=${calendarView}`,
        { token },
      ).catch(() => []);
      if (Array.isArray(data)) {
        setEvents(data.map(e => ({
          id: e.id,
          title: e.title,
          start: new Date(e.start),
          end: e.end ? new Date(e.end) : undefined,
          color: getEventTypeColor(e.type as CalEventType),
          type: e.type as CalEventType,
          allDay: e.allDay ?? false,
          href: e.href,
          location: e.location,
        })));
      }
    } catch { /* ignore */ }
  }, [token, calendarView]);

  const fetchTasks = useCallback(async () => {
    if (!token || calendarView !== 'proyectos') return;
    try {
      const data = await apiFetch<{ _tasks: ProjectTaskRecord[] }>('/projects/_tasks', { token }).catch(() => null);
      if (data?._tasks) setTasks(data._tasks);
    } catch { /* ignore */ }
  }, [token, calendarView]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchCalendar(), fetchTasks()]);
    } catch {
      setError('No se pudieron cargar los datos del calendario.');
    } finally {
      setLoading(false);
    }
  }, [fetchCalendar, fetchTasks]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // ── Now line updater ────────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => setNowLine(minutesToTop(new Date())), 60000);
    return () => clearInterval(interval);
  }, []);

  // ── Computed ─────────────────────────────────────────────────────────────
  const visibleEvents = useMemo(
    () => events.filter(e => activeTypes.includes(e.type)),
    [activeTypes, events],
  );

  const todayVisibleEvents = useMemo(
    () => visibleEvents.filter(e => isSameDay(e.start, new Date())),
    [visibleEvents],
  );

  const upcomingVisibleEvents = useMemo(
    () => [...visibleEvents]
      .filter(e => e.start.getTime() >= Date.now())
      .sort((a, b) => a.start.getTime() - b.start.getTime())
      .slice(0, 5),
    [visibleEvents],
  );

  const eventTypeCounts = useMemo(() => {
    const counts: Partial<Record<CalEventType, number>> = {};
    for (const e of visibleEvents) {
      counts[e.type] = (counts[e.type] || 0) + 1;
    }
    return counts;
  }, [visibleEvents]);

  const activeViewTypes = VIEW_EVENT_TYPES[calendarView];

  // ── Navigation ──────────────────────────────────────────────────────────
  const prev = () => {
    if (timeMode === 'semana') setCurrentDate(d => subWeeks(d, 1));
    else if (timeMode === 'mes') setCurrentDate(d => subMonths(d, 1));
    else setCurrentDate(d => subDays(d, 1));
  };
  const next = () => {
    if (timeMode === 'semana') setCurrentDate(d => addWeeks(d, 1));
    else if (timeMode === 'mes') setCurrentDate(d => addMonths(d, 1));
    else setCurrentDate(d => addDays(d, 1));
  };

  // ── Event helpers ───────────────────────────────────────────────────────
  const handleEventClick = useCallback((event: CalEvent) => {
    if (event.href) router.push(event.href);
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
        body: {
          title: data.title,
          description: data.description,
          location: data.location,
          start_at: startAt,
          end_at: endAt,
          is_all_day: true,
        },
        token,
      });
      await fetchCalendar();
      toast.success('Evento creado');
    } catch (e: any) {
      toast.error('Error al guardar', { description: e.message || 'Error desconocido' });
    }
  }, [token, fetchCalendar]);

  const toggleTypeFilter = useCallback((type: CalEventType) => {
    setActiveTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type],
    );
  }, []);

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

  // ── Loading state ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-xs shadow-lg">
          CCF
        </div>
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
        <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">Cargando {viewMeta.label}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-12 rounded-full bg-red-50 dark:bg-red-500/10 flex items-center justify-center">
          <AlertTriangle size={24} className="text-[hsl(var(--destructive))]" />
        </div>
        <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{error}</p>
        <button
          onClick={fetchAll}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20 hover:brightness-110 transition-all active:scale-95"
        >
          <RefreshCw size={13} /> Reintentar
        </button>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────
  return (
    <>
      {/* ── CALENDAR AREA ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Header */}
        <header className="shrink-0 flex items-center justify-between px-3 py-2.5 border-b border-[hsl(var(--border))] dark:border-white/5 gap-2">
          {/* View badge + navigation */}
          <div className="flex items-center gap-1.5">
            {/* View indicator */}
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide text-white"
              style={{ backgroundColor: viewMeta.color }}
            >
              <ViewIcon size={11} />
              {viewMeta.label}
            </div>

            <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />

            <button onClick={prev} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors">
              <ChevronLeft size={16} />
            </button>
            <button onClick={next} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors">
              <ChevronRight size={16} />
            </button>
            <h2 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white ml-1 min-w-[130px]">
              {timeMode === 'semana'
                ? `${format(weekDays[0], 'd')} – ${format(weekDays[6], 'd MMM', { locale: es })}`
                : timeMode === 'mes'
                  ? format(currentDate, 'MMMM yyyy', { locale: es })
                  : format(currentDate, "EEEE d 'de' MMMM", { locale: es })}
            </h2>
            <button
              onClick={() => setCurrentDate(new Date())}
              className="px-2 py-1 rounded-md text-[10px] font-bold text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors border border-blue-200 dark:border-blue-500/20"
            >
              Hoy
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Time view switcher */}
            <div className="relative">
              <button
                onClick={() => setShowViewDropdown(v => !v)}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all capitalize"
              >
                {timeMode === 'semana' ? 'Semana' : timeMode === 'mes' ? 'Mes' : 'Día'}
                <ChevronDown size={11} />
              </button>
              <AnimatePresence>
                {showViewDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1.5 w-28 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50"
                  >
                    {(['semana', 'mes', 'dia'] as ViewMode[]).map(v => (
                      <button
                        key={v}
                        onClick={() => { setTimeMode(v); setShowViewDropdown(false); }}
                        className={clsx(
                          'w-full text-left px-3 py-1.5 text-[11px] font-bold transition-colors capitalize',
                          timeMode === v
                            ? 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10'
                            : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5',
                        )}
                      >
                        {v === 'semana' ? 'Semana' : v === 'mes' ? 'Mes' : 'Día'}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Create button */}
            <div className="relative">
              <button
                onClick={() => setShowCreateDropdown(v => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold text-white shadow-lg shadow-blue-500/20 hover:brightness-110 active:scale-95 transition-all"
                style={{ backgroundColor: viewMeta.color }}
              >
                <Plus size={13} /> Crear
                <ChevronDown size={11} />
              </button>
              <AnimatePresence>
                {showCreateDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -4, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1.5 w-48 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50"
                  >
                    {VIEW_CREATE_OPTIONS[calendarView].map((opt, i) => (
                      <button
                        key={i}
                        onClick={() => openCreation(opt.kind, opt.preset)}
                        className="w-full text-left px-3 py-2 text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* ── WEEK VIEW ──────────────────────────────────────────────────── */}
        {timeMode === 'semana' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Day headers */}
            <div className="flex shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5">
              <div className="w-16 shrink-0" />
              {weekDays.map((day, i) => (
                <div key={i} className="flex-1 min-w-0 flex flex-col items-center py-2 border-l border-[hsl(var(--border))] dark:border-white/5 first:border-l-0">
                  <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                    {format(day, 'EEE', { locale: es })}
                  </span>
                  <span className={clsx(
                    'size-8 flex items-center justify-center rounded-full text-sm font-bold mt-0.5',
                    isToday(day)
                      ? 'text-white shadow-lg'
                      : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                  )}
                    style={isToday(day) ? { backgroundColor: viewMeta.color } : {}}
                  >
                    {format(day, 'd')}
                  </span>
                </div>
              ))}
            </div>

            {/* All-day row */}
            <div className="flex shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5 min-h-[28px]">
              <div className="w-16 shrink-0 flex items-center justify-end pr-2">
                <span className="text-[9px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold">Todo el día</span>
              </div>
              {weekDays.map((day, i) => {
                const dayAllDay = getAllDayForDay(day);
                return (
                  <div key={i} className="flex-1 border-l border-[hsl(var(--border))] dark:border-white/5 px-1 py-0.5 first:border-l-0">
                    {dayAllDay.map(e => (
                      <div
                        key={e.id}
                        onClick={() => handleEventClick(e)}
                        className="truncate cursor-pointer rounded px-1.5 py-0.5 text-white mb-0.5"
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
                      {h > 0 && <span className="text-[9px] text-[hsl(var(--text-secondary))] font-bold">{formatHour(h)}</span>}
                    </div>
                  ))}
                </div>
                {weekDays.map((day, i) => (
                  <div key={i} className="flex-1 border-l border-[hsl(var(--border))] dark:border-white/5 relative cursor-pointer first:border-l-0">
                    {HOURS.map(h => (
                      <div key={h} className="absolute left-0 right-0 border-t border-[hsl(var(--border))] dark:border-white/[0.04]"
                        style={{ top: h * HOUR_HEIGHT }} />
                    ))}
                    {isToday(day) && (
                      <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                        <div className="flex items-center">
                          <div className="size-2.5 rounded-full -ml-1.5 shrink-0" style={{ backgroundColor: viewMeta.color }} />
                          <div className="flex-1 h-px" style={{ backgroundColor: viewMeta.color }} />
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
                              {e.location && (
                                <p className="text-[9px] truncate opacity-60" style={{ color: e.color }}>{e.location}</p>
                              )}
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

        {/* ── MONTH VIEW ─────────────────────────────────────────────────── */}
        {timeMode === 'mes' && (
          <MonthView
            currentDate={currentDate}
            events={events}
            onSave={handleSaveInlineEvent}
            onEventClick={handleEventClick}
          />
        )}

        {/* ── DAY VIEW ───────────────────────────────────────────────────── */}
        {timeMode === 'dia' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
              <div className="flex" style={{ height: HOUR_HEIGHT * 24 }}>
                <div className="w-20 shrink-0 relative">
                  {HOURS.map(h => (
                    <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-3"
                      style={{ top: h * HOUR_HEIGHT - 7 }}>
                      {h > 0 && <span className="text-[9px] text-[hsl(var(--text-secondary))] font-bold">{formatHour(h)}</span>}
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
                      <div key={h} className="absolute left-0 right-0 border-t border-[hsl(var(--border))] dark:border-white/[0.04]"
                        style={{ top: h * HOUR_HEIGHT }} />
                    ))}
                    {isToday(currentDate) && (
                      <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                        <div className="flex items-center">
                          <div className="size-2.5 rounded-full -ml-1.5 shrink-0" style={{ backgroundColor: viewMeta.color }} />
                          <div className="flex-1 h-px" style={{ backgroundColor: viewMeta.color }} />
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
                            <span className={clsx('inline-flex rounded-full px-1.5 py-0.5 text-[8px] font-semibold uppercase tracking-wide', EVENT_TYPE_META[e.type].chip)}>
                              {EVENT_TYPE_META[e.type].label}
                            </span>
                          </div>
                          <p className="text-[11px] font-bold" style={{ color: e.color }}>{e.title}</p>
                          <p className="text-[10px] text-[hsl(var(--text-secondary))]">{format(e.start, 'h:mm a')}</p>
                          {e.location && <p className="text-[9px] text-[hsl(var(--text-secondary))] mt-0.5">{e.location}</p>}
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
        <div className="shrink-0 border-t border-[hsl(var(--border))] dark:border-white/5 px-4 py-2">
          <div className="max-w-lg mx-auto flex items-center gap-2 px-4 py-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
            <Search size={14} className="text-[hsl(var(--text-secondary))] shrink-0" />
            <input
              placeholder="Busca eventos, personas, actividades..."
              className="flex-1 text-[12px] bg-transparent outline-none text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))]"
            />
            <div className="size-5 rounded-full flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: viewMeta.color }}>
              <span className="text-[10px] font-bold">✦</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT SIDE PANEL ──────────────────────────────────────────────── */}
      <aside className="w-[220px] shrink-0 border-l border-[hsl(var(--border))] dark:border-white/5 flex flex-col overflow-hidden">
        {/* Panel header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5 shrink-0">
          <div className="flex items-center gap-2">
            <ViewIcon size={14} style={{ color: viewMeta.color }} />
            <h2 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">{viewMeta.label}</h2>
          </div>
          <button
            onClick={fetchAll}
            className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors"
            title="Actualizar"
          >
            <RefreshCw size={12} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-4 px-3">

          {/* Resumen de hoy */}
          <PanelSection title="Hoy">
            <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Eventos visibles</p>
                  <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{todayVisibleEvents.length}</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha</p>
                  <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{format(new Date(), 'dd MMM', { locale: es })}</p>
                </div>
              </div>

              {/* Empty state for today */}
              {todayVisibleEvents.length === 0 && (
                <p className="text-[10px] text-[hsl(var(--text-secondary))] text-center py-1">Sin actividades hoy</p>
              )}
            </div>
          </PanelSection>

          {/* Filtros por tipo */}
          <PanelSection title="Filtrar por tipo">
            <div className="space-y-1">
              {activeViewTypes.map(type => (
                <button
                  key={type}
                  onClick={() => toggleTypeFilter(type)}
                  className={clsx(
                    'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left transition-all',
                    activeTypes.includes(type)
                      ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/5 opacity-100'
                      : 'opacity-40 hover:opacity-70',
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: EVENT_TYPE_META[type].color }} />
                    <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                      {EVENT_TYPE_META[type].label}
                    </span>
                  </span>
                  <span className={clsx('rounded-full px-1.5 py-0.5 text-[9px] font-bold', EVENT_TYPE_META[type].chip)}>
                    {eventTypeCounts[type] ?? 0}
                  </span>
                </button>
              ))}
            </div>
          </PanelSection>

          {/* Próximos eventos */}
          <PanelSection title="Próximos">
            {upcomingVisibleEvents.length === 0 ? (
              <div className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] rounded-md p-4 text-center border border-dashed border-[hsl(var(--border))] dark:border-white/5">
                <Flag size={16} className="text-[hsl(var(--text-secondary))] mx-auto mb-2" />
                <p className="text-[10px] text-[hsl(var(--text-secondary))] leading-snug">
                  Sin próximos eventos en {viewMeta.label}.
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {upcomingVisibleEvents.map(e => (
                  <div key={e.id}
                    onClick={() => handleEventClick(e)}
                    className="flex items-start gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors group"
                  >
                    <span className="size-2 rounded-full shrink-0 mt-1" style={{ backgroundColor: e.color }} />
                    <div className="min-w-0">
                      <p className="truncate text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]">{e.title}</p>
                      <p className="text-[9px] text-[hsl(var(--text-secondary))] font-medium">
                        {format(e.start, 'MMM d')}
                        {!e.allDay && ` · ${format(e.start, 'h:mm a')}`}
                      </p>
                      <span className={clsx('inline-flex rounded-full px-1 py-0.5 text-[8px] font-semibold uppercase tracking-wide', EVENT_TYPE_META[e.type].chip)}>
                        {EVENT_TYPE_META[e.type].label}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </PanelSection>

          {/* Acción rápida de creación */}
          <PanelSection title="Acción rápida">
            <div className="space-y-1">
              {VIEW_CREATE_OPTIONS[calendarView].slice(0, 3).map((opt, i) => (
                <button
                  key={i}
                  onClick={() => openCreation(opt.kind, opt.preset)}
                  className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-[11px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 transition-all text-left"
                >
                  <Plus size={12} className="shrink-0" style={{ color: viewMeta.color }} />
                  {opt.label}
                </button>
              ))}
            </div>
          </PanelSection>

          {/* Vistas de módulo */}
          <PanelSection title="Cambiar vista">
            <div className="space-y-0.5">
              {(Object.keys(CALENDAR_VIEW_META) as CalendarView[]).map(v => {
                const meta = CALENDAR_VIEW_META[v];
                const Icon = VIEW_ICONS[v];
                const isActive = v === calendarView;
                return (
                  <button
                    key={v}
                    onClick={() => router.push(v === 'todo' ? '/plataforma/calendar' : `/plataforma/calendar?view=${v}`)}
                    className={clsx(
                      'w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all text-left',
                      isActive
                        ? 'text-white'
                        : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5',
                    )}
                    style={isActive ? { backgroundColor: meta.color } : {}}
                  >
                    <Icon size={12} />
                    {meta.label}
                  </button>
                );
              })}
            </div>
          </PanelSection>

        </div>
      </aside>
    </>
  );
}

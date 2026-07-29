'use client';

import React, { Suspense, useEffect, useState, useMemo, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ChevronLeft, ChevronRight, Plus, ChevronDown, Loader2, AlertTriangle,
  Megaphone, Users, FolderKanban, User, LayoutGrid, Cake,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  format, startOfWeek, endOfWeek, eachDayOfInterval,
  addWeeks, subWeeks, addDays, subMonths, addMonths, subDays, startOfDay,
} from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useCreation } from '@/context/CreationContext';
import { toast } from 'sonner';
import WeekView from '@/components/calendar/WeekView';
import DayView from '@/components/calendar/DayView';
import MonthView from '@/components/calendar/MonthView';
import CalendarPanel from '@/components/calendar/CalendarPanel';
import { useCalendarData } from '@/hooks/useCalendarData';
import {
  CalEvent, CalEventType, CalendarView, ViewMode,
  CALENDAR_VIEW_META, VIEW_EVENT_TYPES,
  minutesToTop,
} from '@/types/calendar';

const VIEW_ICONS: Record<CalendarView, React.ElementType> = {
  todo: LayoutGrid, evangelismo: Megaphone, crm: Users,
  proyectos: FolderKanban, personal: User, cumpleanos: Cake,
};

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

export default function PlanificadorPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-10 rounded-xl bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-white font-bold text-xs shadow-lg">CCF</div>
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">Cargando calendario...</p>
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

  const [timeMode, setTimeMode] = useState<ViewMode>('semana');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [nowLine, setNowLine] = useState<number>(minutesToTop(new Date()));
  const [showViewDropdown, setShowViewDropdown] = useState(false);
  const [showCreateDropdown, setShowCreateDropdown] = useState(false);
  const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<CalEventType[]>(VIEW_EVENT_TYPES[calendarView]);

  const { events, loading, error, refresh } = useCalendarData({ token, calendarView });

  useEffect(() => {
    setActiveTypes(VIEW_EVENT_TYPES[calendarView]);
  }, [calendarView]);

  useEffect(() => {
    const interval = setInterval(() => setNowLine(minutesToTop(new Date())), 60000);
    return () => clearInterval(interval);
  }, []);

  const visibleEvents = useMemo(
    () => events.filter(e => activeTypes.includes(e.type)),
    [activeTypes, events],
  );

  const todayVisibleEvents = useMemo(
    () => visibleEvents.filter(e => {
      const d = new Date(e.start);
      const now = new Date();
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
    }),
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
    for (const e of visibleEvents) { counts[e.type] = (counts[e.type] || 0) + 1; }
    return counts;
  }, [visibleEvents]);

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
        body: { title: data.title, description: data.description, location: data.location, start_at: startAt, end_at: endAt, is_all_day: true },
        token,
      });
      await refresh();
      toast.success('Evento creado');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error desconocido';
      toast.error('Error al guardar', { description: msg });
    }
  }, [token, refresh]);

  const toggleTypeFilter = useCallback((type: CalEventType) => {
    setActiveTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
  }, []);

  const openCreation = useCallback((kind: 'event' | 'task' | 'project', preset: string = 'general') => {
    setShowCreateDropdown(false);
    openModal(kind, { origin: 'calendar', preset });
  }, [openModal]);

  const weekDays = useMemo(() => {
    const start = startOfWeek(currentDate, { weekStartsOn: 0 });
    return eachDayOfInterval({ start, end: endOfWeek(currentDate, { weekStartsOn: 0 }) });
  }, [currentDate]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-10 rounded-xl bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-white font-bold text-xs shadow-lg">CCF</div>
        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} />
        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">Cargando {viewMeta.label}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-4 flex-1">
        <div className="size-12 rounded-full bg-red-50 dark:bg-red-500/10 flex items-center justify-center">
          <AlertTriangle size={24} className="text-[hsl(var(--destructive))]" />
        </div>
        <p className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{error}</p>
        <button onClick={refresh} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[hsl(var(--primary))] text-white shadow-lg shadow-[hsl(var(--info)/20%)] hover:brightness-110 transition-all active:scale-95">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="shrink-0 flex items-center justify-between px-3 py-2.5 border-b border-[hsl(var(--border))] dark:border-white/5 gap-2">
          <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-bold uppercase tracking-wide text-white" style={{ backgroundColor: viewMeta.color }}>
              {React.createElement(VIEW_ICONS[calendarView], { size: 11 })}
              {viewMeta.label}
            </div>
            <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
            <button onClick={prev} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors"><ChevronLeft size={16} /></button>
            <button onClick={next} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] transition-colors"><ChevronRight size={16} /></button>
            <h2 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white ml-1 min-w-[130px]">
              {timeMode === 'semana'
                ? `${format(weekDays[0], 'd')} – ${format(weekDays[6], 'd MMM', { locale: es })}`
                : timeMode === 'mes'
                  ? format(currentDate, 'MMMM yyyy', { locale: es })
                  : format(currentDate, "EEEE d 'de' MMMM", { locale: es })}
            </h2>
            <button onClick={() => setCurrentDate(new Date())} className="px-2 py-1 rounded-md text-2xs font-bold text-[hsl(var(--primary))] hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 transition-colors border border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/20">Hoy</button>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="relative">
              <button onClick={() => setShowViewDropdown(v => !v)} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all capitalize">
                {timeMode === 'semana' ? 'Semana' : timeMode === 'mes' ? 'Mes' : 'Día'}<ChevronDown size={11} />
              </button>
              <AnimatePresence>
                {showViewDropdown && (
                  <motion.div initial={{ opacity: 0, y: -4, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4, scale: 0.96 }} transition={{ duration: 0.12 }} className="absolute right-0 top-full mt-1.5 w-28 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50">
                    {(['semana', 'mes', 'dia'] as ViewMode[]).map(v => (
                      <button key={v} onClick={() => { setTimeMode(v); setShowViewDropdown(false); }} className={clsx('w-full text-left px-3 py-1.5 text-xs font-bold transition-colors capitalize', timeMode === v ? 'text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/10' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5')}>
                        {v === 'semana' ? 'Semana' : v === 'mes' ? 'Mes' : 'Día'}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <div className="relative">
              <button onClick={() => setShowCreateDropdown(v => !v)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-lg shadow-[hsl(var(--info)/20%)] hover:brightness-110 active:scale-95 transition-all" style={{ backgroundColor: viewMeta.color }}>
                <Plus size={13} /> Crear<ChevronDown size={11} />
              </button>
              <AnimatePresence>
                {showCreateDropdown && (
                  <motion.div initial={{ opacity: 0, y: -4, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4, scale: 0.96 }} transition={{ duration: 0.12 }} className="absolute right-0 top-full mt-1.5 w-48 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-xl overflow-hidden z-50">
                    {VIEW_CREATE_OPTIONS[calendarView].map((opt, i) => (
                      <button key={i} onClick={() => openCreation(opt.kind, opt.preset)} className="w-full text-left px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5">{opt.label}</button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {timeMode === 'semana' && (
          <WeekView weekDays={weekDays} visibleEvents={visibleEvents} viewColor={viewMeta.color} nowLine={nowLine} openPopoverDay={openPopoverDay} onOpenPopover={setOpenPopoverDay} onSave={handleSaveInlineEvent} onEventClick={handleEventClick} />
        )}
        {timeMode === 'mes' && (
          <MonthView currentDate={currentDate} events={events} onSave={handleSaveInlineEvent} onEventClick={handleEventClick} />
        )}
        {timeMode === 'dia' && (
          <DayView currentDate={currentDate} visibleEvents={visibleEvents} viewColor={viewMeta.color} nowLine={nowLine} openPopoverDay={openPopoverDay} onOpenPopover={setOpenPopoverDay} onSave={handleSaveInlineEvent} onEventClick={handleEventClick} />
        )}

        <div className="shrink-0 border-t border-[hsl(var(--border))] dark:border-white/5 px-4 py-2">
          <div className="max-w-lg mx-auto flex items-center gap-2 px-4 py-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[hsl(var(--text-secondary))] shrink-0"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <input placeholder="Busca eventos, personas, actividades..." className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))]" />
            <div className="size-5 rounded-full flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: viewMeta.color }}>
              <span className="text-2xs font-bold">✦</span>
            </div>
          </div>
        </div>
      </div>

      <CalendarPanel
        calendarView={calendarView}
        viewMeta={viewMeta}
        todayVisibleEvents={todayVisibleEvents}
        upcomingVisibleEvents={upcomingVisibleEvents}
        eventTypeCounts={eventTypeCounts}
        activeTypes={activeTypes}
        onToggleType={toggleTypeFilter}
        onRefresh={refresh}
        onCreate={openCreation}
        onViewChange={(v) => router.push(v === 'todo' ? '/plataforma/calendar' : `/plataforma/calendar?view=${v}`)}
        viewIcons={VIEW_ICONS}
        createOptions={VIEW_CREATE_OPTIONS[calendarView]}
      />
    </>
  );
}

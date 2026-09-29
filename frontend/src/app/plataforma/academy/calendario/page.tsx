"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { AlertTriangle, CalendarDays, ChevronLeft, ChevronRight, Clock3 } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import CalendarEventDrawer from '@/components/academy/CalendarEventDrawer';
import type { AcademyCalendarEvent, WorkloadPredictionResponse } from '@/types/academy';

type CalendarMode = 'month' | 'week';
type DateRange = { start: Date; end: Date };

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const EVENT_TONES: Record<string, string> = {
  evaluation: 'border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))]',
  assignment: 'border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))]',
  socratic_defense: 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.08)] text-[hsl(var(--warning))]',
  study_group: 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]',
  milestone: 'border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.08)] text-[hsl(var(--success))]',
};

function startOfWeek(date: Date) {
  const result = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  result.setDate(result.getDate() - ((result.getDay() + 6) % 7));
  return result;
}

function getRange(anchor: Date, mode: CalendarMode): DateRange {
  if (mode === 'week') {
    const start = startOfWeek(anchor);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  }
  return {
    start: new Date(anchor.getFullYear(), anchor.getMonth(), 1),
    end: new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0, 23, 59, 59, 999),
  };
}

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function formatDate(value: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('es', options).format(value);
}

export default function AcademyCalendarPage() {
  const [anchor, setAnchor] = useState(() => new Date());
  const [mode, setMode] = useState<CalendarMode>('month');
  const [events, setEvents] = useState<AcademyCalendarEvent[]>([]);
  const [prediction, setPrediction] = useState<WorkloadPredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<AcademyCalendarEvent | null>(null);
  const range = useMemo(() => getRange(anchor, mode), [anchor, mode]);

  const loadCalendar = useCallback(async () => {
    setLoading(true);
    try {
      const query = {
        start_date: range.start.toISOString(),
        end_date: range.end.toISOString(),
      };
      const [calendarEvents, workload] = await Promise.all([
        apiFetch<AcademyCalendarEvent[]>('/academy/calendar/events', { query }),
        apiFetch<WorkloadPredictionResponse>('/academy/calendar/workload-prediction', {
          query: { start_from: range.start.toISOString(), weeks_ahead: mode === 'month' ? 6 : 2 },
        }),
      ]);
      setEvents(calendarEvents);
      setPrediction(workload);
    } catch (error) {
      toast.error(extractErrorMessage(error, 'No pudimos cargar el calendario académico.'));
      setEvents([]);
      setPrediction(null);
    } finally {
      setLoading(false);
    }
  }, [mode, range.end, range.start]);

  useEffect(() => { void loadCalendar(); }, [loadCalendar]);

  const visibleDays = useMemo(() => {
    const first = mode === 'week' ? range.start : startOfWeek(range.start);
    const last = mode === 'week' ? range.end : startOfWeek(range.end);
    if (mode === 'month') last.setDate(last.getDate() + 6);
    const days: Date[] = [];
    for (const cursor = new Date(first); cursor <= last; cursor.setDate(cursor.getDate() + 1)) {
      days.push(new Date(cursor));
    }
    return days;
  }, [mode, range.end, range.start]);

  const eventsByDay = useMemo(() => {
    const groups = new Map<string, AcademyCalendarEvent[]>();
    events.forEach((event) => {
      const key = dateKey(new Date(event.start_date));
      groups.set(key, [...(groups.get(key) ?? []), event]);
    });
    return groups;
  }, [events]);

  const overloadedWeeks = prediction?.weeks.filter((week) => week.is_overloaded) ?? [];
  const title = mode === 'month'
    ? formatDate(anchor, { month: 'long', year: 'numeric' })
    : `${formatDate(range.start, { day: 'numeric', month: 'short' })} – ${formatDate(range.end, { day: 'numeric', month: 'short', year: 'numeric' })}`;

  function movePeriod(direction: -1 | 1) {
    setAnchor((current) => {
      const next = new Date(current);
      if (mode === 'month') next.setMonth(next.getMonth() + direction);
      else next.setDate(next.getDate() + direction * 7);
      return next;
    });
  }

  return (
    <main className="space-y-5 p-4 text-[hsl(var(--text-primary))] md:p-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--primary))]">Organización académica</p>
          <h1 className="mt-1 text-2xl font-bold">Calendario inteligente</h1>
          <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Consulta tus fechas clave y anticipa semanas de alta carga.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-1" aria-label="Vista de calendario">
            {(['month', 'week'] as const).map((value) => (
              <button key={value} type="button" onClick={() => setMode(value)} aria-pressed={mode === value} className={clsx(
                'rounded-md px-3 py-1.5 text-xs font-semibold transition-colors',
                mode === value ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))]',
              )}>{value === 'month' ? 'Mes' : 'Semana'}</button>
            ))}
          </div>
          <DSButton type="button" variant="secondary" onClick={() => movePeriod(-1)} aria-label="Periodo anterior"><ChevronLeft className="size-4" /></DSButton>
          <span className="min-w-36 text-center text-sm font-semibold capitalize">{title}</span>
          <DSButton type="button" variant="secondary" onClick={() => movePeriod(1)} aria-label="Periodo siguiente"><ChevronRight className="size-4" /></DSButton>
        </div>
      </header>

      {overloadedWeeks.length > 0 && (
        <section className="rounded-xl border border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.08)] p-4" aria-live="polite">
          <div className="flex items-start gap-3">
            <span className="rounded-lg bg-[hsl(var(--warning)/0.14)] p-2 text-[hsl(var(--warning))]"><AlertTriangle className="size-5" /></span>
            <div className="min-w-0">
              <h2 className="font-semibold">Semana(s) con sobrecarga detectada</h2>
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">
                {overloadedWeeks.map((week) => `Semana ${week.week_number}`).join(' · ')}. Considera dividir las tareas en sesiones cortas y comenzar por las entregas con fecha más próxima.
              </p>
              {prediction?.recommendations[0] && <p className="mt-2 text-sm">Sugerencia: {prediction.recommendations[0]}</p>}
            </div>
          </div>
        </section>
      )}

      {loading ? (
        <section className="space-y-3" aria-label="Cargando calendario">
          <DSSkeleton className="h-10 w-full rounded-xl" />
          <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--border))] sm:grid-cols-2 lg:grid-cols-7">
            {Array.from({ length: mode === 'month' ? 35 : 7 }, (_, index) => <DSSkeleton key={index} className="min-h-28 rounded-none bg-[hsl(var(--surface-1))]" />)}
          </div>
        </section>
      ) : (
        <section className="overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
          <div className="grid grid-cols-7 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
            {WEEKDAYS.map((day) => <div key={day} className="px-1 py-2 text-center text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] sm:px-2 sm:text-xs">{day}</div>)}
          </div>
          {events.length === 0 && <div className="border-b border-[hsl(var(--border))] p-3"><EmptyState title="Sin eventos en este periodo" description="No hay fechas académicas registradas para el rango seleccionado." icon={CalendarDays} /></div>}
          <div className="grid grid-cols-7 gap-px bg-[hsl(var(--border))]">
            {visibleDays.map((day) => {
              const dayEvents = eventsByDay.get(dateKey(day)) ?? [];
              const inPeriod = mode === 'week' || day.getMonth() === anchor.getMonth();
              return (
                <div key={dateKey(day)} className={clsx('min-h-24 bg-[hsl(var(--surface-1))] p-1 sm:min-h-32 sm:p-2', !inPeriod && 'opacity-45')}>
                  <span className={clsx('grid size-6 place-items-center rounded-full text-xs', dateKey(day) === dateKey(new Date()) && 'bg-[hsl(var(--primary))] font-bold text-[hsl(var(--primary-foreground))]')}>
                    {day.getDate()}
                  </span>
                  <div className="mt-1 space-y-1">
                    {dayEvents.slice(0, mode === 'week' ? 8 : 3).map((event) => (
                      <button key={event.id} type="button" onClick={() => setSelectedEvent(event)} title={event.title} className={clsx('block w-full truncate rounded border px-1 py-1 text-left text-[10px] leading-tight sm:text-xs', EVENT_TONES[event.event_type] ?? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))]')}>
                        <span className="hidden sm:inline">{formatDate(new Date(event.start_date), { hour: '2-digit', minute: '2-digit' })} </span>{event.title}
                      </button>
                    ))}
                    {dayEvents.length > (mode === 'week' ? 8 : 3) && <p className="px-1 text-[10px] text-[hsl(var(--text-secondary))]">+{dayEvents.length - (mode === 'week' ? 8 : 3)} más</p>}
                  </div>
                </div>
              );
            })}
          </div>
          {events.length > 0 && <p className="flex items-center gap-2 border-t border-[hsl(var(--border))] px-3 py-2 text-xs text-[hsl(var(--text-secondary))]"><Clock3 className="size-3.5" /> {events.length} {events.length === 1 ? 'evento' : 'eventos'} en este periodo</p>}
        </section>
      )}

      <CalendarEventDrawer open={selectedEvent !== null} onClose={() => setSelectedEvent(null)} event={selectedEvent} />
    </main>
  );
}

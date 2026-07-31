'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/http';
import { CalEvent, CalEventType, CalendarView, getEventTypeColor } from '@/types/calendar';
import type { ProjectTaskRecord } from '@/types/projects';

interface UseCalendarDataOptions {
  token: string | null;
  calendarView: CalendarView;
}

interface UseCalendarDataResult {
  events: CalEvent[];
  tasks: ProjectTaskRecord[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useCalendarData({ token, calendarView }: UseCalendarDataOptions): UseCalendarDataResult {
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCalendar = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch<Array<Record<string, unknown>>>(
        `/system/calendar?view=${calendarView}`,
        { token },
      ).catch(() => []);
      if (Array.isArray(data)) {
        setEvents(data.map((e: Record<string, unknown>) => ({
          id: e.id as string,
          title: e.title as string,
          start: new Date(e.start as string),
          end: e.end ? new Date(e.end as string) : undefined,
          color: getEventTypeColor(e.type as CalEventType),
          type: e.type as CalEventType,
          allDay: (e.allDay as boolean) ?? false,
          href: e.href as string | undefined,
          location: e.location as string | undefined,
        })));
      }
    } catch {
      // Silently handle fetch errors
    }
  }, [token, calendarView]);

  const fetchTasks = useCallback(async () => {
    if (!token || calendarView !== 'proyectos') return;
    try {
      const data = await apiFetch<{ _tasks: ProjectTaskRecord[] }>('/projects/_tasks', { token }).catch(() => null);
      if (data?._tasks) setTasks(data._tasks);
    } catch {
      // Silently handle fetch errors
    }
  }, [token, calendarView]);

  const refresh = useCallback(async () => {
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

  useEffect(() => { refresh(); }, [refresh]);

  // Reset events when view changes
  useEffect(() => {
    setEvents([]);
  }, [calendarView]);

  return { events, tasks, loading, error, refresh };
}

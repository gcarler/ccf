// ── Types ──────────────────────────────────────────────────────────────────
export type ViewMode = 'semana' | 'mes' | 'dia';

export interface CalEvent {
  id: string;
  title: string;
  start: Date;
  end?: Date;
  color: string;
  type: 'task' | 'agenda_event' | 'evangelism_event' | 'consolidation_case' | 'consolidation_task' | 'birthday' | 'reminder';
  allDay?: boolean;
  priority?: string;
  href?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────
export const HOURS = Array.from({ length: 24 }, (_, i) => i);
export const HOUR_HEIGHT = 60; // px per hour

export const EVENT_TYPE_META: Record<CalEvent['type'], { label: string; chip: string }> = {
  task: {
    label: 'Tarea',
    chip: 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-blue-300',
  },
  agenda_event: {
    label: 'Agenda simple',
    chip: 'bg-red-50 text-[hsl(var(--destructive))] dark:bg-red-500/10 dark:text-red-300',
  },
  evangelism_event: {
    label: 'Evangelismo',
    chip: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
  },
  consolidation_case: {
    label: 'Consolidación',
    chip: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
  },
  consolidation_task: {
    label: 'Seguimiento',
    chip: 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-500/10 dark:text-fuchsia-300',
  },
  birthday: {
    label: 'Cumpleaños',
    chip: 'bg-pink-50 text-pink-700 dark:bg-pink-500/10 dark:text-pink-300',
  },
  reminder: {
    label: 'Recordatorio',
    chip: 'bg-slate-50 text-slate-700 dark:bg-white/10 dark:text-slate-300',
  },
};

export const CALENDAR_EVENT_TYPES: CalEvent['type'][] = [
  'agenda_event',
  'evangelism_event',
  'consolidation_case',
  'consolidation_task',
  'task',
  'birthday',
  'reminder',
];

// ── Helpers ────────────────────────────────────────────────────────────────
export function getEventTypeColor(eventType: CalEvent['type']) {
  if (eventType === 'task') return '#7c3aed';
  if (eventType === 'evangelism_event') return '#10b981';
  if (eventType === 'consolidation_case') return '#f59e0b';
  if (eventType === 'consolidation_task') return '#d946ef';
  if (eventType === 'birthday') return '#ec4899';
  return '#ef4444';
}

export function minutesToTop(date: Date) {
  return (date.getHours() * 60 + date.getMinutes()) * (HOUR_HEIGHT / 60);
}

export function formatHour(h: number) {
  if (h === 0) return '12 am';
  if (h === 12) return '12 pm';
  return h < 12 ? `${h} am` : `${h - 12} pm`;
}

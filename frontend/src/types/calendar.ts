// ── Views ──────────────────────────────────────────────────────────────────
export type CalendarView = 'todo' | 'evangelismo' | 'crm' | 'proyectos' | 'personal' | 'cumpleanos';
export type ViewMode = 'semana' | 'mes' | 'dia';

// ── Event types ─────────────────────────────────────────────────────────────
export type CalEventType =
  | 'task'
  | 'agenda_event'
  | 'evangelism_event'
  | 'evangelism_strategy'
  | 'evangelism_session'
  | 'consolidation_case'
  | 'consolidation_task'
  | 'project_milestone'
  | 'birthday'
  | 'reminder';

export interface CalEvent {
  id: string;
  title: string;
  start: Date;
  end?: Date;
  color: string;
  type: CalEventType;
  allDay?: boolean;
  priority?: string;
  href?: string;
  location?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────
export const HOURS = Array.from({ length: 24 }, (_, i) => i);
export const HOUR_HEIGHT = 60; // px per hour

export const EVENT_TYPE_META: Record<CalEventType, { label: string; chip: string; color: string }> = {
  task: {
    label: 'Tarea',
    chip: 'bg-violet-50 text-violet-700 dark:bg-violet-500/10 dark:text-violet-300',
    color: '#7c3aed',
  },
  agenda_event: {
    label: 'Agenda',
    chip: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-300',
    color: '#ef4444',
  },
  evangelism_event: {
    label: 'Evento',
    chip: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
    color: '#10b981',
  },
  evangelism_strategy: {
    label: 'Estrategia',
    chip: 'bg-teal-50 text-teal-700 dark:bg-teal-500/10 dark:text-teal-300',
    color: '#0d9488',
  },
  evangelism_session: {
    label: 'Sesión grupo',
    chip: 'bg-green-50 text-green-700 dark:bg-green-500/10 dark:text-green-300',
    color: '#16a34a',
  },
  consolidation_case: {
    label: 'Consolidación',
    chip: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
    color: '#f59e0b',
  },
  consolidation_task: {
    label: 'Tarea CRM',
    chip: 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-500/10 dark:text-fuchsia-300',
    color: '#d946ef',
  },
  project_milestone: {
    label: 'Hito',
    chip: 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300',
    color: '#3b82f6',
  },
  birthday: {
    label: 'Cumpleaños',
    chip: 'bg-pink-50 text-pink-700 dark:bg-pink-500/10 dark:text-pink-300',
    color: '#ec4899',
  },
  reminder: {
    label: 'Recordatorio',
    chip: 'bg-slate-50 text-slate-700 dark:bg-white/10 dark:text-slate-300',
    color: '#64748b',
  },
};

// Types shown per calendar view
export const VIEW_EVENT_TYPES: Record<CalendarView, CalEventType[]> = {
  todo: [
    'agenda_event', 'evangelism_event', 'evangelism_strategy', 'evangelism_session',
    'consolidation_case', 'consolidation_task', 'task', 'project_milestone', 'birthday',
  ],
  evangelismo: ['evangelism_strategy', 'evangelism_session', 'evangelism_event'],
  crm: ['consolidation_case', 'consolidation_task'],
  proyectos: ['task', 'project_milestone'],
  personal: ['agenda_event', 'birthday', 'reminder'],
  cumpleanos: ['birthday'],
};

export const CALENDAR_EVENT_TYPES: CalEventType[] = [
  'agenda_event',
  'evangelism_event',
  'evangelism_strategy',
  'evangelism_session',
  'consolidation_case',
  'consolidation_task',
  'task',
  'project_milestone',
  'birthday',
  'reminder',
];

// ── View metadata ──────────────────────────────────────────────────────────
export const CALENDAR_VIEW_META: Record<CalendarView, { label: string; description: string; color: string }> = {
  todo: {
    label: 'Todo',
    description: 'Todos los eventos y actividades',
    color: '#018abd',
  },
  evangelismo: {
    label: 'Evangelismo',
    description: 'Estrategias, sesiones y eventos evangelísticos',
    color: '#10b981',
  },
  crm: {
    label: 'Consolidación',
    description: 'Seguimientos CRM y tareas pastorales',
    color: '#f59e0b',
  },
  proyectos: {
    label: 'Proyectos',
    description: 'Tareas e hitos de proyectos',
    color: '#7c3aed',
  },
  personal: {
    label: 'Personal',
    description: 'Mi agenda y fechas personales',
    color: '#ef4444',
  },
  cumpleanos: {
    label: 'Cumpleaños',
    description: 'Cumpleaños de los miembros de la iglesia',
    color: '#ec4899',
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
export function getEventTypeColor(type: CalEventType): string {
  return EVENT_TYPE_META[type]?.color ?? '#018abd';
}

export function minutesToTop(date: Date): number {
  return (date.getHours() * 60 + date.getMinutes()) * (HOUR_HEIGHT / 60);
}

export function formatHour(h: number): string {
  if (h === 0) return '12 am';
  if (h === 12) return '12 pm';
  return h < 12 ? `${h} am` : `${h - 12} pm`;
}

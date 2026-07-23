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
    chip: 'bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10 dark:text-info-text',
    color: '#3b82f6',
  },
  agenda_event: {
    label: 'Agenda',
    chip: 'bg-red-50 text-[hsl(var(--destructive))] dark:bg-red-500/10 dark:text-red-300',
    color: '#ef4444',
  },
  evangelism_event: {
    label: 'Evento',
    chip: 'bg-success-soft text-success-text dark:bg-[hsl(var(--success))]/10 dark:text-success-text',
    color: '#10b981',
  },
  evangelism_strategy: {
    label: 'Estrategia',
    chip: 'bg-[hsl(var(--domain-teal)/10%)] text-[hsl(var(--domain-teal)/90%)] dark:bg-[hsl(var(--domain-teal)/10%)] dark:text-[hsl(var(--domain-teal))]',
    color: '#0d9488',
  },
  evangelism_session: {
    label: 'Sesión grupo',
    chip: 'bg-green-50 text-[hsl(var(--secondary))] dark:bg-green-500/10 dark:text-green-300',
    color: '#16a34a',
  },
  consolidation_case: {
    label: 'Consolidación',
    chip: 'bg-warning-soft text-warning-text dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text',
    color: '#f59e0b',
  },
  consolidation_task: {
    label: 'Tarea CRM',
    chip: 'bg-[hsl(var(--domain-fuchsia)/10%)] text-[hsl(var(--domain-fuchsia)/90%)] dark:bg-[hsl(var(--domain-fuchsia)/10%)] dark:text-[hsl(var(--domain-fuchsia))]',
    color: '#d946ef',
  },
  project_milestone: {
    label: 'Hito',
    chip: 'bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10 dark:text-info-text',
    color: '#3b82f6',
  },
  birthday: {
    label: 'Cumpleaños',
    chip: 'bg-[hsl(var(--domain-pink)/10%)] text-[hsl(var(--domain-pink)/90%)] dark:bg-[hsl(var(--domain-pink)/10%)] dark:text-[hsl(var(--domain-pink))]',
    color: '#ec4899',
  },
  reminder: {
    label: 'Recordatorio',
    chip: 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]',
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
    description: 'Cumpleaños de las personas de la iglesia',
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

// Canonical task status/priority enums shared across the projects frontend.
// These values must stay in sync with the backend schemas.

export const TASK_STATUSES = ['todo', 'in_progress', 'review', 'completed'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const;
export type TaskPriority = (typeof TASK_PRIORITIES)[number];

export const DEFAULT_TASK_STATUS: TaskStatus = 'todo';
export const DEFAULT_TASK_PRIORITY: TaskPriority = 'medium';

export const STATUS_LABELS: Record<TaskStatus, string> = {
    todo: 'Pendiente',
    in_progress: 'En Progreso',
    review: 'En Revisión',
    completed: 'Completado',
};

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
    low: 'Baja',
    medium: 'Media',
    high: 'Alta',
    urgent: 'Urgente',
};

// Cycles used by click-to-toggle UI flows.
export const STATUS_CYCLE: TaskStatus[] = [...TASK_STATUSES];
export const PRIORITY_CYCLE: TaskPriority[] = [...TASK_PRIORITIES];

// ─── Visual status option configs (shared across project views) ───────────────
export interface StatusOption {
    readonly value: TaskStatus;
    readonly label: string;
    readonly dot: string;
    readonly bg: string;
    readonly text: string;
    readonly border: string;
}

export const STATUS_OPTIONS: readonly StatusOption[] = [
    { value: 'todo',        label: 'Pendiente',   dot: 'bg-[hsl(var(--surface-2))]',   bg: 'bg-[hsl(var(--surface-2))] dark:bg-white/5',           text: 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',    border: 'border-[hsl(var(--border))] dark:border-white/10' },
    { value: 'in_progress', label: 'En Progreso', dot: 'bg-[hsl(var(--primary))]',    bg: 'bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/20',         text: 'text-[hsl(var(--primary))] dark:text-info-text',        border: 'border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/30' },
    { value: 'review',      label: 'En Revisión', dot: 'bg-[hsl(var(--warning))]',   bg: 'bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning))]/20',    text: 'text-warning-text dark:text-warning-text',  border: 'border-[hsl(var(--warning)/25%)] dark:border-[hsl(var(--warning)/100%)]/30' },
    { value: 'completed',   label: 'Completado',  dot: 'bg-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success))]/20',  text: 'text-success-text dark:text-success-text', border: 'border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/30' },
] as const;

export function getStatusOption(val: string): StatusOption {
    return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0];
}

// ─── Visual priority option configs (shared across project views) ─────────────
export interface PriorityOption {
    readonly value: TaskPriority;
    readonly label: string;
    readonly color: string;
    readonly fill: string;
    readonly dot: string;
}

export const PRIORITY_OPTIONS: readonly PriorityOption[] = [
    { value: 'low',    label: 'Baja',    color: 'text-[hsl(var(--text-secondary))]',  fill: 'hsl(var(--text-secondary))', dot: 'bg-slate-500' },
    { value: 'medium', label: 'Media',   color: 'text-[hsl(var(--primary))]',         fill: 'hsl(var(--primary))',        dot: 'bg-[hsl(var(--primary))]' },
    { value: 'high',   label: 'Alta',    color: 'text-orange-600',                    fill: 'hsl(var(--warning))',        dot: 'bg-orange-500' },
    { value: 'urgent', label: 'Urgente', color: 'text-danger-text',                   fill: 'hsl(var(--destructive))',    dot: 'bg-[hsl(var(--danger))]' },
] as const;

export function getPriorityOption(val: string): PriorityOption {
    return PRIORITY_OPTIONS.find(p => p.value === val) ?? PRIORITY_OPTIONS[1];
}

// ─── Group pill styles for status headers ─────────────────────────────────────
export const STATUS_GROUP_PILL: Record<TaskStatus, string> = {
    todo:        'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]',
    in_progress: 'bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/20 dark:text-info-text',
    review:      'bg-[hsl(var(--warning-muted))] text-warning-text dark:bg-[hsl(var(--warning))]/30 dark:text-[hsl(var(--warning))]',
    completed:   'bg-[hsl(var(--success-muted))] text-success-text dark:bg-[hsl(var(--success))]/30 dark:text-[hsl(var(--success))]',
};

/** Return a valid TaskStatus or the default fallback. */
export function getValidStatus(value: string | null | undefined): TaskStatus {
    return TASK_STATUSES.includes(value as TaskStatus) ? (value as TaskStatus) : DEFAULT_TASK_STATUS;
}

/** Return a valid TaskPriority or the default fallback. */
export function getValidPriority(value: string | null | undefined): TaskPriority {
    return TASK_PRIORITIES.includes(value as TaskPriority) ? (value as TaskPriority) : DEFAULT_TASK_PRIORITY;
}

// --- Project-level status (5 canonical values, mirrored from the backend
// Pydantic `ProjectStatus` Literal in `backend/schemas/projects.py`).
//
// Task-level status is intentionally NOT normalized here because it adopts
// dynamic ProjectPhase.slug values (see _assert_status_in_project_phases in
// backend/api/projects.py and PhaseManagerDrawer.tsx on the frontend).
export const PROJECT_STATUSES = ['planning', 'active', 'on_hold', 'completed', 'archived'] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];
export const DEFAULT_PROJECT_STATUS: ProjectStatus = 'planning';

/**
 * Spanish display labels for the project status enum. Per-component visual
 * variants (e.g. InlineProjectStatusPicker) MAY override for friendly copy
 * ("En Marcha", "Alcanzado") — those are visual display decisions, not wire
 * format.
 */
export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
    planning: 'Planificación',
    active: 'Activo',
    on_hold: 'En Pausa',
    completed: 'Completado',
    archived: 'Archivado',
};

/** Return a valid ProjectStatus or the default fallback. */
export function getValidProjectStatus(value: string | null | undefined): ProjectStatus {
    return (PROJECT_STATUSES as readonly string[]).includes(value ?? '')
        ? (value as ProjectStatus)
        : DEFAULT_PROJECT_STATUS;
}

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

/** Return a valid TaskStatus or the default fallback. */
export function getValidStatus(value: string | null | undefined): TaskStatus {
    return TASK_STATUSES.includes(value as TaskStatus) ? (value as TaskStatus) : DEFAULT_TASK_STATUS;
}

/** Return a valid TaskPriority or the default fallback. */
export function getValidPriority(value: string | null | undefined): TaskPriority {
    return TASK_PRIORITIES.includes(value as TaskPriority) ? (value as TaskPriority) : DEFAULT_TASK_PRIORITY;
}

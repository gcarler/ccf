import type { ProjectAttachment, ProjectRecord, ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';
import { normalizeTaskPriority, normalizeTaskStatus } from '@/lib/projects/constants';

export type TaskScope = 'mine' | 'all';
export type TaskStatusFilter = 'all' | 'todo' | 'in_progress' | 'review' | 'completed' | 'overdue';

export type TaskViewItem = ProjectTaskRecord & {
    project_title?: string;
};

type ApiRecord = Record<string, unknown>;

function isRecord(value: unknown): value is ApiRecord {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asRecord(value: unknown): ApiRecord {
    return isRecord(value) ? value : {};
}

function stringValue(value: unknown, fallback = ''): string {
    if (typeof value === 'string') return value;
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
    return fallback;
}

function nullableString(value: unknown): string | null {
    return typeof value === 'string' ? value : null;
}

function optionalString(value: unknown): string | undefined {
    return typeof value === 'string' ? value : undefined;
}

function normalizeSupply(value: unknown): TaskSupplyRecord | null {
    const row = asRecord(value);
    if (
        typeof row.id !== 'string' ||
        typeof row.task_id !== 'string' ||
        typeof row.item_name !== 'string' ||
        typeof row.quantity !== 'number' ||
        typeof row.status !== 'string'
    ) return null;

    // Literal canónico de backend/schemas/projects.py (TaskSupplyBase.status).
    const SUPPLY_STATUSES = [
        'pending', 'ready', 'unavailable', 'received', 'approved', 'purchased', 'paid',
    ] as const;
    const supplyStatus = SUPPLY_STATUSES.includes(row.status as (typeof SUPPLY_STATUSES)[number])
        ? (row.status as (typeof SUPPLY_STATUSES)[number])
        : 'pending';

    return {
        id: row.id,
        task_id: row.task_id,
        item_name: row.item_name,
        quantity: row.quantity,
        status: supplyStatus,
    };
}

function normalizeAttachment(value: unknown): ProjectAttachment | null {
    const row = asRecord(value);
    if (
        typeof row.id !== 'string' ||
        typeof row.task_id !== 'string' ||
        typeof row.filename !== 'string' ||
        typeof row.file_url !== 'string'
    ) return null;

    return {
        id: row.id,
        task_id: row.task_id,
        filename: row.filename,
        file_url: row.file_url,
        file_size: typeof row.file_size === 'number' ? row.file_size : null,
        file_type: nullableString(row.file_type),
        content_type: nullableString(row.content_type),
        uploader_id: nullableString(row.uploader_id),
        uploaded_by: nullableString(row.uploaded_by),
        created_at: optionalString(row.created_at),
    };
}

export function normalizeTaskRow(value: unknown, projectTitle?: string): TaskViewItem {
    const row = asRecord(value);
    const project = asRecord(row.project);
    const supplies = Array.isArray(row.supplies) ? row.supplies.map(normalizeSupply).filter((item) => item !== null) : [];
    const attachments = Array.isArray(row.attachments) ? row.attachments.map(normalizeAttachment).filter((item) => item !== null) : [];
    const subtasks = Array.isArray(row.subtasks)
        ? row.subtasks.filter(isRecord).map((item) => normalizeTaskRow(item, projectTitle))
        : [];

    return {
        id: stringValue(row.id),
        project_id: stringValue(row.project_id),
        title: typeof row.title === 'string' && row.title.trim() ? row.title : 'Tarea sin título',
        description: nullableString(row.description),
        created_at: optionalString(row.created_at),
        updated_at: nullableString(row.updated_at),
        status: normalizeTaskStatus(stringValue(row.status, 'todo')),
        priority: normalizeTaskPriority(stringValue(row.priority, 'medium')),
        assignee_id: nullableString(row.assignee_id),
        parent_id: nullableString(row.parent_id),
        start_date: nullableString(row.start_date),
        due_date: nullableString(row.due_date),
        node: nullableString(row.node),
        labels: Array.isArray(row.labels) ? row.labels.filter((label): label is string => typeof label === 'string') : [],
        order_index: typeof row.order_index === 'number' ? row.order_index : undefined,
        supplies,
        subtasks,
        attachments,
        comments_count: typeof row.comments_count === 'number' ? row.comments_count : undefined,
        project_title: optionalString(row.project_title) || optionalString(project.title) || projectTitle,
    };
}

export function flattenProjectTasks(projects: ProjectRecord[]): TaskViewItem[] {
    const rows = projects.flatMap((project) =>
        (Array.isArray(project.tasks) ? project.tasks : []).map((task) =>
            normalizeTaskRow(task, project.title),
        ),
    );

    return rows.sort((a, b) => {
        const projectCompare = String(a.project_title || '').localeCompare(String(b.project_title || ''));
        if (projectCompare !== 0) return projectCompare;

        const createdA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const createdB = b.created_at ? new Date(b.created_at).getTime() : 0;
        if (createdA !== createdB) return createdB - createdA;

        return String(a.title || '').localeCompare(String(b.title || ''));
    });
}

/** PMI §5.4 / §7.3 — Agregador WBS/EVMT sobre un lote de paquetes de trabajo. */
export interface WbsTaskMetricsSummary {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
  /** Crédito EVMT consolidado (regla fija 0/50/100) del lote, en %. */
  evmtPercent: number;
  /** Paquetes con definición WBS completa: descripción + fecha + responsable. */
  wbsDefinedCount: number;
  /** Preparación WBS del lote, en %. */
  wbsReadinessPercent: number;
}

export type WbsMetricTask = Pick<
  ProjectTaskRecord,
  'status' | 'due_date' | 'assignee_id' | 'description'
>;

export function computeWbsTaskMetrics(tasks: ReadonlyArray<WbsMetricTask>): WbsTaskMetricsSummary {
  let completed = 0;
  let inProgress = 0;
  let overdue = 0;
  let wbsDefinedCount = 0;

  for (const task of tasks) {
    const status = normalizeTaskStatus(task.status);
    if (status === 'completed') completed += 1;
    else if (status === 'in_progress' || status === 'review') inProgress += 1;
    if (isTaskOverdue(task)) overdue += 1;
    const hasWbsDefinition = Boolean(task.description && task.description.trim().length > 0)
      && Boolean(task.due_date)
      && Boolean(task.assignee_id);
    if (hasWbsDefinition) wbsDefinedCount += 1;
  }

  const total = tasks.length;
  return {
    total,
    completed,
    inProgress,
    overdue,
    evmtPercent: total > 0 ? Math.round(((completed * 100 + inProgress * 50) / (total * 100)) * 100) : 0,
    wbsDefinedCount,
    wbsReadinessPercent: total > 0 ? Math.round((wbsDefinedCount / total) * 100) : 0,
  };
}

export function isTaskOverdue(task: Pick<ProjectTaskRecord, 'due_date' | 'status'>): boolean {
    if (!task.due_date) return false;
    if ((task.status || '').toLowerCase() === 'completed') return false;
    return new Date(task.due_date).getTime() < Date.now();
}

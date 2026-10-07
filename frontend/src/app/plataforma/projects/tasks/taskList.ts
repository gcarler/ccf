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

    return {
        id: row.id,
        task_id: row.task_id,
        item_name: row.item_name,
        quantity: row.quantity,
        status: row.status,
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

export function isTaskOverdue(task: Pick<ProjectTaskRecord, 'due_date' | 'status'>): boolean {
    if (!task.due_date) return false;
    if ((task.status || '').toLowerCase() === 'completed') return false;
    return new Date(task.due_date).getTime() < Date.now();
}

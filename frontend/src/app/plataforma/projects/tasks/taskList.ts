import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

export type TaskScope = 'mine' | 'all';
export type TaskStatusFilter = 'all' | 'todo' | 'in_progress' | 'review' | 'completed' | 'overdue';

export type TaskViewItem = ProjectTaskRecord & {
    project_title?: string;
};

export function normalizeTaskRow(row: any, projectTitle?: string): TaskViewItem {
    return {
        id: String(row.id),
        project_id: String(row.project_id || ''),
        title: String(row.title || 'Tarea sin titulo'),
        description: row.description || null,
        created_at: row.created_at || undefined,
        status: String(row.status || 'todo'),
        priority: row.priority || 'medium',
        assignee_id: row.assignee_id ? String(row.assignee_id) : null,
        parent_id: row.parent_id ? String(row.parent_id) : null,
        start_date: row.start_date || null,
        due_date: row.due_date || null,
        labels: Array.isArray(row.labels) ? row.labels : [],
        supplies: Array.isArray(row.supplies) ? row.supplies : [],
        subtasks: Array.isArray(row.subtasks) ? row.subtasks : [],
        attachments: Array.isArray(row.attachments) ? row.attachments : [],
        comments_count: typeof row.comments_count === 'number' ? row.comments_count : undefined,
        project_title: row.project_title || row.project?.title || projectTitle,
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

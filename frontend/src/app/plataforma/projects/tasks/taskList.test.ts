import { describe, expect, it } from 'vitest';
import { flattenProjectTasks, normalizeTaskRow } from './taskList';

describe('normalizeTaskRow', () => {
    it('normalizes API fields and resolves a nested project title', () => {
        const task = normalizeTaskRow({
            id: 42,
            project_id: 'project-1',
            title: 'Preparar reunión',
            status: 'in_progress',
            priority: 'high',
            due_date: '2026-10-20',
            project: { title: 'Plan anual' },
            labels: ['pastoral', 9, null],
            supplies: [{ id: 's1', task_id: '42', item_name: 'Guías', quantity: 3, status: 'ready' }],
            attachments: [{ id: 'a1', task_id: '42', filename: 'agenda.pdf', file_url: '/agenda.pdf' }],
        });

        expect(task).toMatchObject({
            id: '42',
            project_id: 'project-1',
            title: 'Preparar reunión',
            status: 'in_progress',
            priority: 'high',
            due_date: '2026-10-20',
            project_title: 'Plan anual',
            labels: ['pastoral'],
        });
        expect(task.supplies).toHaveLength(1);
    expect(task.attachments).toHaveLength(1);
  });

    it('normalizes compatibility status and priority values from the API', () => {
        expect(normalizeTaskRow({ id: 'done', status: 'done', priority: 'normal' })).toMatchObject({
            status: 'completed',
            priority: 'medium',
        });
        expect(normalizeTaskRow({ id: 'blocked', status: 'blocked', priority: 'high' })).toMatchObject({
            status: 'todo',
            priority: 'high',
        });
    });

    it('uses safe defaults and drops malformed nested values', () => {
        const task = normalizeTaskRow({
            id: { unexpected: true },
            title: 17,
            status: null,
            labels: ['valid', {}, 3],
            supplies: [{ id: 'incomplete' }, null],
            subtasks: [null, 'invalid', { id: 'sub-1', title: 'Subtarea' }],
            attachments: [{ filename: 'orphan.pdf' }, false],
        });

        expect(task).toMatchObject({
            id: '',
            project_id: '',
            title: 'Tarea sin título',
            status: 'todo',
            priority: 'medium',
            labels: ['valid'],
            supplies: [],
            attachments: [],
        });
        expect(task.subtasks).toHaveLength(1);
        expect(task.subtasks?.[0].id).toBe('sub-1');
    });

    it('retains project context when flattening embedded project tasks', () => {
        const tasks = flattenProjectTasks([{
            id: 'project-1',
            title: 'Plan anual',
            status: 'active',
            created_at: '2026-10-01T10:00:00Z',
            tasks: [{ id: 'task-1', project_id: 'project-1', title: 'Definir metas', status: 'todo', priority: 'medium' }],
        }]);

        expect(tasks).toHaveLength(1);
        expect(tasks[0].project_title).toBe('Plan anual');
    });
});

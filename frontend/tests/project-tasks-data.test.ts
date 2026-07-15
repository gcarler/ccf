import { describe, expect, it } from 'vitest';

import { flattenProjectTasks, isTaskOverdue } from '@/app/plataforma/projects/tasks/taskList';

describe('project tasks data helpers', () => {
    it('flattens tasks from multiple projects with project titles attached', () => {
        const rows = flattenProjectTasks([
            {
                id: 'p1',
                title: 'Proyecto Uno',
                status: 'active',
                created_at: '2026-07-01T10:00:00Z',
                tasks: [
                    { id: 't1', project_id: 'p1', title: 'Tarea A', status: 'todo', priority: 'medium', created_at: '2026-07-01T12:00:00Z' } as any,
                ],
            } as any,
            {
                id: 'p2',
                title: 'Proyecto Dos',
                status: 'active',
                created_at: '2026-07-02T10:00:00Z',
                tasks: [
                    { id: 't2', project_id: 'p2', title: 'Tarea B', status: 'completed', priority: 'high', created_at: '2026-07-02T12:00:00Z' } as any,
                ],
            } as any,
        ]);

        expect(rows).toHaveLength(2);
        expect(rows[0].project_title).toBe('Proyecto Dos');
        expect(rows[1].project_title).toBe('Proyecto Uno');
    });

    it('detects overdue tasks only when they are not completed', () => {
        expect(isTaskOverdue({ due_date: '2000-01-01T00:00:00Z', status: 'todo' })).toBe(true);
        expect(isTaskOverdue({ due_date: '2000-01-01T00:00:00Z', status: 'completed' })).toBe(false);
        expect(isTaskOverdue({ due_date: null, status: 'todo' })).toBe(false);
    });
});

import { describe, expect, it } from 'vitest';
import {
  computeWbsTaskMetrics,
  flattenProjectTasks,
  normalizeTaskRow,
} from './taskList';

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

describe('computeWbsTaskMetrics — agregador WBS/EVMT PMI §5.4', () => {
    it('devuelve ceros para un arreglo vacío', () => {
        expect(computeWbsTaskMetrics([])).toEqual({
            total: 0,
            completed: 0,
            inProgress: 0,
            overdue: 0,
            evmtPercent: 0,
            wbsDefinedCount: 0,
            wbsReadinessPercent: 0,
        });
    });

    it('calcula la mezcla mixta con regla fija 0/50/100 y preparación WBS', () => {
        const metrics = computeWbsTaskMetrics([
            // Completada con WBS definido (desc + due + assignee)
            { status: 'completed', due_date: '2026-01-10', assignee_id: 'u1', description: 'Paquete definido' },
            // En progreso, vencida, sin descripción → no WBS definido
            { status: 'in_progress', due_date: '2026-01-01', assignee_id: 'u2', description: null },
            // En revisión (cuenta 50), sin due_date → no WBS definido
            { status: 'review', due_date: null, assignee_id: 'u3', description: 'Falta fecha' },
            // Todo, descripción en blanco → no WBS definido (fecha futura, no vencida)
            { status: 'todo', due_date: '2099-02-01', assignee_id: null, description: '   ' },
            // Alias 'done' cuenta como completada
            { status: 'done', due_date: '2026-03-01', assignee_id: 'u1', description: 'Cerrada con evidencia' },
        ]);

        expect(metrics.total).toBe(5);
        expect(metrics.completed).toBe(2);
        expect(metrics.inProgress).toBe(2); // in_progress + review
        // isTaskOverdue evalúa el status CRUDO: la vencida en progreso y la
        // alias 'done' (no normalizada en ese helper) con fecha pasada cuentan.
        expect(metrics.overdue).toBe(2);
        // (2*100 + 2*50) / (5*100) = 60%
        expect(metrics.evmtPercent).toBe(60);
        expect(metrics.wbsDefinedCount).toBe(2);
        expect(metrics.wbsReadinessPercent).toBe(40); // 2/5
    });

    it('exponde 100% cuando el lote está 100% definido y completado', () => {
        const metrics = computeWbsTaskMetrics([
            { status: 'completed', due_date: '2026-12-01', assignee_id: 'u1', description: 'A' },
            { status: 'completed', due_date: '2026-12-02', assignee_id: 'u2', description: 'B' },
        ]);

        expect(metrics.total).toBe(2);
        expect(metrics.completed).toBe(2);
        expect(metrics.evmtPercent).toBe(100);
        expect(metrics.wbsDefinedCount).toBe(2);
        expect(metrics.wbsReadinessPercent).toBe(100);
        expect(metrics.overdue).toBe(0);
    });
});

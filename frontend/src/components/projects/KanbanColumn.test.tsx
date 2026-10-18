import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { KanbanColumn } from './KanbanColumn';
import { createMockTask } from '@/test-utils/factories';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'mock-token', loading: false }),
  useOptionalAuth: () => ({ token: 'mock-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

describe('KanbanColumn PMI Flow & WIP Governance', () => {
  it('renders PMI column strip with BAC total, WIP exceeded alert (>5 in active column), overdue count, and unassigned RACI gaps', () => {
    const sixTasksInProgress = [
      createMockTask({
        id: 't1',
        title: 'Paquete 1',
        status: 'in_progress',
        budget_allocated: 1200000,
        due_date: '2020-01-10',
        assignee_id: null,
      }),
      createMockTask({
        id: 't2',
        title: 'Paquete 2',
        status: 'in_progress',
        budget_allocated: 800000,
        due_date: '2020-02-15',
        assignee_id: 'u-1',
      }),
      createMockTask({ id: 't3', title: 'Paquete 3', status: 'in_progress', assignee_id: null }),
      createMockTask({ id: 't4', title: 'Paquete 4', status: 'in_progress', assignee_id: 'u-2' }),
      createMockTask({ id: 't5', title: 'Paquete 5', status: 'in_progress', assignee_id: 'u-3' }),
      createMockTask({ id: 't6', title: 'Paquete 6', status: 'in_progress', assignee_id: 'u-4' }),
    ];

    render(
      <KanbanColumn
        id="in_progress"
        name="En Progreso"
        color="hsl(var(--primary))"
        tasks={sixTasksInProgress}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
      />
    );

    const strip = screen.getByTestId('kanban-column-pmi-strip-in_progress');
    expect(strip).toHaveTextContent(`BAC $${(2000000).toLocaleString('es-CO')}`);

    const wipAlert = screen.getByTestId('kanban-column-wip-alert-in_progress');
    expect(wipAlert).toHaveTextContent('WIP Excedido (6/5)');

    const overdueAlert = screen.getByTestId('kanban-column-overdue-in_progress');
    expect(overdueAlert).toHaveTextContent('2 vencida(s)');

    expect(strip).toHaveTextContent('2 sin resp.');
  });

  it('does not trigger WIP exceeded alert on backlog/todo or completed columns even with >5 tasks', () => {
    const sixTodoTasks = Array.from({ length: 6 }, (_, i) =>
      createMockTask({
        id: `todo-${i + 1}`,
        title: `Pendiente ${i + 1}`,
        status: 'todo',
        assignee_id: 'u-1',
      })
    );

    render(
      <KanbanColumn
        id="todo"
        name="Por Hacer"
        color="hsl(var(--muted-foreground))"
        tasks={sixTodoTasks}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
      />
    );

    expect(screen.getByTestId('kanban-column-pmi-strip-todo')).toBeInTheDocument();
    expect(screen.queryByTestId('kanban-column-wip-alert-todo')).not.toBeInTheDocument();
  });
});

import { forwardRef } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'jest-axe';
import { createMockTask } from '@/test-utils/factories';

vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));

vi.mock('@/hooks/useProjectTasks', () => ({
  useProjectTasks: () => ({
    updateTask: vi.fn(),
  }),
}));

vi.mock('@/components/ui/inline-editors', () => ({
  InlineStatusPicker: ({ value }: { value: string }) => <span data-testid="inline-status">{value}</span>,
  InlinePriorityPicker: ({ value }: { value: string }) => <span data-testid="inline-priority">{value}</span>,
  InlineDatePicker: ({ value }: { value: string | null }) => <span data-testid="inline-date">{value ?? '—'}</span>,
  InlineUserPicker: ({ value }: { value: string | null }) => <span data-testid="inline-user">{value ?? '—'}</span>,
  InlineTextInput: ({ value }: { value: string }) => <span>{value}</span>,
  InlineTextArea: ({ value }: { value: string }) => <span>{value}</span>,
  InlineProjectStatusPicker: ({ value }: { value: string }) => <span>{value}</span>,
}));

vi.mock('@/components/projects/TitleCellEditor', () => {
  const MockedTitleCellEditor = forwardRef<HTMLInputElement, { value?: string }>((props, ref) => (
    <input ref={ref} defaultValue={props.value} aria-label="title-editor" />
  ));
  MockedTitleCellEditor.displayName = 'MockedTitleCellEditor';
  return {
    __esModule: true,
    default: MockedTitleCellEditor,
  };
});

import TaskTableView from './TaskTableView';

const tasks = [
  createMockTask({
    id: 't1',
    project_id: 'p1',
    parent_id: null,
    title: 'Tarea de prueba',
    description: null,
    status: 'in_progress',
    priority: 'high',
    assignee_id: 'u1',
    start_date: null,
    due_date: '2026-08-10',
    labels: [],
    order_index: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }),
];

describe('TaskTableView', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('uses declared semantic surface tokens and warning contrast in the favorites filter', () => {
    const { container } = render(
      <TaskTableView projectId="p1" tasks={tasks} onOpenTask={() => {}} onAddTask={() => {}} />,
    );
    const root = container.querySelector('div.flex.min-w-0.flex-col.h-full');

    expect(root).not.toBeNull();
    expect(root).toHaveClass('bg-[hsl(var(--surface-1))]');
    expect(root?.innerHTML).not.toMatch(/--(?:foreground|muted-foreground|background)\b/);
    expect(root?.innerHTML).toContain('--text-primary');
    expect(root?.innerHTML).toContain('--text-secondary');
    const favoritesFilter = screen.getByRole('button', { name: /Solo Mis Favoritas/ });
    fireEvent.click(favoritesFilter);
    expect(favoritesFilter).toHaveClass('bg-[hsl(var(--warning-muted))]');
    expect(favoritesFilter).toHaveClass('text-[hsl(var(--warning-text))]');
  });

  it('renders task rows', () => {
    render(
      <TaskTableView
        projectId="p1"
        tasks={tasks}
        onOpenTask={() => {}}
        onAddTask={() => {}}
      />
    );
    expect(screen.getByText('Tarea de prueba')).toBeInTheDocument();
    expect(screen.getByText('in_progress')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
  });

  it('opens task details through an explicit accessible action', () => {
    const handleOpenTask = vi.fn();
    render(
      <TaskTableView
        projectId="p1"
        tasks={tasks}
        onOpenTask={handleOpenTask}
        onAddTask={() => {}}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Abrir detalle de tarea Tarea de prueba' }));
    expect(handleOpenTask).toHaveBeenCalledTimes(1);
  });

  it('does not open details by double-clicking a task title', () => {
    const handleOpenTask = vi.fn();
    render(
      <TaskTableView
        projectId="p1"
        tasks={tasks}
        onOpenTask={handleOpenTask}
        onAddTask={() => {}}
      />
    );

    fireEvent.doubleClick(screen.getByText('Tarea de prueba'));
    expect(handleOpenTask).not.toHaveBeenCalled();
  });

  it('has no critical accessibility violations in the rendered task table', async () => {
    const { container } = render(
      <TaskTableView projectId="p1" tasks={tasks} onOpenTask={() => {}} onAddTask={() => {}} />
    );
    expect((await axe(container)).violations).toEqual([]);
  });

  it('calls onAddTask when the add button is clicked', () => {
    const handleAddTask = vi.fn();
    render(
      <TaskTableView
        projectId="p1"
        tasks={tasks}
        onOpenTask={() => {}}
        onAddTask={handleAddTask}
      />
    );
    fireEvent.click(screen.getByText('Nueva tarea'));
    expect(handleAddTask).toHaveBeenCalledTimes(1);
  });
});

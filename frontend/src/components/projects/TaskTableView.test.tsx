import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

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
  const MockedTitleCellEditor = React.forwardRef((props: any, ref: any) => <input ref={ref} defaultValue={props.value} aria-label="title-editor" />);
  MockedTitleCellEditor.displayName = 'MockedTitleCellEditor';
  return {
    __esModule: true,
    default: MockedTitleCellEditor,
  };
});

import TaskTableView from './TaskTableView';

const tasks: ProjectTaskRecord[] = [
  {
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
  } as ProjectTaskRecord,
];

describe('TaskTableView', () => {
  beforeEach(() => {
    localStorage.clear();
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

  it('calls onOpenTask when a row is clicked', () => {
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
    expect(handleOpenTask).toHaveBeenCalledTimes(1);
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

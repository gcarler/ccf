import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskMetaFields from './TaskMetaFields';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

const mockTask: ProjectTaskRecord = {
  id: 't-123',
  project_id: 'p-456',
  title: 'Tarea de prueba',
  status: 'todo',
  priority: 'medium',
  due_date: '2026-10-22T00:00:00Z',
  node: 'digital',
};

const defaultPriority = { color: 'text-info', dot: 'bg-info', label: 'Media' };

describe('TaskMetaFields', () => {
  it('renders interactive InlineDatePicker without timezone shift (keeps day 22)', () => {
    const onDueDateChange = vi.fn();
    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onDueDateChange={onDueDateChange}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    // The picker button exists and contains the day 22
    const datePickerButton = screen.getByRole('button', { name: /seleccionar fecha límite/i });
    expect(datePickerButton).toBeInTheDocument();
    expect(datePickerButton.textContent).toMatch(/22/);
    expect(datePickerButton.textContent).not.toMatch(/21 oct/i);
  });

  it('renders fallback calendar format without timezone shift when onDueDateChange is not provided', () => {
    render(
      <TaskMetaFields
        task={mockTask}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    const staticDate = screen.getByText(/22/);
    expect(staticDate).toBeInTheDocument();
    expect(screen.queryByText(/21 oct/i)).not.toBeInTheDocument();
  });

  it('renders "Sin fecha límite" when due_date is null and no onDueDateChange', () => {
    const taskWithoutDate = { ...mockTask, due_date: undefined };
    render(
      <TaskMetaFields
        task={taskWithoutDate}
        labels={[]}
        onLabelsChange={vi.fn()}
        onAssigneeChange={vi.fn()}
        onPriorityCycle={vi.fn()}
        onNodeCycle={vi.fn()}
        priority={defaultPriority}
        token="test-token"
      />
    );

    expect(screen.getByText('Sin fecha límite')).toBeInTheDocument();
  });
});

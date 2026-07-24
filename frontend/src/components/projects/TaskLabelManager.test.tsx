import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskLabelManager from './TaskLabelManager';
import type { ProjectTaskRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

const task: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
};

describe('TaskLabelManager', () => {
  it('renders label chips', () => {
    render(
      <TaskLabelManager task={task} labels={['Urgente', 'Alabanza']} onLabelsChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Urgente')).toBeInTheDocument();
    expect(screen.getByText('Alabanza')).toBeInTheDocument();
  });

  it('renders add button', () => {
    render(
      <TaskLabelManager task={task} labels={[]} onLabelsChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Añadir etiqueta')).toBeInTheDocument();
  });
});

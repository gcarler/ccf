import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TaskSupplySection from './TaskSupplySection';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
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

const supplies: TaskSupplyRecord[] = [
  { id: 's1', task_id: 't1', item_name: 'Cable HDMI', quantity: 3, status: 'pending' },
  { id: 's2', task_id: 't1', item_name: 'Proyector', quantity: 1, status: 'ready' },
];

describe('TaskSupplySection', () => {
  it('renders supplies list with names and count', () => {
    render(
      <TaskSupplySection task={task} supplies={supplies} onSuppliesChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByDisplayValue('Cable HDMI')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Proyector')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty state when no supplies', () => {
    render(
      <TaskSupplySection task={task} supplies={[]} onSuppliesChange={vi.fn()} token="test-token" />
    );
    expect(screen.getByText('Sin insumos registrados.')).toBeInTheDocument();
  });

  it('add button is disabled when name is empty', () => {
    render(
      <TaskSupplySection task={task} supplies={[]} onSuppliesChange={vi.fn()} token="test-token" />
    );
    const button = screen.getByRole('button', { name: /Agregar/ });
    expect(button).toBeDisabled();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectTableView from './ProjectTableView';
import type { ProjectTaskRecord } from '@/types/projects';

// Avoid loading real AG Grid modules in unit tests
vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

const tasks: ProjectTaskRecord[] = [
  {
    id: '1',
    project_id: 'p1',
    parent_id: null,
    title: 'Diseñar mock',
    description: null,
    status: 'in_progress',
    priority: 'high',
    assignee_id: 'u1',
    start_date: null,
    due_date: '2026-08-01',
    labels: [],
    order_index: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as ProjectTaskRecord,
  {
    id: '2',
    project_id: 'p1',
    parent_id: null,
    title: 'Revisar tests',
    description: null,
    status: 'completed',
    priority: 'medium',
    assignee_id: null,
    start_date: null,
    due_date: null,
    labels: [],
    order_index: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as ProjectTaskRecord,
];

describe('ProjectTableView', () => {
  it('renders task titles and statuses', () => {
    render(<ProjectTableView tasks={tasks} />);
    expect(screen.getByText('Diseñar mock')).toBeInTheDocument();
    expect(screen.getByText('Revisar tests')).toBeInTheDocument();
    expect(screen.getByText('En Progreso')).toBeInTheDocument();
    expect(screen.getByText('Completado')).toBeInTheDocument();
  });

  it('renders empty table when no tasks', () => {
    const { container } = render(<ProjectTableView tasks={[]} />);
    expect(container.querySelector('tbody')?.children.length).toBe(0);
  });
});

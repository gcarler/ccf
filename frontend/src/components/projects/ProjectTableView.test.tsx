import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectTableView from './ProjectTableView';
import { createMockTask } from '@/test-utils/factories';

// Avoid loading real AG Grid modules in unit tests
vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

const tasks = [
  createMockTask({
    id: '1',
    title: 'Diseñar mock',
    status: 'in_progress',
    priority: 'high',
    assignee_id: 'u1',
    due_date: '2026-08-01',
  }),
  createMockTask({
    id: '2',
    title: 'Revisar tests',
    status: 'completed',
    priority: 'medium',
  }),
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

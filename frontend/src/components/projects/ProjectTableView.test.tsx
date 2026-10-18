import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, it, expect, vi } from 'vitest';
import ProjectTableView from './ProjectTableView';
import { createMockTask } from '@/test-utils/factories';

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}));

// Avoid loading real AG Grid modules in unit tests
vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: (...args: unknown[]) => mocks.apiFetch(...args),
}));

const tasks = [
  createMockTask({
    id: '1',
    title: 'Diseñar mock',
    status: 'in_progress',
    priority: 'high',
    assignee_id: 'u1',
    due_date: '2020-01-15',
    budget_allocated: 1500000,
    progress_pct: 60,
  }),
  createMockTask({
    id: '2',
    title: 'Revisar tests',
    status: 'completed',
    priority: 'medium',
    assignee_id: null,
    due_date: '2020-01-10',
    budget_allocated: 500000,
  }),
  createMockTask({
    id: '3',
    title: 'Documentar cierre',
    status: 'todo',
    priority: 'urgent',
    assignee_id: null,
    due_date: '2099-12-31',
    budget_allocated: 0,
  }),
];

describe('ProjectTableView', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.apiFetch.mockResolvedValue([]);
  });

  it('renders task titles, statuses, and PMI columns (Avance PMI & BAC Paquete)', () => {
    render(<ProjectTableView tasks={tasks} projectId="proj-1" />);
    expect(screen.getByText('Diseñar mock')).toBeInTheDocument();
    expect(screen.getByText('Revisar tests')).toBeInTheDocument();
    expect(screen.getByText('En Progreso')).toBeInTheDocument();
    expect(screen.getByText('Completado')).toBeInTheDocument();

    expect(screen.getByRole('columnheader', { name: 'Avance PMI' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'BAC Paquete' })).toBeInTheDocument();

    expect(screen.getByText('60%')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText(`$${(1500000).toLocaleString('es-CO')}`)).toBeInTheDocument();
    expect(screen.getByText(`$${(500000).toLocaleString('es-CO')}`)).toBeInTheDocument();
  });

  it('calculates PMI executive summary (Rule 0/50/100, BAC total, RACI gaps, and overdue tasks)', () => {
    render(<ProjectTableView tasks={tasks} projectId="proj-1" />);

    const summary = screen.getByTestId('project-table-pmi-summary');
    // Rule 0/50/100 scores: task 1 (in_progress with 60% -> 60), task 2 (completed -> 100), task 3 (todo -> 0) => avg = round(160/3) = 53%
    expect(summary).toHaveTextContent('53%');
    // Total BAC: 1,500,000 + 500,000 + 0 = 2,000,000
    expect(summary).toHaveTextContent(`$${(2000000).toLocaleString('es-CO')}`);
    // RACI gaps: only task 3 is non-completed without assignee_id (task 2 is completed) -> 1
    expect(summary).toHaveTextContent('Brechas RACI (Sin Responsable)');
    // Overdue: only task 1 is non-completed with past due_date -> 1
    expect(summary).toHaveTextContent('Vencidas');
  });

  it('filters tasks interactively by PMI quick filters and combines with Solo Mis Favoritas', async () => {
    mocks.apiFetch.mockImplementation((url: string) => {
      if (url.includes('/favorites')) {
        return Promise.resolve(['1', '3']);
      }
      return Promise.resolve([]);
    });

    render(<ProjectTableView tasks={tasks} projectId="proj-1" />);

    const filterBar = screen.getByTestId('project-table-pmi-filter');

    // Filter by RACI_GAP ("Sin Responsable") -> only task 3
    fireEvent.click(within(filterBar).getByRole('button', { name: 'Sin Responsable' }));
    expect(screen.getByText('Documentar cierre')).toBeInTheDocument();
    expect(screen.queryByText('Diseñar mock')).not.toBeInTheDocument();
    expect(screen.queryByText('Revisar tests')).not.toBeInTheDocument();

    // Filter by OVERDUE ("Vencidas") -> only task 1
    fireEvent.click(within(filterBar).getByRole('button', { name: 'Vencidas' }));
    expect(screen.getByText('Diseñar mock')).toBeInTheDocument();
    expect(screen.queryByText('Documentar cierre')).not.toBeInTheDocument();

    // Filter by CRITICAL ("Críticas / Urgentes") -> task 1 (high) and task 3 (urgent)
    fireEvent.click(within(filterBar).getByRole('button', { name: 'Críticas / Urgentes' }));
    expect(screen.getByText('Diseñar mock')).toBeInTheDocument();
    expect(screen.getByText('Documentar cierre')).toBeInTheDocument();
    expect(screen.queryByText('Revisar tests')).not.toBeInTheDocument();

    // Reset to ALL and combine with Solo Mis Favoritas (favorites: '1' and '3')
    fireEvent.click(within(filterBar).getByRole('button', { name: 'Todas' }));
    await waitFor(() => {
      expect(screen.getByTitle('Filtrar por tareas favoritas')).toHaveTextContent('2');
    });
    fireEvent.click(screen.getByTitle('Filtrar por tareas favoritas'));
    expect(screen.getByText('Diseñar mock')).toBeInTheDocument();
    expect(screen.getByText('Documentar cierre')).toBeInTheDocument();
    expect(screen.queryByText('Revisar tests')).not.toBeInTheDocument();
  });

  it('renders empty table when no tasks', () => {
    const { container } = render(<ProjectTableView tasks={[]} />);
    expect(container.querySelector('tbody')?.children.length).toBe(0);
  });
});

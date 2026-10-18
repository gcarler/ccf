import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SortableTaskCard } from './SortableTaskCard';
import { createMockTask } from '@/test-utils/factories';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'mock-token', loading: false }),
  useOptionalAuth: () => ({ token: 'mock-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

describe('SortableTaskCard PMI Work Package Indicators', () => {
  it('renders PMI progress percentage, BAC allocated badge, and overdue warning for an active overdue work package', () => {
    const task = createMockTask({
      id: 'wp-101',
      title: 'Implementar Pasarela de Pagos',
      status: 'in_progress',
      priority: 'high',
      due_date: '2020-05-01',
      budget_allocated: 3450000,
    });

    render(<SortableTaskCard task={task} onOpen={vi.fn()} />);

    expect(screen.getByTestId('task-card-pmi-row-wp-101')).toBeInTheDocument();
    expect(screen.getByTestId('task-card-pmi-progress-wp-101')).toHaveTextContent('50%');
    expect(screen.getByTestId('task-card-pmi-bac-wp-101')).toHaveTextContent(
      `BAC $${(3450000).toLocaleString('es-CO')}`
    );
    expect(screen.getByTestId('task-card-pmi-overdue-wp-101')).toHaveTextContent('Vencida');
  });

  it('shows 100% progress and hides overdue badge when task is completed', () => {
    const completedTask = createMockTask({
      id: 'wp-202',
      title: 'Cierre de Auditoría',
      status: 'completed',
      priority: 'medium',
      due_date: '2020-01-01',
      budget_allocated: 0,
    });

    render(<SortableTaskCard task={completedTask} onOpen={vi.fn()} />);

    expect(screen.getByTestId('task-card-pmi-progress-wp-202')).toHaveTextContent('100%');
    expect(screen.queryByTestId('task-card-pmi-bac-wp-202')).not.toBeInTheDocument();
    expect(screen.queryByTestId('task-card-pmi-overdue-wp-202')).not.toBeInTheDocument();
  });
});

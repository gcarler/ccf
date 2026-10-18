import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));
vi.mock('sonner', () => ({ toast: { error: toastErrorMock } }));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/UniversalCalendarView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalGanttView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalWikiView', () => ({ default: () => null }));
vi.mock('@/design', () => ({ DSSkeleton: () => <div data-testid="skeleton" /> }));

import { apiFetch } from '@/lib/http';
import ProjectsInboxPage from './page';

const mockApiFetch = vi.mocked(apiFetch);

describe('ProjectsInboxPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('keeps message actions visible on touch and reveals them on keyboard focus', async () => {
    mockApiFetch.mockResolvedValueOnce([
      {
        id: 'inbox-1',
        type: 'comment',
        user: 'Nora',
        content: 'Revisar el presupuesto',
        project: 'Campaña anual',
        project_id: 'project-1',
        is_read: false,
        created_at: '2026-10-03T12:00:00Z',
      },
    ]);

    const { container } = render(<ProjectsInboxPage />);
    const respond = await screen.findByRole('button', { name: 'Responder' });
    const resolve = screen.getByRole('button', { name: 'Resolver' });

    expect(respond.parentElement).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect(resolve.parentElement).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect(container.querySelector('.group.relative')?.className).not.toContain('cursor-pointer');
    expect((await axe(container)).violations).toEqual([]);
  });

  it('shows one specific notification when inbox loading fails', async () => {
    mockApiFetch.mockRejectedValueOnce(new Error('offline'));

    render(<ProjectsInboxPage />);

    expect(await screen.findByText('No se pudo cargar el inbox de proyectos.')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledOnce();
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar inbox');
  });

  it('recovers from a failed inbox load using the in-page retry action', async () => {
    mockApiFetch
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce([
        {
          id: 'inbox-recovered',
          type: 'comment',
          user: 'Nora',
          content: 'Carga recuperada',
          project: 'Campaña anual',
          project_id: 'project-1',
          is_read: false,
          created_at: '2026-10-03T12:00:00Z',
        },
      ]);

    render(<ProjectsInboxPage />);
    await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Carga recuperada')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it('shows one specific notification when resolving an item fails', async () => {
    mockApiFetch
      .mockResolvedValueOnce([
        {
          id: 'inbox-task-1',
          type: 'task_assigned',
          user: 'Nora',
          content: 'Completar informe',
          project: 'Campaña anual',
          project_id: 'project-1',
          task_id: 'task-1',
          is_read: false,
          created_at: '2026-10-03T12:00:00Z',
        },
      ])
      .mockRejectedValueOnce(new Error('offline'));

    render(<ProjectsInboxPage />);
    await screen.findByText('Completar informe');
    fireEvent.click(screen.getByRole('button', { name: 'Resolver' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al resolver elemento'));
    expect(toastErrorMock).toHaveBeenCalledOnce();
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it('renders PMI §10.3 communications triage header and SLA badge', async () => {
    mockApiFetch.mockResolvedValueOnce([
      {
        id: 'inbox-1',
        type: 'comment',
        user: 'Nora',
        content: 'Revisar el presupuesto',
        project: 'Campaña anual',
        project_id: 'project-1',
        is_read: false,
        created_at: '2026-10-03T12:00:00Z',
      },
      {
        id: 'inbox-2',
        type: 'task_assigned',
        user: 'Carlos',
        content: 'Validar cronograma',
        project: 'Campaña anual',
        project_id: 'project-1',
        task_id: 'task-2',
        is_read: true,
        created_at: '2026-10-03T13:00:00Z',
      },
    ]);

    render(<ProjectsInboxPage />);
    await screen.findByText('Revisar el presupuesto');

    const pmiHeader = screen.getByTestId('projects-inbox-pmi-header');
    expect(pmiHeader).toHaveTextContent('Total Bandeja: 2');
    expect(pmiHeader).toHaveTextContent('Pendientes de Atención: 1');
    expect(pmiHeader).toHaveTextContent('Paquetes Asignados: 1');
    expect(pmiHeader).toHaveTextContent('Menciones / Consultas: 1');
    expect(screen.getByTestId('projects-inbox-sla-badge')).toHaveTextContent('Atención Requerida (1)');
  });
});

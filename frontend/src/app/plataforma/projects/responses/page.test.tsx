import { render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock, toastErrorMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token', loading: false }) }));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/components/ui/UniversalCalendarView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalGanttView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalWikiView', () => ({ default: () => null }));
vi.mock('@/design', () => ({ DSSkeleton: () => <div role="status" /> }));
vi.mock('sonner', () => ({ toast: { error: toastErrorMock } }));

import { apiFetch } from '@/lib/http';
import ProjectsResponsesPage from './page';

describe('ProjectsResponsesPage load recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('retries a failed inbox request and clears the error on recovery', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([]);

    render(<ProjectsResponsesPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar las respuestas de proyectos.');
    screen.getByRole('button', { name: 'Reintentar' }).click();

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(apiFetch).toHaveBeenCalledTimes(2);
    expect(toastErrorMock).toHaveBeenCalledOnce();
  });

  it('renders PMI §10.2 actionable response queue governance header', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      {
        id: 'resp-1',
        type: 'task_assigned',
        user: 'Nora',
        task_title: 'Entregable WBS 1.2',
        content: 'Asignación pendiente',
        project: 'Proyecto Alfa',
        project_id: 'proj-1',
        task_id: 'task-1',
        is_read: false,
        created_at: '2026-10-03T12:00:00Z',
      },
      {
        id: 'resp-2',
        type: 'comment',
        user: 'Carlos',
        content: 'Consulta de alcance',
        project: 'Proyecto Alfa',
        project_id: 'proj-1',
        is_read: false,
        created_at: '2026-10-03T13:00:00Z',
      },
      {
        id: 'resp-3',
        type: 'comment',
        user: 'Lucía',
        content: 'Respondido previamente',
        project: 'Proyecto Alfa',
        project_id: 'proj-1',
        is_read: true,
        created_at: '2026-10-03T14:00:00Z',
      },
    ]);

    render(<ProjectsResponsesPage />);
    await screen.findByText('Entregable WBS 1.2');

    const pmiHeader = screen.getByTestId('projects-responses-pmi-header');
    expect(pmiHeader).toHaveTextContent('Respuestas Pendientes: 2');
    expect(pmiHeader).toHaveTextContent('Asignaciones WBS por Confirmar: 1');
    expect(pmiHeader).toHaveTextContent('Consultas / Menciones: 1');
    expect(pmiHeader).toHaveTextContent('Resueltas en Sesión: 1');
  });
});

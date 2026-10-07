import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock, getAllProjectsMock, toastErrorMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  getAllProjectsMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', loading: false }),
}));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));
vi.mock('@/lib/projects/api', () => ({ getAllProjects: getAllProjectsMock }));
vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/components/ui/UniversalCalendarView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalGanttView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalWikiView', () => ({ default: () => null }));
vi.mock('@/design', () => ({ DSSkeleton: () => <div role="status" /> }));
vi.mock('sonner', () => ({ toast: { error: toastErrorMock } }));

import { apiFetch } from '@/lib/http';
import { getAllProjects } from '@/lib/projects/api';
import ProjectsMorePage from './page';

describe('ProjectsMorePage partial data failures', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockResolvedValue([]);
  });

  it('reports a failed project list instead of silently rendering incomplete summary data', async () => {
    vi.mocked(getAllProjects).mockRejectedValueOnce(new Error('offline'));

    render(<ProjectsMorePage />);

    expect(await screen.findByText('No se pudo cargar el resumen de proyectos.')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledOnce();
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar resumen');
  });

  it('retries after a load failure and recovers to the empty state', async () => {
    vi.mocked(getAllProjects)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce([]);

    render(<ProjectsMorePage />);
    await screen.findByRole('alert');

    screen.getByRole('button', { name: 'Reintentar' }).click();

    expect(await screen.findByText('Sin datos de resumen')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(getAllProjects).toHaveBeenCalledTimes(2);
  });
});

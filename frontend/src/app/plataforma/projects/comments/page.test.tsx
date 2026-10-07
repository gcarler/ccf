import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock, getAllProjectsMock, toastErrorMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  getAllProjectsMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token', loading: false }) }));
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
import ProjectsCommentsPage from './page';

describe('ProjectsCommentsPage load recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockResolvedValue([]);
  });

  it('retries a failed comments/project load and clears the error on recovery', async () => {
    vi.mocked(getAllProjects)
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce([]);

    const { container } = render(<ProjectsCommentsPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar los comentarios de proyectos.');
    screen.getByRole('button', { name: 'Reintentar' }).click();

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(getAllProjects).toHaveBeenCalledTimes(2);
    expect(toastErrorMock).toHaveBeenCalledOnce();
    expect((await axe(container)).violations).toEqual([]);
  });
});

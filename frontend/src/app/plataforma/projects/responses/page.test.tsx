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
});

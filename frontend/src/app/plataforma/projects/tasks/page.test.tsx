import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const { authMock, searchParamsMock, assignedTasksMock, allProjectsMock, apiFetchMock, toastErrorMock } = vi.hoisted(() => ({
  authMock: vi.fn(),
  searchParamsMock: vi.fn(),
  assignedTasksMock: vi.fn(),
  allProjectsMock: vi.fn(),
  apiFetchMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({ useAuth: authMock }));
vi.mock('next/navigation', () => ({
  useSearchParams: searchParamsMock,
}));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));
vi.mock('@/lib/projects/api', () => ({
  getAllAssignedProjectTasks: assignedTasksMock,
  getAllProjects: allProjectsMock,
}));
vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: { children: ReactNode }) => <main aria-label="Workspace de proyectos">{children}</main>,
}));
vi.mock('@/components/ui/UniversalCalendarView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalGanttView', () => ({ default: () => null }));
vi.mock('@/components/ui/UniversalWikiView', () => ({ default: () => null }));
vi.mock('sonner', () => ({ toast: { error: toastErrorMock } }));

import ProjectsTasksPage from './page';

describe('ProjectsTasksPage assigned tasks loading', () => {
  beforeEach(() => {
    authMock.mockReturnValue({ token: 'test-token', loading: false });
    searchParamsMock.mockReturnValue(new URLSearchParams('scope=mine&view=list'));
    assignedTasksMock.mockReset();
    allProjectsMock.mockReset();
    apiFetchMock.mockReset();
    toastErrorMock.mockReset();
  });

  it('offers retry after a recoverable load failure and renders recovered tasks', async () => {
    assignedTasksMock
      .mockRejectedValueOnce(new Error('Temporary API outage'))
      .mockResolvedValueOnce([{
        id: 'task-recovered',
        project_id: 'project-a',
        project_title: 'Proyecto A',
        title: 'Tarea recuperada',
        status: 'todo',
        priority: 'medium',
        due_date: null,
      }]);

    render(<ProjectsTasksPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar las tareas de proyecto.');
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar tareas');

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByText('Tarea recuperada')).toBeInTheDocument();
    await waitFor(() => expect(assignedTasksMock).toHaveBeenCalledTimes(2));
  });

  it('ignores an older scope response when requests resolve out of order', async () => {
    let resolveMine!: (value: Array<Record<string, unknown>>) => void;
    let resolveAll!: (value: Array<Record<string, unknown>>) => void;
    const mineRequest = new Promise<Array<Record<string, unknown>>>((resolve) => { resolveMine = resolve; });
    const allRequest = new Promise<Array<Record<string, unknown>>>((resolve) => { resolveAll = resolve; });
    assignedTasksMock.mockReturnValueOnce(mineRequest);
    allProjectsMock.mockReturnValueOnce(allRequest);

    const { rerender } = render(<ProjectsTasksPage />);
    await waitFor(() => expect(assignedTasksMock).toHaveBeenCalledTimes(1));

    searchParamsMock.mockReturnValue(new URLSearchParams('scope=all&view=list'));
    rerender(<ProjectsTasksPage />);
    await waitFor(() => expect(allProjectsMock).toHaveBeenCalledTimes(1));

    await act(async () => {
      resolveAll([{
        id: 'project-current',
        title: 'Proyecto actual',
        tasks: [{ id: 'task-current', project_id: 'project-current', title: 'Tarea actual', status: 'todo', priority: 'medium' }],
      }]);
      await allRequest;
    });
    expect(await screen.findByText('Tarea actual')).toBeInTheDocument();

    await act(async () => {
      resolveMine([{
        id: 'task-stale',
        project_id: 'project-old',
        project_title: 'Proyecto anterior',
        title: 'Tarea obsoleta',
        status: 'todo',
        priority: 'medium',
      }]);
      await mineRequest;
    });

    expect(screen.getByText('Tarea actual')).toBeInTheDocument();
    expect(screen.queryByText('Tarea obsoleta')).not.toBeInTheDocument();
  });

  it('shows one error notification when advancing a task fails', async () => {
    assignedTasksMock.mockResolvedValueOnce([{
      id: 'task-fails-to-advance',
      project_id: 'project-a',
      project_title: 'Proyecto A',
      title: 'Tarea con error de estado',
      status: 'todo',
      priority: 'medium',
      due_date: null,
    }]);
    apiFetchMock.mockRejectedValueOnce(new Error('API unavailable'));

    render(<ProjectsTasksPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Siguiente estado' }));

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(1));
    expect(toastErrorMock).toHaveBeenCalledTimes(1);
    expect(toastErrorMock).toHaveBeenCalledWith('Error al cambiar estado de tarea');
    expect(screen.getByRole('heading', { name: 'Tarea con error de estado' })).toBeInTheDocument();
  });

  it('keeps task results in an accessible landmark hierarchy', async () => {
    assignedTasksMock.mockResolvedValueOnce([{
      id: 'task-a11y',
      project_id: 'project-a',
      project_title: 'Proyecto A',
      title: 'Tarea accesible',
      status: 'todo',
      priority: 'medium',
      due_date: null,
    }]);

    const { container } = render(<ProjectsTasksPage />);
    expect(await screen.findByRole('heading', { name: 'Tarea accesible' })).toBeInTheDocument();

    expect((await axe(container)).violations).toEqual([]);
  });
});

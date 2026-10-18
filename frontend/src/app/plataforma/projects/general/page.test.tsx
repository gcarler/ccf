import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
import ProjectsGeneralPage from './page';

describe('ProjectsGeneralPage load recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiFetch).mockResolvedValue([]);
  });

  it('retries a failed activity/project load and clears the error on recovery', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline')).mockResolvedValue([]);
    vi.mocked(getAllProjects).mockResolvedValue([]);

    const { container } = render(<ProjectsGeneralPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar el canal general de proyectos.');
    screen.getByRole('button', { name: 'Reintentar' }).click();

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(apiFetch).toHaveBeenCalledTimes(2);
    expect(toastErrorMock).toHaveBeenCalledOnce();
    expect((await axe(container)).violations).toEqual([]);
  });

  it('muestra el cintillo de comunicaciones PMI y las plantillas rapidas rellenan el mensaje', async () => {
    vi.mocked(getAllProjects).mockResolvedValue([
      { id: 'project-1', title: 'Proyecto Alpha', status: 'active', created_at: '2026-01-01T00:00:00Z' },
    ]);
    vi.mocked(apiFetch).mockResolvedValue([
      {
        id: 'act-1',
        project_id: 'project-1',
        project_title: 'Proyecto Alpha',
        task_title: 'Hito base',
        description: 'Avance inicial',
        created_at: '2026-06-01T10:00:00Z',
      },
    ]);

    render(<ProjectsGeneralPage />);

    const header = await screen.findByTestId('projects-general-pmi-header');
    expect(header).toHaveTextContent('Proyectos Conectados: 1');
    expect(header).toHaveTextContent('Eventos Registrados: 1');
    expect(header).toHaveTextContent('Cobertura Activa: 1');

    fireEvent.click(screen.getByTestId('general-template-status'));
    const contentInput = screen.getByLabelText('Actualización para el canal') as HTMLInputElement;
    expect(contentInput.value).toBe(
      '[Reporte PMI §10.2] Avance de línea base en ruta; sin desviaciones críticas en alcance ni cronograma.'
    );

    cleanup();
    render(<ProjectsGeneralPage />);
    await screen.findByTestId('projects-general-pmi-header');
    fireEvent.click(screen.getByTestId('general-template-escalation'));
    expect((screen.getByLabelText('Actualización para el canal') as HTMLInputElement).value).toBe(
      '[Escalamiento PMI §11.6] Se requiere atención de Sponsor/PMO por restricción en paquete de trabajo crítico.'
    );
  });
});

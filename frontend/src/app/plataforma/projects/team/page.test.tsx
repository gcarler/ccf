import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TeamPage from './page';

const { apiFetchMock, getAllProjectsMock, toastErrorMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  getAllProjectsMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  motion: { div: ({ children }: React.PropsWithChildren) => <div>{children}</div> },
}));
vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token', loading: false }) }));
vi.mock('@/context/SidebarLayerContext', () => ({
  useSidebarLayers: () => ({ openLayer: vi.fn(), closeLayer: vi.fn(), setRightMode: vi.fn(), layers: { RIGHT: false } }),
}));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));
vi.mock('@/lib/projects/api', () => ({ getAllProjects: getAllProjectsMock }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: toastErrorMock } }));
vi.mock('@/components/projects/ProjectsShell', () => ({
  default: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
}));
vi.mock('@/components/ui/RightPanel', () => ({
  default: ({ children, open }: React.PropsWithChildren<{ open?: boolean }>) => open ? <aside>{children}</aside> : null,
}));
vi.mock('@/components/ui/PersonaSelect', () => ({ default: () => <div /> }));
vi.mock('@/design', () => ({ DSSkeleton: () => <div role="status" /> }));
vi.mock('@/components/ui/EmptyState', () => ({ default: ({ title }: { title: string }) => <div>{title}</div> }));
vi.mock('@/components/ConfirmActionDrawer', () => ({
  default: ({ action, onClose }: { action: { title: string; description: string; onConfirm: () => void | Promise<void> } | null; onClose: () => void }) => action ? (
    <section aria-label={action.title}>
      <p>{action.description}</p>
      <button type="button" onClick={onClose}>Cancelar</button>
      <button type="button" onClick={() => void action.onConfirm()}>Confirmar</button>
    </section>
  ) : null,
}));

describe('TeamPage member removal confirmation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAllProjectsMock.mockResolvedValue([{ id: 'project-1', title: 'Proyecto Alpha' }]);
    apiFetchMock.mockImplementation((path: string) => {
      if (path === '/system/workload') return Promise.resolve([]);
      if (path === '/projects/project-1/team') return Promise.resolve([
        { id: 'member-1', project_id: 'project-1', persona_id: 'person-1', persona_name: 'Ana Pérez', role: 'editor' },
      ]);
      return Promise.resolve(undefined);
    });
  });

  async function showProjectMember() {
    const { container } = render(<TeamPage />);
    await waitFor(() => expect(getAllProjectsMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByRole('button', { name: 'Integrantes por proyecto' })).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Integrantes por proyecto' }));
    await screen.findByRole('option', { name: 'Proyecto Alpha' });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'project-1' } });
    expect(await screen.findByText('Ana Pérez')).toBeTruthy();
    return container;
  }

  it('uses theme-defined semantic text tokens for the selected project team', async () => {
    const container = await showProjectMember();

    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(screen.getByText('Ana Pérez')).toHaveClass('text-[hsl(var(--text-primary))]');
    expect(container.innerHTML).toContain('--text-secondary');
  });

  it('does not remove a member until confirmation and cancellation makes no request', async () => {
    await showProjectMember();
    fireEvent.click(screen.getByRole('button', { name: 'Remover Ana Pérez del proyecto' }));
    expect(screen.getByText(/remover a Ana Pérez/i)).toBeTruthy();
    expect(apiFetchMock).not.toHaveBeenCalledWith('/projects/project-1/team/person-1', expect.objectContaining({ method: 'DELETE' }));

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(apiFetchMock).not.toHaveBeenCalledWith('/projects/project-1/team/person-1', expect.objectContaining({ method: 'DELETE' }));
    expect(screen.getByText('Ana Pérez')).toBeTruthy();
  });

  it('removes the member only after explicit confirmation', async () => {
    await showProjectMember();
    fireEvent.click(screen.getByRole('button', { name: 'Remover Ana Pérez del proyecto' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/project-1/team/person-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
    await waitFor(() => expect(screen.queryByText('Ana Pérez')).toBeNull());
  });

  describe('projects-team-pmi-header — Nivelación de Recursos PMI §9.6', () => {
    it('muestra el pool, sobrecargados, tareas críticas y diagnóstico', async () => {
      apiFetchMock.mockImplementation((path: string) => {
        if (path === '/system/workload') return Promise.resolve([
          { persona_id: 'p1', name: 'Ana Pérez', load_status: 'sobrecargado', open: 6, critical: 2, capacity_percent: 95 },
          { persona_id: 'p2', name: 'Luis Gómez', load_status: 'en_capacidad', open: 3, critical: 0, capacity_percent: 50 },
          { persona_id: 'p3', name: 'Mila Ferrer', load_status: 'disponible', open: 1, critical: 1, capacity_percent: 40 },
        ]);
        return Promise.resolve([]);
      });

      render(<TeamPage />);

      const header = await screen.findByTestId('projects-team-pmi-header');
      expect(header).toHaveTextContent('Pool Ministerial: 3');
      expect(header).toHaveTextContent('Sobrecargados: 1');
      expect(header).toHaveTextContent('Tareas Criticas: 3');
      expect(header).toHaveTextContent('Requiere Nivelación de Recursos (§9.6)');
      expect(screen.getByTestId('projects-team-pmi-header').innerHTML).toContain('text-[hsl(var(--destructive))]');
      cleanup();

      // Sin sobrecarga → diagnóstico óptimo y badge success
      apiFetchMock.mockImplementation((path: string) => {
        if (path === '/system/workload') return Promise.resolve([
          { persona_id: 'p2', name: 'Luis Gómez', load_status: 'en_capacidad', open: 3, critical: 0, capacity_percent: 50 },
          { persona_id: 'p3', name: 'Mila Ferrer', load_status: 'disponible', open: 1, critical: 1, capacity_percent: 40 },
        ]);
        return Promise.resolve([]);
      });
      render(<TeamPage />);
      expect(await screen.findByTestId('projects-team-pmi-header')).toHaveTextContent(
        'Asignación Nivelada Óptima'
      );
    });
  });
});

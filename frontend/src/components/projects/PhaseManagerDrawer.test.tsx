import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const mocks = vi.hoisted(() => ({
  tasks: [] as Array<{ id: string; title: string; status: string }>,
  addToast: vi.fn(),
  apiFetch: vi.fn(),
  reloadProject: vi.fn(),
}));

vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'token', loading: false }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/lib/http', () => ({ apiFetch: (...args: unknown[]) => mocks.apiFetch(...args) }));
vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => ({
    phases: [
      { slug: 'planning', name: 'Planificación', color: 'hsl(var(--primary))', order_index: 0 },
      { slug: 'active', name: 'En marcha', color: 'hsl(var(--success))', order_index: 1 },
    ],
    tasks: mocks.tasks,
    reloadProject: mocks.reloadProject,
  }),
}));

import { PhaseManagerDrawer } from './PhaseManagerDrawer';

describe('PhaseManagerDrawer accessibility & PMI Stage-Gate Governance', () => {
  beforeEach(() => {
    mocks.tasks = [];
    mocks.addToast.mockClear();
    mocks.apiFetch.mockReset();
    mocks.reloadProject.mockReset();
    window.localStorage.clear();
  });

  it('names reorder and delete actions and keeps deletion reachable on touch and focus', async () => {
    const { container } = render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'Mover fase Planificación arriba' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Mover fase Planificación abajo' })).toBeEnabled();
    const deleteButton = screen.getByRole('button', { name: 'Eliminar fase Planificación' });
    expect(deleteButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect((await axe(container)).violations).toEqual([]);
  });

  it('confirms removing an empty phase from the draft and keeps it unchanged on cancel', async () => {
    render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));
    const confirmDrawer = await screen.findByRole('complementary', { name: 'Eliminar fase del borrador' });
    expect(confirmDrawer).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();

    fireEvent.click(within(confirmDrawer).getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar fase del borrador' })).not.toBeInTheDocument());
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar fase' }));
    expect(screen.queryByRole('textbox', { name: 'Nombre de fase Planificación' })).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase En marcha' })).toBeInTheDocument();
  });

  it('blocks removing a phase that still owns tasks and explains how to proceed', () => {
    mocks.tasks = [{ id: 'task-1', title: 'Preparar reunión', status: 'planning' }];
    render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar fase Planificación' }));

    expect(mocks.addToast).toHaveBeenCalledWith('Mueve la tarea de esta fase antes de eliminarla.', 'error');
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();
    expect(screen.queryByRole('complementary', { name: 'Eliminar fase del borrador' })).not.toBeInTheDocument();
  });

  it('renders PMI Stage-Gate summary banner, bottleneck phase, orphan detection, and per-phase package metrics', () => {
    mocks.tasks = [
      { id: 't1', title: 'Acta de constitución', status: 'planning' },
      { id: 't2', title: 'Registro de interesados', status: 'planning' },
      { id: 't3', title: 'Tarea legada', status: 'archived_phase' },
    ];
    render(<PhaseManagerDrawer projectId="project-1" onClose={vi.fn()} />);

    const summary = screen.getByTestId('phase-manager-pmi-summary');
    expect(summary).toHaveTextContent('2');
    expect(summary).toHaveTextContent('3');
    expect(summary).toHaveTextContent('Planificación (2)');
    expect(summary).toHaveTextContent('1 huérfano(s)');

    const planningMetrics = screen.getByTestId('phase-card-metrics-planning');
    expect(planningMetrics).toHaveTextContent('2 paquete(s)');
    expect(planningMetrics).toHaveTextContent('En uso');

    const activeMetrics = screen.getByTestId('phase-card-metrics-active');
    expect(activeMetrics).toHaveTextContent('0 paquete(s)');
    expect(activeMetrics).toHaveTextContent('Libre');
  });

  it('applies PMI lifecycle presets safely without removing existing phases and saves via apiFetch', async () => {
    mocks.apiFetch.mockResolvedValueOnce({});
    mocks.reloadProject.mockResolvedValueOnce(undefined);
    const onClose = vi.fn();

    render(<PhaseManagerDrawer projectId="project-42" onClose={onClose} />);

    const summary = screen.getByTestId('phase-manager-pmi-summary');
    expect(summary).toHaveTextContent('Sin carga');
    expect(summary).toHaveTextContent('0 huérfanos');

    fireEvent.click(screen.getByTestId('phase-preset-predictive'));

    // Keeps existing "Planificación" and "En marcha" and appends missing predictive phases
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Planificación' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase En marcha' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Inicio' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Ejecución' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Monitoreo y Control' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Nombre de fase Cierre' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }));

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        '/projects/project-42/phases',
        expect.objectContaining({
          method: 'PUT',
          token: 'token',
          body: expect.arrayContaining([
            expect.objectContaining({ slug: 'planning', name: 'Planificación', order_index: 0 }),
            expect.objectContaining({ slug: 'active', name: 'En marcha', order_index: 1 }),
            expect.objectContaining({ name: 'Inicio', order_index: 2 }),
            expect.objectContaining({ name: 'Ejecución', order_index: 3 }),
            expect.objectContaining({ name: 'Monitoreo y Control', order_index: 4 }),
            expect.objectContaining({ name: 'Cierre', order_index: 5 }),
          ]),
        }),
      );
    });
    expect(mocks.reloadProject).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});

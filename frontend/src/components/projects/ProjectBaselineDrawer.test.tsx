import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectBaselineDrawer } from './ProjectBaselineDrawer';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({
    open,
    title,
    children,
  }: {
    open: boolean;
    title: string;
    children: ReactNode;
  }) => open ? <section role="dialog" aria-label={title}>{children}</section> : null,
}));

describe('ProjectBaselineDrawer read states', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
  });

  it('does not call a failed baseline/history lookup an empty baseline and recovers on retry', async () => {
    let latestAttempts = 0;
    let historyAttempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/baseline')) {
        latestAttempts += 1;
        return latestAttempts === 1 ? Promise.reject(new Error('offline')) : Promise.resolve(null);
      }
      if (path.endsWith('/baselines')) {
        historyAttempts += 1;
        return historyAttempts === 1 ? Promise.reject(new Error('offline')) : Promise.resolve([]);
      }
      return Promise.resolve(null);
    });

    render(
      <ProjectBaselineDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
      />,
    );

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No se pudo consultar la línea base ni su historial.');
    expect(screen.queryByText('Sin Línea Base Registrada')).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'No se pudo actualizar el historial de línea base',
      variant: 'destructive',
    }));

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar carga' }));
    await waitFor(() => expect(latestAttempts).toBe(2));
    await waitFor(() => expect(historyAttempts).toBe(2));
    expect(await screen.findByText('Sin Línea Base Registrada')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('associates the create-baseline fields with their labels', async () => {
    mocks.apiFetch.mockResolvedValue(null);

    render(
      <ProjectBaselineDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole('button', { name: /Congelar Nueva Línea Base/i }));
    expect(screen.getByLabelText('Nombre de la Línea Base')).toBeInTheDocument();
    expect(screen.getByLabelText('Descripción / Motivo del Congelamiento (Opcional)')).toBeInTheDocument();
  });

  it('indicates the active EVM baseline snapshot and compares baseline BAC against currentBac', async () => {
    const activeSnapshot = {
      id: 'bl-active-1',
      project_id: 'project-1',
      name: 'Línea Base Inicial Q1',
      description: 'Foto aprobada por comité',
      created_at: '2026-09-01T00:00:00Z',
      is_active: true,
      snapshot_data: {
        bac: 80000,
        progress_percentage: 25,
        total_tasks: 12,
        completed_tasks: 3,
      },
    };
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/baseline')) return Promise.resolve(activeSnapshot);
      if (path.endsWith('/baselines')) return Promise.resolve([activeSnapshot]);
      return Promise.resolve(null);
    });

    render(
      <ProjectBaselineDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
        currentBac={95000}
      />,
    );

    expect(await screen.findByText('Activa en Motor EVM')).toBeInTheDocument();
    expect(screen.getByText('BAC Línea Base (Congelado):')).toBeInTheDocument();
    expect(screen.getByText('BAC Actual vs Línea Base:')).toBeInTheDocument();
    expect(screen.getByText('EVM Activa')).toBeInTheDocument();
  });

  it('diagnoses PMB scope, schedule and cost deviations and submits a re-baseline request to the CCB', async () => {
    const activeSnapshot = {
      id: 'bl-active-2',
      project_id: 'project-1',
      name: 'PMB aprobada',
      created_at: '2026-09-01T00:00:00Z',
      snapshot_data: { tasks_count: 2, bac: 80000 },
      total_variance_days: 4,
      comparisons: [
        { task_id: 'task-1', title: 'Diseño', baseline_duration: 4, current_duration: 9, variance_days: 5, status: 'in_progress' },
        { task_id: 'task-2', title: 'Compra', baseline_duration: 3, current_duration: 1, variance_days: -2, status: 'completed' },
        { task_id: 'task-3', title: 'Instalación', baseline_duration: 2, current_duration: 3, variance_days: 1, status: 'todo' },
      ],
    };
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith('/change-requests') && options?.method === 'POST') return Promise.resolve({ id: 'cr-1' });
      if (path.endsWith('/baseline')) return Promise.resolve(activeSnapshot);
      if (path.endsWith('/baselines')) return Promise.resolve([activeSnapshot]);
      return Promise.resolve(null);
    });

    render(
      <ProjectBaselineDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
        currentBac={95000}
      />,
    );

    expect(await screen.findByRole('heading', { name: /Diagnóstico de Integridad PMB/ })).toBeInTheDocument();
    expect(screen.getByText('2 congelados · 3 auditados')).toBeInTheDocument();
    expect(screen.getByText('+1 entregable(s) · Scope Creep')).toBeInTheDocument();
    expect(screen.getByText('Desvío acumulado: 4 días')).toBeInTheDocument();
    expect(screen.getByText('2 con atraso · 1 en fecha o adelantadas')).toBeInTheDocument();
    expect(screen.getByText('Delta: +$15.000')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Desviación sobre la PMB Detectada');

    fireEvent.click(screen.getByRole('button', { name: 'Radicar Solicitud de Re-baseline al CCB' }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/change-requests',
      expect.objectContaining({
        method: 'POST',
        token: 'test-token',
        body: {
          title: 'Solicitud de Re-baseline PMB por desviación detectada',
          description: expect.stringContaining('Desvío acumulado del cronograma: 4 días'),
          justification: 'Alineación formal de la PMB bajo Control Integrado de Cambios PMI',
          change_type: 'integrated',
          cost_impact_delta: 15000,
          scope_impact_summary: 'Adición de 1 entregable(s): 2 paquetes congelados frente a 3 tareas auditadas.',
          scope_impact: 'Adición de 1 entregable(s): 2 paquetes congelados frente a 3 tareas auditadas.',
          schedule_impact_days: 4,
          cost_impact: 15000,
        },
      }),
    ));
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Solicitud radicada ante el CCB',
    }));
    expect(screen.getByRole('button', { name: 'Solicitud radicada ante el CCB' })).toBeDisabled();
  });
});

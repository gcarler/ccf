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
});

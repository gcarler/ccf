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
});

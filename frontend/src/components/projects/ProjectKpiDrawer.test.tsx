import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectKpiDrawer } from './ProjectKpiDrawer';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));
const kpi = {
  id: 'kpi-1',
  project_id: 'project-1',
  title: 'Asistencia objetivo',
  description: 'Medición semanal',
  target_value: 100,
  current_value: 75,
  unit: '%',
  category: 'impact',
};

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ open, children }: React.PropsWithChildren<{ open: boolean }>) => open ? <div>{children}</div> : null,
}));

describe('ProjectKpiDrawer deletion', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset().mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.resolve({ ok: true });
      if (path.endsWith('/kpis')) return Promise.resolve([kpi]);
      return Promise.resolve([]);
    });
    mocks.addToast.mockClear();
  });

  it('requires confirmation and cancellation leaves the KPI intact', async () => {
    const { container } = render(<ProjectKpiDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText('Asistencia objetivo')).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(container.innerHTML).toContain('--text-primary');
    expect(container.innerHTML).toContain('--text-secondary');

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar KPI Asistencia objetivo' }));
    expect(await screen.findByRole('complementary', { name: 'Eliminar indicador' })).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar indicador' })).not.toBeInTheDocument());
    expect(screen.getByText('Asistencia objetivo')).toBeInTheDocument();
  });

  it('removes a KPI after confirmation and retains it if the request fails', async () => {
    const onKpisUpdated = vi.fn();
    render(<ProjectKpiDrawer projectId="project-1" isOpen onClose={vi.fn()} onKpisUpdated={onKpisUpdated} />);
    expect(await screen.findByText('Asistencia objetivo')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar KPI Asistencia objetivo' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar indicador' }));
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/kpis/kpi-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
    await waitFor(() => expect(screen.getByText('Sin indicadores configurados')).toBeInTheDocument());
    expect(onKpisUpdated).toHaveBeenCalledTimes(1);
  });

  it('keeps the KPI and drawer available for retry after a failed deletion', async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.reject(new Error('offline'));
      if (path.endsWith('/kpis')) return Promise.resolve([kpi]);
      return Promise.resolve([]);
    });
    render(<ProjectKpiDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText('Asistencia objetivo')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar KPI Asistencia objetivo' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar indicador' }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Error al eliminar',
      variant: 'destructive',
    })));
    expect(screen.getByText('Asistencia objetivo')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Eliminar indicador' })).toBeInTheDocument();
  });
});

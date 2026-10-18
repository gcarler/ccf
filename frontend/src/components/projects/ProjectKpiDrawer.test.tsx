import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

  it('renders benefits realization, RAG counts and filters KPIs by tolerance threshold', async () => {
    const portfolioKpis = [
      { ...kpi, id: 'kpi-green-1', title: 'KPI en camino', current_value: 75, source_type: 'pro_edt_progress' },
      { ...kpi, id: 'kpi-green-2', title: 'KPI completado', current_value: 100, source_type: 'manual' },
      { ...kpi, id: 'kpi-amber', title: 'KPI en riesgo', current_value: 55, source_type: 'pro_cost_efficiency' },
      { ...kpi, id: 'kpi-red', title: 'KPI crítico', current_value: 30, source_type: 'evm_cr' },
    ];
    mocks.apiFetch.mockImplementation((path: string) =>
      path.endsWith('/kpis') ? Promise.resolve(portfolioKpis) : Promise.resolve([]),
    );

    render(<ProjectKpiDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(await screen.findByRole('heading', {
      name: 'Tablero PMI de Realización de Beneficios y Tolerancia RAG (Vol. 1 & 5)',
    })).toBeInTheDocument();
    const benefitsDashboard = screen.getByRole('region', {
      name: 'Tablero PMI de Realización de Beneficios y Tolerancia RAG (Vol. 1 & 5)',
    });
    expect(screen.getByText('65.0%')).toBeInTheDocument();
    expect(within(benefitsDashboard).getByText('Completados o En Camino').parentElement).toHaveTextContent('2');
    expect(within(benefitsDashboard).getByText('En Riesgo').parentElement).toHaveTextContent('1');
    expect(within(benefitsDashboard).getByText('Críticos').parentElement).toHaveTextContent('1');
    expect(screen.getByText('Tiempo')).toBeInTheDocument();
    expect(screen.getByText('Financiero')).toBeInTheDocument();
    expect(screen.getByText('Cruce EVM')).toBeInTheDocument();
    expect(screen.getByText('Manual')).toBeInTheDocument();
    expect(within(benefitsDashboard).getByRole('alert')).toHaveTextContent('Acción correctiva PMI requerida');
    expect(screen.getByText('KPI en camino')).toBeInTheDocument();
    expect(screen.getByText('KPI en riesgo')).toBeInTheDocument();
    expect(screen.getByText('KPI crítico')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Fuera de Tolerancia <40%' }));
    expect(screen.getByText('KPI crítico')).toBeInTheDocument();
    expect(screen.queryByText('KPI en camino')).not.toBeInTheDocument();
    expect(screen.queryByText('KPI en riesgo')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Fuera de Tolerancia <40%' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'En Alerta 40-69%' }));
    expect(screen.getByText('KPI en riesgo')).toBeInTheDocument();
    expect(screen.queryByText('KPI crítico')).not.toBeInTheDocument();
  });
});

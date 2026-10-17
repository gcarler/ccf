import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectEVMDrawer } from './ProjectEVMDrawer';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), toast: { error: vi.fn(), success: vi.fn() } }));

const mockCurveSResponse = {
  project_id: 'proj-123',
  summary: {
    project_id: 'proj-123',
    calculated_at: '2026-10-09T00:00:00Z',
    bac: 100000,
    ac: 45000,
    ev: 50000,
    pv: 48000,
    progress_percentage: 50.0,
    financial_percentage: 45.0,
    cpi: 1.11,
    spi: 1.04,
    cv: 5000,
    sv: 2000,
    cr: 1.15,
    eac: 90090.09,
    vac: 9909.91,
    health_status: 'OPTIMO',
    health_color: 'success' as const,
    recommendations: ['El proyecto avanza dentro del presupuesto.'],
  },
  points: [
    { date: '2026-09-01', label: '01 Sep', pv: 0, ev: 0, ac: 0, cpi: 1.0, spi: 1.0 },
    { date: '2026-10-01', label: '01 Oct', pv: 48000, ev: 50000, ac: 45000, cpi: 1.11, spi: 1.04 },
  ],
};

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('sonner', () => ({ toast: mocks.toast }));
vi.mock('@/components/ui/RightPanel', () => ({
  default: ({ isOpen, children, title, subtitle }: { isOpen: boolean; children: React.ReactNode; title?: React.ReactNode; subtitle?: React.ReactNode }) =>
    isOpen ? (
      <aside data-testid="right-panel">
        <div>{title}</div>
        <div>{subtitle}</div>
        {children}
      </aside>
    ) : null,
}));

describe('ProjectEVMDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apiFetch.mockResolvedValue(mockCurveSResponse);
  });

  it('renders EVM metrics, CPI, SPI and Curva S correctly', async () => {
    render(
      <ProjectEVMDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    // La vista inicial de Curva S renderiza el gráfico de desempeño acumulado
    // (el drawer migró de RightPanel a header con pestañas: "Curva S / 4 Cuadrantes / WBS")
    expect(await screen.findByText(/Curva S de Desempeño Acumulado/i)).toBeInTheDocument();

    // Debe mostrar los indicadores CPI y SPI calculados
    expect(await screen.findByText('1.11')).toBeInTheDocument();
    expect(screen.getByText('1.04')).toBeInTheDocument();

    // Debe mostrar estado de salud
    expect(screen.getByText('OPTIMO')).toBeInTheDocument();

    // Debe mostrar recomendaciones
    expect(screen.getByText(/El proyecto avanza dentro del presupuesto/i)).toBeInTheDocument();

    // Debe verificar que llamó al endpoint canónico de curve-s
    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        '/projects/proj-123/evm/curve-s?points=10',
        expect.objectContaining({ token: 'test-token' })
      );
    });
  });

  it('renders Tiempo Ganado (ES / SPI(t)) and Tributación EDT when execution_matrix is included', async () => {
    mocks.apiFetch.mockResolvedValueOnce({
      ...mockCurveSResponse,
      execution_matrix: {
        project_id: 'proj-123',
        calculated_at: '2026-10-17T00:00:00Z',
        frentes: {
          tiempo: {
            spi: 1.04,
            spi_t: 1.08,
            sv: 2000,
            progress_pct: 50,
            planned_duration_days: 40,
            actual_time_days: 20,
            earned_schedule_days: 21.6,
            estimated_hours: 120,
            actual_hours: 55,
            hours_efficiency_pct: 109.1,
            milestones_total: 2,
            milestones_completed: 1,
            milestones_ontime: 1,
            milestones_ontime_pct: 50,
            tasks_total: 4,
            tasks_completed: 2,
            tasks_overdue: 0,
          },
          financiero: {
            cpi: 1.11,
            cv: 5000,
            bac: 100000,
            ac: 45000,
            remaining_budget: 55000,
            burn_rate_pct: 45,
            financial_progress_pct: 45,
            expenses_count: 3,
          },
          cruce_evm: {
            ev: 50000,
            pv: 48000,
            ac: 45000,
            bac: 100000,
            cpi: 1.11,
            spi: 1.04,
            cr: 1.15,
            eac: 90090.09,
            vac: 9909.91,
            balance_gap_pct: 5,
            health_status: 'OPTIMO',
            health_color: 'success',
          },
        },
        familias_pro: {},
        rollup_hierarchy: {
          overall_progress_pct: 50,
          components: [
            {
              component_id: 'comp-a',
              code: 'EDT-01',
              name: 'Cimentación Norte',
              budget_allocated: 100000,
              budget_weight_pct: 100,
              physical_progress_pct: 50,
              financial_progress_pct: 45,
              spi: 1.04,
              cpi: 1.11,
              cr: 1.15,
              ev: 50000,
              pv: 48000,
              ac: 45000,
              health_status: 'OPTIMO',
              health_color: 'success',
              activities_count: 2,
              subtasks_count: 4,
              estimated_hours: 120,
              actual_hours: 55,
              activities: [],
            },
          ],
          unassigned_activities_count: 0,
          unassigned_progress_pct: 0,
        },
        raid_summary: {
          total_risks: 0,
          mitigated_risks: 0,
          active_risks: 0,
          occurred_risks: 0,
          mitigated_pct: 100,
        },
        sources_catalog: {},
      },
    });

    render(
      <ProjectEVMDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(await screen.findByText(/Tiempo Ganado \(ES \/ SPI\(t\)\) y Tributación EDT/i)).toBeInTheDocument();
    expect(screen.getByText(/21\.6d \/ 40d/i)).toBeInTheDocument();
    expect(screen.getByText(/SPI\(t\): 1\.08/i)).toBeInTheDocument();
    expect(screen.getByText(/\[EDT-01\] Cimentación Norte/i)).toBeInTheDocument();
  });
});


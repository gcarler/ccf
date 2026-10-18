import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch, apiFetchBlob } from "@/lib/http";
import type { ProjectExecutiveReportData } from "@/types/projects";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { ProjectReportDrawer } from "./ProjectReportDrawer";

const mocks = vi.hoisted(() => ({ addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

vi.mock("@/context/ToastContext", () => ({
  useToast: () => ({ addToast: mocks.addToast }),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
  apiFetchBlob: vi.fn(),
}));

const reportData = {
  project: {
    id: "project-1",
    title: "Campamento de verano",
    description: "Preparación anual",
    status: "active",
    priority: "high",
    progress_percentage: 40,
    budget_allocated: 10000,
    budget_spent: 2500,
    owner_name: "Ana Pérez",
  },
  tasks_metrics: { total: 5, completed: 2, in_progress: 1, todo: 1, blocked: 1, completion_rate: 40 },
  financial_kpis: {
    project_id: "project-1", budget_allocated: 10000, budget_spent: 2500,
    remaining_budget: 7500, burn_rate_percent: 25, total_expenses_count: 1, by_category: {},
  },
  raid_kpis: { total_risks: 0, critical_count: 0, high_count: 0, medium_count: 0, low_count: 0, risks: [] },
  cpm_metrics: { project_id: "project-1", total_duration_days: 0, critical_tasks_count: 0, critical_path_task_ids: [], tasks: [] },
  time_metrics: { total_hours: 0, billable_hours: 0, non_billable_hours: 0, total_logs: 0, by_task: [], by_member: [] },
  phases: [],
  generated_at: "2026-10-04T00:00:00Z",
  organization: "CCF",
} satisfies ProjectExecutiveReportData;

function renderDrawer() {
  return render(
    <SidebarLayerProvider>
      <ProjectReportDrawer projectId="project-1" isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectReportDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses declared design-system tokens throughout the report", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(reportData);

    const { container } = renderDrawer();
    await screen.findByText("Campamento de verano");

    // El drawer migró de RightPanel a header propio: el body del reporte es .flex-1.overflow-y-auto
    const reportBody = container.querySelector(".flex-1.overflow-y-auto");
    expect(reportBody).not.toBeNull();
    expect(reportBody?.innerHTML).not.toMatch(/--(?:card|foreground|muted-foreground)\b/);
  });

  it("renderiza la tarjeta ejecutiva CCB, Aceptación DoD y CoQ por categoría", async () => {
    const reportWithCcb = {
      ...reportData,
      ccb_and_quality_summary: {
        total_change_requests: 3,
        pending_ccb_count: 1,
        approved_count: 2,
        rejected_count: 0,
        net_approved_cost_delta: 20000,
        net_approved_schedule_days: 15,
        tasks_dod_accepted_count: 4,
        total_coq_cost: 350,
        coq_by_category: {
          prevention: 250,
          appraisal: 100,
          internal_failure: 0,
          external_failure: 0,
        },
      },
    } satisfies ProjectExecutiveReportData;
    vi.mocked(apiFetch).mockResolvedValueOnce(reportWithCcb);

    const { container } = renderDrawer();

    expect(
      await screen.findByText(/Control de Cambios \(CCB\) · Aceptación DoD · Costo de Calidad/),
    ).toBeInTheDocument();
    expect(screen.getByText("3 solicitudes de cambio")).toBeInTheDocument();
    expect(screen.getAllByText("Pendientes CCB").length).toBeGreaterThan(0);
    expect(screen.getByText(/\$20,000 y 15 días/)).toBeInTheDocument();
    expect(screen.getByText(/Entregables aceptados \(DoD 4\/4\):/)).toBeInTheDocument();
    for (const categoryLabel of ["Prevención", "Evaluación", "Falla Interna", "Falla Externa"]) {
      expect(screen.getByText(categoryLabel)).toBeInTheDocument();
    }
    expect(screen.getByText(/\$350/)).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it("shows loading state and renders executive data when it arrives", async () => {
    let resolveReport: ((value: ProjectExecutiveReportData) => void) | undefined;
    vi.mocked(apiFetch).mockImplementation(() => new Promise((resolve) => {
      resolveReport = resolve as (value: ProjectExecutiveReportData) => void;
    }));

    const { container } = renderDrawer();
    expect(screen.getByText("Consolidando métricas e indicadores ejecutivos del proyecto...")).toBeInTheDocument();
    resolveReport?.(reportData);

    expect(await screen.findByText("Campamento de verano")).toBeInTheDocument();
    // Header con pestañas propio del drawer (ya no hay shell role=dialog)
    expect(screen.getByText("Previsualización Ejecutiva")).toBeInTheDocument();
    expect(screen.getByText("Ana Pérez")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/export/executive-data", { token: "test-token" });
    expect((await axe(container)).violations).toEqual([]);
  });

  it("renders the PMI governance summary when the API includes it", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...reportData,
      governance_summary: {
        charter_status: "authorized",
        sponsor_id: "persona-sponsor-1",
        authorized_at: "2026-10-18T12:00:00Z",
        measurable_objectives_count: 3,
        stakeholders_total: 4,
        stakeholders_by_quadrant: {
          manage_closely: 1,
          keep_satisfied: 1,
          keep_informed: 1,
          monitor: 1,
        },
        closure_status: "open",
        deliverables_accepted_verified: false,
        financial_reconciliation_completed: false,
        lessons_learned_count: 0,
      },
    });

    renderDrawer();

    const summary = await screen.findByTestId("governance-summary");
    expect(within(summary).getByText("Gobernanza del Ciclo de Vida PMI")).toBeInTheDocument();
    expect(within(summary).getByText(/Gestionar de cerca:/).parentElement).toHaveTextContent("1");
    expect(within(summary).getByText("persona-sponsor-1")).toBeInTheDocument();
    expect(within(summary).getByText(/Lecciones aprendidas:/).parentElement).toHaveTextContent("0");
  });

  it("announces report loading errors and provides the empty recovery state", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Servicio no disponible"));

    renderDrawer();

    expect(await screen.findByText("No se pudieron cargar los datos del informe")).toBeInTheDocument();
    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: "Error al cargar reporte",
      description: "Servicio no disponible",
      type: "error",
    })));

    vi.mocked(apiFetch).mockResolvedValueOnce(reportData);
    await user.click(screen.getByTitle("Refrescar datos del reporte"));
    expect(await screen.findByText("Campamento de verano")).toBeInTheDocument();
  });

  it("reports PDF export failures without pretending the file downloaded", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce(reportData);
    vi.mocked(apiFetchBlob).mockRejectedValueOnce(new Error("PDF no disponible"));

    renderDrawer();
    await screen.findByText("Campamento de verano");
    await user.click(screen.getByRole("button", { name: /Centro de Descargas/ }));
    await user.click(screen.getByRole("button", { name: /Descargar PDF/ }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: "Error en la exportación",
      description: "PDF no disponible",
      type: "error",
    })));
    expect(apiFetchBlob).toHaveBeenCalledWith("/projects/project-1/export/summary-pdf", { token: "test-token" });
  });

  it("renders 3 Frentes de Ejecución, Tributación EDT and 6 Familias Pro when execution_matrix is present", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...reportData,
      project: { ...reportData.project, progress_percentage: 68 },
      execution_matrix: {
        project_id: "project-1",
        calculated_at: "2026-10-17T00:00:00Z",
        frentes: {
          tiempo: {
            spi: 1.05,
            spi_t: 1.02,
            sv: 500,
            progress_pct: 68,
            planned_duration_days: 30,
            actual_time_days: 20,
            earned_schedule_days: 20.4,
            estimated_hours: 100,
            actual_hours: 65,
            hours_efficiency_pct: 104.6,
            milestones_total: 2,
            milestones_completed: 2,
            milestones_ontime: 2,
            milestones_ontime_pct: 100,
            tasks_total: 5,
            tasks_completed: 2,
            tasks_overdue: 0,
          },
          financiero: {
            cpi: 1.36,
            cv: 1800,
            bac: 10000,
            ac: 5000,
            remaining_budget: 5000,
            burn_rate_pct: 50,
            financial_progress_pct: 50,
            expenses_count: 2,
          },
          cruce_evm: {
            ev: 6800,
            pv: 6476,
            ac: 5000,
            bac: 10000,
            cpi: 1.36,
            spi: 1.05,
            cr: 1.43,
            eac: 7352.94,
            vac: 2647.06,
            balance_gap_pct: 18,
            health_status: "OPTIMO",
            health_color: "success",
          },
        },
        familias_pro: {
          pro_edt_progress: {
            code: "PRO-01",
            title: "Avance Físico Ponderado (EDT -> Proyecto)",
            current_value: 68,
            target_value: 100,
            unit: "%",
            spi: 0.68,
            frente: "tiempo",
          },
        },
        rollup_hierarchy: {
          overall_progress_pct: 68,
          components: [
            {
              component_id: "comp-1",
              code: "EDT-01",
              name: "Infraestructura Base",
              budget_allocated: 6000,
              budget_weight_pct: 60,
              physical_progress_pct: 80,
              financial_progress_pct: 50,
              spi: 1.1,
              cpi: 1.6,
              cr: 1.76,
              ev: 4800,
              pv: 4363,
              ac: 3000,
              health_status: "OPTIMO",
              health_color: "success",
              activities_count: 2,
              subtasks_count: 3,
              estimated_hours: 60,
              actual_hours: 40,
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

    const { container } = renderDrawer();
    expect(await screen.findByText(/Balance Integral de los 3 Frentes de Ejecución/i)).toBeInTheDocument();
    expect(screen.getByText(/\[EDT-01\] Infraestructura Base/i)).toBeInTheDocument();
    expect(screen.getByText("PRO-01")).toBeInTheDocument();

    const reportBody = container.querySelector(".flex-1.overflow-y-auto");
    expect(reportBody?.innerHTML).not.toMatch(/--(?:card|foreground|muted-foreground)\b/);
  });

  it("renders the 360° summary of all 6 operational submodules when submodules_summary is present", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...reportData,
      submodules_summary: {
        baseline: {
          has_active_baseline: true,
          baseline_id: "base-1",
          baseline_name: "Línea Base Inicial Q4",
          baseline_bac: 10000,
          baseline_variance_cost: 7500,
          baseline_variance_schedule: 15,
          snapshots_count: 2,
        },
        supplies: {
          total_supplies_count: 4,
          delivered_supplies_count: 3,
          total_supplies_cost: 1800,
          auto_generated_expenses_count: 2,
          auto_generated_expenses_total: 1200,
        },
        time_tracking: {
          logs_count: 5,
          billable_hours: 32,
          non_billable_hours: 8,
          total_logged_hours: 40,
          estimated_hours_total: 80,
          hours_utilization_pct: 50,
        },
        workload: {
          members_with_tasks_count: 3,
          overloaded_members_count: 1,
          avg_utilization_pct: 62.5,
        },
        cpm: {
          critical_tasks_count: 3,
          critical_completed_count: 2,
          dependencies_count: 4,
        },
        automations: {
          total_rules_count: 3,
          active_rules_count: 2,
          total_executions_count: 9,
        },
      },
    });

    const { container } = renderDrawer();
    expect(await screen.findByText(/Estado 360° de Submódulos de Control Operativo/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. Línea Base EVM/i)).toBeInTheDocument();
    expect(screen.getByText(/Línea Base Inicial Q4/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Suministros e Insumos/i)).toBeInTheDocument();
    expect(screen.getByText(/3\/4 entregados/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Hojas de Tiempo/i)).toBeInTheDocument();
    expect(screen.getByText(/5 registros/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Carga de Equipo \(Workload\)/i)).toBeInTheDocument();
    expect(screen.getByText(/62\.5%/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Ruta Crítica \(CPM \/ EDT\)/i)).toBeInTheDocument();
    expect(screen.getByText(/4 dependencias/i)).toBeInTheDocument();
    expect(screen.getByText(/6\. Automatizaciones/i)).toBeInTheDocument();
    expect(screen.getByText(/2\/3 activas/i)).toBeInTheDocument();

    const reportBody = container.querySelector(".flex-1.overflow-y-auto");
    expect(reportBody?.innerHTML).not.toMatch(/--(?:card|foreground|muted-foreground)\b/);
  });

  it("renders Canonical Reserves (EMV), 15% CPI Stability Rule, and Early Warning Sentinel in the financial section", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...reportData,
      financial_kpis: {
        ...reportData.financial_kpis,
        work_packages_budget: 8500,
        contingency_reserve: 1500,
        management_reserve: 1000,
        total_project_budget: 11000,
        cpi_stability_rule: {
          is_applicable: true,
          is_locked: true,
          threshold_pct: 15,
          progress_pct: 40,
          current_cpi: 0.92,
          cpi_locked_value: 0.92,
          expected_cpi_floor: 0.82,
          expected_cpi_ceiling: 1.02,
          eac_floor: 10869.57,
          eac_ceiling: 11500,
          status: "LOCKED",
          is_irrecoverable_without_rebaseline: false,
          diagnostic_message: "Con 40% de avance (≥15%), el CPI es estadísticamente estable.",
          explanation: "Con 40% de avance (≥15%), el CPI es estadísticamente estable.",
        },
        early_warning_sentinel: {
          level: "ALERTA_PREVENTIVA",
          label: "Alerta Preventiva (CPI < 0.95)",
          color: "warning",
          min_index: 0.92,
          cpi: 0.92,
          spi: 0.96,
          tcpi: 1.05,
          protocol_action: "Revisar paquetes de trabajo activos.",
          is_recoverable_without_ccb: true,
          requires_ccb: false,
          message: "Ligera desviación de costos detectada antes de umbral crítico.",
          recommended_action: "Revisar paquetes de trabajo activos.",
        },
      },
    });

    renderDrawer();

    const reserves = await screen.findByTestId("report-canonical-reserves");
    expect(within(reserves).getByText("Paquetes de Trabajo")).toBeInTheDocument();
    expect(within(reserves).getByText("$8,500")).toBeInTheDocument();
    expect(within(reserves).getByText("Reserva Contingencia (EMV)")).toBeInTheDocument();
    expect(within(reserves).getByText("$1,500")).toBeInTheDocument();
    expect(within(reserves).getByText("Reserva de Gestión")).toBeInTheDocument();
    expect(within(reserves).getByText("$1,000")).toBeInTheDocument();
    expect(within(reserves).getByText("Presupuesto Total Proyecto")).toBeInTheDocument();
    expect(within(reserves).getByText("$11,000")).toBeInTheDocument();

    const cpiRule = screen.getByTestId("report-cpi-stability-rule");
    expect(within(cpiRule).getByText(/Regla del 15% de Estabilidad CPI/i)).toBeInTheDocument();
    expect(within(cpiRule).getByText(/CPI Bloqueado \(≥15%\)/i)).toBeInTheDocument();

    const sentinel = screen.getByTestId("report-early-warning-sentinel");
    expect(within(sentinel).getByText("ALERTA_PREVENTIVA")).toBeInTheDocument();
    expect(within(sentinel).getByText(/Ligera desviación de costos detectada/i)).toBeInTheDocument();
  });
});



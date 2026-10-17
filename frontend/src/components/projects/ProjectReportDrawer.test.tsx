import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
});


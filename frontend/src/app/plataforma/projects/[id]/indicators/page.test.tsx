import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import type { ProjectIndicator } from "@/types/projects";
import ProjectIndicatorsPage from "./page";

const mocks = vi.hoisted(() => ({ projectId: "project-1", toastError: vi.fn() }));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: mocks.projectId }) }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
vi.mock("@/components/projects/ProjectIndicatorsDrawer", () => ({ ProjectIndicatorsDrawer: () => null }));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError } }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function indicator(id: string, projectId: string, name: string): ProjectIndicator {
  return {
    id,
    project_id: projectId,
    name,
    level: "PRODUCTO_PRINCIPAL",
    calculation_type: "ABSOLUTO_ACUMULADO",
    baseline_value: 0,
    target_value: 10,
    current_value: 0,
    frequency: "mensual",
    period_targets: {},
    crema_evaluation: {},
    created_at: "2026-10-04T00:00:00Z",
    updated_at: "2026-10-04T00:00:00Z",
  };
}

describe("ProjectIndicatorsPage loading recovery", () => {
  beforeEach(() => {
    mocks.projectId = "project-1";
    vi.clearAllMocks();
  });

  it("keeps API failure distinct from a successful empty response and retries", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ title: "Proyecto de prueba" })
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ title: "Proyecto de prueba" })
      .mockResolvedValueOnce([]);

    const { container } = render(<ProjectIndicatorsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar los indicadores");
    expect((await axe(container)).violations).toEqual([]);
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(screen.queryByText("Sin indicadores configurados")).not.toBeInTheDocument();
    expect(screen.queryByText("Total Indicadores")).not.toBeInTheDocument();
    expect(mocks.toastError).toHaveBeenCalledWith("Error al cargar indicadores MGA");

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Sin indicadores configurados")).toBeInTheDocument();
  });

  it("ignores responses from the previous project after switching routes", async () => {
    const projectATitle = deferred<{ title: string }>();
    const projectAIndicators = deferred<ProjectIndicator[]>();
    const projectBTitle = deferred<{ title: string }>();
    const projectBIndicators = deferred<ProjectIndicator[]>();
    const responses = new Map<string, Promise<unknown>>([
      ["/projects/project-a", projectATitle.promise],
      ["/projects/project-a/advanced-indicators", projectAIndicators.promise],
      ["/projects/project-b", projectBTitle.promise],
      ["/projects/project-b/advanced-indicators", projectBIndicators.promise],
    ]);
    vi.mocked(apiFetch).mockImplementation(async <T,>(path: string): Promise<T> => {
      return (await responses.get(path)) as T;
    });

    mocks.projectId = "project-a";
    const { rerender } = render(<ProjectIndicatorsPage />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2));

    mocks.projectId = "project-b";
    rerender(<ProjectIndicatorsPage />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(4));

    await act(async () => {
      projectBTitle.resolve({ title: "Proyecto B" });
      projectBIndicators.resolve([indicator("indicator-b", "project-b", "Indicador B")]);
    });
    expect(await screen.findByText("Indicador B")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyecto B" })).toBeInTheDocument();

    await act(async () => {
      projectATitle.resolve({ title: "Proyecto A" });
      projectAIndicators.resolve([indicator("indicator-a", "project-a", "Indicador A")]);
    });

    expect(screen.getByText("Indicador B")).toBeInTheDocument();
    expect(screen.queryByText("Indicador A")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyecto B" })).toBeInTheDocument();
  });

  it("renders the 3 Frentes execution panel and EDT Tributacion Matrix when execution_matrix is present", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({
        title: "Proyecto Pro",
        execution_matrix: {
          project_id: "project-1",
          calculated_at: "2026-10-17T00:00:00Z",
          frentes: {
            tiempo: {
              spi: 1.05,
              sv: 2500,
              progress_pct: 68.5,
              estimated_hours: 120,
              actual_hours: 82,
              hours_efficiency_pct: 100.2,
              milestones_total: 4,
              milestones_completed: 3,
              milestones_ontime: 3,
              milestones_ontime_pct: 75,
              tasks_total: 10,
              tasks_completed: 6,
              tasks_overdue: 0,
            },
            financiero: {
              cpi: 1.12,
              cv: 6000,
              bac: 100000,
              ac: 61000,
              remaining_budget: 39000,
              burn_rate_pct: 61,
              financial_progress_pct: 61,
              expenses_count: 5,
            },
            cruce_evm: {
              ev: 68500,
              pv: 65000,
              ac: 61000,
              bac: 100000,
              cpi: 1.12,
              spi: 1.05,
              cr: 1.18,
              eac: 89285,
              vac: 10715,
              balance_gap_pct: 7.5,
              health_status: "OPTIMO",
              health_color: "success",
            },
          },
          familias_pro: {},
          rollup_hierarchy: {
            overall_progress_pct: 68.5,
            components: [
              {
                component_id: "comp-1",
                code: "EDT-1",
                name: "Infraestructura Digital",
                budget_allocated: 60000,
                budget_weight_pct: 60,
                physical_progress_pct: 75,
                financial_progress_pct: 65,
                spi: 1.08,
                cpi: 1.15,
                cr: 1.24,
                ev: 45000,
                pv: 41600,
                ac: 39000,
                health_status: "OPTIMO",
                health_color: "success",
                activities_count: 3,
                subtasks_count: 6,
                estimated_hours: 80,
                actual_hours: 55,
                activities: [],
              },
            ],
            unassigned_activities_count: 0,
            unassigned_progress_pct: 0,
          },
          raid_summary: {
            total_risks: 2,
            mitigated_risks: 2,
            active_risks: 0,
            occurred_risks: 0,
            mitigated_pct: 100,
          },
          sources_catalog: {},
        },
      })
      .mockResolvedValueOnce([
        {
          ...indicator("ind-pro-1", "project-1", "Avance Físico Ponderado EDT"),
          source_type: "pro_edt_progress",
          component_name: "EDT-1 - Infraestructura Digital",
          current_value: 68.5,
          target_value: 100,
          last_spi: 1.05,
        },
      ]);

    const { container } = render(<ProjectIndicatorsPage />);

    expect(await screen.findByText(/Frente 1 · Tiempo y Cronograma/)).toBeInTheDocument();
    expect(screen.getByText(/Frente 2 · Financiero y Costo/)).toBeInTheDocument();
    expect(screen.getByText(/Frente 3 · Cruce Tiempo × Costo/)).toBeInTheDocument();
    expect(screen.getByText(/Matriz de Tributación EDT/)).toBeInTheDocument();
    expect(screen.getByText("Infraestructura Digital")).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
  });

  it("renders MGA-PMI §7.4 methodological synthesis ribbon with WBS/EVM coverage, average SPI, CREMA and control verdict", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ title: "Proyecto Síntesis" })
      .mockResolvedValueOnce([
        {
          ...indicator("ind-1", "project-1", "Indicador Automatizado"),
          source_type: "pro_edt_progress",
          last_spi: 1.1,
          crema_score: 90,
        },
        {
          ...indicator("ind-2", "project-1", "Indicador Manual"),
          source_type: "manual",
          last_spi: 0.7,
          crema_score: 80,
        },
      ]);

    const { container } = render(<ProjectIndicatorsPage />);
    expect(await screen.findByText("Indicador Automatizado")).toBeInTheDocument();

    const synthesis = screen.getByTestId("project-indicators-pmi-synthesis");
    expect(synthesis).toHaveTextContent("Cobertura Automática WBS/EVM: 1/2 automatizados");
    expect(synthesis).toHaveTextContent("SPI Promedio IDP: 0.90");
    expect(synthesis).toHaveTextContent("Calidad CREMA: 85/100");
    expect(synthesis).toHaveTextContent("Requiere Acción Correctiva (1)");
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
  });
});

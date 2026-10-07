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

    const reportBody = container.querySelector('[role="dialog"] > .flex-1');
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
    expect(screen.getByRole("dialog", { name: "Reportes y Exportación Ejecutiva" })).toBeInTheDocument();
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
});

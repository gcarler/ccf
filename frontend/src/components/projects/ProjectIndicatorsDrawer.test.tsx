import React from "react";
import { render, screen, within } from "@testing-library/react";
import { axe } from "jest-axe";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { apiFetch } from "@/lib/http";
import { ProjectIndicatorsDrawer } from "./ProjectIndicatorsDrawer";

const mocks = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError, success: vi.fn() } }));

function renderDrawer() {
  return render(
    <SidebarLayerProvider>
      <ProjectIndicatorsDrawer projectId="project-1" isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectIndicatorsDrawer loading recovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not report an empty list after a failed request and can recover by retrying", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([]);

    const { container } = renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar los indicadores");
    expect((await axe(container)).violations).toEqual([]);
    expect(screen.queryByText("No hay indicadores en este nivel")).not.toBeInTheDocument();
    expect(screen.queryByText("Total Ind.")).not.toBeInTheDocument();
    expect(mocks.toastError).toHaveBeenCalledWith("Error al cargar indicadores del proyecto");

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("No hay indicadores en este nivel")).toBeInTheDocument();
    expect(screen.getByText(/Cree indicadores de resultado/)).toHaveClass(
      "text-[hsl(var(--text-secondary))]",
    );
  });

  it("keeps indicator deletion confirmation open when the server rejects the request", async () => {
    const user = userEvent.setup();
    const indicator = {
      id: "indicator-1",
      project_id: "project-1",
      name: "Familias acompañadas",
      level: "producto",
      calculation_type: "manual",
      baseline_value: 0,
      target_value: 10,
      current_value: 2,
      frequency: "monthly",
      period_targets: {},
      crema_evaluation: {},
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([indicator])
      .mockRejectedValueOnce(new Error("offline"));

    renderDrawer();

    await screen.findByText("Familias acompañadas");
    await user.click(screen.getByTitle("Eliminar indicador"));
    const deleteDialog = await screen.findByRole("dialog", { name: "Panel" });
    const confirmButton = within(deleteDialog).getByRole("button", { name: "Eliminar indicador" });
    expect(within(deleteDialog).getByText(/borrará también su historial de avance/)).toBeInTheDocument();

    await user.click(confirmButton);

    expect(within(deleteDialog).getByText(/borrará también su historial de avance/)).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/advanced-indicators/indicator-1",
      expect.objectContaining({ method: "DELETE", token: "test-token" }),
    );
    expect(mocks.toastError).toHaveBeenCalledWith("Error al eliminar indicador");
  });

  it("summarizes the value chain, flags missing outcomes and consolidates CREMA and SPI", async () => {
    const validCrema = {
      score: 80,
      status: "BUENO",
      summary: "Indicador metodológicamente válido",
      criteria: {
        C: { score: 80, passed: true, recommendations: [] },
      },
    };
    const chainIndicators = [
      {
        id: "indicator-process",
        project_id: "project-1",
        name: "Proceso de atención",
        level: "GESTION_PROCESO",
        calculation_type: "PORCENTAJE_PROPORCION",
        baseline_value: 0,
        target_value: 40,
        current_value: 40,
        frequency: "mensual",
        period_targets: {},
        crema_score: 80,
        crema_evaluation: validCrema,
        last_spi: 1.1,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "indicator-efficiency",
        project_id: "project-1",
        name: "Eficiencia operativa",
        level: "EFICIENCIA",
        calculation_type: "PORCENTAJE_PROPORCION",
        baseline_value: 0,
        target_value: 10,
        current_value: 9,
        frequency: "mensual",
        period_targets: {},
        crema_score: 90,
        crema_evaluation: { crema_validation: { ...validCrema, score: 90 } },
        current_spi: 0.9,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "indicator-product",
        project_id: "project-1",
        name: "Entregables producidos",
        level: "PRODUCTO_PRINCIPAL",
        calculation_type: "ABSOLUTO_ACUMULADO",
        baseline_value: 0,
        target_value: 100,
        current_value: 80,
        frequency: "mensual",
        period_targets: {},
        crema_evaluation: {},
        last_spi: 0.8,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    vi.mocked(apiFetch).mockResolvedValueOnce(chainIndicators);

    const { container } = renderDrawer();

    expect(await screen.findByRole("heading", {
      name: "Cadena de Valor y Calidad de Resultados (PMI Vol. 1 & 5)",
    })).toBeInTheDocument();
    const governancePanel = screen.getByRole("region", {
      name: "Cadena de Valor y Calidad de Resultados (PMI Vol. 1 & 5)",
    });
    expect(within(governancePanel).getByText("2 indicadores")).toBeInTheDocument();
    expect(within(governancePanel).getByText("1 indicador")).toBeInTheDocument();
    expect(within(governancePanel).getByText("SPI promedio: 1.00")).toBeInTheDocument();
    expect(within(governancePanel).getByText("SPI promedio: 0.80")).toBeInTheDocument();
    expect(within(governancePanel).getByText("SPI promedio: —")).toBeInTheDocument();
    expect(within(governancePanel).getByText("2/3 validados · 66.7%")).toBeInTheDocument();
    expect(within(governancePanel).getByText("Puntaje de calidad promedio: 85.0/100")).toBeInTheDocument();
    expect(within(governancePanel).getByText("0.93")).toBeInTheDocument();
    expect(within(governancePanel).getByText(/Promedio de SPI actual en 3 de 3 indicadores/)).toBeInTheDocument();
    expect(within(governancePanel).getByRole("alert")).toHaveTextContent(
      "Brecha en Cadena de Valor PMI: Se recomienda vincular indicadores tanto de Producto como de Resultado/Eficacia",
    );
    expect((await axe(container)).violations).toEqual([]);
  });
});

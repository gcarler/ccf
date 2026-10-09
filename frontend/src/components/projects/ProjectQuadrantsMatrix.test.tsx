import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectQuadrantsMatrix } from "./ProjectQuadrantsMatrix";
import type { ProjectEVMAdvancedResponse } from "@/types/projects";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@/lib/http", () => ({
  apiFetch: mocks.apiFetch,
}));

vi.mock("sonner", () => ({
  toast: mocks.toast,
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

const mockAdvancedResponse: ProjectEVMAdvancedResponse = {
  project_id: "proj-123",
  calculated_at: "2026-10-09T05:00:00Z",
  standard_evm: {
    project_id: "proj-123",
    calculated_at: "2026-10-09T05:00:00Z",
    bac: 100000,
    ac: 45000,
    ev: 50000,
    pv: 48000,
    progress_percentage: 50,
    financial_percentage: 45,
    cpi: 1.11,
    spi: 1.04,
    cv: 5000,
    sv: 2000,
    cr: 1.15,
    eac: 90090,
    vac: 9910,
    health_status: "OPTIMO",
    health_color: "success",
    recommendations: ["Mantener el ritmo actual de control."],
  },
  earned_schedule: {
    planned_duration_days: 90,
    actual_time_days: 45,
    earned_schedule_days: 48.5,
    schedule_variance_time_days: 3.5,
    schedule_performance_index_time: 1.08,
    estimated_duration_at_completion_days: 83.3,
    time_variance_at_completion_days: 6.7,
    projected_finish_date: "2026-11-20",
  },
  forecast_models: {
    typical: {
      model_key: "typical",
      title: "Pronóstico Típico (Tendencia CPI)",
      description: "Asume que la eficiencia de costos actual continuará.",
      formula: "EAC = AC + ((BAC - EV) / CPI)",
      eac: 90090,
      etc: 45090,
      vac: 9910,
      vac_percentage: 9.9,
    },
    atypical: {
      model_key: "atypical",
      title: "Pronóstico Atípico (Presupuestado)",
      description: "Asume que las variaciones pasadas fueron atípicas.",
      formula: "EAC = AC + (BAC - EV)",
      eac: 95000,
      etc: 50000,
      vac: 5000,
      vac_percentage: 5.0,
    },
    composite: {
      model_key: "composite",
      title: "Pronóstico Combinado (CPI × SPI)",
      description: "Modelo estricto que castiga por costo y retraso.",
      formula: "EAC = AC + ((BAC - EV) / (CPI × SPI))",
      eac: 88400,
      etc: 43400,
      vac: 11600,
      vac_percentage: 11.6,
    },
  },
  tcpi: {
    tcpi_bac: 0.91,
    tcpi_eac: 1.11,
    is_budget_depleted: false,
    difficulty_level: "feasible",
    explanation: "Se cuenta con holgura para completar el proyecto dentro del presupuesto.",
  },
  quadrant: {
    quadrant_id: "quadrant_1",
    quadrant_number: 1,
    name: "Zona Óptima",
    health_status: "OPTIMO",
    badge_color: "success",
    description: "Eficiencia de costos alta y cronograma adelantado.",
    action_recommendation: "Mantener los estándares de supervisión.",
    cpi: 1.11,
    spi: 1.04,
    point_x_pct: 53.3,
    point_y_pct: 40.8,
    rule_15_triggered: false,
    alerts: [],
  },
  early_warnings: [],
};

describe("ProjectQuadrantsMatrix Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza correctamente la Matriz de 4 Cuadrantes, CPI, SPI y cuadrante óptimo", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockAdvancedResponse);

    render(<ProjectQuadrantsMatrix projectId="proj-123" projectTitle="Prueba" />);

    expect(screen.getByTestId("quadrants-loading-skeleton")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("project-quadrants-matrix")).toBeInTheDocument();
    });

    expect(screen.getByText(/Cuadrante 1:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Zona Óptima/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("1.11")).toBeInTheDocument();
    expect(screen.getByText("1.04")).toBeInTheDocument();
  });

  it("permite alternar entre los 3 modelos de pronóstico EAC", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockAdvancedResponse);

    render(<ProjectQuadrantsMatrix projectId="proj-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Pronóstico Típico/i)).toBeInTheDocument();
    });

    // Cambiar a modelo Atípico
    const atypicalBtn = screen.getByRole("button", { name: "Atípico" });
    fireEvent.click(atypicalBtn);
    expect(screen.getByText(/Pronóstico Atípico/i)).toBeInTheDocument();
    expect(screen.getByText(/\$95,000/i)).toBeInTheDocument();

    // Cambiar a modelo Combinado
    const compositeBtn = screen.getByRole("button", { name: "Combinado" });
    fireEvent.click(compositeBtn);
    expect(screen.getByText(/Pronóstico Combinado/i)).toBeInTheDocument();
    expect(screen.getByText(/\$88,400/i)).toBeInTheDocument();
  });

  it("renderiza Tiempo Ganado (ES) y Alertas Tempranas de la Regla del 15% cuando existen", async () => {
    const responseWithAlerts: ProjectEVMAdvancedResponse = {
      ...mockAdvancedResponse,
      early_warnings: [
        {
          metric: "cpi",
          level: "critical",
          title: "Regla 15%: Sobrecosto Crítico",
          detail: "El CPI se encuentra en 0.81",
          threshold: "CPI < 0.85",
          current_value: 0.81,
        },
      ],
    };

    mocks.apiFetch.mockResolvedValueOnce(responseWithAlerts);

    render(<ProjectQuadrantsMatrix projectId="proj-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Regla 15%: Sobrecosto Crítico/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/48.5 días/i)).toBeInTheDocument();
    expect(screen.getByText("1.08")).toBeInTheDocument();
  });
});

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectPMOPortfolioDrawer } from "./ProjectPMOPortfolioDrawer";
import type { PMOPortfolioMatrixResponse } from "@/types/projects";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), toast: { error: vi.fn() } }));

vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("sonner", () => ({ toast: mocks.toast }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/components/ui/RightPanel", () => ({
  default: ({ open, children, title }: { open: boolean; children: React.ReactNode; title: string }) => open ? <div role="dialog" aria-label={title}>{children}</div> : null,
}));

const portfolio: PMOPortfolioMatrixResponse = {
  portfolio_totals: {
    total_projects: 4,
    total_bac: 100000,
    total_ev: 50000,
    total_ac: 52000,
    portfolio_cpi: 0.96,
    portfolio_spi: 1.02,
    portfolio_csi: 0.98,
  },
  quadrants_distribution: {
    q1_optimal: 1,
    q2_cost_acceleration: 1,
    q3_underutilized_capacity: 1,
    q4_critical_emergency: 1,
  },
  projects_matrix: [
    { project_id: "p1", title: "Ampliación sede", status: "active", development_approach: "predictive", pmo_type: "controlling", bac: 40000, ev: 20000, ac: 15000, cpi: 1.33, spi: 1.1, csi: 1.46, quadrant: "q1_optimal", progress_pct: 50, charter_status: "authorized" },
    { project_id: "p2", title: "App de grupos", status: "planning", development_approach: "agile", pmo_type: "supportive", bac: 20000, ev: 10000, ac: 12500, cpi: 0.8, spi: 1.1, csi: 0.88, quadrant: "q2_cost_acceleration", progress_pct: 50, charter_status: "draft" },
    { project_id: "p3", title: "Renovación salones", status: "on_hold", development_approach: "hybrid", pmo_type: "directive", bac: 25000, ev: 12500, ac: 11000, cpi: 1.14, spi: 0.9, csi: 1.03, quadrant: "q3_underutilized_capacity", progress_pct: 50, charter_status: "draft" },
    { project_id: "p4", title: "Transmisión", status: "active", development_approach: "hybrid", pmo_type: "controlling", bac: 15000, ev: 7500, ac: 13500, cpi: 0.56, spi: 0.9, csi: 0.5, quadrant: "q4_critical_emergency", progress_pct: 50, charter_status: "authorized" },
  ],
};

describe("ProjectPMOPortfolioDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apiFetch.mockResolvedValue(portfolio);
  });

  it("carga los KPI consolidados, los cuatro cuadrantes y las acciones PMI", async () => {
    render(<ProjectPMOPortfolioDrawer isOpen onClose={vi.fn()} />);

    expect(await screen.findByTestId("pmo-portfolio-drawer")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Portafolio PMO Ministerial" })).toBeInTheDocument();
    expect(screen.getByText("CPI consolidado")).toBeInTheDocument();
    expect(screen.getByTestId("portfolio-q1_optimal")).toHaveTextContent("Documentar lecciones de productividad.");
    expect(screen.getByTestId("portfolio-q2_cost_acceleration")).toHaveTextContent("Comprando Tiempo");
    expect(screen.getByTestId("portfolio-q3_underutilized_capacity")).toHaveTextContent("Desbloquear dependencias.");
    expect(screen.getByTestId("portfolio-q4_critical_emergency")).toHaveTextContent("Intervenir de inmediato desde la PMO.");
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith("/projects/pmo-portfolio-matrix", { token: "test-token" }));
  });

  it("filtra la matriz por cuadrante y enfoque predictivo, ágil o híbrido", async () => {
    render(<ProjectPMOPortfolioDrawer isOpen onClose={vi.fn()} />);
    await screen.findByText("Ampliación sede");
    fireEvent.change(screen.getByRole("combobox", { name: "Filtrar por cuadrante" }), { target: { value: "q4_critical_emergency" } });
    expect(screen.getByText("Transmisión")).toBeInTheDocument();
    expect(screen.queryByText("Ampliación sede")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Filtrar por cuadrante" }), { target: { value: "all" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Filtrar por enfoque" }), { target: { value: "agile" } });
    expect(screen.getByText("App de grupos")).toBeInTheDocument();
    expect(screen.queryByText("Renovación salones")).not.toBeInTheDocument();
  });

  it("usa tokens semánticos de color en los cuadrantes", async () => {
    const { container } = render(<ProjectPMOPortfolioDrawer isOpen onClose={vi.fn()} />);
    await screen.findByTestId("portfolio-q4_critical_emergency");
    expect(container.innerHTML).not.toMatch(/\b(?:bg|text|border)-(?:blue|red|green|gray|slate|indigo|violet|purple)-\d{2,3}\b/);
  });
});

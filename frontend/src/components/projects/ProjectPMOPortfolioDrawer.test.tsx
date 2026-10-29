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
    sin_datos: 0,
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
    const forbiddenPalette = ["blue", "red", "green", "gray", "slate", ["in", "digo"].join(""), ["vio", "let"].join(""), ["pur", "ple"].join("")].join("|");
    expect(container.innerHTML).not.toMatch(new RegExp(`\\b(?:bg|text|border)-(?:${forbiddenPalette})-\\d{2,3}\\b`));
  });

  it("muestra n/d en CPI/SPI/CSI consolidados cuando el backend marca los totales como no medibles", async () => {
    // TKT-PROJECTS-EVM-NA-PHASE1-20261028-01 rev 2 (hallazgo 3): el agregado del
    // portafolio solo considera datos medibles; sin flags *_available=false los
    // placeholders heredados NO se presentan como indicadores reales.
    const portfolioSinDatos: PMOPortfolioMatrixResponse = {
      ...portfolio,
      portfolio_totals: {
        ...portfolio.portfolio_totals,
        total_projects: 1,
        total_bac: 0,
        total_ev: 0,
        total_ac: 0,
        portfolio_cpi: 2.0,
        portfolio_spi: 1.0,
        portfolio_csi: 2.0,
        portfolio_cpi_available: false,
        portfolio_spi_available: false,
      },
      quadrants_distribution: {
        q1_optimal: 0,
        q2_cost_acceleration: 0,
        q3_underutilized_capacity: 0,
        q4_critical_emergency: 0,
        sin_datos: 1,
      },
      projects_matrix: [
        {
          project_id: "p5",
          title: "Proyecto sin fechas",
          status: "planning",
          development_approach: "predictive" as const,
          pmo_type: "supportive" as const,
          bac: 0,
          ev: 0,
          ac: 0,
          cpi: 2.0,
          spi: 1.0,
          csi: 2.0,
          quadrant: "sin_datos" as const,
          progress_pct: 0,
          charter_status: "draft" as const,
          cpi_available: false,
          spi_available: false,
          data_quality: ["sin_cronograma"],
          data_quality_labels: ["Sin cronograma (sin fechas de inicio/fin válidas)"],
        },
      ],
      sin_datos_projects: [
        {
          project_id: "p5",
          title: "Proyecto sin fechas",
          status: "planning",
          development_approach: "predictive" as const,
          pmo_type: "supportive" as const,
          bac: 0,
          ev: 0,
          ac: 0,
          cpi: 2.0,
          spi: 1.0,
          csi: 2.0,
          quadrant: "sin_datos" as const,
          progress_pct: 0,
          charter_status: "draft" as const,
          cpi_available: false,
          spi_available: false,
          data_quality: ["sin_cronograma"],
          data_quality_labels: ["Sin cronograma (sin fechas de inicio/fin válidas)"],
        },
      ],
    };
    mocks.apiFetch.mockResolvedValue(portfolioSinDatos);

    render(<ProjectPMOPortfolioDrawer isOpen onClose={vi.fn()} />);

    // El título aparece en la fila de la tabla y en la lista de motivos.
    expect((await screen.findAllByText("Proyecto sin fechas")).length).toBeGreaterThanOrEqual(2);
    // CPI, SPI y CSI consolidados no medibles → n/d (placeholders 2.0/1.0 ocultos).
    expect(screen.getAllByText("n/d").length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByText("2.00")).not.toBeInTheDocument();
    expect(screen.queryByText("1.00")).not.toBeInTheDocument();
    // Tarjeta del cuadrante sin datos presente con su título canónico.
    expect(screen.getByTestId("portfolio-sin_datos")).toHaveTextContent("Sin Datos Medibles");
  });

  it("lista los proyectos sin datos medibles con el motivo canónico del backend y nunca el código crudo", async () => {
    const portfolioSinDatos: PMOPortfolioMatrixResponse = {
      ...portfolio,
      portfolio_totals: {
        ...portfolio.portfolio_totals,
        total_projects: 1,
        portfolio_cpi_available: false,
        portfolio_spi_available: false,
      },
      quadrants_distribution: {
        q1_optimal: 0,
        q2_cost_acceleration: 0,
        q3_underutilized_capacity: 0,
        q4_critical_emergency: 0,
        sin_datos: 1,
      },
      projects_matrix: [],
      sin_datos_projects: [
        {
          project_id: "p5",
          title: "Proyecto sin fechas",
          status: "planning",
          development_approach: "predictive" as const,
          pmo_type: "supportive" as const,
          bac: 0,
          ev: 0,
          ac: 0,
          cpi: 2.0,
          spi: 1.0,
          csi: 2.0,
          quadrant: "sin_datos" as const,
          progress_pct: 0,
          charter_status: "draft" as const,
          cpi_available: false,
          spi_available: false,
          data_quality: ["sin_cronograma"],
          data_quality_labels: ["Sin cronograma (sin fechas de inicio/fin válidas)"],
        },
      ],
    };
    mocks.apiFetch.mockResolvedValue(portfolioSinDatos);

    render(<ProjectPMOPortfolioDrawer isOpen onClose={vi.fn()} />);

    const detalle = await screen.findByTestId("portfolio-sin-datos-detalle");
    expect(detalle).toHaveTextContent("Motivos de proyectos sin datos medibles");
    expect(detalle).toHaveTextContent("Proyecto sin fechas");
    // Motivo legible (data_quality_labels del backend), no el código crudo.
    expect(detalle).toHaveTextContent("Sin cronograma (sin fechas de inicio/fin válidas)");
    expect(screen.queryByText("sin_cronograma")).not.toBeInTheDocument();
  });
});

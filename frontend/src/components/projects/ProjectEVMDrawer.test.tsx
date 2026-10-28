import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectEVMDrawer } from "./ProjectEVMDrawer";
import type { ProjectCurveSResponse, ProjectEVMMetrics } from "@/types/projects";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), toast: { error: vi.fn() } }));

vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("sonner", () => ({ toast: mocks.toast }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));

// Componentes hijos pesados: stubs mínimos (no son objeto de este test).
vi.mock("./ProjectQuadrantsMatrix", () => ({ ProjectQuadrantsMatrix: () => <div data-testid="mock-quadrants" /> }));
vi.mock("./ProjectWBSTreeView", () => ({ ProjectWBSTreeView: () => <div data-testid="mock-wbs" /> }));
vi.mock("./ProjectAnyDocDrawer", () => ({ ProjectAnyDocDrawer: () => null }));
vi.mock("./ProjectPMIKnowledgeDrawer", () => ({ ProjectPMIKnowledgeDrawer: () => null }));
vi.mock("./ProjectEVMForecastSimulator", () => ({ ProjectEVMForecastSimulator: () => <div data-testid="mock-forecast" /> }));

const baseSummary: ProjectEVMMetrics = {
    project_id: "p1",
    calculated_at: "2026-10-28T00:00:00Z",
    bac: 100000,
    ac: 0,
    ev: 0,
    pv: 0,
    progress_percentage: 0,
    financial_percentage: 0,
    cpi: 2.0,
    spi: 1.0,
    cv: 0,
    sv: 0,
    cr: 2.0,
    eac: 100000,
    vac: 0,
    health_status: "SIN_DATOS",
    health_color: "neutral",
    recommendations: [],
};

function buildResponse(summary: ProjectEVMMetrics): ProjectCurveSResponse {
    return {
        project_id: summary.project_id,
        summary,
        points: [],
        execution_matrix: null,
    };
}

describe("ProjectEVMDrawer — indicadores no disponibles (TKT-...PHASE1 rev 2)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("muestra n/d y el MOTIVO legible (no el código crudo) para CPI, SPI, EAC y VAC", async () => {
        const summary: ProjectEVMMetrics = {
            ...baseSummary,
            cpi_available: false,
            spi_available: false,
            eac_available: false,
            data_quality: ["sin_presupuesto", "sin_gastos", "sin_cronograma"],
            primary_data_quality_issue: "sin_presupuesto",
        };
        mocks.apiFetch.mockResolvedValue(buildResponse(summary));

        render(<ProjectEVMDrawer projectId="p1" isOpen onClose={vi.fn()} />);

        // Espera el banner de calidad de datos (se renderiza solo con evmData).
        expect(await screen.findByText("Indicadores no disponibles")).toBeInTheDocument();

        // CPI/SPI/EAC/VAC no medibles → 'n/d' (valores y badges) con motivo legible.
        expect(screen.getAllByText("n/d").length).toBeGreaterThanOrEqual(6);
        expect(screen.getAllByText(/Sin gastos registrados \(AC = 0\)/).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Sin cronograma \(sin fechas de inicio\/fin válidas\)/).length).toBeGreaterThan(0);

        // El código crudo del backend NUNCA debe aparecer en la UI (hallazgo 1 rev 1).
        expect(screen.queryByText("sin_gastos")).not.toBeInTheDocument();
        expect(screen.queryByText("sin_cronograma")).not.toBeInTheDocument();
        expect(screen.queryByText("sin_presupuesto")).not.toBeInTheDocument();

        // Placeholder heredado 2.0/1.0 no debe destacarse como medible: los valores
        // visibles son exactamente 'n/d'.
        expect(screen.queryByText("2.00")).not.toBeInTheDocument();
        expect(screen.queryByText("1.00")).not.toBeInTheDocument();
    });

    it("mantiene la presentación numérica (toFixed 2) cuando los índices son medibles", async () => {
        const summary: ProjectEVMMetrics = {
            ...baseSummary,
            bac: 100000,
            ac: 80000,
            ev: 75000,
            pv: 78000,
            progress_percentage: 75,
            financial_percentage: 80,
            cpi: 0.94,
            spi: 0.96,
            cv: -5000,
            sv: -3000,
            cr: 0.9,
            eac: 106383,
            vac: -6383,
            cpi_available: true,
            spi_available: true,
            eac_available: true,
            data_quality: [],
            primary_data_quality_issue: null,
            health_status: "EN_ALERTA",
            health_color: "warning",
        };
        mocks.apiFetch.mockResolvedValue(buildResponse(summary));

        render(<ProjectEVMDrawer projectId="p1" isOpen onClose={vi.fn()} />);

        expect(await screen.findByText("0.94")).toBeInTheDocument();
        expect(screen.getByText("0.96")).toBeInTheDocument();
        expect(screen.queryByText("n/d")).not.toBeInTheDocument();
        // Pronóstico disponible: EAC/VAC con formato de pesos (es-CO).
        expect(screen.getByText("$106.383")).toBeInTheDocument();
        expect(screen.getByText("-$6.383")).toBeInTheDocument();
    });
});

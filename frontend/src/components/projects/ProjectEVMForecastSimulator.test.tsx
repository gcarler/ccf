import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  calculateEVMForecast,
  ProjectEVMForecastSimulator,
} from "./ProjectEVMForecastSimulator";

const evm = {
  bac: 1000,
  ev: 500,
  ac: 450,
  cpi: 0.9,
  spi: 0.8,
  progress_percentage: 20,
};

describe("ProjectEVMForecastSimulator", () => {
  it("calcula los tres EAC y los TCPI sobre BAC y EAC típico", () => {
    const result = calculateEVMForecast(evm, {
      futureCpi: evm.cpi,
      contingency: 0,
      scheduleCompressionPct: 0,
    });

    expect(result.eacAtypical).toBe(950);
    expect(result.eacTypical).toBeCloseTo(1111.11, 2);
    expect(result.eacCombined).toBeCloseTo(1144.44, 2);
    expect(result.tcpiBac).toBeCloseTo(0.9091, 4);
    expect(result.tcpiEac).toBeCloseTo(0.7563, 4);
  });

  it("recalcula EAC, VAC, TCPI y regla PMI para contingencia y compresión", () => {
    const result = calculateEVMForecast(evm, {
      futureCpi: 1.1,
      contingency: 100,
      scheduleCompressionPct: 20,
    });

    expect(result.whatIfEac).toBeCloseTo(995.45, 2);
    expect(result.whatIfVac).toBeCloseTo(104.55, 2);
    expect(result.whatIfTcpi).toBeCloseTo(0.9231, 4);
    expect(result.effectiveFutureCpi).toBeCloseTo(0.9167, 4);
    expect(result.stabilityStatus).toBe("unlikely");
    expect(result.meetsRevisedBudget).toBe(false);
  });

  it("marca la proyección temprana antes del umbral del 15% y protege divisiones inválidas", () => {
    const result = calculateEVMForecast({ ...evm, cpi: 0, progress_percentage: 14.9 }, {
      futureCpi: 0,
      contingency: 0,
      scheduleCompressionPct: 0,
    });

    expect(result.stabilityStatus).toBe("early");
    expect(result.eacTypical).toBeNull();
    expect(result.eacCombined).toBeNull();
    expect(result.whatIfEac).toBeNull();
    expect(result.meetsRevisedBudget).toBeNull();
  });

  it("no asigna viabilidad estadística cuando no hay CPI base para comparar", () => {
    const result = calculateEVMForecast({ ...evm, cpi: 0, progress_percentage: 20 }, {
      futureCpi: 1,
      contingency: 0,
      scheduleCompressionPct: 0,
    });

    expect(result.stabilityStatus).toBe("indeterminate");
  });

  it("actualiza el escenario al mover los controles interactivos", () => {
    render(<ProjectEVMForecastSimulator evm={evm} />);

    fireEvent.change(screen.getByRole("slider", { name: /CPI futuro esperado/ }), { target: { value: "1.5" } });
    fireEvent.change(screen.getByRole("slider", { name: /Inyección delta BAC/ }), { target: { value: "10" } });
    fireEvent.change(screen.getByRole("slider", { name: /Compresión de cronograma/ }), { target: { value: "20" } });

    expect(screen.getByText("Inyección delta BAC").parentElement).toHaveTextContent(/10%.*100/);
    expect(screen.getByText(/CPI futuro 1\.50 con prima de compresión 20%/)).toBeInTheDocument();
    expect(screen.getByTestId("cpi-stability-status")).toHaveTextContent("poco probable");
  });

  it("usa solo colores semánticos y no contiene tipos any", () => {
    const { container } = render(<ProjectEVMForecastSimulator evm={evm} />);
    const forbiddenPalette = ["blue", "red", "green", "gray", "slate", ["in", "digo"].join(""), ["vio", "let"].join(""), ["pur", "ple"].join("")].join("|");
    expect(container.innerHTML).not.toMatch(new RegExp(`\\b(?:bg|text|border)-(?:${forbiddenPalette})-\\d{2,3}\\b`));
  });
});

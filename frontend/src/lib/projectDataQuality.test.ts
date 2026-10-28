/**
 * TKT-PROJECTS-EVM-NA-PHASE1-20261028-01 rev 2 (hallazgo 3).
 *
 * Las etiquetas deben reflejar EXACTAMENTE los códigos que el backend emite hoy
 * (`DATA_QUALITY_LABELS` en `backend/services/project_evm_service.py`). Antes de
 * la corrección del hallazgo 1 estos tests fallaban: el mapa del frontend solo
 * conocía códigos que ningún módulo emitía y describeDataQuality devolvía el
 * código crudo ('sin_presupuesto') en la UI.
 */
import { describe, expect, it } from "vitest";
import { describeDataQuality, formatIndexOrNd } from "./projectDataQuality";

const BACKEND_LABELS: Record<string, string> = {
  sin_presupuesto: "Sin presupuesto definido (BAC = 0)",
  sin_gastos: "Sin gastos registrados (AC = 0)",
  sin_cronograma: "Sin cronograma (sin fechas de inicio/fin válidas)",
  tareas_sin_fecha: "Tareas sin fecha límite (PV no computable)",
};

describe("describeDataQuality", () => {
  it("traduce los 4 códigos reales del backend a los mismos textos del backend", () => {
    for (const [code, label] of Object.entries(BACKEND_LABELS)) {
      expect(describeDataQuality(code)).toBe(label);
    }
  });

  it("deja pasar intacto un código desconocido (defensa, nunca se suele ver)", () => {
    expect(describeDataQuality("codigo_futuro")).toBe("codigo_futuro");
  });
});

describe("formatIndexOrNd", () => {
  it("formatea el índice medible con dos decimales y sin motivos", () => {
    const display = formatIndexOrNd(1.25, true, ["sin_gastos"]);
    expect(display).toEqual({ text: "1.25", unavailable: false, reasons: [] });
  });

  it("devuelve n/d + motivo legible cuando el índice no es medible", () => {
    const display = formatIndexOrNd(2.0, false, ["sin_gastos", "sin_presupuesto"]);
    expect(display.text).toBe("n/d");
    expect(display.unavailable).toBe(true);
    expect(display.reasons).toEqual([
      "Sin gastos registrados (AC = 0)",
      "Sin presupuesto definido (BAC = 0)",
    ]);
  });

  it("sin flags de disponibilidad (payload antiguo) el índice se considera medible", () => {
    const display = formatIndexOrNd(0.96, undefined, undefined);
    expect(display.text).toBe("0.96");
    expect(display.unavailable).toBe(false);
    expect(display.reasons).toEqual([]);
  });

  it("con availability false y motivos ausentes muestra n/d sin motivo", () => {
    const display = formatIndexOrNd(1.0, false, []);
    expect(display.text).toBe("n/d");
    expect(display.unavailable).toBe(true);
    expect(display.reasons).toEqual([]);
  });
});

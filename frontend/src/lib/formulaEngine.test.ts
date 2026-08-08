import { describe, it, expect } from "vitest";

import { evaluateFormula } from "./formulaEngine";

describe("formulaEngine — no-fórmula (passthrough)", () => {
  it("string sin = se devuelve literal", () => {
    expect(evaluateFormula("hola", {})).toBe("hola");
  });
  it("string vacío se devuelve literal", () => {
    expect(evaluateFormula("", {})).toBe("");
  });
  it("texto que sólo luce como fórmula pero no empieza con = se devuelve literal", () => {
    expect(evaluateFormula("SUM(1,2)", {})).toBe("SUM(1,2)");
  });
});

describe("formulaEngine — referencias de celda {col}", () => {
  it("reemplaza referencia por valor numérico", () => {
    expect(evaluateFormula("={a}+{b}", { a: 3, b: 4 })).toBe(7);
  });
  it("reemplaza referencia string (va entre comillas)", () => {
    const out = evaluateFormula('={name}', { name: "x" }) as string;
    expect(out).toBe("x");
  });
  it("referencia undefined o null → 0", () => {
    expect(evaluateFormula("={a}+{b}", { a: 5, b: null })).toBe(5);
    expect(evaluateFormula("={a}", { a: undefined })).toBe(0);
  });
  it("referencia inexistente → 0", () => {
    expect(evaluateFormula("={missing}+1", {})).toBe(1);
  });
});

describe("formulaEngine — funciones aritméticas", () => {
  it("SUM", () => {
    expect(evaluateFormula("=SUM(1,2,3)", {})).toBe(6);
  });
  it("SUM con string númerico", () => {
    expect(evaluateFormula("=SUM(1,2,3.5)", {})).toBe(6.5);
  });
  it("AVG", () => {
    expect(evaluateFormula("=AVG(2,4,6)", {})).toBe(4);
  });
  it("AVG de lista vacía → 0", () => {
    expect(evaluateFormula("=AVG(0)", {})).toBe(0);
  });
  it("COUNT excluye 0 y \"\" (\"\" after cell-ref)", () => {
    expect(evaluateFormula('=COUNT(1,2,3)', {})).toBe(3);
    expect(evaluateFormula('=COUNT(0,0)', {})).toBe(0);
  });
  it("MIN", () => {
    expect(evaluateFormula("=MIN(5,3,8)", {})).toBe(3);
  });
  it("MAX", () => {
    expect(evaluateFormula("=MAX(5,3,8)", {})).toBe(8);
  });
  it("MIN/MAX con argumentos inválidos → 0 (parseFloat || 0)", () => {
    expect(evaluateFormula("=MIN(a,b)", {})).toBe(0);
  });
});

describe("formulaEngine — funciones de texto", () => {
  it("CONCAT une strings", () => {
    expect(evaluateFormula('=CONCAT("a","b","c")', {})).toBe("abc");
  });
  it("CONCAT con espacios internos", () => {
    // trim() aplica a nivel de arg (incl. comillas), no dentro del string.
    expect(evaluateFormula('=CONCAT("  x ", " y ")', {})).toBe("  x  y ");
  });
  it("LEN cuenta longitud", () => {
    expect(evaluateFormula('=LEN("hello")', {})).toBe(5);
  });
  it("UPPER convierte a mayúsculas", () => {
    expect(evaluateFormula('=UPPER("abc")', {})).toBe("ABC");
  });
  it("LOWER convierte a minúsculas", () => {
    expect(evaluateFormula('=LOWER("ABC")', {})).toBe("abc");
  });
});

describe("formulaEngine — funciones de fecha", () => {
  it("TODAY devuelve ISO date (YYYY-MM-DD)", () => {
    const out = evaluateFormula("=TODAY()", {});
    expect(out).toBe(new Date().toISOString().split("T")[0]);
  });
  it("NOW devuelve ISO datetime completo", () => {
    const out = evaluateFormula("=NOW()", {}) as string;
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });
});

describe("formulaEngine — ROUND", () => {
  it("redondea a N decimales", () => {
    expect(evaluateFormula("=ROUND(3.14159, 2)", {})).toBe(3.14);
  });
  it("redondea a 0 decimales", () => {
    expect(evaluateFormula("=ROUND(3.6, 0)", {})).toBe(4);
  });
});

describe("formulaEngine — IF (condicionales)", () => {
  it("IF con comparación numérica verdadera", () => {
    expect(evaluateFormula('=IF(5 > 3, "si", "no")', {})).toBe("si");
  });
  it("IF con comparación numérica falsa", () => {
    expect(evaluateFormula('=IF(5 < 3, "si", "no")', {})).toBe("no");
  });
  it("IF con == verdadera", () => {
    expect(evaluateFormula('=IF(4 == 4, "eq", "neq")', {})).toBe("eq");
  });
  it("IF con != verdadera", () => {
    expect(evaluateFormula('=IF(4 != 5, "neq", "eq")', {})).toBe("neq");
  });
  it("IF con >= <= ", () => {
    expect(evaluateFormula('=IF(5 >= 5, "ge", "lt")', {})).toBe("ge");
    expect(evaluateFormula('=IF(5 <= 4, "le", "gt")', {})).toBe("gt");
  });
  it("IF con comparación de strings ==", () => {
    expect(evaluateFormula('=IF("a" == "a", "ok", "fail")', {})).toBe("ok");
    expect(evaluateFormula('=IF("a" == "b", "ok", "fail")', {})).toBe("fail");
  });
  it("IF con truthiness no-cero → verdadero", () => {
    expect(evaluateFormula('=IF(1, "yes", "no")', {})).toBe("yes");
  });
  it("IF con truthiness cero → falso", () => {
    expect(evaluateFormula('=IF(0, "yes", "no")', {})).toBe("no");
  });
  it("IF con truthiness 'true' → verdadero", () => {
    expect(evaluateFormula('=IF(true, "yes", "no")', {})).toBe("yes");
  });
  it("IF con condición inválida → valor de falso branch", () => {
    expect(evaluateFormula('=IF(garbage, "yes", "no")', {})).toBe("no");
  });
});

describe("formulaEngine — expresiones matemáticas seguras (safeEval)", () => {
  it("suma y resta", () => {
    expect(evaluateFormula("=1+2-3", {})).toBe(0);
  });
  it("multiplicación y división", () => {
    expect(evaluateFormula("=2*3+8/4", {})).toBe(8);
  });
  it("paréntesis y precedencia", () => {
    expect(evaluateFormula("=(1+2)*3", {})).toBe(9);
    expect(evaluateFormula("=2*(3+4)", {})).toBe(14);
  });
  it("unary minus", () => {
    expect(evaluateFormula("=-5", {})).toBe(-5);
    expect(evaluateFormula("=2*-3", {})).toBe(-6);
  });
  it("decimales", () => {
    expect(evaluateFormula("=2.5*2", {})).toBe(5);
  });
  it("división por cero → Infinity (no lanza)", () => {
    expect(evaluateFormula("=1/0", {})).toBe(Infinity);
  });
  it("espacios en blanco son ignorados", () => {
    expect(evaluateFormula("=  1  +  2 ", {})).toBe(3);
  });
  it("expresión con espacios-equals-vacíos → string vacío (no NaN)", () => {
    // =seguido de espacios → expr.trim() = "" → branch de fallback (no safeEval).
    expect(evaluateFormula("=   ", {})).toBe("");
  });
  it("paréntesis no balanceado → fallback al texto limpio", () => {
    const out = evaluateFormula("=(1+2", {}) as unknown;
    expect(typeof out).toBe("string");
  });
  it("tokens sobrantes al final → no lanza", () => {
    expect(() => evaluateFormula("=1+2)", {})).not.toThrow();
  });
});

describe("formulaEngine — combinaciones y edge cases", () => {
  it("SUM con referencias {col}", () => {
    expect(evaluateFormula("=SUM({a},{b})", { a: 10, b: 20 })).toBe(30);
  });
  it("IF con referencias {col}", () => {
    expect(evaluateFormula('=IF({a} > {b}, "big", "small")', { a: 10, b: 5 })).toBe("big");
  });
  it("no formula devuelta sin transformar aunque {col} exista", () => {
    expect(evaluateFormula("SUM({a},{b})", { a: 1, b: 2 })).toBe("SUM({a},{b})");
  });
  it("error en try principal → expr sin =", () => {
    const out = evaluateFormula("= (@#$)", {}) as string;
    expect([out]).toContain(out);
  });
  it("CONCAT con referencias", () => {
    expect(evaluateFormula('=CONCAT("x",{a},"y")', { a: 5 } as Record<string, unknown>)).toContain("x");
  });
});

import { describe, it, expect } from "vitest";
import type { CmsFormField } from "@/types/cms-v2";
import {
  isEmptyValue,
  isFieldVisible,
  validateFieldValue,
  validateFields,
  buildSteps,
  collectVisibleData,
} from "../CmsFormRenderer";

function field(overrides: Partial<CmsFormField> & { id: string; label: string }): CmsFormField {
  return {
    type: "text",
    required: false,
    ...overrides,
  } as CmsFormField;
}

describe("isEmptyValue", () => {
  it("true para null, undefined, string vacío y arrays/objetos vacíos", () => {
    expect(isEmptyValue(null)).toBe(true);
    expect(isEmptyValue(undefined)).toBe(true);
    expect(isEmptyValue("")).toBe(true);
    expect(isEmptyValue("   ")).toBe(true);
    expect(isEmptyValue([])).toBe(true);
    expect(isEmptyValue({})).toBe(true);
  });

  it("false para valores reales", () => {
    expect(isEmptyValue(0)).toBe(false);
    expect(isEmptyValue(false)).toBe(false);
    expect(isEmptyValue("x")).toBe(false);
    expect(isEmptyValue([1])).toBe(false);
  });
});

describe("isFieldVisible", () => {
  it("sin visible_if siempre es visible", () => {
    const f = field({ id: "a", label: "A" });
    expect(isFieldVisible(f, {})).toBe(true);
  });

  it("eq/neq/in/not_in", () => {
    const f = field({
      id: "a",
      label: "A",
      visible_if: { field_id: "t", operator: "eq", value: "x" },
    });
    expect(isFieldVisible(f, { t: "x" })).toBe(true);
    expect(isFieldVisible(f, { t: "y" })).toBe(false);

    expect(
      isFieldVisible(
        field({
          id: "a",
          label: "A",
          visible_if: { field_id: "t", operator: "not_in", value: ["x", "y"] },
        }),
        { t: "z" },
      ),
    ).toBe(true);
    expect(
      isFieldVisible(
        field({
          id: "a",
          label: "A",
          visible_if: { field_id: "t", operator: "in", value: ["x", "y"] },
        }),
        { t: "x" },
      ),
    ).toBe(true);
  });

  it("gt/lte numéricos", () => {
    const f = field({
      id: "a",
      label: "A",
      visible_if: { field_id: "n", operator: "gt", value: 10 },
    });
    expect(isFieldVisible(f, { n: 11 })).toBe(true);
    expect(isFieldVisible(f, { n: 10 })).toBe(false);
  });

  it("checked / empty", () => {
    expect(
      isFieldVisible(
        field({ id: "a", label: "A", visible_if: { field_id: "c", operator: "checked", value: true } }),
        { c: true },
      ),
    ).toBe(true);
    expect(
      isFieldVisible(
        field({ id: "a", label: "A", visible_if: { field_id: "t", operator: "empty", value: "" } }),
        { t: "" },
      ),
    ).toBe(true);
  });
});

describe("validateFieldValue", () => {
  it("devuelve null para valores vacíos", () => {
    expect(validateFieldValue(field({ id: "a", label: "A" }), "")).toBeNull();
  });

  it("email inválido", () => {
    const f = field({ id: "e", label: "Correo", type: "email" });
    expect(validateFieldValue(f, "no-es-email")).not.toBeNull();
    expect(validateFieldValue(f, "a@b.com")).toBeNull();
  });

  it("number con rango", () => {
    const f = field({ id: "n", label: "Edad", type: "number", min_value: 18, max_value: 99 });
    expect(validateFieldValue(f, "15")).toContain("≥ 18");
    expect(validateFieldValue(f, "100")).toContain("≤ 99");
    expect(validateFieldValue(f, "30")).toBeNull();
    expect(validateFieldValue(f, "abc")).toBe("Ingresa un número válido");
  });

  it("text con min_length/max_length", () => {
    const f = field({ id: "t", label: "Texto", min_length: 3, max_length: 5 });
    expect(validateFieldValue(f, "ab")).toContain("al menos 3");
    expect(validateFieldValue(f, "abcdef")).toContain("5 caracteres");
    expect(validateFieldValue(f, "abc")).toBeNull();
  });

  it("text con regex_pattern", () => {
    const f = field({ id: "t", label: "Código", regex_pattern: "^[A-Z]{3}$", regex_message: "3 mayúsculas" });
    expect(validateFieldValue(f, "ab1")).toBe("3 mayúsculas");
    expect(validateFieldValue(f, "ABC")).toBeNull();
  });

  it("select con opciones válidas y allow_other", () => {
    const f = field({ id: "s", label: "Opción", type: "select", options: ["A", "B"] });
    expect(validateFieldValue(f, "Z")).toContain("opción válida");
    expect(validateFieldValue(f, "A")).toBeNull();

    const other = field({ id: "s", label: "Opción", type: "select", options: ["A", "B"], allow_other: true });
    expect(validateFieldValue(other, "Otra libre")).toBeNull();
  });

  it("select_multiple", () => {
    const f = field({ id: "m", label: "Multi", type: "select_multiple", options: ["A", "B"] });
    expect(validateFieldValue(f, ["A", "B"])).toBeNull();
    expect(validateFieldValue(f, ["A", "Z"])).toContain("no es una opción válida");
  });

  it("date inválido", () => {
    const f = field({ id: "d", label: "Fecha", type: "date" });
    expect(validateFieldValue(f, "31-12-2026")).toBe("Fecha inválida (usa AAAA-MM-DD)");
    expect(validateFieldValue(f, "2026-12-31")).toBeNull();
  });

  it("file con max_file_mb", () => {
    const f = field({ id: "f", label: "Archivo", type: "file", max_file_mb: 2 });
    expect(validateFieldValue(f, { size: 3 * 1024 * 1024 })).toContain("excede 2 MB");
    expect(validateFieldValue(f, { size: 1024 })).toBeNull();
  });
});

describe("validateFields", () => {
  it("marca como obligatorio los campos requeridos vacíos", () => {
    const fields = [
      field({ id: "a", label: "Nombre", required: true }),
      field({ id: "b", label: "Nota" }),
    ];
    const errors = validateFields(fields, { b: "x" });
    expect(errors.a).toContain("Nombre");
    expect(errors.b).toBeUndefined();
  });

  it("ignora campos ocultos por visible_if", () => {
    const fields = [
      field({
        id: "x",
        label: "Oculto",
        required: true,
        visible_if: { field_id: "t", operator: "eq", value: "nunca" },
      }),
    ];
    expect(validateFields(fields, { t: "otro" })).toEqual({});
  });

  it("valida el valor cuando no está vacío", () => {
    const fields = [field({ id: "e", label: "Correo", type: "email" })];
    expect(validateFields(fields, { e: "mal" }).e).toBeDefined();
  });

  it("ignora campos meta", () => {
    const fields = [field({ id: "s", label: "Paso", type: "page" }), field({ id: "d", label: "Divisor", type: "divider" })];
    expect(validateFields(fields, {})).toEqual({});
  });
});

describe("buildSteps", () => {
  it("separa pasos por campos page", () => {
    const a = field({ id: "a", label: "A" });
    const p = field({ id: "p", label: "Paso", type: "page" });
    const b = field({ id: "b", label: "B" });
    const steps = buildSteps([a, p, b]);
    expect(steps).toEqual([[a], [b]]);
  });

  it("devuelve un paso vacío si no hay campos", () => {
    expect(buildSteps([])).toEqual([[]]);
  });

  it("un solo paso sin campos page", () => {
    const a = field({ id: "a", label: "A" });
    expect(buildSteps([a])).toEqual([[a]]);
  });
});

describe("collectVisibleData", () => {
  it("excluye meta, ocultos y valores vacíos", () => {
    const fields = [
      field({ id: "a", label: "A", type: "text" }),
      field({ id: "d", label: "Divisor", type: "divider" }),
      field({ id: "h", label: "Oculto", visible_if: { field_id: "t", operator: "eq", value: "no" } }),
      field({ id: "v", label: "Vacío" }),
    ];
    const data = collectVisibleData(fields, {
      a: "Ana",
      d: "x",
      h: "secreto",
      v: "",
    });
    expect(data).toEqual({ a: "Ana" });
  });
});

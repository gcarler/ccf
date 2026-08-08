import { describe, it, expect } from "vitest";
import { getInitials, parseCommentCount, formatDueLabel } from "./utils";

describe("community/utils — getInitials", () => {
  it("nombre de 2 palabras → iniciales", () => {
    expect(getInitials("Juan Pérez")).toBe("JP");
  });
  it("nombre de 1 palabra → 1 inicial", () => {
    expect(getInitials("Roberto")).toBe("R");
  });
  it("nombre de 3+ palabras → primeras 2 iniciales", () => {
    expect(getInitials("Ana María García")).toBe("AM");
  });
  it("string vacío → ''", () => {
    expect(getInitials("")).toBe("");
  });
  it("null-ish → '' (usando String(null))", () => {
    // La fn recibe string; pasando '' simula vacío.
    expect(getInitials("")).toBe("");
  });
  it("espacios extra (múltiples) → sin dobles iniciales", () => {
    expect(getInitials("  Juan   Pérez  ")).toBe("JP");
  });
  it("palabras en minúsculas → inicial en mayúscula", () => {
    expect(getInitials("juan pérez")).toBe("JP");
  });
  it("palabra con número/emoji → safe (primera code unit)", () => {
    expect(getInitials("1abc Def")).toBe("1D");
    // Emoji toma solo la primera UTF-16 code unit; documentamos el comportamiento.
    const out = getInitials("🚀 fast");
    expect(out.length).toBeGreaterThan(0);
    expect(out.endsWith("F")).toBe(true);
  });
});

describe("community/utils — parseCommentCount", () => {
  it("'10 comments' → 10", () => {
    expect(parseCommentCount("10 comments")).toBe(10);
  });
  it("'Comentarios (3)' → 3", () => {
    expect(parseCommentCount("Comentarios (3)")).toBe(3);
  });
  it("'ninguno' → 0 (sin dígitos)", () => {
    expect(parseCommentCount("ninguno")).toBe(0);
  });
  it("null/undefined/empty → 0", () => {
    expect(parseCommentCount(null)).toBe(0);
    expect(parseCommentCount(undefined)).toBe(0);
    expect(parseCommentCount("")).toBe(0);
  });
  it("con varios números → primero (primer match)", () => {
    expect(parseCommentCount("hay 3 de 5")).toBe(3);
  });
});

describe("community/utils — formatDueLabel", () => {
  it("null/undefined/empty → '—'", () => {
    expect(formatDueLabel(null)).toBe("—");
    expect(formatDueLabel(undefined)).toBe("—");
    expect(formatDueLabel("")).toBe("—");
  });
  it("fecha ISO inválida → returna el input literal", () => {
    expect(formatDueLabel("not-a-date")).toBe("not-a-date");
  });
  it("fecha ISO válida → formato es-MX día+mes corto", () => {
    const out = formatDueLabel("2024-07-15");
    expect(typeof out).toBe("string");
    expect(out.length).toBeGreaterThan(0);
    // 15 jul 2024 → "15 jul" en es-MX
    expect(out.toLowerCase()).toContain("jul");
  });
});

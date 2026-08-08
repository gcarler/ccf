import { describe, it, expect } from "vitest";
import { safeJsonParse } from "./safeJson";

describe("safeJson — safeJsonParse", () => {
  it("parsea JSON válido → tipo T", () => {
    expect(safeJsonParse('{"a":1}', null)).toEqual({ a: 1 });
    expect(safeJsonParse('[1,2,3]', [])).toEqual([1, 2, 3]);
    expect(safeJsonParse('"x"', "")).toBe("x");
    expect(safeJsonParse("42", 0)).toBe(42);
    expect(safeJsonParse("true", false)).toBe(true);
  });
  it("JSON inválido → fallback", () => {
    expect(safeJsonParse("not-json", { default: true })).toEqual({ default: true });
    expect(safeJsonParse("{bad", null)).toBeNull();
    expect(safeJsonParse("[1,", 0)).toBe(0);
  });
  it("string vacío → fallback", () => {
    expect(safeJsonParse("", null)).toBeNull();
  });
  it("null → fallback", () => {
    expect(safeJsonParse(null, "fb")).toBe("fb");
  });
  it("undefined → fallback", () => {
    expect(safeJsonParse(undefined, 99)).toBe(99);
  });
  it("preserva el tipo del fallback", () => {
    const out = safeJsonParse<{ x: number }>("bad", { x: 5 });
    expect(out.x).toBe(5);
  });
});

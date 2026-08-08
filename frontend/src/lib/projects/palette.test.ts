import { describe, it, expect } from "vitest";

import {
  PROJECT_COLOR_OPTIONS,
  DEFAULT_PROJECT_COLOR,
  DEFAULT_PHASE_COLOR,
  PHASE_COLOR_OPTIONS,
  getPhaseColorOption,
  getProjectColorOption,
  type ProjectColorOption,
} from "./palette";

describe("projects/palette — PROJECT_COLOR_OPTIONS", () => {
  it("tiene 5 opciones, cada una con value/label/token/preview", () => {
    expect(PROJECT_COLOR_OPTIONS.length).toBe(5);
    PROJECT_COLOR_OPTIONS.forEach((opt) => {
      expect(opt.value).toMatch(/^#[0-9a-f]{6}$/);
      expect(opt.label.length).toBeGreaterThan(0);
      expect(opt.token.length).toBeGreaterThan(0);
      expect(opt.preview).toContain("bg-[hsl(var(");
    });
  });
  it("el primer option valor hex = #2563eb (Azul ministerial)", () => {
    expect(PROJECT_COLOR_OPTIONS[0]).toEqual({
      value: "#2563eb",
      label: "Azul ministerial",
      token: "primary",
      preview: "bg-[hsl(var(--primary))]",
    } satisfies ProjectColorOption);
  });
  it("valores hex son únicos", () => {
    const vals = PROJECT_COLOR_OPTIONS.map((o) => o.value);
    expect(new Set(vals).size).toBe(vals.length);
  });
  it("tokens son únicos (semánticos)", () => {
    const tokens = PROJECT_COLOR_OPTIONS.map((o) => o.token);
    expect(new Set(tokens).size).toBe(tokens.length);
  });
});

describe("projects/palette — PHASE_COLOR_OPTIONS", () => {
  it("tiene 10 opciones, cada una con value/label/token/preview", () => {
    expect(PHASE_COLOR_OPTIONS.length).toBe(10);
    PHASE_COLOR_OPTIONS.forEach((opt) => {
      expect(opt.value).toMatch(/^#[0-9a-f]{6}$/);
      expect(opt.label.length).toBeGreaterThan(0);
      expect(opt.token.length).toBeGreaterThan(0);
      expect(opt.preview).toContain("bg-[hsl(var(");
    });
  });
  it("el primer option = gris (#94a3b8, token surface-2)", () => {
    expect(PHASE_COLOR_OPTIONS[0]).toEqual({
      value: "#94a3b8",
      label: "Gris",
      token: "surface-2",
      preview: "bg-[hsl(var(--surface-2))]",
    } satisfies ProjectColorOption);
  });
  it("valores hex únicos", () => {
    const vals = PHASE_COLOR_OPTIONS.map((o) => o.value);
    expect(new Set(vals).size).toBe(vals.length);
  });
  it("incluye tokens de domain-* (iris, pink, cyan, lime, fuchsia)", () => {
    const tokens = PHASE_COLOR_OPTIONS.map((o) => o.token);
    expect(tokens).toContain("domain-iris");
    expect(tokens).toContain("domain-pink");
    expect(tokens).toContain("domain-cyan");
    expect(tokens).toContain("domain-lime");
    expect(tokens).toContain("domain-fuchsia");
  });
});

describe("projects/palette — defaults", () => {
  it("DEFAULT_PROJECT_COLOR = primer valor del array", () => {
    expect(DEFAULT_PROJECT_COLOR).toBe("#2563eb");
    expect(DEFAULT_PROJECT_COLOR).toBe(PROJECT_COLOR_OPTIONS[0].value);
  });
  it("DEFAULT_PHASE_COLOR = '#94a3b8'", () => {
    expect(DEFAULT_PHASE_COLOR).toBe("#94a3b8");
    expect(DEFAULT_PHASE_COLOR).toBe(PHASE_COLOR_OPTIONS[0].value);
  });
});

describe("projects/palette — getPhaseColorOption", () => {
  it("value existente → opción correcta", () => {
    const out = getPhaseColorOption("#94a3b8");
    expect(out.value).toBe("#94a3b8");
    expect(out.label).toBe("Gris");
  });
  it("value no existente → fallback al primero (gris)", () => {
    const out = getPhaseColorOption("#000000");
    expect(out.value).toBe(PHASE_COLOR_OPTIONS[0].value);
  });
  it.each(PHASE_COLOR_OPTIONS.map((o) => o.value))("lookup exacto: %s", (val) => {
    expect(getPhaseColorOption(val).value).toBe(val);
  });
});

describe("projects/palette — getProjectColorOption", () => {
  it("value existente → opción correcta", () => {
    const out = getProjectColorOption("#2563eb");
    expect(out.value).toBe("#2563eb");
    expect(out.label).toBe("Azul ministerial");
  });
  it("value no existente → fallback al primero (azul)", () => {
    const out = getProjectColorOption("#ffffff");
    expect(out.value).toBe(PROJECT_COLOR_OPTIONS[0].value);
  });
  it.each(PROJECT_COLOR_OPTIONS.map((o) => o.value))("lookup exacto: %s", (val) => {
    expect(getProjectColorOption(val).value).toBe(val);
  });
});

describe("projects/palette — coherencia cross-options", () => {
  it("PROJECT y PHASE comparten los 4 tokens semantic-name no-domain", () => {
    const projTokens = PROJECT_COLOR_OPTIONS.map((o) => o.token);
    const phaseTokens = PHASE_COLOR_OPTIONS.map((o) => o.token);
    expect(projTokens).toEqual(["primary", "info", "success", "warning", "danger"]);
    expect(phaseTokens).toContain("primary");
    expect(phaseTokens).toContain("success");
    expect(phaseTokens).toContain("warning");
    expect(phaseTokens).toContain("danger");
  });
});

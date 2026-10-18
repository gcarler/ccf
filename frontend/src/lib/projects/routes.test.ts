import { describe, it, expect } from "vitest";
import { GLOBAL_PROJECT_ROUTES, isGlobalProjectRoute, isProjectEntityRoute } from "./routes";

describe("projects/routes — GLOBAL_PROJECT_ROUTES", () => {
  it("contiene las sub-rutas globales esperadas", () => {
    expect(GLOBAL_PROJECT_ROUTES.has("list")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("tasks")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("inbox")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("general")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("comments")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("team")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("responses")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("more")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("automations")).toBe(true);
    expect(GLOBAL_PROJECT_ROUTES.has("welcome")).toBe(true);
  });
  it("no contiene UUID-like u otras rutas (coverage edge)", () => {
    expect(GLOBAL_PROJECT_ROUTES.has("settings")).toBe(false);
    expect(GLOBAL_PROJECT_ROUTES.has("projects")).toBe(false);
    expect(GLOBAL_PROJECT_ROUTES.has("")).toBe(false);
  });
  it("es Read-only: same Set instance, has method", () => {
    expect(GLOBAL_PROJECT_ROUTES).toBeInstanceOf(Set);
    expect(typeof GLOBAL_PROJECT_ROUTES.has).toBe("function");
  });
});

describe("projects/routes — isGlobalProjectRoute", () => {
  it.each([...GLOBAL_PROJECT_ROUTES])("reconoce la sub-ruta global: %s", (segment) => {
    expect(isGlobalProjectRoute(segment)).toBe(true);
  });

  it("normaliza a minúsculas y sin espacios", () => {
    expect(isGlobalProjectRoute("  Tasks ")).toBe(true);
    expect(isGlobalProjectRoute("TEAM")).toBe(true);
    expect(isGlobalProjectRoute("More")).toBe(true);
  });

  it("devuelve false para UUIDs/types de proyecto y valores vacíos", () => {
    expect(isGlobalProjectRoute("550e8400-e29b-41d4-a716-446655440000")).toBe(false);
    expect(isGlobalProjectRoute("settings")).toBe(false);
    expect(isGlobalProjectRoute("")).toBe(false);
    expect(isGlobalProjectRoute("   ")).toBe(false);
    expect(isGlobalProjectRoute(null)).toBe(false);
    expect(isGlobalProjectRoute(undefined)).toBe(false);
  });
});

describe("projects/routes — isProjectEntityRoute", () => {
  it.each([...GLOBAL_PROJECT_ROUTES])("devuelve false para la sub-ruta global: %s", (segment) => {
    expect(isProjectEntityRoute(segment)).toBe(false);
  });

  it("devuelve true para UUIDs de proyecto", () => {
    expect(isProjectEntityRoute("550e8400-e29b-41d4-a716-446655440000")).toBe(true);
    expect(isProjectEntityRoute("  550e8400-E29B-41D4-A716-446655440000 ")).toBe(true);
  });

  it("normaliza a minúsculas antes de comparar con las rutas globales", () => {
    expect(isProjectEntityRoute("TASKS")).toBe(false);
    expect(isProjectEntityRoute(" Inbox ")).toBe(false);
  });

  it("devuelve false para valores vacíos/null", () => {
    expect(isProjectEntityRoute("")).toBe(false);
    expect(isProjectEntityRoute("   ")).toBe(false);
    expect(isProjectEntityRoute(null)).toBe(false);
    expect(isProjectEntityRoute(undefined)).toBe(false);
  });
});

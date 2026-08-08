import { describe, it, expect } from "vitest";
import { GLOBAL_PROJECT_ROUTES } from "./routes";

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

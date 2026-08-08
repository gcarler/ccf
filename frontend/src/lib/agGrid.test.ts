import { describe, it, expect, vi } from "vitest";

vi.mock("ag-grid-community", () => ({
  AllCommunityModule: { id: "all-community" },
  ModuleRegistry: { registerModules: vi.fn() },
}));

import { ModuleRegistry } from "ag-grid-community";
import { ensureAgGridModulesRegistered } from "./agGrid";

describe("agGrid — ensureAgGridModulesRegistered", () => {
  it("ya registrado en import (auto-init) → ya llamó ModuleRegistry.registerModules", () => {
    const spy = vi.mocked(ModuleRegistry.registerModules);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith([{ id: "all-community" }]);
  });

  it("segunda llamada explícita → no registra de nuevo (idempotente)", () => {
    const spy = vi.mocked(ModuleRegistry.registerModules);
    const prev = spy.mock.calls.length;
    ensureAgGridModulesRegistered();
    expect(spy.mock.calls.length).toBe(prev);
  });
});

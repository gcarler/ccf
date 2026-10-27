import { describe, expect, it } from "vitest";
import {
  hubStateChanged,
  readHubState,
  writeHubParams,
} from "./projectHubUrl";

describe("projectHubUrl — serialización del Hub en la query string (H-PROJ-UI-02)", () => {
  it("lee el estado del hub desde la URL compartida", () => {
    const params = new URLSearchParams("view=dashboard&tool=evm&tool=risks&toolActive=risks");
    expect(readHubState(params)).toEqual({ open: ["evm", "risks"], active: "risks" });
  });

  it("devuelve hub cerrado cuando no hay tool en la query", () => {
    expect(readHubState(new URLSearchParams("view=dashboard"))).toEqual({
      open: [],
      active: null,
    });
  });

  it("sin toolActive, la activa es la última abierta", () => {
    const params = new URLSearchParams("tool=time&tool=evm");
    expect(readHubState(params).active).toBe("evm");
  });

  it("ignora un toolActive que no pertenece a la lista abierta", () => {
    const params = new URLSearchParams("tool=evm&toolActive=risks");
    expect(readHubState(params).active).toBe("evm");
  });

  it("escribe el estado del hub preservando el resto de la query", () => {
    const base = new URLSearchParams("view=gantt&scope=mine");
    const next = writeHubParams(base, { open: ["labels", "drive"], active: "drive" });
    expect(next.get("view")).toBe("gantt");
    expect(next.get("scope")).toBe("mine");
    expect(next.getAll("tool")).toEqual(["labels", "drive"]);
    expect(next.get("toolActive")).toBe("drive");
  });

  it("cierra el hub al escribir un estado vacío (elimina los params)", () => {
    const base = new URLSearchParams("view=dashboard&tool=evm&toolActive=evm");
    const next = writeHubParams(base, { open: [], active: null });
    expect(next.has("tool")).toBe(false);
    expect(next.has("toolActive")).toBe(false);
    expect(next.get("view")).toBe("dashboard");
  });

  it("es idempotente: escribir el mismo estado no lo duplica", () => {
    let params = writeHubParams(new URLSearchParams(), { open: ["evm"], active: "evm" });
    params = writeHubParams(params, { open: ["evm"], active: "evm" });
    expect(params.getAll("tool")).toEqual(["evm"]);
  });

  it("detecta cambios de estado con hubStateChanged", () => {
    const a: Parameters<typeof hubStateChanged>[0] = { open: ["evm"], active: "evm" };
    expect(hubStateChanged(a, { open: ["evm"], active: "evm" })).toBe(false);
    expect(hubStateChanged(a, { open: [], active: null })).toBe(true);
    expect(hubStateChanged(a, { open: ["evm", "risks"], active: "evm" })).toBe(true);
    expect(hubStateChanged(a, { open: ["evm"], active: "risks" })).toBe(true);
  });
});

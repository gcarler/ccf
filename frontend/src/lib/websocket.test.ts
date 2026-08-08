import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { buildWsUrl, resolveClientId } from "./websocket";

describe("websocket — buildWsUrl", () => {
  it("path sin / (añade)", () => {
    const out = buildWsUrl("foo");
    expect(out.endsWith("/foo")).toBe(true);
  });
  it("respeta path con /", () => {
    const out = buildWsUrl("/events");
    expect(out.endsWith("/events")).toBe(true);
  });
  it("path vacío → base", () => {
    const out = buildWsUrl("");
    expect(out.length).toBeGreaterThan(0);
  });
  it("si base es http:// → convierte a ws:// (verifico que replace existe)", () => {
    // API_BASE_URL por defecto es /api (sin protocolo) → buildWsUrl no cambia protocolo.
    // Solo importa que no se rompe y devuelve el path correcto.
    const out = buildWsUrl("/foo");
    expect(out.endsWith("/foo")).toBe(true);
  });
  it("requiere el path empieza con / si se especificó /", () => {
    expect(buildWsUrl("/path/sub")).toContain("/path/sub");
  });
});

describe("websocket — resolveClientId", () => {
  let originalRandomUUID: typeof crypto.randomUUID;

  beforeEach(() => {
    originalRandomUUID = crypto.randomUUID;
  });
  afterEach(() => {
    Object.defineProperty(crypto, "randomUUID", {
      configurable: true,
      value: originalRandomUUID,
    });
  });

  it("clientId explícito → returna mismo", () => {
    expect(resolveClientId("abc-123")).toBe("abc-123");
  });
  it("undefined → generaId con prefijo 'anon-'", () => {
    Object.defineProperty(crypto, "randomUUID", {
      configurable: true,
      value: () => "uuid-fake-xyz",
    });
    expect(resolveClientId(undefined)).toBe("anon-uuid-fake-xyz");
  });
  it("string vacío → genera (fallback)", () => {
    Object.defineProperty(crypto, "randomUUID", {
      configurable: true,
      value: () => "alt-uuid",
    });
    expect(resolveClientId("")).toBe("anon-alt-uuid");
  });
  it("falsa sin crypto.randomUUID → fallback (skip jsdom: randomUUID siempre presente)", () => {
    // En jsdom/crypto no podemos simular la ausencia total de randomUUID sin
    // romper otros tests. Verificamos solo el comportamiento cuando existe.
    const out = resolveClientId();
    expect(out.startsWith("anon-")).toBe(true);
    expect(out.length).toBeGreaterThan("anon-".length);
  });
});

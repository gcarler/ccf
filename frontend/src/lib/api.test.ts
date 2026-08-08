import { describe, it, expect } from "vitest";
import { apiUrl, API_BASE_URL } from "./api";

describe("api — apiUrl", () => {
  it("prefija path sin / con /", () => {
    expect(apiUrl("users")).toBe(`${API_BASE_URL}/users`);
  });
  it("respeta path con / inicial", () => {
    expect(apiUrl("/users")).toBe(`${API_BASE_URL}/users`);
  });
  it("path vacío → base + '/'", () => {
    expect(apiUrl("")).toBe(`${API_BASE_URL}/`);
  });
  it("path con sub-rutas profundas", () => {
    expect(apiUrl("/cms/v2/sites")).toBe(`${API_BASE_URL}/cms/v2/sites`);
  });
  it("no añade / extra si base ya lo termina (USO_API_BASE es /api)", () => {
    // Verifica que no produzca "/api//users"
    expect(apiUrl("users")).not.toContain("//");
    expect(apiUrl("/users")).not.toContain("//");
  });
});

describe("api — API_BASE_URL", () => {
  it("es string no vacío", () => {
    expect(typeof API_BASE_URL).toBe("string");
    expect(API_BASE_URL.length).toBeGreaterThan(0);
  });
  it("default es '/api' si no hay env", () => {
    if (!process.env.NEXT_PUBLIC_API_URL && !process.env.API_BASE_URL) {
      expect(API_BASE_URL).toBe("/api");
    }
  });
  it("no termina con / en cliente (NEXT_PUBLIC_API_URL ya trimeado)", () => {
    // Siempre que no sea el default, asegura sin trailing slash.
    if (API_BASE_URL !== "/api") {
      expect(API_BASE_URL.endsWith("/")).toBe(false);
    }
  });
});

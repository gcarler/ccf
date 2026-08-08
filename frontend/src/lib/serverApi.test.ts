import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { serverApiFetch } from "./serverApi";

const cookiesMock = vi.mocked(cookies);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockCookieStore(all: Array<{ name: string; value: string }> = []) {
  return { getAll: vi.fn(() => all) };
}

describe("serverApiFetch — éxito", () => {
  it("adjunta Accept, cookies, fetch con cache no-store default", async () => {
    cookiesMock.mockResolvedValueOnce(
      mockCookieStore([
        { name: "session", value: "abc" },
        { name: "csrf", value: "xyz" },
      ]) as never,
    );
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({ hello: "world" }),
    } as unknown as Response);
    const out = await serverApiFetch<{ hello: string }>("/users/me");
    expect(out).toEqual({ hello: "world" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/users/me");
    expect(init.cache).toBe("no-store");
    const headers = new Headers(init.headers);
    expect(headers.get("Accept")).toBe("application/json");
    expect(headers.get("cookie")).toContain("session=abc");
    expect(headers.get("cookie")).toContain("csrf=xyz");
  });
  it("init.cache explícito respeta el valor (no sobrescribe con no-store)", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => "null",
    } as unknown as Response);
    await serverApiFetch("/x", { cache: "force-cache" });
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(init.cache).toBe("force-cache");
  });
  it("body vacío → parseResponse devuelve undefined sin lanzar", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => "",
    } as unknown as Response);
    const out = await serverApiFetch<unknown>("/x");
    expect(out).toBeUndefined();
  });
  it("body no-JSON pero OK → parseResponse devuelve texto bruto", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => "hello-plain",
    } as unknown as Response);
    const out = await serverApiFetch<string>("/x");
    expect(out).toBe("hello-plain");
  });
  it("preserva headers pasados por init (se añaden a los defaults)", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => "null",
    } as unknown as Response);
    await serverApiFetch("/x", { headers: { "X-Custom": "abc" } });
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("X-Custom")).toBe("abc");
    expect(headers.get("Accept")).toBe("application/json");
  });
});

describe("serverApiFetch — error", () => {
  it("response not-ok → throw Error con .detail = body (JSON)", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: async () => JSON.stringify({ detail: "validation" }),
    } as unknown as Response);
    try {
      await serverApiFetch("/x");
      throw new Error("should have thrown");
    } catch (err) {
      expect((err as Error).message).toBe("Server API request failed");
      expect((err as Error & { detail?: unknown }).detail).toEqual({ detail: "validation" });
    }
  });
  it("response not-ok con body no-JSON → detail = texto bruto", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore() as never);
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: async () => "Bad Gateway",
    } as unknown as Response);
    try {
      await serverApiFetch("/x");
      throw new Error("should have thrown");
    } catch (err) {
      expect((err as Error & { detail?: unknown }).detail).toBe("Bad Gateway");
    }
  });
});

describe("serverApiFetch — sin cookies", () => {
  it("cookieStore vacío → no añade cookie header (append no hace nada)", async () => {
    cookiesMock.mockResolvedValueOnce(mockCookieStore([]) as never);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      text: async () => "",
    } as unknown as Response);
    await serverApiFetch("/x");
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("cookie")).toBeNull();
  });
});

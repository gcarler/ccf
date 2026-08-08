import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, apiFetchBlob, ApiError, extractErrorMessage } from "./http";

vi.mock("@/lib/api", () => ({
  apiUrl: (p: string) => `/api${p.startsWith("/") ? p : `/${p}`}`,
}));

type FetchLike = typeof fetch;

let mockFetch: ReturnType<typeof vi.fn>;
let originalFetch: FetchLike | undefined;
let originalRandomUUID: typeof crypto.randomUUID | undefined;

function mockResponse(body: unknown, init: Partial<Response> = {}): Response {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: init.statusText ?? "OK",
    text: () => Promise.resolve(text),
    json: () => Promise.resolve(typeof body === "string" ? body : JSON.parse(text)),
    blob: () => Promise.resolve(new Blob([text])),
    headers: new Headers(init.headers),
  } as unknown as Response;
}

/** Extrae headers de la llamada mock como Headers legibles (.get). */
function headersOf(call: unknown): Headers {
  const [, init] = call as [string, RequestInit];
  return new Headers(init.headers);
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();

  mockFetch = vi.fn();
  originalFetch = (globalThis as { __ccfOriginalFetch?: FetchLike }).__ccfOriginalFetch;
  (globalThis as { __ccfOriginalFetch?: FetchLike }).__ccfOriginalFetch = mockFetch as unknown as FetchLike;

  originalRandomUUID = crypto.randomUUID;
  Object.defineProperty(crypto, "randomUUID", {
    configurable: true,
    value: () => "test-uuid-1234",
  });
});

afterEach(() => {
  if (originalFetch === undefined) {
    delete (globalThis as { __ccfOriginalFetch?: FetchLike }).__ccfOriginalFetch;
  } else {
    (globalThis as { __ccfOriginalFetch?: FetchLike }).__ccfOriginalFetch = originalFetch;
  }
  if (originalRandomUUID === undefined) {
    Object.defineProperty(crypto, "randomUUID", { configurable: true, value: undefined });
  } else {
    Object.defineProperty(crypto, "randomUUID", { configurable: true, value: originalRandomUUID });
  }
});

describe("http — ApiError", () => {
  it("construye con status y detail", () => {
    const err = new ApiError("algo", 500, { detail: "x" });
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(500);
    expect(err.detail).toEqual({ detail: "x" });
    expect(err.message).toBe("algo");
  });

  it("detail opcional queda undefined", () => {
    const err = new ApiError("boom", 500);
    expect(err.detail).toBeUndefined();
  });
});

describe("http — extractErrorMessage", () => {
  it("ApiError con detail objeto {detail: string}", () => {
    const err = new ApiError("x", 422, { detail: "validación fallida" });
    expect(extractErrorMessage(err)).toBe("validación fallida");
  });
  it("ApiError con detail objeto {message: string}", () => {
    const err = new ApiError("x", 422, { message: "mensaje interno" });
    expect(extractErrorMessage(err)).toBe("mensaje interno");
  });
  it("ApiError con detail string", () => {
    const err = new ApiError("x", 500, "detalle directo");
    expect(extractErrorMessage(err)).toBe("detalle directo");
  });
  it("ApiError sin detail útil cae a message", () => {
    const err = new ApiError("fallback msg", 500);
    expect(extractErrorMessage(err)).toBe("fallback msg");
  });
  it("ApiError sin detail ni message cae a fallback", () => {
    const err = new ApiError("", 500);
    expect(extractErrorMessage(err, "default-msg")).toBe("default-msg");
  });
  it("Error genérico usa message", () => {
    expect(extractErrorMessage(new Error("boom"))).toBe("boom");
  });
  it("valor no-Error usa fallback", () => {
    expect(extractErrorMessage(null)).toBe("Error inesperado");
    expect(extractErrorMessage("texto", "def")).toBe("def");
  });
});

describe("http — apiFetch (éxito]", () => {
  it("GET pasandose Bearer y X-Request-ID, query string correcto", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ ok: true }));
    const out = await apiFetch<{ ok: boolean }>("/users", { token: "tok", query: { page: 2, q: "a" } });
    expect(out).toEqual({ ok: true });
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/users?page=2&q=a");
    expect(init.method).toBe("GET");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer tok");
    expect(new Headers(init.headers).get("X-Request-ID")).toBe("test-uuid-1234");
    expect(new Headers(init.headers).get("Accept")).toBe("application/json");
  });

  it("strings body con Content-Type personalizado lo respeta", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x", {
      method: "POST",
      body: "raw-text",
      headers: { "Content-Type": "text/plain" },
    });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe("raw-text");
    expect(new Headers(init.headers).get("Content-Type")).toBe("text/plain");
  });
  it("string body sin Content-Type setea application/json", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x", { method: "POST", body: "{a:1}" });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });
  it("objeto body → JSON.stringify + application/json", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x", { method: "PUT", body: { a: 1 } });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });
  it("URLSearchParams body → form-urlencoded", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    const form = new URLSearchParams({ x: "1" });
    await apiFetch("/x", { method: "POST", body: form });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(form);
    expect(new Headers(init.headers).get("Content-Type")).toContain("application/x-www-form-urlencoded");
  });
  it("FormData body → init.body sin setear Content-Type", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    const fd = new FormData();
    fd.append("file", new Blob(["a"]), "f.txt");
    await apiFetch("/x", { method: "POST", body: fd });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(fd);
    expect(new Headers(init.headers).get("Content-Type")).toBeNull();
  });
  it("query undefined/null → omitido del querystring", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x", { query: { a: null, b: undefined, c: 1 } });
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("c=1");
    expect(url).not.toContain("a=");
    expect(url).not.toContain("b=");
  });
  it("path http(s):// absoluto no se prefija con apiUrl", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("https://example.com/x");
    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://example.com/x");
  });
  it("body undefined → init.body queda undefined", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x");
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeUndefined();
  });
});

describe("http — apiFetch (token)", () => {
  it("auto-inyecta token de sessionStorage si no se pasa", async () => {
    sessionStorage.setItem("ccf_token", "AUTO");
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x");
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer AUTO");
  });
  it("no inyecta Authorization si no hay token ni sessionStorage", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x");
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBeNull();
  });
  it("token explícito tiene prioridad sobre sessionStorage", async () => {
    sessionStorage.setItem("ccf_token", "OLD");
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    await apiFetch("/x", { token: "EXPLICIT" });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer EXPLICIT");
  });
});

describe("http — apiFetch (errores)", () => {
  it("status != ok lanza ApiError con status y detail parseado", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ detail: "bad" }, { ok: false, status: 500 }));
    await expect(apiFetch("/x")).rejects.toMatchObject({ status: 500, detail: { detail: "bad" } });
  });
  it("body no-JSON → detail queda como texto bruto", async () => {
    mockFetch.mockResolvedValueOnce(
      mockResponse("not-json", { ok: false, status: 500, statusText: "Internal" }),
    );
    await expect(apiFetch("/x", { silent: true })).rejects.toMatchObject({ status: 500 });
  });
  it("fetch aborta (AbortError) → ApiError status 0 'timed out'", async () => {
    const err = new Error("aborted");
    err.name = "AbortError";
    mockFetch.mockRejectedValueOnce(err);
    await expect(apiFetch("/x", { silent: true })).rejects.toMatchObject({
      status: 0,
      message: "Request timed out",
    });
  });
  it("error de red genérico → ApiError status 0 sin log si silent=true", async () => {
    const spy = vi.spyOn(console, "error");
    mockFetch.mockRejectedValueOnce(new Error("net fail"));
    await expect(apiFetch("/x", { silent: true })).rejects.toMatchObject({ status: 0 });
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
  it("error de red sin silent → console.error se llama", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockFetch.mockRejectedValueOnce(new Error("net fail"));
    await expect(apiFetch("/x")).rejects.toMatchObject({ status: 0 });
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe("http — apiFetch (401 + refresh)]", () => {
  it("401 en /v3/auth/login no intenta refresh, lanza ApiError", async () => {
    mockFetch.mockResolvedValueOnce(
      mockResponse({ detail: "bad creds" }, { ok: false, status: 401 }),
    );
    await expect(apiFetch("/v3/auth/login", { silent: true })).rejects.toMatchObject({
      status: 401,
      message: "bad creds",
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
  it("401 no-auth-path intenta refresh y reintenta con nuevo token", async () => {
    sessionStorage.setItem("ccf_refresh_token", "rt");
    mockFetch
      .mockResolvedValueOnce(mockResponse({ detail: "expired" }, { ok: false, status: 401 }))
      .mockResolvedValueOnce(mockResponse({ access_token: "NEW" }))
      .mockResolvedValueOnce(mockResponse({ ok: true }));
    const out = await apiFetch<{ ok: boolean }>("/users");
    expect(out).toEqual({ ok: true });
    expect(mockFetch).toHaveBeenCalledTimes(3);
    const retryInit = mockFetch.mock.calls[2][1] as RequestInit;
    expect(new Headers(retryInit.headers).get("Authorization")).toBe("Bearer NEW");
  });
  it("401 con refresh fallido limpia sesión y redirige a /login?expired", async () => {
    sessionStorage.setItem("ccf_token", "old");
    sessionStorage.setItem("ccf_refresh_token", "rt");
    mockFetch.mockResolvedValue(null);
    mockFetch
      .mockResolvedValueOnce(mockResponse({ detail: "expired" }, { ok: false, status: 401 }))
      .mockResolvedValueOnce(mockResponse({}));
    let assigned = "";
    const origAssign = window.location.assign;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        assign: (u: string) => { assigned = u; },
        set href(v: string) { assigned = v; },
        get href() { return ""; },
      },
    });
    await expect(apiFetch("/users", { silent: true })).rejects.toThrow();
    expect(sessionStorage.getItem("ccf_token")).toBeNull();
    expect(sessionStorage.getItem("ccf_refresh_token")).toBeNull();
    expect(assigned).toBe("/login?expired=true");
    Object.defineProperty(window, "location", { configurable: true, value: { assign: origAssign } });
  });
});

describe("http — apiFetchBlob", () => {
  it("devuelve Blob en éxito", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse("ok"));
    const out = await apiFetchBlob("/x");
    expect(out).toBeInstanceOf(Blob);
  });
  it("status no-ok lanza ApiError con detail parseado", async () => {
    mockFetch.mockResolvedValueOnce(
      mockResponse({ detail: "bad" }, { ok: false, status: 404 }),
    );
    await expect(apiFetchBlob("/x")).rejects.toMatchObject({ status: 404, detail: { detail: "bad" } });
  });
});

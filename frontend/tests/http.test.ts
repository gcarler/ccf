import { describe, it, expect, beforeEach, afterAll, vi } from "vitest";
import { apiFetch, ApiError } from "../src/lib/http";

const original = globalThis.fetch;

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("apiFetch", () => {
  it("adds authorization header and serializes JSON bodies", async () => {
    const mockFetch = vi.fn(async () => new Response(JSON.stringify({ message: "ok" }), { status: 200 }));
    (globalThis as any).__ccfOriginalFetch = mockFetch;

    const result = await apiFetch<{ message: string }>("/sample", {
      method: "POST",
      token: "token-123",
      body: { foo: "bar" },
    });

    expect(result.message).toBe("ok");
    const firstCall = (mockFetch.mock.calls[0] ?? []) as unknown as [RequestInfo, RequestInit];
    const options = firstCall?.[1];
    const headers = options?.headers as Headers | undefined;
    expect(headers?.get("Authorization")).toBe("Bearer token-123");
    expect(options?.body).toBe(JSON.stringify({ foo: "bar" }));
  });

  it("throws ApiError when response is not ok", async () => {
    const mockFetch = vi.fn(async () => new Response(JSON.stringify({ detail: "fail" }), { status: 500, statusText: "boom" }));
    (globalThis as any).__ccfOriginalFetch = mockFetch;

    let caught: ApiError | null = null;
    try {
      await apiFetch('/boom');
    } catch (error) {
      caught = error as ApiError;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught?.status).toBe(500);
    expect((caught?.detail as any).detail).toBe("fail");
  });
});

afterAll(() => {
  globalThis.fetch = original;
});

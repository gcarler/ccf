import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiFetch, ApiError } from "../src/lib/http";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("apiFetch", () => {
  it("adds authorization header and serializes JSON bodies", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      new Response(JSON.stringify({ message: "ok" }), { status: 200 })
    );

    const result = await apiFetch<{ message: string }>("/sample", {
      method: "POST",
      token: "token-123",
      body: { foo: "bar" },
    });

    expect(result.message).toBe("ok");
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toEqual(expect.stringContaining("/api/sample"));
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ foo: "bar" }));
    const headers = init?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("throws ApiError when response is not ok", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      new Response(JSON.stringify({ detail: "fail" }), { status: 500, statusText: "boom" })
    );

    let caught: ApiError | null = null;
    try {
      await apiFetch('/boom');
    } catch (error) {
      caught = error as ApiError;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught?.status).toBe(500);
    expect((caught?.detail as { detail?: string } | undefined)?.detail).toBe("fail");
  });
});

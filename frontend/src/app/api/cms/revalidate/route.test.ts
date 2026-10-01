import { describe, it, expect, vi, beforeEach } from "vitest";
import { POST } from "./route";
import { NextRequest } from "next/server";
import * as nextCache from "next/cache";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
  revalidateTag: vi.fn(),
}));

describe("POST /api/cms/revalidate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("retorna 400 si no se envia path ni tag", async () => {
    const req = new NextRequest("http://localhost:3000/api/cms/revalidate", {
      method: "POST",
      body: JSON.stringify({}),
    });

    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.success).toBe(false);
    expect(data.message).toContain("path");
  });

  it("revalida un path especifico exitosamente", async () => {
    const req = new NextRequest("http://localhost:3000/api/cms/revalidate", {
      method: "POST",
      body: JSON.stringify({ path: "/pastores" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.revalidated).toBe(true);
    expect(data.path).toBe("/pastores");
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/pastores");
  });

  it("revalida un tag de cache exitosamente", async () => {
    const req = new NextRequest("http://localhost:3000/api/cms/revalidate", {
      method: "POST",
      body: JSON.stringify({ tag: "cms-pages" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.revalidated).toBe(true);
    expect(data.tag).toBe("cms-pages");
    expect(nextCache.revalidateTag).toHaveBeenCalledWith("cms-pages");
  });

  it("soporta revalidacion por query params", async () => {
    const req = new NextRequest("http://localhost:3000/api/cms/revalidate?path=/sedes", {
      method: "POST",
    });

    const res = await POST(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.path).toBe("/sedes");
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/sedes");
  });
});

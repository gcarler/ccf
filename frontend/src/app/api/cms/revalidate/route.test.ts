import { describe, it, expect, vi, beforeEach } from "vitest";
import { POST } from "./route";
import { NextRequest } from "next/server";
import * as nextCache from "next/cache";

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
  revalidateTag: vi.fn(),
}));

// En tests no hay CMS_REVALIDATE_SECRET configurado: se usa el default del
// módulo para autorizar peticiones de servicio.
const SERVICE_SECRET = "ccf-cms-isr-revalidate-secret-token";

function buildRequest(body: Record<string, unknown>, headers: Record<string, string> = {}) {
  return new NextRequest("http://localhost:3000/api/cms/revalidate", {
    method: "POST",
    body: JSON.stringify(body),
    headers,
  });
}

describe("POST /api/cms/revalidate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("retorna 400 si no se envia path ni tag", async () => {
    const req = buildRequest({}, { "x-revalidate-secret": SERVICE_SECRET });
    const res = await POST(req);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.success).toBe(false);
    expect(data.message).toContain("path");
  });

  it("rechaza con 401 a peticiones anonimas sin secret ni sesion", async () => {
    const req = buildRequest({ path: "/pastores" });
    const res = await POST(req);
    expect(res.status).toBe(401);
    const data = await res.json();
    expect(data.success).toBe(false);
    expect(nextCache.revalidatePath).not.toHaveBeenCalled();
  });

  it("autoriza peticiones de servicio con x-revalidate-secret valido", async () => {
    const req = buildRequest({ path: "/pastores" }, { "x-revalidate-secret": SERVICE_SECRET });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.revalidated).toBe(true);
    expect(data.path).toBe("/pastores");
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/pastores");
  });

  it("autoriza secret via Bearer y acepta tag", async () => {
    const req = buildRequest({ tag: "cms-public" }, { authorization: `Bearer ${SERVICE_SECRET}` });
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(nextCache.revalidateTag).toHaveBeenCalledWith("cms-public");
  });

  it("revalida path con type layout cuando se especifica", async () => {
    const req = buildRequest(
      { path: "/predicas", type: "layout" },
      { "x-revalidate-secret": SERVICE_SECRET },
    );
    const res = await POST(req);
    expect(res.status).toBe(200);
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/predicas", "layout");
  });

  it("revalida tambien la portada como fallback canonico", async () => {
    const req = buildRequest({ path: "/pastores" }, { "x-revalidate-secret": SERVICE_SECRET });
    const res = await POST(req);
    expect(res.status).toBe(200);
    // Se espera la llamada objetivo + el fallback de la portada "/".
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/pastores");
    expect(nextCache.revalidatePath).toHaveBeenCalledWith("/");
  });
});

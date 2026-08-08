import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch, type ApiFetchOptions } from "@/lib/http";

type CmsV2Call = [string, ApiFetchOptions];

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

import {
  listCmsSites,
  createCmsSite,
  patchCmsSite,
  listCmsMenus,
  patchCmsMenu,
  deleteCmsMenu,
  listCmsThemes,
  createCmsTheme,
  deleteCmsTheme,
  listCmsPages,
  createCmsPage,
  patchCmsPage,
  deleteCmsPage,
  listCmsSections,
  createCmsSection,
  patchCmsSection,
  deleteCmsSection,
  reorderCmsSections,
  getPublicCmsForm,
  submitPublicCmsFormV2,
  listCmsForms,
  createCmsForm,
  putCmsForm,
  patchCmsForm,
  deleteCmsForm,
  listCmsFormSubmissions,
} from "./v2";

const mockApi = vi.mocked(apiFetch);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("cms/v2 — sites", () => {
  it("lists sites on GET /cms/v2/sites", async () => {
    const sample = [{ site_key: "faro" }];
    mockApi.mockResolvedValueOnce(sample);
    const res = await listCmsSites("tok");
    expect(res).toBe(sample);
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites", { token: "tok" });
  });

  it("creates a site via POST with payload", async () => {
    const created = { site_key: "faro" };
    mockApi.mockResolvedValueOnce(created);
    const payload = { site_key: "faro", name: "Faro", base_path: "/" };
    const res = await createCmsSite(payload, "tok");
    expect(res).toBe(created);
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites", {
      method: "POST",
      token: "tok",
      body: payload,
    });
  });

  it("patches a site via PATCH /cms/v2/sites/{key}", async () => {
    mockApi.mockResolvedValueOnce({ site_key: "faro" });
    await patchCmsSite("faro", { name: "Faro Global" }, undefined);
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro", {
      method: "PATCH",
      token: undefined,
      body: { name: "Faro Global" },
    });
  });
});

describe("cms/v2 — menus", () => {
  it("lists menus of a site", async () => {
    mockApi.mockResolvedValueOnce([]);
    await listCmsMenus("faro", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/menus", { token: "tok" });
  });

  it("patches a menu", async () => {
    mockApi.mockResolvedValueOnce({});
    await patchCmsMenu("faro", "main", { name: "Principal" }, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/menus/main", {
      method: "PATCH",
      token: "tok",
      body: { name: "Principal" },
    });
  });

  it("deletes a menu (void)", async () => {
    mockApi.mockResolvedValueOnce(undefined);
    await deleteCmsMenu("faro", "main", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/menus/main", {
      method: "DELETE",
      token: "tok",
    });
  });
});

describe("cms/v2 —themes", () => {
  it("lists themes", async () => {
    mockApi.mockResolvedValueOnce([]);
    await listCmsThemes("faro", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/themes", { token: "tok" });
  });

  it("creates a theme via POST", async () => {
    const payload = { name: "T", tokens_json: { "--bg": "#fff" } };
    mockApi.mockResolvedValueOnce({ id: "t1" });
    await createCmsTheme("faro", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/themes", {
      method: "POST",
      token: "tok",
      body: payload,
    });
  });

  it("deletes a theme (void)", async () => {
    mockApi.mockResolvedValueOnce(undefined);
    await deleteCmsTheme("faro", "t1", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/themes/t1", {
      method: "DELETE",
      token: "tok",
    });
  });
});

describe("cms/v2 — pages + sections", () => {
  it("listCmsPages returns the array when the API responds an array", async () => {
    const items = [{ id: "p1", slug: "landing" }];
    mockApi.mockResolvedValueOnce(items);
    const res = await listCmsPages("faro", "tok");
    expect(res).toBe(items);
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/pages", { token: "tok" });
  });

  it("listCmsPages normalizes {items, total} into an array", async () => {
    mockApi.mockResolvedValueOnce({ items: [{ id: "p1" }, { id: "p2" }], total: 2 });
    const res = await listCmsPages("faro");
    expect(res).toHaveLength(2);
  });

  it("listCmsPages returns [] when payload is missing items", async () => {
    mockApi.mockResolvedValueOnce({});
    expect(await listCmsPages("faro")).toEqual([]);
  });

  it("creates a page via POST", async () => {
    const payload = { slug: "landing", title: "Landing" };
    mockApi.mockResolvedValueOnce({ id: "p1" });
    await createCmsPage("faro", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/pages", {
      method: "POST",
      token: "tok",
      body: payload,
    });
  });

  it("patches a page via PATCH /pages/{slug}", async () => {
    const payload = { title: "Nuevo" };
    mockApi.mockResolvedValueOnce({});
    await patchCmsPage("faro", "landing", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/pages/landing", {
      method: "PATCH",
      token: "tok",
      body: payload,
    });
  });

  it("deletes a page (void)", async () => {
    mockApi.mockResolvedValueOnce(undefined);
    await deleteCmsPage("faro", "landing", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/pages/landing", {
      method: "DELETE",
      token: "tok",
    });
  });

  it("listCmsSections returns the array when API responds an array", async () => {
    const items = [{ id: "s1", type: "hero" }];
    mockApi.mockResolvedValueOnce(items);
    const res = await listCmsSections("faro", "landing", "tok");
    expect(res).toBe(items);
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/pages/landing/sections",
      { token: "tok" },
    );
  });

  it("listCmsSections normalizes {items,...} into an array", async () => {
    mockApi.mockResolvedValueOnce({ items: [{ id: "s1" }, { id: "s2" }], total: 2, skip: 0, limit: 20 });
    const res = await listCmsSections("faro", "landing");
    expect(res).toHaveLength(2);
  });

  it("listCmsSections returns [] when payload is missing items", async () => {
    mockApi.mockResolvedValueOnce({});
    expect(await listCmsSections("faro", "landing")).toEqual([]);
  });

  it("creates a section via POST", async () => {
    const payload = { type: "hero", props_json: { title: "T" } };
    mockApi.mockResolvedValueOnce({ id: "s1" });
    await createCmsSection("faro", "landing", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/pages/landing/sections",
      { method: "POST", token: "tok", body: payload },
    );
  });

  it("patches a section via PATCH /sections/{id}", async () => {
    const payload = { props_json: { title: "Nuevo" } };
    mockApi.mockResolvedValueOnce({});
    await patchCmsSection("faro", "landing", "s1", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/pages/landing/sections/s1",
      { method: "PATCH", token: "tok", body: payload },
    );
  });

  it("deletes a section (void)", async () => {
    mockApi.mockResolvedValueOnce(undefined);
    await deleteCmsSection("faro", "landing", "s1", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/pages/landing/sections/s1",
      { method: "DELETE", token: "tok" },
    );
  });

  it("reorders sections via POST /sections/reorder with {items}", async () => {
    const items = [{ id: "s1", sort_order: 1 }, { id: "s2", sort_order: 2 }];
    mockApi.mockResolvedValueOnce([]);
    await reorderCmsSections("faro", "landing", items, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/pages/landing/sections/reorder",
      { method: "POST", token: "tok", body: { items } },
    );
  });
});

describe("cms/v2 — forms (form-builder)", () => {
  it("getPublicCmsForm fetches the public form definition", async () => {
    mockApi.mockResolvedValueOnce({ id: "f1" });
    await getPublicCmsForm("f1", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/public/forms/f1", { token: "tok" });
  });

  it("submitPublicCmsFormV2 posts data, captcha and honeypot", async () => {
    const payload = { data: { name: "Ana" }, captcha_token: "tok", hp: "" };
    mockApi.mockResolvedValueOnce({ success: true, message: "ok", submission_id: "s1" });
    await submitPublicCmsFormV2("f1", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/public/forms/f1/submit/v2", {
      method: "POST",
      token: "tok",
      body: payload,
    });
  });

  it("listCmsForms fetches forms of a site", async () => {
    mockApi.mockResolvedValueOnce([]);
    await listCmsForms("faro", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/forms", { token: "tok" });
  });

  it("createCmsForm posts the payload", async () => {
    const payload = { name: "Contacto" };
    mockApi.mockResolvedValueOnce({ id: "f1" });
    await createCmsForm("faro", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/forms", {
      method: "POST",
      token: "tok",
      body: payload,
    });
  });

  it("putCmsForm replaces the form via PUT /forms/{id}", async () => {
    const payload = { name: "Contacto" };
    mockApi.mockResolvedValueOnce({ id: "f1" });
    await putCmsForm("faro", "f1", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/forms/f1", {
      method: "PUT",
      token: "tok",
      body: payload,
    });
  });

  it("patchCmsForm patches the form via PATCH /forms/{id}", async () => {
    const payload = { is_active: false };
    mockApi.mockResolvedValueOnce({ id: "f1" });
    await patchCmsForm("faro", "f1", payload, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/forms/f1", {
      method: "PATCH",
      token: "tok",
      body: payload,
    });
  });

  it("deleteCmsForm deletes via DELETE (void)", async () => {
    mockApi.mockResolvedValueOnce(undefined);
    await deleteCmsForm("faro", "f1", "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>("/cms/v2/sites/faro/forms/f1", {
      method: "DELETE",
      token: "tok",
    });
  });

  it("listCmsFormSubmissions sends page + page_size as query", async () => {
    mockApi.mockResolvedValueOnce({ items: [], total: 0, page: 2, page_size: 10, total_pages: 0 });
    await listCmsFormSubmissions("faro", "f1", 2, 10, "tok");
    expect(mockApi).toHaveBeenCalledWith<CmsV2Call>(
      "/cms/v2/sites/faro/forms/f1/submissions",
      { token: "tok", query: { page: "2", page_size: "10" } },
    );
  });

  it("listCmsFormSubmissions uses default page=1 + page_size=20", async () => {
    mockApi.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
    await listCmsFormSubmissions("faro", "f1");
    const [, opts] = mockApi.mock.calls[0] as CmsV2Call[];
    expect(opts.query).toEqual({ page: "1", page_size: "20" });
  });
});


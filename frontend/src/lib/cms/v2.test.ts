import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CmsPostWithTaxonomies, CmsPublicPost } from "@/types/cms-v2";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));

import {
  activateCmsTheme,
  applyCmsAbTestWinner,
  createCmsAbTest,
  createCmsCategory,
  createCmsForm,
  createCmsNewsletter,
  createCmsPage,
  createCmsPopup,
  createCmsPostByCategory,
  createCmsSection,
  createCmsTheme,
  createPublicPostComment,
  deleteCmsAbTest,
  deleteCmsForm,
  deleteCmsMenu,
  deleteCmsPopup,
  deleteCmsSection,
  deleteCmsTheme,
  fromLocalDateTimeInputValue,
  getCmsAbTest,
  getCmsPagePreview,
  getCmsPastoralTeam,
  getCmsPostByCategory,
  getCmsPublicPage,
  getPageAnalytics,
  getPublicPastoralTeam,
  getPublicTestimonials,
  importCmsSubscribers,
  isExpiringPage,
  isScheduledPage,
  listCmsAbTests,
  listCmsCategories,
  listCmsForms,
  listCmsFormSubmissions,
  listCmsMenus,
  listCmsNewsletters,
  listCmsPages,
  listCmsPostComments,
  listCmsPostsByCategory,
  listCmsSections,
  listCmsSites,
  listCmsSubscribers,
  listCmsTags,
  listPublicAnnouncements,
  listPublicPopups,
  listPublicTestimonials,
  patchCmsAbTest,
  patchCmsForm,
  patchCmsMenu,
  patchCmsPopup,
  patchCmsPostCommentStatus,
  patchCmsSection,
  postToAnnouncement,
  postToTestimonial,
  publicPostToAnnouncement,
  publicPostToTestimonial,
  putCmsForm,
  recordCmsAbTestEvent,
  reorderCmsMenuItems,
  reorderCmsSections,
  saveTestimonial,
  scheduleEventColor,
  sendCmsNewsletter,
  toLocalDateTimeInputValue,
  updateCmsPastoralProfile,
  workflowCmsPage,
} from "./v2";

function makePost(overrides: Partial<CmsPostWithTaxonomies> = {}): CmsPostWithTaxonomies {
  return {
    id: "p1",
    site_id: "s1",
    slug: "testimonio-1",
    title: "Testimonio Uno",
    excerpt: null,
    content: "Contenido del testimonio",
    featured_image_url: null,
    status: "published",
    seo_json: {},
    locale: "es",
    published_at: "2026-01-01T00:00:00Z",
    expires_at: null,
    author_persona_id: null,
    created_by_persona_id: null,
    updated_by_persona_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    categories: [],
    tags: [],
    ...overrides,
  };
}

function makeCat(id: string, slug: string): import("@/types/cms-v2").CmsCategory {
  return {
    id,
    site_id: "s1",
    parent_id: null,
    slug,
    name: slug,
    description: null,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function makePublicPost(overrides: Partial<CmsPublicPost> = {}): CmsPublicPost {
  return {
    site_key: "ccf",
    slug: "testimonio-1",
    title: "Testimonio Uno",
    excerpt: null,
    content: "Contenido",
    featured_image_url: null,
    seo_json: {},
    published_at: "2026-01-01T00:00:00Z",
    author_name: null,
    categories: [],
    tags: [],
    ...overrides,
  };
}

describe("v2: adapters postToTestimonial / postToAnnouncement", () => {
  it("mapea un post publicado a testimonial aprobado con seo_json plano", () => {
    const t = postToTestimonial(
      makePost({
        seo_json: {
          emotion: "Alegría",
          media_type: "video",
          video_url: "https://v/x",
          show_on_home: true,
        },
      })
    );
    expect(t.status).toBe("approved");
    expect(t.is_approved).toBe(true);
    expect(t.published).toBe(true);
    expect(t.emotion).toBe("Alegría");
    expect(t.media_type).toBe("video");
    expect(t.video_url).toBe("https://v/x");
    expect(t.show_on_home).toBe(true);
  });

  it("usa defaults cuando el seo_json no trae emotion/media_type", () => {
    const t = postToTestimonial(makePost());
    expect(t.emotion).toBe("Testimonio");
    expect(t.media_type).toBe("text");
    expect(t.media_url).toBeNull();
  });

  it("mapea status draft → pending y archived → archived", () => {
    expect(postToTestimonial(makePost({ status: "draft" })).status).toBe("pending");
    expect(postToTestimonial(makePost({ status: "archived" })).status).toBe("archived");
    expect(postToTestimonial(makePost({ status: "in_review" })).status).toBe("pending");
  });

  it("postToAnnouncement: category/is_featured desde seo y is_active desde published", () => {
    const a = postToAnnouncement(
      makePost({
        title: "Anuncio 1",
        slug: "anuncio-1",
        seo_json: { category: "avisos", is_featured: true },
      })
    );
    expect(a.category).toBe("avisos");
    expect(a.is_featured).toBe(true);
    expect(a.is_active).toBe(true);
    expect(a.status).toBe("published");
    expect(a.title).toBe("Anuncio 1");
  });

  it("postToAnnouncement: defaults category announcements / no featured", () => {
    const a = postToAnnouncement(makePost({ status: "draft" }));
    expect(a.category).toBe("announcements");
    expect(a.is_featured).toBe(false);
    expect(a.is_active).toBe(false);
  });
});

describe("v2: adapters públicos publicPostToTestimonial / publicPostToAnnouncement", () => {
  it("mapea un CmsPublicPost a testimonial público", () => {
    const t = publicPostToTestimonial(
      makePublicPost({
        author_name: "Ana",
        seo_json: { emotion: "Gratitud", media_type: "image", show_on_home: true },
        featured_image_url: "https://img/f.png",
      })
    );
    expect(t.author_name).toBe("Ana");
    expect(t.emotion).toBe("Gratitud");
    expect(t.media_type).toBe("image");
    expect(t.image_url).toBe("https://img/f.png");
    expect(t.is_approved).toBe(true);
    expect(t.id).toBe("testimonio-1");
  });

  it("usa defaults 'General'/'text' y author null", () => {
    const t = publicPostToTestimonial(makePublicPost());
    expect(t.emotion).toBe("General");
    expect(t.media_type).toBe("text");
    expect(t.author_name).toBeNull();
  });

  it("publicPostToAnnouncement: category por defecto announcements", () => {
    const a = publicPostToAnnouncement(makePublicPost({ seo_json: { is_featured: true } }));
    expect(a.category).toBe("announcements");
    expect(a.is_featured).toBe(true);
    expect(a.slug).toBe("testimonio-1");
  });
});

describe("v2: helpers de scheduling", () => {
  it("isScheduledPage: null / published sin publish_at → false", () => {
    expect(isScheduledPage(null)).toBe(false);
    expect(isScheduledPage(undefined)).toBe(false);
    expect(isScheduledPage({ status: "published", publish_at: null })).toBe(false);
  });

  it("isScheduledPage: status scheduled o publish_at → true", () => {
    expect(isScheduledPage({ status: "scheduled", publish_at: null })).toBe(true);
    expect(isScheduledPage({ status: "draft", publish_at: "2026-02-01T10:00:00Z" })).toBe(true);
  });

  it("isExpiringPage: solo con expires_at presente", () => {
    expect(isExpiringPage(null)).toBe(false);
    expect(isExpiringPage({ status: "published", expires_at: null })).toBe(false);
    expect(isExpiringPage({ status: "published", expires_at: "2026-03-01T10:00:00Z" })).toBe(true);
    expect(isExpiringPage({ status: "draft", expires_at: "2026-03-01T10:00:00Z" })).toBe(true);
  });

  it("scheduleEventColor: expiry amber/rose según estado", () => {
    expect(scheduleEventColor("published", "expiry")).toBe("amber");
    expect(scheduleEventColor("draft", "expiry")).toBe("rose");
  });

  it("scheduleEventColor: publish blue/emerald/rose según estado", () => {
    expect(scheduleEventColor("scheduled", "publish")).toBe("blue");
    expect(scheduleEventColor("published", "publish")).toBe("emerald");
    expect(scheduleEventColor("approved", "publish")).toBe("blue");
    expect(scheduleEventColor("draft", "publish")).toBe("rose");
  });

  it("toLocalDateTimeInputValue: vacío/inválido → '' y válido → YYYY-MM-DDTHH:mm", () => {
    expect(toLocalDateTimeInputValue(null)).toBe("");
    expect(toLocalDateTimeInputValue("no-fecha")).toBe("");
    // Aserción autoconsistente con la TZ local del runner (no asume UTC).
    const iso = "2026-01-02T15:45:00Z";
    const out = toLocalDateTimeInputValue(iso);
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    expect(out).toBe(
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
    );
  });

  it("fromLocalDateTimeInputValue: vacío/inválido → null y válido → ISO local", () => {
    expect(fromLocalDateTimeInputValue(null)).toBeNull();
    expect(fromLocalDateTimeInputValue("basura")).toBeNull();
    // Igual: comparado contra el mismo Date para no depender de la TZ.
    const local = "2026-01-02T15:45";
    expect(fromLocalDateTimeInputValue(local)).toBe(new Date(local).toISOString());
  });
});

describe("v2: posts por categoría canónica (testimonials/announcements)", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
  });

  it("listCmsPostsByCategory filtra por el id de la categoría", async () => {
    const cat = makeCat("cat-1", "testimonials");
    mocks.apiFetch
      .mockResolvedValueOnce([cat])
      .mockResolvedValueOnce([
        makePost({ id: "a", slug: "a", categories: [{ ...cat }] }),
        makePost({ id: "b", slug: "b", categories: [] }),
      ]);
    const posts = await listCmsPostsByCategory("ccf", "testimonials", {}, "tok");
    expect(posts.map((p) => p.slug)).toEqual(["a"]);
  });

  it("listCmsPostsByCategory devuelve [] si la categoría no existe", async () => {
    mocks.apiFetch.mockResolvedValueOnce([makeCat("x", "otra")]);
    const posts = await listCmsPostsByCategory("ccf", "testimonials", {}, "tok");
    expect(posts).toEqual([]);
  });

  it("createCmsPostByCategory reusa la categoría existente", async () => {
    const cat = makeCat("cat-1", "announcements");
    mocks.apiFetch.mockResolvedValueOnce([cat]).mockResolvedValueOnce({ id: "nuevo" });
    const post = await createCmsPostByCategory("ccf", "announcements", { title: "T" }, "tok");
    expect(post).toEqual({ id: "nuevo" });
    const createCall = mocks.apiFetch.mock.calls[1];
    expect(createCall[0]).toContain("/posts");
    expect(createCall[1].body.category_ids).toEqual(["cat-1"]);
  });

  it("createCmsPostByCategory crea la categoría si falta y autogenera slug", async () => {
    mocks.apiFetch
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({ id: "cat-new" })
      .mockResolvedValueOnce({ id: "nuevo2" });
    const post = await createCmsPostByCategory("ccf", "testimonials", { title: "T2" }, "tok");
    expect(post.id).toBe("nuevo2");
    expect(mocks.apiFetch.mock.calls[2][1].body.slug).toMatch(/^testimonials-\d+$/);
    expect(mocks.apiFetch.mock.calls[2][1].body.category_ids).toEqual(["cat-new"]);
  });

  it("getCmsPostByCategory: null si falla o si la categoría no matchea", async () => {
    mocks.apiFetch.mockRejectedValueOnce(new Error("boom"));
    expect(await getCmsPostByCategory("ccf", "x", "testimonials", "tok")).toBeNull();

    mocks.apiFetch.mockResolvedValueOnce(makePost({ categories: [] }));
    expect(await getCmsPostByCategory("ccf", "x", "testimonials", "tok")).toBeNull();
  });

  it("getCmsPostByCategory devuelve el post cuando matchea la categoría", async () => {
    const post = makePost({ categories: [makeCat("c", "testimonials")] });
    mocks.apiFetch.mockResolvedValueOnce(post);
    expect(await getCmsPostByCategory("ccf", "t-1", "testimonials", "tok")).toEqual(post);
  });

  it("getPublicTestimonials mapea la lista pública", async () => {
    mocks.apiFetch.mockResolvedValueOnce([
      makePublicPost({ author_name: "Ana", seo_json: { emotion: "Fe" } }),
    ]);
    const items = await getPublicTestimonials("ccf");
    expect(items).toHaveLength(1);
    expect(items[0].emotion).toBe("Fe");
    expect(items[0].author).toEqual({ username: "Ana" });
    expect(mocks.apiFetch.mock.calls[0][1].query.category_slug).toBe("testimonials");
  });

  it("listPublicTestimonials y listPublicAnnouncements mapean la lista pública", async () => {
    mocks.apiFetch.mockResolvedValueOnce([makePublicPost({ seo_json: { emotion: "X" } })]);
    const ts = await listPublicTestimonials("ccf");
    expect(ts[0].emotion).toBe("X");

    mocks.apiFetch.mockResolvedValueOnce([makePublicPost({ seo_json: { category: "avisos" } })]);
    const anns = await listPublicAnnouncements("ccf");
    expect(anns[0].category).toBe("avisos");
  });
});

describe("v2: saveTestimonial", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
  });

  it("mapea emotion/media_type/status de vuelta al post y retorna el testimonial", async () => {
    mocks.apiFetch.mockResolvedValueOnce(
      makePost({ seo_json: { emotion: "Alegría", media_type: "text" } })
    );
    const saved = await saveTestimonial(
      "ccf",
      "t-1",
      {
        content: "Nuevo contenido",
        emotion: "Alegría",
        media_type: "text",
        show_on_home: true,
        status: "approved",
      },
      "tok"
    );
    expect(saved.emotion).toBe("Alegría");
    const call = mocks.apiFetch.mock.calls[0];
    expect(call[0]).toContain("/posts/t-1");
    expect(call[1].body.status).toBe("published");
    expect(call[1].body.featured_image_url).toBeNull();
  });

  it("media_type image setea featured_image_url y status archived → archived", async () => {
    mocks.apiFetch.mockResolvedValueOnce(makePost({ featured_image_url: "https://img/1.png" }));
    await saveTestimonial(
      "ccf",
      "t-2",
      { content: "c", emotion: "e", media_type: "image", image_url: "https://img/1.png", status: "archived" },
      "tok"
    );
    const call = mocks.apiFetch.mock.calls[0];
    expect(call[1].body.featured_image_url).toBe("https://img/1.png");
    expect(call[1].body.status).toBe("archived");
  });
});

describe("v2: wrappers apiFetch (contrato de llamada)", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
  });

  it("listCmsSites pasa token y ruta", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsSites("tok");
    expect(mocks.apiFetch).toHaveBeenCalledWith("/cms/v2/sites", { token: "tok" });
  });

  it("createCmsPage hace POST con payload", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ id: "p" });
    await createCmsPage("ccf", { slug: "inicio", title: "Inicio", status: "draft" }, "tok");
    const [url, opts] = mocks.apiFetch.mock.calls[0];
    expect(url).toBe("/cms/v2/sites/ccf/pages");
    expect(opts.method).toBe("POST");
    expect(opts.body.slug).toBe("inicio");
    expect(opts.token).toBe("tok");
  });

  it("workflowCmsPage hace POST con action/notes", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ id: "p" });
    await workflowCmsPage("ccf", "inicio", "publish", "lista", "tok");
    const [url, opts] = mocks.apiFetch.mock.calls[0];
    expect(url).toBe("/cms/v2/sites/ccf/pages/inicio/workflow");
    expect(opts.body).toEqual({ action: "publish", notes: "lista" });
  });

  it("listCmsPages normaliza {items} y arrays", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ items: [makePost()], total: 1 });
    expect(await listCmsPages("ccf", "tok")).toHaveLength(1);
    mocks.apiFetch.mockResolvedValueOnce([makePost(), makePost()]);
    expect(await listCmsPages("ccf", "tok")).toHaveLength(2);
  });

  it("listCmsSections normaliza {items} y arrays", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ items: [{ id: "s1" }], total: 1, skip: 0, limit: 50 });
    expect(await listCmsSections("ccf", "inicio", "tok")).toHaveLength(1);
    mocks.apiFetch.mockResolvedValueOnce([{ id: "s2" }]);
    expect(await listCmsSections("ccf", "inicio", "tok")).toHaveLength(1);
  });

  it("getPageAnalytics usa días por defecto 30 y encodeURIComponent", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ page_key: "a b", total_views: 1, days: 30, daily_views: [] });
    await getPageAnalytics("a b");
    expect(mocks.apiFetch.mock.calls[0][0]).toContain("days=30");
    expect(mocks.apiFetch.mock.calls[0][0]).toContain("a%20b");
  });

  it("wrappers de menús: list/patch/delete/reorder con ruta y payload", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsMenus("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[0][0]).toBe("/cms/v2/sites/ccf/menus");

    mocks.apiFetch.mockResolvedValueOnce({ id: "m" });
    await patchCmsMenu("ccf", "principal", { is_active: false }, "tok");
    const [, opts] = mocks.apiFetch.mock.calls[1];
    expect(opts.method).toBe("PATCH");
    expect(opts.body.is_active).toBe(false);

    mocks.apiFetch.mockResolvedValueOnce(undefined);
    await deleteCmsMenu("ccf", "principal", "tok");
    expect(mocks.apiFetch.mock.calls[2][0]).toContain("/menus/principal");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("DELETE");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await reorderCmsMenuItems("ccf", "principal", [{ id: "i1", parent_id: null, sort_order: 2 }], "tok");
    expect(mocks.apiFetch.mock.calls[3][1].body.items[0].sort_order).toBe(2);
  });

  it("wrappers de themes: create/activate/delete con payload", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ id: "t" });
    await createCmsTheme("ccf", { name: "Tema", tokens_json: { "--x": "#fff" }, is_active: true }, "tok");
    expect(mocks.apiFetch.mock.calls[0][0]).toBe("/cms/v2/sites/ccf/themes");
    expect(mocks.apiFetch.mock.calls[0][1].method).toBe("POST");

    mocks.apiFetch.mockResolvedValueOnce({ id: "t" });
    await activateCmsTheme("ccf", "t1", "tok");
    expect(mocks.apiFetch.mock.calls[1][0]).toContain("/themes/t1/activate");

    mocks.apiFetch.mockResolvedValueOnce(undefined);
    await deleteCmsTheme("ccf", "t1", "tok");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("DELETE");
  });

  it("wrappers de secciones: create/patch/delete/reorder/updateCmsSectionProps", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ id: "sec" });
    await createCmsSection("ccf", "inicio", { type: "hero", props_json: {} }, "tok");
    expect(mocks.apiFetch.mock.calls[0][1].body.type).toBe("hero");

    mocks.apiFetch.mockResolvedValueOnce({ id: "sec" });
    await patchCmsSection("ccf", "inicio", "sec", { sort_order: 3 }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].body.sort_order).toBe(3);

    mocks.apiFetch.mockResolvedValueOnce(undefined);
    await deleteCmsSection("ccf", "inicio", "sec", "tok");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("DELETE");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await reorderCmsSections("ccf", "inicio", [{ id: "s1", sort_order: 1 }], "tok");
    expect(mocks.apiFetch.mock.calls[3][1].body.items).toHaveLength(1);
  });

  it("wrappers de popups: create/patch/delete/listPublicPopups", async () => {
    mocks.apiFetch.mockResolvedValueOnce({ id: "pop" });
    await createCmsPopup("ccf", { name: "P", content_html: "<p>x</p>", trigger_type: "time_delay" }, "tok");
    expect(mocks.apiFetch.mock.calls[0][1].body.name).toBe("P");

    mocks.apiFetch.mockResolvedValueOnce({ id: "pop" });
    await patchCmsPopup("ccf", "pop", { is_active: false }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].method).toBe("PATCH");

    mocks.apiFetch.mockResolvedValueOnce(undefined);
    await deleteCmsPopup("ccf", "pop", "tok");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("DELETE");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await listPublicPopups("ccf");
    expect(mocks.apiFetch.mock.calls[3][1].query.site_key).toBe("ccf");
  });

  it("wrappers de forms: list/create/put/patch/delete/submissions", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsForms("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[0][0]).toBe("/cms/v2/sites/ccf/forms");

    mocks.apiFetch.mockResolvedValueOnce({ id: "f" });
    await createCmsForm("ccf", { name: "Contacto" }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].method).toBe("POST");

    mocks.apiFetch.mockResolvedValueOnce({ id: "f" });
    await putCmsForm("ccf", "f", { name: "X" }, "tok");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("PUT");

    mocks.apiFetch.mockResolvedValueOnce({ id: "f" });
    await patchCmsForm("ccf", "f", { is_active: false }, "tok");
    expect(mocks.apiFetch.mock.calls[3][1].method).toBe("PATCH");

    mocks.apiFetch.mockResolvedValueOnce(undefined);
    await deleteCmsForm("ccf", "f", "tok");
    expect(mocks.apiFetch.mock.calls[4][1].method).toBe("DELETE");

    mocks.apiFetch.mockResolvedValueOnce({ page: 1, page_size: 20, total: 0, items: [] });
    await listCmsFormSubmissions("ccf", "f", 2, 10, "tok");
    expect(mocks.apiFetch.mock.calls[5][1].query.page).toBe("2");
    expect(mocks.apiFetch.mock.calls[5][1].query.page_size).toBe("10");
  });

  it("wrappers de newsletters y subscribers", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsNewsletters("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[0][0]).toContain("/newsletters");

    mocks.apiFetch.mockResolvedValueOnce({ id: "n" });
    await createCmsNewsletter("ccf", { name: "N", subject: "S", content_html: "<p>h</p>" }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].method).toBe("POST");

    mocks.apiFetch.mockResolvedValueOnce({ id: "n" });
    await sendCmsNewsletter("ccf", "n", "tok");
    expect(mocks.apiFetch.mock.calls[2][0]).toContain("/newsletters/n/send");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsSubscribers("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[3][0]).toContain("/subscribers");

    mocks.apiFetch.mockResolvedValueOnce({ success: true, imported_count: 2, total_subscribers: 2 });
    await importCmsSubscribers("ccf", { emails: ["a@b.c"] }, "tok");
    expect(mocks.apiFetch.mock.calls[4][0]).toContain("/subscribers/import");
    expect(mocks.apiFetch.mock.calls[4][1].body.emails).toEqual(["a@b.c"]);
  });

  it("wrappers de ab-tests: create/get/patch/record/results/apply/delete", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsAbTests("ccf", { status: "running" }, "tok");
    expect(mocks.apiFetch.mock.calls[0][1].query.status).toBe("running");

    mocks.apiFetch.mockResolvedValueOnce({ id: "ab" });
    await createCmsAbTest("ccf", { name: "A/B", page_id: "p", section_a_id: "a", section_b_id: "b" }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].method).toBe("POST");

    mocks.apiFetch.mockResolvedValueOnce({ id: "ab" });
    await getCmsAbTest("ccf", "ab", "tok");
    expect(mocks.apiFetch.mock.calls[2][0]).toContain("/ab-tests/ab");

    mocks.apiFetch.mockResolvedValueOnce({ id: "ab" });
    await patchCmsAbTest("ccf", "ab", { traffic_split: 50 }, "tok");
    expect(mocks.apiFetch.mock.calls[3][1].body.traffic_split).toBe(50);

    mocks.apiFetch.mockResolvedValueOnce({ id: "ev" });
    await recordCmsAbTestEvent("ccf", "ab", { variant: "a", event_type: "click", visitor_id: "v1" });
    expect(mocks.apiFetch.mock.calls[4][0]).toContain("/ab-tests/ab/record-event");

    mocks.apiFetch.mockResolvedValueOnce({ id: "ab" });
    await applyCmsAbTestWinner("ccf", "ab", { winner_variant: "b" }, "tok");
    expect(mocks.apiFetch.mock.calls[5][0]).toContain("/ab-tests/ab/apply-winner");

    mocks.apiFetch.mockResolvedValueOnce({});
    await deleteCmsAbTest("ccf", "ab", "tok");
    expect(mocks.apiFetch.mock.calls[6][1].method).toBe("DELETE");
  });

  it("wrappers de comentarios y categorías/tags", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsCategories("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[0][0]).toContain("/categories");

    mocks.apiFetch.mockResolvedValueOnce({ id: "c" });
    await createCmsCategory("ccf", { slug: "nuevas", name: "Nuevas" }, "tok");
    expect(mocks.apiFetch.mock.calls[1][1].method).toBe("POST");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await listCmsTags("ccf", "tok");
    expect(mocks.apiFetch.mock.calls[2][0]).toContain("/tags");

    mocks.apiFetch.mockResolvedValueOnce({ items: [], total: 0 });
    await listCmsPostComments("ccf", { status: "pending", skip: 5, limit: 20 }, "tok");
    const q = mocks.apiFetch.mock.calls[3][1].query;
    expect(q.status).toBe("pending");
    expect(q.skip).toBe("5");
    expect(q.limit).toBe("20");

    mocks.apiFetch.mockResolvedValueOnce({ id: "cm" });
    await patchCmsPostCommentStatus("ccf", "cm", "approved", "tok");
    expect(mocks.apiFetch.mock.calls[4][1].body.status).toBe("approved");

    mocks.apiFetch.mockResolvedValueOnce({ id: "cm" });
    await createPublicPostComment("post-1", { author_name: "Ana", author_email: "a@b.c", content: "ok" });
    expect(mocks.apiFetch.mock.calls[5][0]).toContain("/public/posts/post-1/comments");
  });

  it("wrappers de pastoral team y public page/preview", async () => {
    mocks.apiFetch.mockResolvedValueOnce([]);
    await getPublicPastoralTeam("ccf");
    expect(mocks.apiFetch.mock.calls[0][0]).toContain("/public/sites/ccf/pastoral-team");

    mocks.apiFetch.mockResolvedValueOnce([]);
    await getCmsPastoralTeam("tok");
    expect(mocks.apiFetch.mock.calls[1][0]).toContain("/cms/pastoral-team");

    mocks.apiFetch.mockResolvedValueOnce({ id: "p" });
    await updateCmsPastoralProfile("pers-1", { name: "X" }, "tok");
    expect(mocks.apiFetch.mock.calls[2][1].method).toBe("PATCH");

    mocks.apiFetch.mockResolvedValueOnce({ slug: "inicio" });
    await getCmsPublicPage("ccf", "inicio");
    expect(mocks.apiFetch.mock.calls[3][1].silent).toBe(true);

    mocks.apiFetch.mockResolvedValueOnce({ slug: "inicio" });
    await getCmsPagePreview("ccf", "inicio", "tok");
    expect(mocks.apiFetch.mock.calls[4][1].cache).toBe("no-store");
  });
});

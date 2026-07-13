import { describe, expect, it } from "vitest";
import {
  matchesCmsPathRule,
  normalizeHeroProps,
  normalizePopupProps,
  shouldRenderCmsPopup,
} from "./heroPopup";

describe("CMS hero normalization", () => {
  it("maps builder hero fields to public renderer props", () => {
    const hero = normalizeHeroProps({
      eyebrow: "Bienvenido",
      title_lead: "Una casa",
      title_accent: "para todos",
      title_tail: "en la ciudad",
      description: "Texto principal",
      primary_cta: "Visitar",
      primary_cta_href: "/conocer-a-jesus",
      secondary_cta: "Eventos",
      secondary_cta_href: "/eventos",
      bg_image: "/static/cms/hero.webp",
    });

    expect(hero).toMatchObject({
      eyebrow: "Bienvenido",
      title: undefined,
      titleLead: "Una casa",
      titleAccent: "para todos",
      titleTail: "en la ciudad",
      description: "Texto principal",
      primaryCta: { label: "Visitar", href: "/conocer-a-jesus" },
      secondaryCta: { label: "Eventos", href: "/eventos" },
    });
    expect(hero.slides[0]).toMatchObject({
      src: "/api/static/cms/hero.webp",
      alt: "",
      caption: "Texto principal",
    });
  });

  it("keeps simple title/body/cta/image_url pages working", () => {
    const hero = normalizeHeroProps({
      title: "Titulo simple",
      body: "Cuerpo",
      cta_label: "Continuar",
      cta_href: "/nosotros",
      image_url: "/images/convenccion/IMG_6813.webp",
    });

    expect(hero.title).toBe("Titulo simple");
    expect(hero.description).toBe("Cuerpo");
    expect(hero.primaryCta).toEqual({ label: "Continuar", href: "/nosotros" });
    expect(hero.slides[0]?.src).toBe("/images/convenccion/IMG_6813.webp");
  });

  it("filters archived gallery items and normalizes CMS media URLs", () => {
    const hero = normalizeHeroProps({
      title: "Galeria",
      items: [
        { url: "/static/cms/active.webp", title: "Activa" },
        { url: "/static/cms/archived.webp", title: "Archivada", status: "archived" },
      ],
    });

    expect(hero.slides).toHaveLength(1);
    expect(hero.slides[0]).toMatchObject({
      src: "/api/static/cms/active.webp",
      title: "Activa",
    });
  });
});

describe("CMS popup normalization and visibility", () => {
  it("allows zero delay and clamps invalid dismiss settings", () => {
    const popup = normalizePopupProps({
      delay_ms: 0,
      dismiss_mode: "invalid",
      dismiss_days: -10,
    }, "section-1");

    expect(popup.delayMs).toBe(0);
    expect(popup.dismissMode).toBe("local");
    expect(popup.dismissDays).toBe(1);
    expect(popup.dismissKey).toBe("cms_popup_section-1");
  });

  it("parses show/hide path lists from textarea strings", () => {
    const popup = normalizePopupProps({
      show_on_paths: "/\n/nosotros, /eventos/*",
      hide_on_paths: "/plataforma\n/login",
    }, "section-2");

    expect(popup.showOnPaths).toEqual(["/", "/nosotros", "/eventos/*"]);
    expect(popup.hideOnPaths).toEqual(["/plataforma", "/login"]);
  });

  it("matches exact, nested, and wildcard path rules", () => {
    expect(matchesCmsPathRule("/", "/")).toBe(true);
    expect(matchesCmsPathRule("/nosotros/equipo", "/nosotros")).toBe(true);
    expect(matchesCmsPathRule("/eventos/especial", "/eventos/*")).toBe(true);
    expect(matchesCmsPathRule("/nosotros", "/")).toBe(true);
  });

  it("honors route include/exclude and publication windows", () => {
    const popup = normalizePopupProps({
      start_at: "2026-07-01T00:00:00Z",
      end_at: "2026-07-31T23:59:59Z",
      show_on_paths: ["/eventos/*"],
      hide_on_paths: ["/eventos/privado"],
    }, "section-3");
    const now = new Date("2026-07-13T12:00:00Z");

    expect(shouldRenderCmsPopup(popup, "/eventos/conferencia", now)).toBe(true);
    expect(shouldRenderCmsPopup(popup, "/eventos/privado", now)).toBe(false);
    expect(shouldRenderCmsPopup(popup, "/nosotros", now)).toBe(false);
    expect(shouldRenderCmsPopup(popup, "/eventos/conferencia", new Date("2026-08-01T00:00:00Z"))).toBe(false);
  });
});

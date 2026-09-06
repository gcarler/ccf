/**
 * Test Suite for Milestone 3: Dynamic Section Rendering in Public Home Page
 * File: frontend/src/app/(public)/__tests__/PublicHomePageReorder.test.tsx
 *
 * Verifies:
 * 1. Default modular order: renders Welcome, Activities, Newsletter, Discover CTA in ascending sort_order.
 * 2. Dynamic reordering: moving Newsletter before Welcome (e.g. Newsletter sort_order: 1, Welcome sort_order: 2)
 *    immediately reflects Newsletter before Welcome in DOM.
 * 3. Feed fallback backward compatibility: passing only monolithic combined feed section renders Bento, Activities,
 *    and Newsletter with fallback props intact.
 * 4. Missing props gracefully fallback without runtime exceptions or crashes.
 */

import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PublicHomePage from "../PublicHomePage";
import type { CmsPublicPage, CmsSection } from "@/types/cms-v2";
import { filterMotionProps } from "@/test-utils/filter-motion-props";

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("next/image", () => ({
  __esModule: true,
  default: ({ src, alt, ...props }: { src?: string; alt?: string; [key: string]: unknown }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt || "mock-img"} {...props} />
  ),
}));

vi.mock("framer-motion", () => {
  const cleanProps = (props: Record<string, unknown>) => {
    const filtered = filterMotionProps(props);
    const { whileInView: _whileInView, viewport: _viewport, ...rest } = filtered;
    return rest;
  };
  return {
    motion: {
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
        <div {...cleanProps(props as Record<string, unknown>)}>{children}</div>
      ),
      section: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => (
        <section {...cleanProps(props as Record<string, unknown>)}>{children}</section>
      ),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue([]),
}));

vi.mock("@/hooks/useCmsV2Page", () => ({
  useCmsV2Page: vi.fn().mockReturnValue(null),
}));

vi.mock("@/components/public/PublicHeroWithSlides", () => ({
  __esModule: true,
  default: () => <div data-testid="public-hero" data-section-key="hero">Hero Component</div>,
}));

// ── Test Fixtures ───────────────────────────────────────────────────────────

const createMockModularSections = (): CmsSection[] => [
  {
    id: "sec-hero",
    page_id: "page-home",
    section_key: "hero",
    type: "hero",
    sort_order: 0,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: {
      title_lead: "Bienvenidos a",
      title_accent: "CCF",
      title_tail: "Faro",
    },
  },
  {
    id: "sec-welcome",
    page_id: "page-home",
    section_key: "welcome",
    type: "feed",
    sort_order: 1,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: {
      section_title: "Bienvenidos a Casa",
      section_description: "Rutas públicas para conocer la comunidad.",
      featured_card: {
        title: "Nuestra Comunidad",
        desc: "Un lugar para crecer juntos.",
        cta: "Conocer más",
        href: "/nosotros",
      },
      cards: [
        { title: "Prédicas", desc: "Mensajes de esperanza", href: "/predicas" },
      ],
    },
  },
  {
    id: "sec-activities",
    page_id: "page-home",
    section_key: "activities",
    type: "events_calendar",
    sort_order: 2,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: {
      title: "Actividades Recientes",
      activities_title: "Actividades Recientes",
      eyebrow: "Actualidad",
      activities_eyebrow: "Actualidad",
      empty: "No hay actividades próximas por ahora.",
      activities_empty: "No hay actividades próximas por ahora.",
    },
  },
  {
    id: "sec-newsletter",
    page_id: "page-home",
    section_key: "newsletter",
    type: "newsletter",
    sort_order: 3,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: {
      title: "¿Quieres recibir nuestras novedades?",
      newsletter_title: "¿Quieres recibir nuestras novedades?",
      eyebrow: "Boletín semanal",
      newsletter_eyebrow: "Boletín semanal",
      description: "Meditaciones semanales y novedades.",
      newsletter_description: "Meditaciones semanales y novedades.",
      placeholder: "Tu correo electrónico",
      newsletter_placeholder: "Tu correo electrónico",
      submit: "Suscribirme",
      newsletter_submit: "Suscribirme",
    },
  },
  {
    id: "sec-discover-cta",
    page_id: "page-home",
    section_key: "discover_cta",
    type: "cta_block",
    sort_order: 4,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: {
      eyebrow: "Una invitación para ti",
      title: "¿Quieres conocer a Jesús?",
      description: "No es una religión, es una relación transformadora.",
      cta_label: "Quiero conocer a Jesús",
      cta_href: "/conocer-a-jesus",
    },
  },
];

const createMockModularPage = (): CmsPublicPage => ({
  site_key: "ccf",
  slug: "home",
  title: "CCF - Comunidad Cristiana El Faro",
  seo_json: {},
  sections: createMockModularSections(),
});

const createMockFallbackFeedPage = (): CmsPublicPage => ({
  site_key: "ccf",
  slug: "home",
  title: "CCF - Comunidad Cristiana El Faro",
  seo_json: {},
  sections: [
    {
      id: "sec-hero",
      page_id: "page-home",
      section_key: "hero",
      type: "hero",
      sort_order: 0,
      is_visible: true,
      status: "active",
      created_at: "",
      updated_at: "",
      props_json: {
        title_lead: "Bienvenidos a",
        title_accent: "CCF",
      },
    },
    {
      id: "sec-feed-fallback",
      page_id: "page-home",
      section_key: "feed",
      type: "feed",
      sort_order: 1,
      is_visible: true,
      status: "active",
      created_at: "",
      updated_at: "",
      props_json: {
        eyebrow: "Nuestra esencia",
        section_title: "Bienvenidos a Casa Fallback",
        section_description: "Comunidad de fe y crecimiento.",
        featured_card: {
          title: "Comunidad Faro Fallback",
          desc: "Un lugar para pertenecer.",
          cta: "Conocer más",
          href: "/nosotros",
        },
        cards: [
          { title: "Grupos de Conexión", desc: "Crece en comunidad", href: "/grupos" },
        ],
        // Embedded fallback activities
        activities_eyebrow: "Próximos Encuentros",
        activities_title: "Actividades de la Iglesia Fallback",
        activities_view_all: "Ver todos los eventos",
        activities_view_all_href: "/eventos",
        activities_empty: "No hay eventos esta semana.",
        // Embedded fallback newsletter
        newsletter_eyebrow: "Mantente Conectado",
        newsletter_title: "Boletín Informativo El Faro Fallback",
        newsletter_description: "Entérate de todo lo que sucede cada semana.",
        newsletter_placeholder: "Ingresa tu email",
        newsletter_submit: "Unirme al boletín",
      },
    },
    {
      id: "sec-discover-cta",
      page_id: "page-home",
      section_key: "discover_cta",
      type: "cta_block",
      sort_order: 2,
      is_visible: true,
      status: "active",
      created_at: "",
      updated_at: "",
      props_json: {
        title: "¿Quieres conocer a Jesús?",
        cta_label: "Quiero conocer a Jesús",
        cta_href: "/conocer-a-jesus",
      },
    },
  ],
});

// ── Test Suite ──────────────────────────────────────────────────────────────

describe("PublicHomePage Dynamic Section Rendering (Milestone 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ── Test 1: Default Modular Order ─────────────────────────────────────────
  describe("Test 1: Default Modular Order", () => {
    it("renders Welcome, Activities, Newsletter, and Discover CTA in ascending sort_order", () => {
      const page = createMockModularPage();
      const { container } = render(<PublicHomePage initialHomePage={page} />);

      // 1. Assert presence of each section's primary content
      expect(screen.getByRole("heading", { name: /Bienvenidos a Casa/i })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: /Actividades Recientes/i })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: /¿Quieres recibir nuestras novedades\?/i })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: /¿Quieres conocer a Jesús\?/i })).toBeInTheDocument();

      // 2. Assert presence via data-testid
      const welcome = screen.getByTestId("public-section-welcome");
      const activities = screen.getByTestId("public-section-activities");
      const newsletter = screen.getByTestId("public-section-newsletter");
      const discoverCta = screen.getByTestId("public-section-discover_cta");

      expect(welcome).toBeInTheDocument();
      expect(activities).toBeInTheDocument();
      expect(newsletter).toBeInTheDocument();
      expect(discoverCta).toBeInTheDocument();

      // Also assert public-home-section-* test ids
      expect(screen.getByTestId("public-home-section-welcome")).toBeInTheDocument();
      expect(screen.getByTestId("public-home-section-activities")).toBeInTheDocument();
      expect(screen.getByTestId("public-home-section-newsletter")).toBeInTheDocument();
      expect(screen.getByTestId("public-home-section-discover_cta")).toBeInTheDocument();

      // 3. Assert relative DOM position via compareDocumentPosition
      // Welcome comes BEFORE Activities
      expect(welcome.compareDocumentPosition(activities) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      // Activities comes BEFORE Newsletter
      expect(activities.compareDocumentPosition(newsletter) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      // Newsletter comes BEFORE Discover CTA
      expect(newsletter.compareDocumentPosition(discoverCta) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

      // 4. Assert exact sequence by querying data-section-key in container
      const sectionKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(sectionKeys).toEqual(["welcome", "activities", "newsletter", "discover_cta"]);
    });
  });

  // ── Test 2: Dynamic Reordering ───────────────────────────────────────────
  describe("Test 2: Dynamic Reordering", () => {
    it("immediately reflects Newsletter before Welcome when Newsletter sort_order is lower than Welcome", () => {
      const defaultPage = createMockModularPage();
      const { rerender, container } = render(<PublicHomePage initialHomePage={defaultPage} />);

      // Verify baseline order: Welcome is before Newsletter
      let welcome = screen.getByTestId("public-section-welcome");
      let newsletter = screen.getByTestId("public-section-newsletter");
      expect(welcome.compareDocumentPosition(newsletter) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

      // Create reordered page: Newsletter moved to sort_order 1, Welcome moved to sort_order 2
      const reorderedPage: CmsPublicPage = {
        ...defaultPage,
        sections: [
          { ...defaultPage.sections[0], sort_order: 0 }, // hero
          { ...defaultPage.sections[3], sort_order: 1 }, // newsletter moved to 1
          { ...defaultPage.sections[1], sort_order: 2 }, // welcome moved to 2
          { ...defaultPage.sections[2], sort_order: 3 }, // activities at 3
          { ...defaultPage.sections[4], sort_order: 4 }, // discover_cta at 4
        ],
      };

      rerender(<PublicHomePage initialHomePage={reorderedPage} />);

      // Re-query section elements from DOM
      welcome = screen.getByTestId("public-section-welcome");
      newsletter = screen.getByTestId("public-section-newsletter");
      const activities = screen.getByTestId("public-section-activities");
      const discoverCta = screen.getByTestId("public-section-discover_cta");

      // Newsletter is now strictly BEFORE Welcome in DOM!
      expect(newsletter.compareDocumentPosition(welcome) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      // Welcome is before Activities
      expect(welcome.compareDocumentPosition(activities) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      // Activities is before Discover CTA
      expect(activities.compareDocumentPosition(discoverCta) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

      // Assert full sequence reflects new ordering: newsletter -> welcome -> activities -> discover_cta
      const sectionKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(sectionKeys).toEqual(["newsletter", "welcome", "activities", "discover_cta"]);
    });

    it("supports moving Activities above Welcome and Newsletter to the bottom", () => {
      const defaultPage = createMockModularPage();
      const reorderedPage: CmsPublicPage = {
        ...defaultPage,
        sections: [
          { ...defaultPage.sections[0], sort_order: 0 }, // hero
          { ...defaultPage.sections[2], sort_order: 1 }, // activities at 1
          { ...defaultPage.sections[1], sort_order: 2 }, // welcome at 2
          { ...defaultPage.sections[4], sort_order: 3 }, // discover_cta at 3
          { ...defaultPage.sections[3], sort_order: 4 }, // newsletter at 4
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={reorderedPage} />);

      const sectionKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(sectionKeys).toEqual(["activities", "welcome", "discover_cta", "newsletter"]);
    });
  });

  // ── Test 3: Monolithic Feed Backward Compatibility ────────────────────────
  describe("Test 3: Monolithic Feed Backward Compatibility", () => {
    it("renders Bento, Activities, and Newsletter with fallback props when only combined feed section exists", () => {
      const fallbackPage = createMockFallbackFeedPage();
      const { container } = render(<PublicHomePage initialHomePage={fallbackPage} />);

      // 1. Bento rendered with fallback props from feed
      expect(screen.getByRole("heading", { name: /Bienvenidos a Casa Fallback/i })).toBeInTheDocument();
      expect(screen.getByText(/Comunidad Faro Fallback/i)).toBeInTheDocument();
      expect(screen.getByText(/Grupos de Conexión/i)).toBeInTheDocument();

      // 2. Activities rendered with fallback props from feed
      expect(screen.getByRole("heading", { name: /Actividades de la Iglesia Fallback/i })).toBeInTheDocument();
      expect(screen.getByText(/Próximos Encuentros/i)).toBeInTheDocument();
      expect(screen.getByText(/No hay eventos esta semana/i)).toBeInTheDocument();

      // 3. Newsletter rendered with fallback props from feed
      expect(screen.getByRole("heading", { name: /Boletín Informativo El Faro Fallback/i })).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Ingresa tu email/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Unirme al boletín/i })).toBeInTheDocument();

      // 4. Sequence assertion: Bento -> Activities -> Newsletter -> Discover CTA
      const bentoEl = screen.getByText("Bienvenidos a Casa Fallback");
      const actEl = screen.getByText("Actividades de la Iglesia Fallback");
      const nlEl = screen.getByText("Boletín Informativo El Faro Fallback");
      const ctaEl = screen.getByText("¿Quieres conocer a Jesús?");

      expect(bentoEl.compareDocumentPosition(actEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(actEl.compareDocumentPosition(nlEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(nlEl.compareDocumentPosition(ctaEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

      const sectionKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(sectionKeys).toEqual(["welcome", "activities", "newsletter", "discover_cta"]);
    });
  });

  // ── Test 4: Graceful Missing Props Fallback ──────────────────────────────
  describe("Test 4: Missing Props Graceful Fallback", () => {
    it("renders without runtime exceptions when initialHomePage is null or undefined", () => {
      expect(() => {
        render(<PublicHomePage initialHomePage={null} />);
      }).not.toThrow();

      // Fallback Discover CTA default copy is preserved
      expect(screen.getByText(/¿Quieres conocer a Jesús\?/i)).toBeInTheDocument();
    });

    it("renders without runtime exceptions when sections array is empty", () => {
      const emptyPage: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Página Vacía",
        seo_json: {},
        sections: [],
      };

      expect(() => {
        render(<PublicHomePage initialHomePage={emptyPage} />);
      }).not.toThrow();

      // Verify page container is present
      expect(screen.getByText(/¿Quieres conocer a Jesús\?/i)).toBeInTheDocument();
    });

    it("renders safely when sections contain empty props_json without crashing", () => {
      const emptyPropsPage: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Página Props Vacíos",
        seo_json: {},
        sections: [
          {
            id: "s-hero",
            page_id: "p-1",
            section_key: "hero",
            type: "hero",
            sort_order: 0,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          {
            id: "s-welcome",
            page_id: "p-1",
            section_key: "welcome",
            type: "feed",
            sort_order: 1,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          {
            id: "s-activities",
            page_id: "p-1",
            section_key: "activities",
            type: "events_calendar",
            sort_order: 2,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          {
            id: "s-newsletter",
            page_id: "p-1",
            section_key: "newsletter",
            type: "newsletter",
            sort_order: 3,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          {
            id: "s-discover",
            page_id: "p-1",
            section_key: "discover_cta",
            type: "cta_block",
            sort_order: 4,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
        ],
      };

      expect(() => {
        render(<PublicHomePage initialHomePage={emptyPropsPage} />);
      }).not.toThrow();

      expect(screen.getByText(/¿Quieres conocer a Jesús\?/i)).toBeInTheDocument();
    });

    it("safely ignores hidden (is_visible=false) or archived sections", () => {
      const pageWithHiddenSections: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "CCF",
        seo_json: {},
        sections: [
          ...createMockModularSections().slice(0, 3),
          {
            id: "sec-newsletter-hidden",
            page_id: "page-home",
            section_key: "newsletter",
            type: "newsletter",
            sort_order: 3,
            is_visible: false, // hidden!
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: { title: "Boletín Oculto" },
          },
          createMockModularSections()[4],
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={pageWithHiddenSections} />);

      expect(screen.queryByText("Boletín Oculto")).not.toBeInTheDocument();

      const sectionKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(sectionKeys).toEqual(["welcome", "activities", "discover_cta"]);
    });
  });
});

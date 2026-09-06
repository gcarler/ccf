/**
 * Adversarial Empirical Stress Test Suite for Milestone 3
 * Tests all 24 permutations, dynamic re-rendering, boundary edge cases,
 * corrupted props, duplicate/negative sort_order, and feed fallbacks.
 */

import React from "react";
import { render, cleanup } from "@testing-library/react";
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

// Helper to generate base section fixtures
function createBaseSection(key: string, type: string, sort_order: number): CmsSection {
  const propsMap: Record<string, Record<string, unknown>> = {
    welcome: {
      section_title: "Bienvenidos a Casa",
      section_description: "Comunidad de fe",
      featured_card: { title: "Destacado", desc: "Descripción", cta: "Ver", href: "/ver" },
      cards: [{ title: "Card 1", desc: "Desc 1", href: "/c1" }],
    },
    activities: {
      title: "Actividades Recientes",
      eyebrow: "Actualidad",
      empty: "Sin actividades",
    },
    newsletter: {
      title: "¿Quieres recibir novedades?",
      description: "Boletín semanal",
      submit: "Suscribirse",
    },
    discover_cta: {
      title: "¿Quieres conocer a Jesús?",
      cta_label: "Conocer",
      cta_href: "/conocer",
    },
  };

  return {
    id: `sec-${key}`,
    page_id: "page-1",
    section_key: key,
    type,
    sort_order,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
    props_json: propsMap[key] || {},
  };
}

// Generate all permutations of an array
function permute<T>(arr: T[]): T[][] {
  if (arr.length <= 1) return [arr];
  const result: T[][] = [];
  for (let i = 0; i < arr.length; i++) {
    const current = arr[i];
    const remaining = [...arr.slice(0, i), ...arr.slice(i + 1)];
    const remainingPermuted = permute(remaining);
    for (const p of remainingPermuted) {
      result.push([current, ...p]);
    }
  }
  return result;
}

describe("Milestone 3 Empirical Challenger: Stress & Permutation Harness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ── Dimension 1: Full 24 Permutations Oracle ─────────────────────────────
  describe("Dimension 1: Complete 24 Section Permutations Oracle", () => {
    const sectionTypes: Record<string, string> = {
      welcome: "feed",
      activities: "events_calendar",
      newsletter: "newsletter",
      discover_cta: "cta_block",
    };

    const keys = ["welcome", "activities", "newsletter", "discover_cta"];
    const all24Permutations = permute(keys);

    expect(all24Permutations).toHaveLength(24);

    all24Permutations.forEach((permutation, idx) => {
      it(`Permutation #${idx + 1}: renders [${permutation.join(" -> ")}] in exact DOM order`, () => {
        const sections: CmsSection[] = [
          {
            id: "sec-hero",
            page_id: "page-1",
            section_key: "hero",
            type: "hero",
            sort_order: 0,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          ...permutation.map((key, pos) => createBaseSection(key, sectionTypes[key], pos + 1)),
        ];

        const page: CmsPublicPage = {
          site_key: "ccf",
          slug: "home",
          title: "Test Permutations",
          seo_json: {},
          sections,
        };

        const { container } = render(<PublicHomePage initialHomePage={page} />);

        const domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
          .map((el) => el.getAttribute("data-section-key"))
          .filter((k) => k !== "hero");

        expect(domOrder).toEqual(permutation);

        // Also check pairwise compareDocumentPosition
        for (let i = 0; i < permutation.length - 1; i++) {
          const firstEl = container.querySelector(`[data-section-key="${permutation[i]}"]`);
          const secondEl = container.querySelector(`[data-section-key="${permutation[i + 1]}"]`);
          expect(firstEl).toBeTruthy();
          expect(secondEl).toBeTruthy();
          expect(firstEl!.compareDocumentPosition(secondEl!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        }
      });
    });
  });

  // ── Dimension 2: Explicit Target Scenarios ────────────────────────────────
  describe("Dimension 2: Specific Reordering Scenarios", () => {
    it("Newsletter (sort_order: 1) before Welcome (sort_order: 2)", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          createBaseSection("newsletter", "newsletter", 1),
          createBaseSection("welcome", "feed", 2),
          createBaseSection("activities", "events_calendar", 3),
          createBaseSection("discover_cta", "cta_block", 4),
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);
      const domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(domOrder).toEqual(["newsletter", "welcome", "activities", "discover_cta"]);
    });

    it("Activities at the top, Discover CTA before Newsletter", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          createBaseSection("activities", "events_calendar", 1),
          createBaseSection("welcome", "feed", 2),
          createBaseSection("discover_cta", "cta_block", 3),
          createBaseSection("newsletter", "newsletter", 4),
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);
      const domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(domOrder).toEqual(["activities", "welcome", "discover_cta", "newsletter"]);
    });
  });

  // ── Dimension 3: Consecutive Rerenders & State Stability ───────────────────
  describe("Dimension 3: Dynamic State Transitions & Rerenders", () => {
    it("dynamically reacts to multiple consecutive section swaps without hydration or state artifacts", () => {
      const baseSections = [
        createBaseSection("welcome", "feed", 1),
        createBaseSection("activities", "events_calendar", 2),
        createBaseSection("newsletter", "newsletter", 3),
        createBaseSection("discover_cta", "cta_block", 4),
      ];

      const page1: CmsPublicPage = { site_key: "ccf", slug: "home", title: "Home", seo_json: {}, sections: baseSections };
      const { rerender, container } = render(<PublicHomePage initialHomePage={page1} />);

      let domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");
      expect(domOrder).toEqual(["welcome", "activities", "newsletter", "discover_cta"]);

      // Step 2: Swap Newsletter to 1
      const page2: CmsPublicPage = {
        ...page1,
        sections: [
          createBaseSection("newsletter", "newsletter", 1),
          createBaseSection("welcome", "feed", 2),
          createBaseSection("activities", "events_calendar", 3),
          createBaseSection("discover_cta", "cta_block", 4),
        ],
      };
      rerender(<PublicHomePage initialHomePage={page2} />);

      domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");
      expect(domOrder).toEqual(["newsletter", "welcome", "activities", "discover_cta"]);

      // Step 3: Move Discover CTA to top
      const page3: CmsPublicPage = {
        ...page1,
        sections: [
          createBaseSection("discover_cta", "cta_block", 1),
          createBaseSection("newsletter", "newsletter", 2),
          createBaseSection("welcome", "feed", 3),
          createBaseSection("activities", "events_calendar", 4),
        ],
      };
      rerender(<PublicHomePage initialHomePage={page3} />);

      domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");
      expect(domOrder).toEqual(["discover_cta", "newsletter", "welcome", "activities"]);
    });
  });

  // ── Dimension 4: Boundary Cases & Sort Order Robustness ───────────────────
  describe("Dimension 4: Boundary Cases & Sort Order Robustness", () => {
    it("handles negative and non-sequential sort_orders correctly", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          createBaseSection("newsletter", "newsletter", -50),
          createBaseSection("discover_cta", "cta_block", 0),
          createBaseSection("activities", "events_calendar", 25),
          createBaseSection("welcome", "feed", 1000),
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);
      const domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(domOrder).toEqual(["newsletter", "discover_cta", "activities", "welcome"]);
    });

    it("handles sections with null or undefined sort_order without crash", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          { ...createBaseSection("welcome", "feed", 0), sort_order: undefined as unknown as number },
          createBaseSection("newsletter", "newsletter", 1),
          { ...createBaseSection("activities", "events_calendar", 0), sort_order: null as unknown as number },
          createBaseSection("discover_cta", "cta_block", 2),
        ],
      };

      expect(() => render(<PublicHomePage initialHomePage={page} />)).not.toThrow();
    });

    it("handles unknown section_key or unexpected type gracefully", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          createBaseSection("welcome", "feed", 1),
          {
            id: "sec-custom",
            page_id: "p1",
            section_key: "unsupported_key",
            type: "custom_future_type",
            sort_order: 2,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {},
          },
          createBaseSection("newsletter", "newsletter", 3),
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);
      const domOrder = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      expect(domOrder).toEqual(["welcome", "newsletter"]);
    });

    it("handles corrupted props_json safely", () => {
      const corruptedPage: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Home",
        seo_json: {},
        sections: [
          {
            id: "s-1",
            page_id: "p1",
            section_key: "welcome",
            type: "feed",
            sort_order: 1,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {
              cards: "not an array",
              featured_card: 12345,
              section_title: null,
            } as unknown as Record<string, unknown>,
          },
          {
            id: "s-2",
            page_id: "p1",
            section_key: "activities",
            type: "events_calendar",
            sort_order: 2,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: {
              title: undefined,
              empty: false,
            } as unknown as Record<string, unknown>,
          },
        ],
      };

      expect(() => render(<PublicHomePage initialHomePage={corruptedPage} />)).not.toThrow();
    });
  });
});

  // ── Dimension 5: Deep Edge Cases (null, empty, is_visible=false, hero pinning) ─
  describe("Dimension 5: Deep Edge Cases Specified in Milestone 3", () => {
    it("handles initialHomePage = null gracefully without throwing", () => {
      let renderResult: ReturnType<typeof render> | undefined;
      expect(() => {
        renderResult = render(<PublicHomePage initialHomePage={null} />);
      }).not.toThrow();

      // Should render fallback sections without crash
      expect(renderResult?.container.querySelector("[data-section-key='discover_cta']")).toBeTruthy();
    });

    it("handles initialHomePage with empty sections array gracefully", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Empty Sections",
        seo_json: {},
        sections: [],
      };

      let renderResult: ReturnType<typeof render> | undefined;
      expect(() => {
        renderResult = render(<PublicHomePage initialHomePage={page} />);
      }).not.toThrow();

      expect(renderResult?.container.querySelector("[data-section-key='discover_cta']")).toBeTruthy();
    });

    it("handles is_visible=false for all content sections gracefully", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "All Hidden",
        seo_json: {},
        sections: [
          { ...createBaseSection("welcome", "feed", 1), is_visible: false },
          { ...createBaseSection("activities", "events_calendar", 2), is_visible: false },
          { ...createBaseSection("newsletter", "newsletter", 3), is_visible: false },
          { ...createBaseSection("discover_cta", "cta_block", 4), is_visible: false },
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);
      const contentKeys = Array.from(container.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"))
        .filter((k) => k !== "hero");

      // All content sections are hidden
      expect(contentKeys).toHaveLength(0);
    });

    it("preserves Hero outside the relative z-10 content wrapper regardless of hero sort_order", () => {
      const page: CmsPublicPage = {
        site_key: "ccf",
        slug: "home",
        title: "Hero Ordering Check",
        seo_json: {},
        sections: [
          createBaseSection("welcome", "feed", 1),
          // Hero with high sort_order
          {
            id: "sec-hero",
            page_id: "page-1",
            section_key: "hero",
            type: "hero",
            sort_order: 99,
            is_visible: true,
            status: "active",
            created_at: "",
            updated_at: "",
            props_json: { title_lead: "Lead", title_accent: "Accent" },
          },
          createBaseSection("newsletter", "newsletter", 2),
        ],
      };

      const { container } = render(<PublicHomePage initialHomePage={page} />);

      // Hero should NOT be inside .bg-site-background
      const contentWrapper = container.querySelector(".bg-site-background");
      expect(contentWrapper).toBeTruthy();

      const heroInsideContent = contentWrapper?.querySelector("[data-section-key='hero']");
      expect(heroInsideContent).toBeNull();

      // Content sections inside wrapper should only be welcome -> newsletter
      const innerKeys = Array.from(contentWrapper!.querySelectorAll("[data-section-key]"))
        .map((el) => el.getAttribute("data-section-key"));
      expect(innerKeys).toEqual(["welcome", "newsletter"]);
    });
  });

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CmsModuleNav } from "./CmsModuleNav";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockUsePathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...mod,
    listCmsPostsByCategory: vi.fn().mockResolvedValue([]),
  };
});

vi.mock("@/lib/site-config", () => ({
  SITE_KEY: "ccf",
}));

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CmsModuleNav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue("/plataforma/cms");
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
  });

  it("renders the breadcrumb with Sitio web", () => {
    render(<CmsModuleNav />);

    expect(screen.getByText(/sitio web/i)).toBeInTheDocument();
  });

  it("renders the Resumen tab link in the navigation", () => {
    render(<CmsModuleNav />);

    // There are two "Resumen" texts (breadcrumb span + tab link) — use getAllByText
    const resumenElements = screen.getAllByText(/resumen/i);
    expect(resumenElements.length).toBe(2);
  });

  it("renders all CMS navigation tabs for admin role", () => {
    render(<CmsModuleNav />);

    expect(screen.getByRole("tablist")).toBeInTheDocument();

    // Use exact labels from CMS_TABS (no accent on "Paginas")
    expect(screen.getByText(/paginas/i)).toBeInTheDocument();
    expect(screen.getByText(/testimonios/i)).toBeInTheDocument();
    expect(screen.getByText(/menus/i)).toBeInTheDocument();
    expect(screen.getByText(/media/i)).toBeInTheDocument();
    expect(screen.getByText(/builder/i)).toBeInTheDocument();
    expect(screen.getByText(/temas/i)).toBeInTheDocument();
    expect(screen.getByText(/sitios/i)).toBeInTheDocument();
    expect(screen.getByText(/auditoria/i)).toBeInTheDocument();
  });

  it("hides sites tab when user cannot manage sites", () => {
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "docente" },
    });

    render(<CmsModuleNav />);

    expect(screen.queryByText(/sitios/i)).not.toBeInTheDocument();
  });

  it("only shows resumen tab when user cannot edit CMS", () => {
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "estudiante" },
    });

    render(<CmsModuleNav />);

    // Resumen should appear (breadcrumb + tab) = 2 elements
    const resumenElements = screen.getAllByText(/resumen/i);
    expect(resumenElements.length).toBe(2);

    // Other tabs should NOT be visible
    expect(screen.queryByText(/paginas/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/media/i)).not.toBeInTheDocument();
  });

  it("highlights the active tab based on current pathname", () => {
    mockUsePathname.mockReturnValue("/plataforma/cms/pages");

    render(<CmsModuleNav />);

    // The active link should have aria-current="page"
    const pagesLink = screen.getByRole("link", { name: /paginas/i });
    expect(pagesLink).toHaveAttribute("aria-current", "page");
  });

  it("shows the resumen tab as active when pathname is /plataforma/cms exactly", () => {
    mockUsePathname.mockReturnValue("/plataforma/cms");

    render(<CmsModuleNav />);

    // Active link is the one with aria-current
    const resumenLink = screen.getByRole("link", { current: "page" });
    expect(resumenLink).toHaveAttribute("href", "/plataforma/cms");
  });

  it("renders navigation links with correct hrefs", () => {
    render(<CmsModuleNav />);

    const pagesLink = screen.getByRole("link", { name: /paginas/i });
    expect(pagesLink).toHaveAttribute("href", "/plataforma/cms/pages");

    const mediaLink = screen.getByRole("link", { name: /media/i });
    expect(mediaLink).toHaveAttribute("href", "/plataforma/cms/media");
  });

  it("does not render tabs when not authenticated", () => {
    mockUseAuth.mockReturnValue({
      token: null,
      user: null,
    });

    render(<CmsModuleNav />);

    // Only Resumen breadcrumb/tab should appear (canEdit defaults to false for null role)
    expect(screen.getAllByText(/resumen/i).length).toBe(2);
    expect(screen.queryByText(/paginas/i)).not.toBeInTheDocument();
  });

  it("does not render stats row initially when stats is null", () => {
    render(<CmsModuleNav />);

    // Breadcrumb and tabs are always present
    expect(screen.getByText(/sitio web/i)).toBeInTheDocument();

    // The stats container is a bordered div with links — it should NOT be present
    // because stats is null on initial render (Promise.allSettled hasn't resolved yet)
    const statsContainer = document.querySelector(".border-t");
    // There is only the nav's border-t element initially (stats container has border-t too)
    // When stats is null, the stats div is not rendered at all
    expect(screen.queryByText(/0 paginas/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/0 media/i)).not.toBeInTheDocument();
  });

  it("renders the tablist with aria-label", () => {
    render(<CmsModuleNav />);

    expect(screen.getByRole("tablist")).toHaveAttribute(
      "aria-label",
      "Navegacion del CMS",
    );
  });

  it("renders tab icons via lucide-react components", () => {
    render(<CmsModuleNav />);

    // The breadcrumb uses Globe icon (rendered as SVG)
    const globes = document.querySelectorAll("svg");
    expect(globes.length).toBeGreaterThan(0);
  });
});

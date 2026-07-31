/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import BuilderSidebar from "./BuilderSidebar";

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    siteKey: "ccf",
    setSiteKey: vi.fn(),
    sites: [{ site_key: "ccf", name: "CCF Principal", base_path: "/" }],
    pages: [],
    activeSlug: "home",
    setActiveSlug: vi.fn(),
    newPageTitle: "",
    setNewPageTitle: vi.fn(),
    canEdit: true,
    createPage: vi.fn(),
    pageTemplateKey: "simple",
    setPageTemplateKey: vi.fn(),
    createPageFromTemplate: vi.fn(),
    addTemplateSection: vi.fn(),
  };
  return { ...base, ...overrides } as unknown as PageBuilderState;
}

describe("BuilderSidebar", () => {
  it("renders site selector and new page form", () => {
    const builder = createMockBuilder();
    render(<BuilderSidebar builder={builder} />);

    expect(screen.getByText(/sitio/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/página de bienvenida/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /crear vacía/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /crear con plantilla/i })).toBeInTheDocument();
  });

  it("switches active page when clicking a page in the list", () => {
    const setActiveSlug = vi.fn();
    const pages = [{ id: "p1", slug: "home", title: "Inicio", status: "published" }] as any;
    const builder = createMockBuilder({ pages, setActiveSlug });

    render(<BuilderSidebar builder={builder} />);

    fireEvent.click(screen.getByText("Inicio"));
    expect(setActiveSlug).toHaveBeenCalledWith("home");
  });

  it("calls createPage when clicking Crear vacía", () => {
    const createPage = vi.fn();
    const builder = createMockBuilder({ createPage });

    render(<BuilderSidebar builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /crear vacía/i }));
    expect(createPage).toHaveBeenCalled();
  });

  it("updates newPageTitle while typing", () => {
    const setNewPageTitle = vi.fn();
    const builder = createMockBuilder({ setNewPageTitle });

    render(<BuilderSidebar builder={builder} />);

    fireEvent.change(screen.getByPlaceholderText(/página de bienvenida/i), {
      target: { value: "Nueva página" },
    });
    expect(setNewPageTitle).toHaveBeenCalledWith("Nueva página");
  });

  it("calls createPageFromTemplate when clicking Crear con plantilla", () => {
    const createPageFromTemplate = vi.fn();
    const builder = createMockBuilder({ createPageFromTemplate });

    render(<BuilderSidebar builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /crear con plantilla/i }));
    expect(createPageFromTemplate).toHaveBeenCalled();
  });

  it("calls addTemplateSection when clicking a quick template", () => {
    const addTemplateSection = vi.fn();
    const builder = createMockBuilder({ addTemplateSection });

    render(<BuilderSidebar builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /crear pop-up/i }));
    expect(addTemplateSection).toHaveBeenCalled();
  });

  it("disables creation buttons when canEdit is false", () => {
    const createPage = vi.fn();
    const createPageFromTemplate = vi.fn();
    const builder = createMockBuilder({
      canEdit: false,
      createPage,
      createPageFromTemplate,
    });

    render(<BuilderSidebar builder={builder} />);

    const emptyButton = screen.getByRole("button", { name: /crear vacía/i });
    const templateButton = screen.getByRole("button", { name: /crear con plantilla/i });

    expect(emptyButton).toBeDisabled();
    expect(templateButton).toBeDisabled();

    fireEvent.click(emptyButton);
    fireEvent.click(templateButton);
    expect(createPage).not.toHaveBeenCalled();
    expect(createPageFromTemplate).not.toHaveBeenCalled();
  });

  it("updates siteKey when selecting a different site", () => {
    const setSiteKey = vi.fn();
    const sites = [
      { site_key: "ccf", name: "CCF Principal", base_path: "/" },
      { site_key: "faro", name: "Faro", base_path: "/faro" },
    ];
    const builder = createMockBuilder({ sites, setSiteKey });

    render(<BuilderSidebar builder={builder} />);

    const siteSelect = screen.getByRole("combobox", { name: /sitio/i });
    fireEvent.change(siteSelect, { target: { value: "faro" } });
    expect(setSiteKey).toHaveBeenCalledWith("faro");
  });

  it("updates pageTemplateKey when selecting a template", () => {
    const setPageTemplateKey = vi.fn();
    const builder = createMockBuilder({ setPageTemplateKey });

    render(<BuilderSidebar builder={builder} />);

    const templateSelect = screen.getByRole("combobox", { name: /plantilla/i });
    fireEvent.change(templateSelect, { target: { value: "landing" } });
    expect(setPageTemplateKey).toHaveBeenCalledWith("landing");
  });
});

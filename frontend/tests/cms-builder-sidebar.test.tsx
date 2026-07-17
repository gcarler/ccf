import React from "react";
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import BuilderSidebar from "../src/components/cms/builder/BuilderSidebar";

describe("BuilderSidebar", () => {
  it("exposes an explicit popup creation action", () => {
    const addTemplateSection = vi.fn();
    const builder = {
      siteKey: "faro",
      setSiteKey: vi.fn(),
      sites: [],
      pages: [],
      activeSlug: "inicio",
      setActiveSlug: vi.fn(),
      newPageTitle: "",
      setNewPageTitle: vi.fn(),
      canEdit: true,
      createPage: vi.fn(),
      pageTemplateKey: "simple",
      setPageTemplateKey: vi.fn(),
      createPageFromTemplate: vi.fn(),
      addTemplateSection,
    } as any;

    render(<BuilderSidebar builder={builder} />);

    expect(screen.getByRole("button", { name: /crear pop-up/i })).toBeTruthy();
  });
});

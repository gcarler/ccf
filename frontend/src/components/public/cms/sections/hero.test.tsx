import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CmsSection } from "@/types/cms-v2";
import { HeroSection } from "./hero";

describe("published CMS hero rendering", () => {
  it("renders the exact text published by the CMS", () => {
    const editedTitle = "Texto CMS publicado exactamente";
    const publishedSection = {
      id: "published-hero",
      page_id: "published-page",
      section_key: "published-hero",
      type: "hero",
      props_json: { title: editedTitle },
      sort_order: 0,
      is_visible: true,
      status: "active",
    } as CmsSection<"hero">;

    render(<HeroSection section={publishedSection} />);

    expect(screen.getByRole("heading", { name: editedTitle })).toBeInTheDocument();
  });
});

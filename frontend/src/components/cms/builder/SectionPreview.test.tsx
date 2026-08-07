import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SectionPreview, SectionRenderPreview, SectionRenderErrorBoundary } from "./SectionPreview";
import { createMockCmsSection } from "@/test-utils/factories";

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));

vi.mock("@/components/public/cms/PublicSectionRenderer", () => ({
  default: ({ section }: { section: { type: string } }) => <div data-testid="public-renderer">{section.type}</div>,
}));

describe("SectionPreview", () => {
  it("renders hero section with title, body and cta", () => {
    const section = createMockCmsSection("hero", {
      props_json: { title: "Hero title", body: "Hero body", cta_label: "Ver más" },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("Hero title")).toBeInTheDocument();
    expect(screen.getByText("Hero body")).toBeInTheDocument();
    expect(screen.getByText("Ver más")).toBeInTheDocument();
  });

  it("renders default hero placeholders when fields are missing", () => {
    const section = createMockCmsSection("hero", { props_json: {} });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("Título hero")).toBeInTheDocument();
    expect(screen.getByText("Subtítulo o descripción principal")).toBeInTheDocument();
  });

  it("renders cards section with items", () => {
    const section = createMockCmsSection("cards", {
      props_json: {
        title: "Mis tarjetas",
        items: [{ title: "Card 1" }, { title: "Card 2" }, { title: "Card 3" }, { title: "Card 4" }],
      },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("Mis tarjetas")).toBeInTheDocument();
    expect(screen.getByText("Card 1")).toBeInTheDocument();
    expect(screen.getByText("+1 más")).toBeInTheDocument();
  });

  it("renders gallery section with image", () => {
    const section = createMockCmsSection("gallery", {
      props_json: { image_url: "/gallery.jpg" },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByRole("img")).toHaveAttribute("src", "/gallery.jpg");
  });

  it("renders stats section with items", () => {
    const section = createMockCmsSection("stats", {
      props_json: {
        items: [
          { value: "100", label: "Personas" },
          { value: "50", label: "Grupos" },
        ],
      },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("Personas")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("renders faq section with questions", () => {
    const section = createMockCmsSection("faq", {
      props_json: {
        title: "Preguntas",
        items: [{ q: "¿Q1?", a: "A1" }, { q: "¿Q2?", a: "A2" }],
      },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("Preguntas")).toBeInTheDocument();
    expect(screen.getByText("¿Q1?")).toBeInTheDocument();
  });

  it("renders default fallback for rich_text sections", () => {
    const section = createMockCmsSection("rich_text", {
      props_json: { title: "Título", body: "Contenido" },
    });
    render(<SectionPreview section={section} />);

    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.getByText("Contenido")).toBeInTheDocument();
  });

  it("renders type label badge", () => {
    const section = createMockCmsSection("cta_banner", { props_json: {} });
    render(<SectionPreview section={section} />);
    expect(screen.getByText("Banner CTA")).toBeInTheDocument();
  });

  it("renders SectionRenderPreview with public renderer", () => {
    const section = createMockCmsSection("hero", { props_json: {} });
    render(<SectionRenderPreview section={section} mobile={false} />);
    expect(screen.getByTestId("public-renderer")).toHaveTextContent("hero");
  });

  it("renders SectionRenderPreview in mobile mode", () => {
    const section = createMockCmsSection("hero", { props_json: {} });
    render(<SectionRenderPreview section={section} mobile />);
    expect(screen.getByTestId("section-render-preview")).toHaveClass("max-w-[420px]");
  });

  it("catches render errors via SectionRenderErrorBoundary", () => {
    const Thrower = () => {
      throw new Error("Render error");
    };

    render(
      <SectionRenderErrorBoundary>
        <Thrower />
      </SectionRenderErrorBoundary>
    );

    expect(screen.getByText(/no se pudo renderizar esta sección/i)).toBeInTheDocument();
  });
});

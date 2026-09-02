/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";
import type { Config } from "@puckeditor/core";

// Mock dependencies for PuckBuilderPage
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("site=ccf&page=home&mode=visual"),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { role: "admin" } }),
}));

vi.mock("@/lib/cms/permissions", () => ({
  canEditCms: () => true,
  canPublishCms: () => true,
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSections: vi.fn().mockResolvedValue([]),
  patchCmsSection: vi.fn(),
  createCmsSection: vi.fn(),
  deleteCmsSection: vi.fn(),
  workflowCmsPage: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue(null),
}));

// Capture config passed to Puck
let capturedConfig: Config | null = null;
vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => {
    capturedConfig = props?.config;
    return <div data-testid="puck-editor-mock">Puck Editor</div>;
  },
}));

describe("Puck Block Schema Registrations for MediaPicker", () => {
  it("registers MediaPicker custom fields for hero.bg_image, gallery.items[].url, and cards.items[].image_url", async () => {
    render(<PuckBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
    expect(capturedConfig).not.toBeNull();

    const components = capturedConfig?.components;
    expect(components).toBeDefined();

    // 1. Hero bg_image
    const heroField = components?.hero?.fields?.bg_image as any;
    expect(heroField).toBeDefined();
    expect(heroField?.type).toBe("custom");
    expect(typeof heroField?.render).toBe("function");

    // 2. Gallery items[].url
    const galleryItems = components?.gallery?.fields?.items as any;
    expect(galleryItems).toBeDefined();
    expect(galleryItems?.type).toBe("array");
    expect(galleryItems?.arrayFields?.url).toBeDefined();
    expect(galleryItems?.arrayFields?.url?.type).toBe("custom");
    expect(typeof galleryItems?.arrayFields?.url?.render).toBe("function");

    // 3. Cards items[].image_url
    const cardsItems = components?.cards?.fields?.items as any;
    expect(cardsItems).toBeDefined();
    expect(cardsItems?.type).toBe("array");
    expect(cardsItems?.arrayFields?.image_url).toBeDefined();
    expect(cardsItems?.arrayFields?.image_url?.type).toBe("custom");
    expect(typeof cardsItems?.arrayFields?.image_url?.render).toBe("function");
  });

  it("registers JSON editors for every public projection section type", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    for (const type of ["contact_form", "course_grid", "locations_list", "testimonials_masonry"]) {
      expect(components[type]).toBeDefined();
      expect(components[type].fields.__cms_json.type).toBe("custom");
      expect(typeof components[type].fields.__cms_json.render).toBe("function");
    }
  });

  it("renders MediaPickerField correctly from hero bg_image custom field render function", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
    const bgImageField = capturedConfig?.components?.hero?.fields?.bg_image as any;
    
    const { container } = render(bgImageField.render({ value: "http://test.com/bg.jpg", onChange: vi.fn() }));
    expect(container.querySelector("img")).toHaveAttribute("src", "http://test.com/bg.jpg");
    expect(screen.getByText("Cambiar Imagen")).toBeInTheDocument();
    expect(screen.getByText("Quitar")).toBeInTheDocument();
  });

  it("renders MediaPickerField correctly from gallery items url custom field render function", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
    const galleryUrlField = (capturedConfig?.components?.gallery?.fields?.items as any)?.arrayFields?.url;
    
    const { container } = render(galleryUrlField.render({ value: "", onChange: vi.fn() }));
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("Seleccionar Imagen")).toBeInTheDocument();
  });

  it("renders MediaPickerField correctly from cards items image_url custom field render function", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
    const cardsImageField = (capturedConfig?.components?.cards?.fields?.items as any)?.arrayFields?.image_url;
    
    const { container } = render(cardsImageField.render({ value: "http://test.com/card.png", onChange: vi.fn() }));
    expect(container.querySelector("img")).toHaveAttribute("src", "http://test.com/card.png");
    expect(screen.getByText("Cambiar Imagen")).toBeInTheDocument();
  });

  it("registers AiField custom fields for Hero (title, body, cta_label), Rich Text (title, body), and CTA Banner (title, body, cta_label)", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    expect(components).toBeDefined();

    // Hero AI fields
    expect(components.hero.fields.title.type).toBe("custom");
    expect(components.hero.fields.body.type).toBe("custom");
    expect(components.hero.fields.cta_label.type).toBe("custom");

    // Rich Text AI fields
    expect(components.rich_text.fields.title.type).toBe("custom");
    expect(components.rich_text.fields.body.type).toBe("custom");

    // CTA Banner AI fields
    expect(components.cta_banner.fields.title.type).toBe("custom");
    expect(components.cta_banner.fields.body.type).toBe("custom");
    expect(components.cta_banner.fields.cta_label.type).toBe("custom");

    // Test rendering of one of the fields (e.g. Hero title)
    render(components.hero.fields.title.render({ value: "Hero Title", onChange: vi.fn() }));
    expect(screen.getByText("Título Principal")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Hero Title")).toBeInTheDocument();
    expect(screen.getByText("Redactar con IA")).toBeInTheDocument();
  });

  it("registers defaultProps, min/max limits, getItemSummary, and AiFields for gallery and cards components", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    expect(components).toBeDefined();

    // 1. Gallery defaultProps
    expect(components.gallery.defaultProps).toBeDefined();
    expect(components.gallery.defaultProps.items).toHaveLength(3);
    expect(components.gallery.defaultProps.items[0]).toEqual({ url: "", alt: "Galería 1", caption: "Imagen 1" });

    // 2. Gallery items schema (min, max, getItemSummary)
    const galleryItems = components.gallery.fields.items;
    expect(galleryItems.min).toBe(1);
    expect(galleryItems.max).toBe(12);
    expect(galleryItems.getItemSummary({ caption: "Mi leyenda" }, 0)).toBe("Mi leyenda");
    expect(galleryItems.getItemSummary({ alt: "Foto especial" }, 1)).toBe("Foto especial");
    expect(galleryItems.getItemSummary({ alt: "Imagen" }, 2)).toBe("Imagen #3");
    expect(galleryItems.getItemSummary({}, 0)).toBe("Imagen #1");

    // 3. Cards defaultProps
    expect(components.cards.defaultProps).toBeDefined();
    expect(components.cards.defaultProps.items).toHaveLength(3);
    expect(components.cards.defaultProps.items[0]).toEqual({
      title: "Tarjeta 1",
      body: "Descripción de la tarjeta 1...",
      cta_label: "Saber más",
      cta_href: "/",
      image_url: "",
    });

    // 4. Cards items schema (min, max, getItemSummary, AiField arrayFields)
    const cardsItems = components.cards.fields.items;
    expect(cardsItems.min).toBe(1);
    expect(cardsItems.max).toBe(6);
    expect(cardsItems.getItemSummary({ title: "Tarjeta Test" }, 0)).toBe("Tarjeta Test");
    expect(cardsItems.getItemSummary({}, 3)).toBe("Tarjeta #4");

    // Cards sub-element arrayFields AiFields
    expect(cardsItems.arrayFields.title.type).toBe("custom");
    expect(typeof cardsItems.arrayFields.title.render).toBe("function");
    expect(cardsItems.arrayFields.body.type).toBe("custom");
    expect(typeof cardsItems.arrayFields.body.render).toBe("function");

    render(cardsItems.arrayFields.title.render({ value: "Título de Tarjeta Test", onChange: vi.fn() }));
    expect(screen.getByDisplayValue("Título de Tarjeta Test")).toBeInTheDocument();

    render(cardsItems.arrayFields.body.render({ value: "Descripción de Tarjeta Test", onChange: vi.fn() }));
    expect(screen.getByDisplayValue("Descripción de Tarjeta Test")).toBeInTheDocument();
  });

  it("renders gallery and cards components with empty array fallbacks and blank image badges", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;

    // Gallery empty items fallback
    render(
      components.gallery.render({ title: "Galería Vacía", items: [] })
    );
    expect(screen.getByText("No hay imágenes agregadas. Añade elementos desde el panel lateral.")).toBeInTheDocument();

    // Gallery item with empty image url -> renders "Sin imagen" badge
    render(
      components.gallery.render({ title: "Galería Con Items", items: [{ url: "", alt: "Imagen" }] })
    );
    expect(screen.getByText("Sin imagen")).toBeInTheDocument();

    // Cards empty items fallback
    render(
      components.cards.render({ title: "Tarjetas Vacías", items: [] })
    );
    expect(screen.getByText("No hay tarjetas agregadas. Añade elementos desde el panel lateral.")).toBeInTheDocument();

    // Cards item with empty image url -> renders "Sin imagen" badge
    render(
      components.cards.render({ title: "Tarjetas Con Items", items: [{ title: "Tarjeta 1", image_url: "" }] })
    );
    expect(screen.getAllByText("Sin imagen").length).toBeGreaterThan(0);
  });
});


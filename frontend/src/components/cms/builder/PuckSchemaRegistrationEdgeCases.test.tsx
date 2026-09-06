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

let capturedConfig: Config | null = null;
vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => {
    capturedConfig = props?.config;
    return <div data-testid="puck-editor-mock">Puck Editor</div>;
  },
}));

describe("M4 Schema Edge Cases & Empirical Stress Tests", () => {
  it("tests getItemSummary with extreme edge cases (null, empty object, undefined index, negative index)", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    const galleryGetItemSummary = components.gallery.fields.items.getItemSummary;
    const cardsGetItemSummary = components.cards.fields.items.getItemSummary;

    // Gallery getItemSummary edge cases
    expect(galleryGetItemSummary(null, undefined)).toBe("Imagen #1");
    expect(galleryGetItemSummary(undefined, 5)).toBe("Imagen #6");
    expect(galleryGetItemSummary({}, 0)).toBe("Imagen #1");
    expect(galleryGetItemSummary({ caption: "" }, 2)).toBe("Imagen #3");
    expect(galleryGetItemSummary({ alt: "" }, 0)).toBe("Imagen #1");
    expect(galleryGetItemSummary({ alt: "Imagen" }, 0)).toBe("Imagen #1");
    expect(galleryGetItemSummary({ alt: "Custom Alt" }, 0)).toBe("Custom Alt");
    expect(galleryGetItemSummary({ caption: "Caption Wins", alt: "Alt Ignored" }, 0)).toBe("Caption Wins");
    expect(galleryGetItemSummary({}, -1)).toBe("Imagen #0");
    expect(galleryGetItemSummary({}, 999)).toBe("Imagen #1000");

    // Cards getItemSummary edge cases
    expect(cardsGetItemSummary(null, undefined)).toBe("Tarjeta #1");
    expect(cardsGetItemSummary(undefined, 3)).toBe("Tarjeta #4");
    expect(cardsGetItemSummary({}, 0)).toBe("Tarjeta #1");
    expect(cardsGetItemSummary({ title: "" }, 1)).toBe("Tarjeta #2");
    expect(cardsGetItemSummary({ title: "Custom Title" }, 0)).toBe("Custom Title");
    expect(cardsGetItemSummary({}, -1)).toBe("Tarjeta #0");
    expect(cardsGetItemSummary({}, 999)).toBe("Tarjeta #1000");
  });

  it("verifies puck array field constraints min and max for gallery and cards", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;

    // Gallery array field limits
    expect(components.gallery.fields.items.min).toBe(1);
    expect(components.gallery.fields.items.max).toBe(12);

    // Cards array field limits
    expect(components.cards.fields.items.min).toBe(1);
    expect(components.cards.fields.items.max).toBe(6);
  });

  it("renders gallery block under edge cases: null items, array with undefined/empty elements", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    const galleryRender = components.gallery.render;

    // 1. null items -> renders empty placeholder without throw
    render(galleryRender({ items: null }));
    expect(screen.getAllByText("No hay imágenes agregadas. Añade elementos desde el panel lateral.").length).toBeGreaterThan(0);

    // 2. undefined items -> renders empty placeholder without throw
    render(galleryRender({ items: undefined }));
    expect(screen.getAllByText("No hay imágenes agregadas. Añade elementos desde el panel lateral.").length).toBeGreaterThan(0);

    // 3. items containing null, undefined, and empty object -> handles gracefully
    render(
      galleryRender({
        title: "Test Gallery",
        items: [null, undefined, {}, { url: "http://example.com/test.jpg", alt: "", caption: "Test Caption" }],
      })
    );
    expect(screen.getAllByText("Sin imagen").length).toBeGreaterThan(0);
    expect(screen.getByText("Test Caption")).toBeInTheDocument();
  });

  it("renders cards block under edge cases: null items, array with undefined/empty elements, missing href/label", async () => {
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const components = capturedConfig?.components as any;
    const cardsRender = components.cards.render;

    // 1. null items -> renders empty placeholder without throw
    render(cardsRender({ items: null }));
    expect(screen.getAllByText("No hay tarjetas agregadas. Añade elementos desde el panel lateral.").length).toBeGreaterThan(0);

    // 2. items containing null, undefined, empty object
    render(
      cardsRender({
        title: "Test Cards",
        items: [null, undefined, {}, { title: "Complete Card", image_url: "http://example.com/card.jpg", cta_label: "Click Me" }],
      })
    );

    // Default titles for null, undefined, {}
    expect(screen.getAllByText("Tarjeta #1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tarjeta #2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tarjeta #3").length).toBeGreaterThan(0);
    expect(screen.getByText("Complete Card")).toBeInTheDocument();

    // Sin imagen badges for 3 items without image_url
    expect(screen.getAllByText("Sin imagen").length).toBeGreaterThan(0);
    expect(screen.getByText("Click Me →")).toBeInTheDocument();
  });
});

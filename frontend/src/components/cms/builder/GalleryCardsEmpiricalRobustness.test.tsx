/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";
import type { Config } from "@puckeditor/core";

// Mock dependencies for PuckBuilderPage
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("site=ccf&page=home"),
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

describe("Empirical Robustness Suite: Gallery & Cards Blocks", () => {
  const setupConfig = async () => {
    if (capturedConfig) return capturedConfig;
    render(<PuckBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
    return capturedConfig!;
  };

  describe("Gallery Block Empirical Tests", () => {
    it("renders gallery with 0 items (empty array, null, undefined)", async () => {
      const config = await setupConfig();
      const galleryRender = (config.components.gallery.render as any);

      const { container: c0 } = render(galleryRender({ items: [] }));
      expect(c0.textContent).toContain("No hay imágenes agregadas");

      const { container: cNull } = render(galleryRender({ items: null }));
      expect(cNull.textContent).toContain("No hay imágenes agregadas");

      const { container: cUndef } = render(galleryRender({ items: undefined }));
      expect(cUndef.textContent).toContain("No hay imágenes agregadas");
    });

    it("renders gallery with 1 item, 2 items, 3 items, 6 items, and 12 items", async () => {
      const config = await setupConfig();
      const galleryRender = (config.components.gallery.render as any);

      const counts = [1, 2, 3, 6, 12];
      for (const count of counts) {
        const items = Array.from({ length: count }, (_, i) => ({
          url: `https://example.com/img-${i + 1}.jpg`,
          alt: `Alt text ${i + 1}`,
          caption: `Caption ${i + 1}`,
        }));

        const { container } = render(galleryRender({ title: `Gallery with ${count} items`, items }));
        const imgElements = container.querySelectorAll("img");
        expect(imgElements.length).toBe(count);
        expect(container.textContent).toContain(`Gallery with ${count} items`);
      }
    });

    it("renders gallery under special characters, XSS attempts, long titles/captions", async () => {
      const config = await setupConfig();
      const galleryRender = (config.components.gallery.render as any);

      const longTitle = "A".repeat(300);
      const xssCaption = "<script>alert('xss')</script> & <b>bold</b> 😊";
      const unicodeAlt = "Español: Ñandú, Canción & <Tag> 🎉";

      const { container } = render(
        galleryRender({
          title: longTitle,
          body: "Special text & <script>",
          items: [{ url: "", alt: unicodeAlt, caption: xssCaption }],
        })
      );

      expect(container.textContent).toContain(longTitle);
      expect(container.textContent).toContain("<script>alert('xss')</script> & <b>bold</b> 😊");
      expect(container.textContent).toContain(unicodeAlt);
      // Ensure raw HTML tags are NOT inserted into DOM as unescaped elements
      expect(container.querySelector("script")).toBeNull();
      expect(container.querySelector("b")).toBeNull();
    });
  });

  describe("Cards Block Empirical Tests", () => {
    it("renders cards with 0 items (empty array, null, undefined)", async () => {
      const config = await setupConfig();
      const cardsRender = (config.components.cards.render as any);

      const { container: c0 } = render(cardsRender({ items: [] }));
      expect(c0.textContent).toContain("No hay tarjetas agregadas");

      const { container: cNull } = render(cardsRender({ items: null }));
      expect(cNull.textContent).toContain("No hay tarjetas agregadas");

      const { container: cUndef } = render(cardsRender({ items: undefined }));
      expect(cUndef.textContent).toContain("No hay tarjetas agregadas");
    });

    it("renders cards with 1 item, 2 items, 3 items, and 6 items", async () => {
      const config = await setupConfig();
      const cardsRender = (config.components.cards.render as any);

      const counts = [1, 2, 3, 6];
      for (const count of counts) {
        const items = Array.from({ length: count }, (_, i) => ({
          title: `Tarjeta ${i + 1}`,
          body: `Descripción ${i + 1}`,
          href: `/link-${i + 1}`,
          image_url: `https://example.com/card-${i + 1}.jpg`,
        }));

        const { container } = render(cardsRender({ title: `Cards section ${count}`, items }));
        const cardCards = container.querySelectorAll(".shadow-sm");
        expect(cardCards.length).toBe(count);
        expect(container.textContent).toContain(`Cards section ${count}`);
      }
    });

    it("handles href edge cases: missing href, empty href, valid href", async () => {
      const config = await setupConfig();
      const cardsRender = (config.components.cards.render as any);

      const { container } = render(
        cardsRender({
          title: "CTA Test",
          items: [
            // Case 1: href missing -> no <a> tag rendered (item?.href is falsy)
            { title: "Card 1" },
            // Case 2: href empty string -> no <a> tag rendered
            { title: "Card 2", href: "" },
            // Case 3: href valid -> renders <a> tag with href
            { title: "Card 3", href: "/valid-path" },
          ],
        })
      );

      const links = container.querySelectorAll("a");
      // Only Card 3 has a truthy href, so exactly 1 link should be rendered
      expect(links.length).toBe(1);

      expect(links[0].getAttribute("href")).toBe("/valid-path");
      expect(links[0].textContent).toContain("Ver más");
    });

    it("handles extreme text lengths, special characters, and missing images in cards", async () => {
      const config = await setupConfig();
      const cardsRender = (config.components.cards.render as any);

      const hugeTitle = "T".repeat(250);
      const hugeBody = "B".repeat(1500);
      const xssTitle = "<img src=x onerror=alert(1)> & 🚀";

      const { container } = render(
        cardsRender({
          title: "Extreme Test",
          items: [
            { title: hugeTitle, body: hugeBody, image_url: "" },
            { title: xssTitle, body: "Normal body", image_url: "http://example.com/a.jpg" },
          ],
        })
      );

      expect(container.textContent).toContain(hugeTitle);
      expect(container.textContent).toContain(hugeBody);
      expect(container.textContent).toContain("<img src=x onerror=alert(1)> & 🚀");
      expect(container.textContent).toContain("Sin imagen");
      // Ensure no script execution or image onerror injection
      expect(container.querySelectorAll("img").length).toBe(1);
    });
  });
});

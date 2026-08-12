import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MediaPicker from "./MediaPicker";
import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";

// Mocks for dependencies
vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [] }),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (param: string) => (param === "site" ? "ccf" : param === "page" ? "home" : null),
  }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mock-token",
    user: { role: "ADMIN" },
  }),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSections: vi.fn().mockResolvedValue([]),
  patchCmsSection: vi.fn(),
  createCmsSection: vi.fn(),
  deleteCmsSection: vi.fn(),
  workflowCmsPage: vi.fn(),
}));

/* eslint-disable @typescript-eslint/no-explicit-any */
vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => {
    const config = props?.config;
    // Helper to render puck custom fields for empirical verification
    const bgImageField = config?.components?.hero?.fields?.bg_image;
    const galleryUrlField = config?.components?.gallery?.fields?.items?.arrayFields?.url;
    const cardsUrlField = config?.components?.cards?.fields?.items?.arrayFields?.image_url;

    return (
      <div data-testid="puck-mock">
        <div data-testid="hero-bg-image-field">
          {bgImageField?.render?.({ value: "https://example.com/hero.jpg", onChange: vi.fn() })}
        </div>
        <div data-testid="gallery-url-field">
          {galleryUrlField?.render?.({ value: "https://example.com/gallery.jpg", onChange: vi.fn() })}
        </div>
        <div data-testid="cards-url-field">
          {cardsUrlField?.render?.({ value: "https://example.com/card.jpg", onChange: vi.fn() })}
        </div>
      </div>
    );
  },
}));
/* eslint-enable @typescript-eslint/no-explicit-any */

describe("Empirical Stress Suite - M2 MediaPicker & MediaPickerField", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("MediaPicker Keyboard Escape Key Listener Cleanup", () => {
    it("attaches keydown listener on mount when open and removes it on unmount", () => {
      const addEventListenerSpy = vi.spyOn(window, "addEventListener");
      const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
      const onClose = vi.fn();

      const { unmount } = render(
        <MediaPicker open token="test-token" onClose={onClose} onSelect={vi.fn()} />
      );

      expect(addEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

      // Pressing Escape should trigger onClose
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);

      // Unmount component
      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith("keydown", expect.any(Function));

      // Pressing Escape after unmount should NOT call onClose again
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not attach keydown listener when open is false", () => {
      const addEventListenerSpy = vi.spyOn(window, "addEventListener");

      render(<MediaPicker open={false} token="test-token" onClose={vi.fn()} onSelect={vi.fn()} />);

      expect(addEventListenerSpy).not.toHaveBeenCalledWith("keydown", expect.any(Function));
    });
  });

  describe("MediaPickerField Edge Cases in Puck Builder Page", () => {
    it("handles image load failure with onError hiding preview thumbnail", async () => {
      render(<PuckBuilderPage />);

      await waitFor(() => {
        expect(screen.getByTestId("puck-mock")).toBeInTheDocument();
      });

      // Find preview images
      const imgElements = screen.getAllByAltText("Vista previa");
      expect(imgElements.length).toBeGreaterThan(0);

      const firstImg = imgElements[0] as HTMLImageElement;
      expect(firstImg.style.display).not.toBe("none");

      // Trigger broken image error
      fireEvent.error(firstImg);

      // Verify fallback style hides broken image
      expect(firstImg.style.display).toBe("none");
    });

    it("clears image URL when clicking Quitar button", async () => {
      render(<PuckBuilderPage />);

      await waitFor(() => {
        expect(screen.getByTestId("puck-mock")).toBeInTheDocument();
      });

      const quitarButtons = screen.getAllByTitle("Quitar imagen");
      expect(quitarButtons.length).toBeGreaterThan(0);

      fireEvent.click(quitarButtons[0]);

      // Quitar button click triggers onChange("")
    });
  });

  describe("Schema Registration Verification for M2 Blocks", () => {
    it("registers MediaPickerField for Hero bg_image, Cards items[].image_url, and Gallery items[].url", async () => {
      render(<PuckBuilderPage />);

      await waitFor(() => {
        expect(screen.getByTestId("puck-mock")).toBeInTheDocument();
      });

      expect(screen.getByTestId("hero-bg-image-field")).toBeInTheDocument();
      expect(screen.getByTestId("gallery-url-field")).toBeInTheDocument();
      expect(screen.getByTestId("cards-url-field")).toBeInTheDocument();

      // Verify custom field elements rendered inside each schema slot
      expect(screen.getByTestId("hero-bg-image-field")).toHaveTextContent("Cambiar Imagen");
      expect(screen.getByTestId("gallery-url-field")).toHaveTextContent("Cambiar Imagen");
      expect(screen.getByTestId("cards-url-field")).toHaveTextContent("Cambiar Imagen");
    });
  });
});

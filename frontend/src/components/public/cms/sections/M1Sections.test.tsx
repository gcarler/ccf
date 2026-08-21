import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnimatedCounterSection } from "./AnimatedCounterSection";
import { VideoEmbedSection } from "./VideoEmbedSection";
import { GalleryMasonrySection } from "./GalleryMasonrySection";
import { MapEmbedSection } from "./MapEmbedSection";
import type { CmsSection } from "@/types/cms-v2";

describe("M1 Public Section Components", () => {
  describe("AnimatedCounterSection", () => {
    it("renders counter title and items correctly", () => {
      const section: CmsSection<"animated_counter"> = {
        id: "s1",
        page_id: "p1",
        section_key: "counter-1",
        type: "animated_counter",
        sort_order: 1,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          title: "Estadísticas de Impacto",
          items: [
            { label: "Personas", value: 500, prefix: "+", suffix: "k", duration_ms: 100 },
            { label: "Ciudades", value: 10, prefix: "", suffix: "", duration_ms: 100 },
          ],
        },
      };

      render(<AnimatedCounterSection section={section} />);

      expect(screen.getByText("Estadísticas de Impacto")).toBeDefined();
      expect(screen.getByText("Personas")).toBeDefined();
      expect(screen.getByText("Ciudades")).toBeDefined();
    });
  });

  describe("VideoEmbedSection", () => {
    it("parses and renders YouTube embed iframe correctly", () => {
      const section: CmsSection<"video_embed"> = {
        id: "s2",
        page_id: "p1",
        section_key: "video-1",
        type: "video_embed",
        sort_order: 2,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          title: "Video YouTube",
          video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
          caption: "Demostración",
          autoplay: true,
        },
      };

      render(<VideoEmbedSection section={section} />);

      expect(screen.getByText("Video YouTube")).toBeDefined();
      expect(screen.getByText("Demostración")).toBeDefined();

      const iframe = screen.getByTitle("Video YouTube") as HTMLIFrameElement;
      expect(iframe).toBeDefined();
      expect(iframe.src).toContain("youtube.com/embed/dQw4w9WgXcQ");
      expect(iframe.src).toContain("autoplay=1");
    });

    it("parses and renders Vimeo embed iframe correctly", () => {
      const section: CmsSection<"video_embed"> = {
        id: "s2b",
        page_id: "p1",
        section_key: "video-vimeo",
        type: "video_embed",
        sort_order: 2,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          title: "Video Vimeo",
          video_url: "https://vimeo.com/123456789",
          autoplay: false,
        },
      };

      render(<VideoEmbedSection section={section} />);

      const iframe = screen.getByTitle("Video Vimeo") as HTMLIFrameElement;
      expect(iframe.src).toContain("player.vimeo.com/video/123456789");
      expect(iframe.src).toContain("autoplay=0");
    });

    it("renders direct HTML5 video tag for mp4 files", () => {
      const section: CmsSection<"video_embed"> = {
        id: "s2c",
        page_id: "p1",
        section_key: "video-direct",
        type: "video_embed",
        sort_order: 2,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          title: "Direct Video",
          video_url: "https://cdn.example.com/video.mp4",
          autoplay: false,
        },
      };

      const { container } = render(<VideoEmbedSection section={section} />);
      const video = container.querySelector("video");
      expect(video).not.toBeNull();
      expect(video?.src).toBe("https://cdn.example.com/video.mp4");
    });

    it("renders placeholder when video_url is empty", () => {
      const section: CmsSection<"video_embed"> = {
        id: "s2d",
        page_id: "p1",
        section_key: "video-empty",
        type: "video_embed",
        sort_order: 2,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          video_url: "",
        },
      };

      render(<VideoEmbedSection section={section} />);
      expect(screen.getByText("Sin URL de video configurada")).toBeDefined();
    });
  });

  describe("GalleryMasonrySection", () => {
    const gallerySection: CmsSection<"gallery_masonry"> = {
      id: "s3",
      page_id: "p1",
      section_key: "gallery-1",
      type: "gallery_masonry",
      sort_order: 3,
      is_visible: true,
      status: "active",
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
      props_json: {
        title: "Galería de Fotos",
        columns: 4,
        images: [
          { url: "/img1.jpg", alt: "Foto 1", caption: "Caption 1" },
          { url: "/img2.jpg", alt: "Foto 2", caption: "Caption 2" },
        ],
      },
    };

    it("renders images and opens Lightbox modal on click", () => {
      render(<GalleryMasonrySection section={gallerySection} />);

      expect(screen.getByText("Galería de Fotos")).toBeDefined();
      const images = screen.getAllByRole("img");
      expect(images.length).toBeGreaterThanOrEqual(2);

      // Click first image container to open lightbox
      const firstCard = images[0].closest(".cursor-pointer");
      expect(firstCard).not.toBeNull();
      if (firstCard) {
        fireEvent.click(firstCard);
      }

      // Check modal components
      expect(screen.getByLabelText("Cerrar")).toBeDefined();
      expect(screen.getByLabelText("Siguiente")).toBeDefined();
      expect(screen.getByLabelText("Anterior")).toBeDefined();

      // Click Next
      fireEvent.click(screen.getByLabelText("Siguiente"));

      // Press Escape to close modal
      fireEvent.keyDown(window, { key: "Escape" });
      expect(screen.queryByLabelText("Cerrar")).toBeNull();
    });

    it("navigates images with arrow keys when lightbox is open", () => {
      render(<GalleryMasonrySection section={gallerySection} />);
      const images = screen.getAllByRole("img");
      const firstCard = images[0].closest(".cursor-pointer");
      if (firstCard) {
        fireEvent.click(firstCard);
      }

      expect(screen.getByLabelText("Cerrar")).toBeDefined();
      fireEvent.keyDown(window, { key: "ArrowRight" });
      fireEvent.keyDown(window, { key: "ArrowLeft" });
    });

    it("renders the anniversary carousel and the full album CTA", () => {
      render(
        <GalleryMasonrySection
          section={{
            ...gallerySection,
            props_json: {
              ...gallerySection.props_json,
              layout: "carousel",
              album_url: "https://photos.app.goo.gl/example",
              album_label: "Ver más fotos en Google Fotos",
            },
          }}
        />,
      );

      expect(screen.getByRole("link", { name: "Ver más fotos en Google Fotos" })).toBeDefined();
      expect(screen.getByLabelText("Foto anterior")).toBeDefined();
      expect(screen.getByLabelText("Foto siguiente")).toBeDefined();
    });
  });

  describe("MapEmbedSection", () => {
    it("renders OpenStreetMap iframe when lat and lng are provided", () => {
      const section: CmsSection<"map_embed"> = {
        id: "s4",
        page_id: "p1",
        section_key: "map-1",
        type: "map_embed",
        sort_order: 4,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          title: "Ubicación Central",
          address: "Calle 100 # 15-20, Bogotá",
          lat: 4.6097,
          lng: -74.0817,
          zoom: 15,
          height_px: 450,
        },
      };

      render(<MapEmbedSection section={section} />);

      expect(screen.getByText("Ubicación Central")).toBeDefined();
      expect(screen.getByText(/Calle 100 # 15-20/)).toBeDefined();

      const iframe = screen.getByTitle("Ubicación Central") as HTMLIFrameElement;
      expect(iframe).toBeDefined();
      expect(iframe.src).toContain("openstreetmap.org/export/embed.html");
      expect(iframe.src).toContain("marker=4.6097%2C-74.0817");
    });

    it("falls back to address embed when coordinates are missing", () => {
      const section: CmsSection<"map_embed"> = {
        id: "s4b",
        page_id: "p1",
        section_key: "map-2",
        type: "map_embed",
        sort_order: 4,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {
          address: "Medellín, Colombia",
        },
      };

      render(<MapEmbedSection section={section} />);

      const iframe = screen.getByTitle("Mapa") as HTMLIFrameElement;
      expect(iframe.src).toContain("maps.google.com/maps?q=Medell%C3%ADn");
    });

    it("renders empty state when no location info is configured", () => {
      const section: CmsSection<"map_embed"> = {
        id: "s4c",
        page_id: "p1",
        section_key: "map-empty",
        type: "map_embed",
        sort_order: 4,
        is_visible: true,
        status: "active",
        created_at: "2026-01-01",
        updated_at: "2026-01-01",
        props_json: {},
      };

      render(<MapEmbedSection section={section} />);
      expect(screen.getByText(/Sin ubicación o coordenadas/)).toBeDefined();
    });
  });
});

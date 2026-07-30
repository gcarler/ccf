import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RichEditor from "./RichEditor";
import { apiFetch } from "@/lib/http";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

describe("RichEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders editor without crashing", () => {
    render(<RichEditor content="<p>Test content</p>" onChange={vi.fn()} />);
    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("opens image picker modal and fetches media from API", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [
        { id: 10, url: "https://example.com/test.jpg", filename: "test.jpg", alt_text: "Test image" },
      ],
    });

    render(<RichEditor content="<p>Content</p>" onChange={vi.fn()} token="test-token" />);

    const imageBtn = screen.getByTitle("Insertar Imagen");
    fireEvent.click(imageBtn);

    expect(screen.getByText("Insertar Imagen")).toBeInTheDocument();

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/cms/media?type=image&limit=12", {
        token: "test-token",
        cache: "no-store",
      });
    });
  });

  it("toggles fullscreen mode and handles Escape key", () => {
    render(<RichEditor content="<p>Content</p>" onChange={vi.fn()} />);

    const fullscreenBtn = screen.getByTitle("Pantalla completa");
    fireEvent.click(fullscreenBtn);

    expect(screen.getByText(/Modo Pantalla Completa/i)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText(/Modo Pantalla Completa/i)).not.toBeInTheDocument();
  });
});

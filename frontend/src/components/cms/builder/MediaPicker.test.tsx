import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MediaPicker from "./MediaPicker";
import { apiFetch } from "@/lib/http";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));

describe("MediaPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when not open", () => {
    const { container } = render(
      <MediaPicker open={false} onClose={vi.fn()} onSelect={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("fetches media items when opened", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [
        { id: 1, url: "/img1.jpg", filename: "img1.jpg", mime_type: "image/jpeg", alt_text: "Img 1" },
        { id: 2, url: "/img2.png", filename: "img2.png", mime_type: "image/png", alt_text: "Img 2" },
      ],
    });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("img1.jpg")).toBeInTheDocument();
      expect(screen.getByText("img2.png")).toBeInTheDocument();
    });

    expect(apiFetch).toHaveBeenCalledWith("/cms/media", { token: "token", cache: "no-store" });
  });

  it("filters non-image items", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [
        { id: 1, url: "/img1.jpg", filename: "img1.jpg", mime_type: "image/jpeg" },
        { id: 2, url: "/doc.pdf", filename: "doc.pdf", mime_type: "application/pdf" },
      ],
    });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("img1.jpg")).toBeInTheDocument();
    });
    expect(screen.queryByText("doc.pdf")).not.toBeInTheDocument();
  });

  it("filters items by search term", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [
        { id: 1, url: "/alpha.jpg", filename: "alpha.jpg", mime_type: "image/jpeg" },
        { id: 2, url: "/beta.jpg", filename: "beta.jpg", mime_type: "image/jpeg" },
      ],
    });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("alpha.jpg")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/buscar por archivo/i);
    fireEvent.change(searchInput, { target: { value: "beta" } });

    expect(screen.queryByText("alpha.jpg")).not.toBeInTheDocument();
    expect(screen.getByText("beta.jpg")).toBeInTheDocument();
  });

  it("calls onSelect when clicking an item", async () => {
    const onSelect = vi.fn();
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [{ id: 1, url: "/img1.jpg", filename: "img1.jpg", mime_type: "image/jpeg" }],
    });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={onSelect} />);

    await waitFor(() => {
      expect(screen.getByTestId("media-item-button")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("media-item-button"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1, url: "/img1.jpg" })
    );
  });

  it("highlights the selected item", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      items: [{ id: 1, url: "/img1.jpg", filename: "img1.jpg", mime_type: "image/jpeg" }],
    });

    render(<MediaPicker open token="token" selectedUrl="/img1.jpg" onClose={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId("media-item-button")).toHaveAttribute("aria-pressed", "true");
    });
  });

  it("uploads a file and selects the created item", async () => {
    const onSelect = vi.fn();
    const file = new File(["content"], "new.png", { type: "image/png" });
    (apiFetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ id: 3, url: "/new.png", filename: "new.png", mime_type: "image/png" });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={onSelect} />);

    const input = screen.getByLabelText(/subir imagen/i);
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ url: "/new.png" }));
    });

    expect(apiFetch).toHaveBeenLastCalledWith(
      "/cms/media/upload",
      expect.objectContaining({ method: "POST", token: "token" })
    );
  });

  it("calls onClose when clicking the close button", () => {
    const onClose = vi.fn();
    render(<MediaPicker open onClose={onClose} onSelect={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /cerrar modal/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows empty state when no images match", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ items: [] });

    render(<MediaPicker open token="token" onClose={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/no hay imagenes disponibles/i)).toBeInTheDocument();
    });
  });
});

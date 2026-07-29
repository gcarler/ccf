import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "@/lib/http";
import MediaFoldersPage from "./page";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
vi.mock("@/lib/site-config", () => ({ SITE_KEY: "test-site" }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("MediaFoldersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state and then the empty state", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<MediaFoldersPage />);

    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/sin carpetas/i)).toBeInTheDocument());
  });

  it("renders a tree of folders", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", name: "Fotos", slug: "fotos", path: "/fotos", parent_id: null },
      { id: "2", name: "2024", slug: "2024", path: "/fotos/2024", parent_id: "1" },
    ]);
    render(<MediaFoldersPage />);

    await waitFor(() => expect(screen.getByText("Fotos")).toBeInTheDocument());
    expect(screen.getByText("2024")).toBeInTheDocument();
  });

  it("creates a new folder and reloads the list", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<MediaFoldersPage />);
    await waitFor(() => expect(screen.getByText(/nueva carpeta/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /nueva carpeta/i }));

    const nameInput = screen.getByPlaceholderText("Nombre");
    const slugInput = screen.getByPlaceholderText("slug");

    fireEvent.change(nameInput, { target: { value: "Eventos" } });
    fireEvent.change(slugInput, { target: { value: "eventos" } });

    apiFetchMock.mockResolvedValueOnce({}).mockResolvedValueOnce([
      { id: "1", name: "Eventos", slug: "eventos", path: "/eventos", parent_id: null },
    ]);

    fireEvent.click(screen.getByRole("button", { name: /^crear$/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/media-folders",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});

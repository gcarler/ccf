import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "@/lib/http";
import SearchAdminPage from "./page";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
vi.mock("@/lib/site-config", () => ({ SITE_KEY: "test-site" }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("SearchAdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders promotions and the search input", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<SearchAdminPage />);

    expect(screen.getByPlaceholderText(/buscar contenido/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/resultados promocionados/i)).toBeInTheDocument());
  });

  it("performs a search and displays results", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<SearchAdminPage />);
    await waitFor(() => expect(screen.getByText(/resultados promocionados/i)).toBeInTheDocument());

    apiFetchMock.mockResolvedValueOnce({ results: [{ entity_type: "cms_page", entity_id: "1", entity_slug: "home", title: "Home", category: null, boost_score: 0 }] });

    const input = screen.getByPlaceholderText(/buscar contenido/i);
    fireEvent.change(input, { target: { value: "home" } });
    fireEvent.click(screen.getByRole("button", { name: /buscar/i }));

    await waitFor(() => expect(screen.getByText("Home")).toBeInTheDocument());
  });

  it("creates a new promotion", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<SearchAdminPage />);
    await waitFor(() => expect(screen.getByText(/promocionar/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /promocionar/i }));

    const keywordInput = screen.getByPlaceholderText("Keyword (ej: vacaciones)");
    const entityIdInput = screen.getByPlaceholderText("Entity ID");

    fireEvent.change(keywordInput, { target: { value: "home" } });
    fireEvent.change(entityIdInput, { target: { value: "1" } });

    apiFetchMock.mockResolvedValueOnce({}).mockResolvedValueOnce([]);
    fireEvent.click(screen.getByRole("button", { name: /^crear$/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/search/promotions",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});

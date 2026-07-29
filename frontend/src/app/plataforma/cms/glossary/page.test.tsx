import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "@/lib/http";
import GlossaryPage from "./page";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
vi.mock("@/lib/site-config", () => ({ SITE_KEY: "test-site" }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("GlossaryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state and then the empty state", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<GlossaryPage />);

    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/0 terminos definidos/i)).toBeInTheDocument());
  });

  it("renders glossary terms grouped by category", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", term: "Bautismo", definition: "Rito de iniciación", aliases: [], category: "Doctrina", language: "es" },
    ]);
    render(<GlossaryPage />);

    await waitFor(() => expect(screen.getByText("Bautismo")).toBeInTheDocument());
    expect(screen.getByText("Doctrina")).toBeInTheDocument();
  });

  it("searches terms via the API", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<GlossaryPage />);
    await waitFor(() => expect(screen.getByText(/0 terminos definidos/i)).toBeInTheDocument());

    apiFetchMock.mockResolvedValueOnce([]);
    const input = screen.getByPlaceholderText(/buscar termino/i);
    fireEvent.change(input, { target: { value: "bautismo" } });

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("search=bautismo"),
        expect.anything(),
      ),
    );
  });

  it("creates a new term and reloads the list", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<GlossaryPage />);
    await waitFor(() => expect(screen.getByText(/nuevo termino/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /nuevo termino/i }));
    const termInput = screen.getByPlaceholderText("Termino");
    const definitionInput = screen.getByPlaceholderText("Definicion...");

    fireEvent.change(termInput, { target: { value: "Comunión" } });
    fireEvent.change(definitionInput, { target: { value: "Sacramento" } });

    apiFetchMock.mockResolvedValueOnce({}).mockResolvedValueOnce([
      { id: "1", term: "Comunión", definition: "Sacramento", aliases: [], category: "General", language: "es" },
    ]);

    fireEvent.click(screen.getByRole("button", { name: /^crear$/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/glossary",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});

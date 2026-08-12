import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsSitesPage from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn(),
    createCmsSite: vi.fn(),
    patchCmsSite: vi.fn(),
  };
});

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import { listCmsSites, createCmsSite, patchCmsSite } from "@/lib/cms/v2";

const site = {
  id: "s1",
  site_key: "ccf",
  name: "CCF Central",
  base_path: "/ccf",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("CmsSitesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([]);
  });

  it("muestra el título y el estado vacío cuando no hay sitios", async () => {
    render(<CmsSitesPage />);

    expect(screen.getByText("Gestión de sitios")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("No hay sitios creados.")).toBeInTheDocument(),
    );
  });

  it("renderiza los sitios registrados con su estado", async () => {
    vi.mocked(listCmsSites).mockResolvedValue([
      site,
      { ...site, id: "s2", site_key: "norte", name: "Comunidad Norte", is_active: false },
    ]);
    render(<CmsSitesPage />);

    await waitFor(() => expect(screen.getByText("CCF Central")).toBeInTheDocument());
    expect(screen.getByText("Comunidad Norte")).toBeInTheDocument();
    expect(screen.getByText("ccf · /ccf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^activo$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^inactivo$/i })).toBeInTheDocument();
  });

  it("sanitiza el site_key mientras se escribe", async () => {
    render(<CmsSitesPage />);

    const keyInput = screen.getByPlaceholderText("site_key (ej. comunidad)");
    fireEvent.change(keyInput, { target: { value: "Mi Sitio 123!" } });
    expect(keyInput).toHaveValue("mi-sitio-123");
  });

  it("crea un sitio derivando y sanitizando el site_key del nombre", async () => {
    render(<CmsSitesPage />);
    await waitFor(() =>
      expect(screen.getByPlaceholderText("Nombre (ej. Comunidad)")).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByPlaceholderText("Nombre (ej. Comunidad)"), {
      target: { value: "Comunidad Cristiana!" },
    });
    fireEvent.change(screen.getByPlaceholderText("base_path (ej. /comunidad)"), {
      target: { value: "comunidad" },
    });
    fireEvent.click(screen.getByRole("button", { name: /crear sitio/i }));

    await waitFor(() =>
      expect(createCmsSite).toHaveBeenCalledWith(
        expect.objectContaining({
          site_key: "comunidad-cristiana",
          name: "Comunidad Cristiana!",
          base_path: "/comunidad",
          is_active: true,
        }),
        "test-token",
      ),
    );
  });

  it("alterna el estado de un sitio con patchCmsSite", async () => {
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    render(<CmsSitesPage />);
    await waitFor(() => expect(screen.getByText("CCF Central")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^activo$/i }));

    await waitFor(() =>
      expect(patchCmsSite).toHaveBeenCalledWith("ccf", { is_active: false }, "test-token"),
    );
  });

  it("un rol sin permisos no puede crear ni alternar sitios", async () => {
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "estudiante" } });
    render(<CmsSitesPage />);

    await waitFor(() =>
      expect(screen.getByText(/Tu rol puede consultar sitios/i)).toBeInTheDocument(),
    );
    const createButton = screen.getByRole("button", { name: /crear sitio/i });
    expect(createButton).toBeDisabled();
    fireEvent.click(createButton);
    expect(createCmsSite).not.toHaveBeenCalled();
  });

  it("recupera el estado vacío si la carga falla", async () => {
    vi.mocked(listCmsSites).mockRejectedValue(new Error("boom"));
    render(<CmsSitesPage />);

    await waitFor(() => expect(screen.getByText("No hay sitios creados.")).toBeInTheDocument());
  });
});

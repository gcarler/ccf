import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsThemesPage from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/site-config", () => ({ SITE_KEY: "ccf" }));

vi.mock("@/components/cms/themes/ThemePreview", () => ({
  __esModule: true,
  default: () => <div data-testid="theme-preview" />,
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn(),
    listCmsThemes: vi.fn(),
    createCmsTheme: vi.fn(),
    patchCmsTheme: vi.fn(),
    deleteCmsTheme: vi.fn(),
    activateCmsTheme: vi.fn(),
  };
});

import {
  listCmsSites,
  listCmsThemes,
  createCmsTheme,
  patchCmsTheme,
  deleteCmsTheme,
  activateCmsTheme,
} from "@/lib/cms/v2";

const site = {
  id: "s1",
  site_key: "ccf",
  name: "CCF",
  base_path: "/",
  is_active: true,
  created_at: "",
  updated_at: "",
};
const theme = {
  id: "t1",
  site_id: "s1",
  name: "Tema Oscuro",
  tokens_json: { "--site-primary": "#123456" },
  is_active: true,
  status: "active",
  version: 1,
  created_at: "",
  updated_at: "",
};

describe("CmsThemesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    vi.mocked(listCmsThemes).mockResolvedValue([]);
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
    // jsdom no implementa navegación: stub del click del enlace de exportación.
    HTMLAnchorElement.prototype.click = vi.fn();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });
  });

  it("renderiza el editor de temas y el estado vacío", async () => {
    render(<CmsThemesPage />);

    expect(screen.getByText("Editor de Temas")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("No hay temas guardados para este sitio.")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("theme-preview")).toBeInTheDocument();
  });

  it("renderiza los temas guardados con la insignia Activo", async () => {
    vi.mocked(listCmsThemes).mockResolvedValue([theme]);
    render(<CmsThemesPage />);

    await waitFor(() => expect(screen.getByText("Tema Oscuro")).toBeInTheDocument());
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.queryByText("No hay temas guardados para este sitio.")).not.toBeInTheDocument();
  });

  it("guarda y activa un tema nuevo", async () => {
    vi.mocked(createCmsTheme).mockResolvedValue({ ...theme, id: "t-new", name: "Tema Nuevo" });
    render(<CmsThemesPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /guardar y activar/i })).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByDisplayValue("Tema personalizado"), {
      target: { value: "Tema Nuevo" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar y activar/i }));

    await waitFor(() =>
      expect(createCmsTheme).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ name: "Tema Nuevo", status: "active", is_active: true }),
        "test-token",
      ),
    );
    await waitFor(() =>
      expect(activateCmsTheme).toHaveBeenCalledWith("ccf", "t-new", "test-token"),
    );
    expect(await screen.findByText("Tema guardado y activado.")).toBeInTheDocument();
  });

  it("edita y actualiza un tema existente", async () => {
    vi.mocked(listCmsThemes).mockResolvedValue([theme]);
    render(<CmsThemesPage />);
    await waitFor(() => expect(screen.getByText("Tema Oscuro")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^editar$/i }));
    fireEvent.click(screen.getByRole("button", { name: /actualizar y activar/i }));

    await waitFor(() =>
      expect(patchCmsTheme).toHaveBeenCalledWith(
        "ccf",
        "t1",
        expect.objectContaining({ name: "Tema Oscuro" }),
        "test-token",
      ),
    );
    await waitFor(() =>
      expect(activateCmsTheme).toHaveBeenCalledWith("ccf", "t1", "test-token"),
    );
    expect(await screen.findByText("Tema actualizado y activado.")).toBeInTheDocument();
  });

  it("activa un tema inactivo", async () => {
    vi.mocked(listCmsThemes).mockResolvedValue([{ ...theme, is_active: false }]);
    render(<CmsThemesPage />);
    await waitFor(() => expect(screen.getByText("Tema Oscuro")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^activar$/i }));

    await waitFor(() =>
      expect(activateCmsTheme).toHaveBeenCalledWith("ccf", "t1", "test-token"),
    );
    expect(await screen.findByText("Tema activado.")).toBeInTheDocument();
  });

  it("archiva un tema tras confirmar el modal", async () => {
    vi.mocked(listCmsThemes).mockResolvedValue([theme]);
    render(<CmsThemesPage />);
    await waitFor(() => expect(screen.getByText("Tema Oscuro")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^archivar$/i }));
    expect(screen.getByText("¿Archivar tema?")).toBeInTheDocument();

    const confirm = screen.getAllByRole("button", { name: /^archivar$/i }).at(-1);
    expect(confirm).toBeDefined();
    fireEvent.click(confirm!);

    await waitFor(() =>
      expect(deleteCmsTheme).toHaveBeenCalledWith("ccf", "t1", "test-token"),
    );
    expect(await screen.findByText("Tema archivado.")).toBeInTheDocument();
  });

  it("restaura un tema archivado", async () => {
    vi.mocked(listCmsThemes).mockResolvedValue([
      { ...theme, status: "archived", is_active: false },
    ]);
    render(<CmsThemesPage />);
    await waitFor(() => expect(screen.getByText("Tema Oscuro")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^restaurar$/i }));

    await waitFor(() =>
      expect(patchCmsTheme).toHaveBeenCalledWith(
        "ccf",
        "t1",
        { status: "active", is_active: false },
        "test-token",
      ),
    );
    expect(await screen.findByText("Tema restaurado.")).toBeInTheDocument();
  });

  it("importa un tema desde JSON", async () => {
    render(<CmsThemesPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /importar json/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /importar json/i }));
    fireEvent.change(screen.getByPlaceholderText(/tokens_json/), {
      target: { value: JSON.stringify({ name: "Mi tema", tokens_json: { "--site-primary": "#ff0000" } }) },
    });
    fireEvent.click(screen.getByRole("button", { name: /aplicar json/i }));

    expect(screen.getByText("Tema importado correctamente.")).toBeInTheDocument();
  });

  it("exporta el tema a JSON", async () => {
    render(<CmsThemesPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^exportar$/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /^exportar$/i }));

    expect(screen.getByText("JSON exportado.")).toBeInTheDocument();
  });

  it("copia los tokens al portapapeles", async () => {
    render(<CmsThemesPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^copiar$/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /^copiar$/i }));

    expect(navigator.clipboard.writeText).toHaveBeenCalled();
    expect(await screen.findByText("Tokens copiados al portapapeles.")).toBeInTheDocument();
  });

  it("un rol editor sin permiso de publicación guarda sin activar", async () => {
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "docente" } });
    vi.mocked(createCmsTheme).mockResolvedValue({ ...theme, id: "t-new", name: "Tema Nuevo" });
    render(<CmsThemesPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /guardar y activar/i })).toBeInTheDocument(),
    );

    fireEvent.change(screen.getByDisplayValue("Tema personalizado"), {
      target: { value: "Tema Nuevo" },
    });
    fireEvent.click(screen.getByRole("button", { name: /guardar y activar/i }));

    await waitFor(() =>
      expect(createCmsTheme).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ name: "Tema Nuevo", is_active: false }),
        "test-token",
      ),
    );
    expect(activateCmsTheme).not.toHaveBeenCalled();
    expect(
      await screen.findByText("Tema guardado. Solo un publicador puede activarlo."),
    ).toBeInTheDocument();
  });
});

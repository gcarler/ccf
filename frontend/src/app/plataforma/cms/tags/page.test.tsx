import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsTagsManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/site-config", () => ({ SITE_KEY: "ccf" }));

vi.mock("@/components/ui/SidePanel", () => ({
  __esModule: true,
  default: ({ isOpen, children }: { isOpen: boolean; children?: React.ReactNode }) =>
    isOpen ? <div role="dialog" aria-label="side-panel">{children}</div> : null,
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn(),
    listCmsTags: vi.fn(),
    createCmsTag: vi.fn(),
    patchCmsTag: vi.fn(),
    deleteCmsTag: vi.fn(),
  };
});

import {
  listCmsSites,
  listCmsTags,
  createCmsTag,
  patchCmsTag,
  deleteCmsTag,
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
const tag = {
  id: "t1",
  site_id: "s1",
  slug: "fe",
  name: "Fe",
  is_active: true,
  created_at: "",
  updated_at: "",
};

describe("CmsTagsManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    vi.mocked(listCmsTags).mockResolvedValue([]);
  });

  it("muestra el estado vacío cuando no hay etiquetas", async () => {
    render(<CmsTagsManagement />);

    await waitFor(() => expect(screen.getByText("Sin etiquetas")).toBeInTheDocument());
  });

  it("renderiza las etiquetas con su slug", async () => {
    vi.mocked(listCmsTags).mockResolvedValue([tag]);
    render(<CmsTagsManagement />);

    await waitFor(() => expect(screen.getByText("Fe")).toBeInTheDocument());
    expect(screen.getByText("/fe")).toBeInTheDocument();
  });

  it("filtra por búsqueda", async () => {
    vi.mocked(listCmsTags).mockResolvedValue([
      tag,
      { ...tag, id: "t2", slug: "oracion", name: "Oración" },
    ]);
    render(<CmsTagsManagement />);
    await waitFor(() => expect(screen.getByText("Fe")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Buscar..."), { target: { value: "oracion" } });

    expect(screen.queryByText("Fe")).not.toBeInTheDocument();
    expect(screen.getByText("Oración")).toBeInTheDocument();
  });

  it("crea una etiqueta vía quick add con slug derivado", async () => {
    render(<CmsTagsManagement />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /nueva etiqueta/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /nueva etiqueta/i }));
    fireEvent.change(screen.getByPlaceholderText("Nombre de la etiqueta (Enter para crear)"), {
      target: { value: "Discipulado" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() =>
      expect(createCmsTag).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ name: "Discipulado", slug: "discipulado" }),
        "test-token",
      ),
    );
  });

  it("archiva una etiqueta tras confirmar el modal", async () => {
    vi.mocked(listCmsTags).mockResolvedValue([tag]);
    render(<CmsTagsManagement />);
    await waitFor(() => expect(screen.getByText("Fe")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Archivar"));
    expect(screen.getByText("¿Archivar etiqueta?")).toBeInTheDocument();

    const confirm = screen.getAllByRole("button", { name: /^archivar$/i }).at(-1);
    expect(confirm).toBeDefined();
    fireEvent.click(confirm!);

    await waitFor(() =>
      expect(deleteCmsTag).toHaveBeenCalledWith("ccf", "fe", "test-token"),
    );
  });

  it("restaura una etiqueta archivada", async () => {
    vi.mocked(listCmsTags).mockResolvedValue([{ ...tag, is_active: false }]);
    render(<CmsTagsManagement />);
    await waitFor(() => expect(screen.getByText("Fe")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Restaurar"));

    await waitFor(() =>
      expect(patchCmsTag).toHaveBeenCalledWith("ccf", "fe", { is_active: true }, "test-token"),
    );
  });

  it("edita una etiqueta desde el panel lateral", async () => {
    vi.mocked(listCmsTags).mockResolvedValue([tag]);
    render(<CmsTagsManagement />);
    await waitFor(() => expect(screen.getByText("Fe")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Fe"));
    const nameInput = screen.getByDisplayValue("Fe");
    fireEvent.change(nameInput, { target: { value: "Fe y Esperanza" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() =>
      expect(patchCmsTag).toHaveBeenCalledWith(
        "ccf",
        "fe",
        expect.objectContaining({ name: "Fe y Esperanza" }),
        "test-token",
      ),
    );
  });

  it("muestra el banner de error cuando la carga falla", async () => {
    vi.mocked(listCmsTags).mockRejectedValue(new Error("boom"));
    render(<CmsTagsManagement />);

    await waitFor(() =>
      expect(screen.getByText("No se pudieron cargar las etiquetas.")).toBeInTheDocument(),
    );
  });
});

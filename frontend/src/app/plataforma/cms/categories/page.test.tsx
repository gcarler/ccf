import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsCategoriesManagement from "./page";

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
    listCmsCategories: vi.fn(),
    createCmsCategory: vi.fn(),
    patchCmsCategory: vi.fn(),
    deleteCmsCategory: vi.fn(),
  };
});

import {
  listCmsSites,
  listCmsCategories,
  createCmsCategory,
  patchCmsCategory,
  deleteCmsCategory,
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
const category = {
  id: "c1",
  site_id: "s1",
  parent_id: null,
  slug: "ensenanza",
  name: "Enseñanza",
  description: "Predicaciones",
  is_active: true,
  created_at: "",
  updated_at: "",
};

describe("CmsCategoriesManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    vi.mocked(listCmsCategories).mockResolvedValue([]);
  });

  it("muestra el estado vacío cuando no hay categorías", async () => {
    render(<CmsCategoriesManagement />);

    await waitFor(() => expect(screen.getByText("Sin categorías")).toBeInTheDocument());
  });

  it("renderiza las categorías con slug y descripción", async () => {
    vi.mocked(listCmsCategories).mockResolvedValue([category]);
    render(<CmsCategoriesManagement />);

    await waitFor(() => expect(screen.getByText("Enseñanza")).toBeInTheDocument());
    expect(screen.getByText("/ensenanza")).toBeInTheDocument();
    expect(screen.getByText("Predicaciones")).toBeInTheDocument();
  });

  it("filtra por búsqueda por nombre o slug", async () => {
    vi.mocked(listCmsCategories).mockResolvedValue([
      category,
      { ...category, id: "c2", slug: "oracion", name: "Oración" },
    ]);
    render(<CmsCategoriesManagement />);
    await waitFor(() => expect(screen.getByText("Enseñanza")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Buscar..."), { target: { value: "oracion" } });

    expect(screen.queryByText("Enseñanza")).not.toBeInTheDocument();
    expect(screen.getByText("Oración")).toBeInTheDocument();
  });

  it("crea una categoría vía quick add con slug derivado", async () => {
    render(<CmsCategoriesManagement />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /nueva categor/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /nueva categor/i }));
    fireEvent.change(screen.getByPlaceholderText("Nombre de la categoría (Enter para crear)"), {
      target: { value: "Misiones" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() =>
      expect(createCmsCategory).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ name: "Misiones", slug: "misiones" }),
        "test-token",
      ),
    );
  });

  it("archiva una categoría tras confirmar el modal", async () => {
    vi.mocked(listCmsCategories).mockResolvedValue([category]);
    render(<CmsCategoriesManagement />);
    await waitFor(() => expect(screen.getByText("Enseñanza")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Archivar"));
    expect(screen.getByText("¿Archivar categoría?")).toBeInTheDocument();

    const confirm = screen.getAllByRole("button", { name: /^archivar$/i }).at(-1);
    expect(confirm).toBeDefined();
    fireEvent.click(confirm!);

    await waitFor(() =>
      expect(deleteCmsCategory).toHaveBeenCalledWith("ccf", "ensenanza", "test-token"),
    );
  });

  it("restaura una categoría archivada", async () => {
    vi.mocked(listCmsCategories).mockResolvedValue([{ ...category, is_active: false }]);
    render(<CmsCategoriesManagement />);
    await waitFor(() => expect(screen.getByText("Enseñanza")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Restaurar"));

    await waitFor(() =>
      expect(patchCmsCategory).toHaveBeenCalledWith(
        "ccf",
        "ensenanza",
        { is_active: true },
        "test-token",
      ),
    );
  });

  it("edita una categoría desde el panel lateral", async () => {
    vi.mocked(listCmsCategories).mockResolvedValue([category]);
    render(<CmsCategoriesManagement />);
    await waitFor(() => expect(screen.getByText("Enseñanza")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Enseñanza"));
    const nameInput = screen.getByDisplayValue("Enseñanza");
    fireEvent.change(nameInput, { target: { value: "Enseñanza Avanzada" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() =>
      expect(patchCmsCategory).toHaveBeenCalledWith(
        "ccf",
        "ensenanza",
        expect.objectContaining({ name: "Enseñanza Avanzada" }),
        "test-token",
      ),
    );
  });

  it("muestra el banner de error cuando la carga falla", async () => {
    vi.mocked(listCmsCategories).mockRejectedValue(new Error("boom"));
    render(<CmsCategoriesManagement />);

    await waitFor(() =>
      expect(screen.getByText("No se pudieron cargar las categorías.")).toBeInTheDocument(),
    );
  });
});

import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsPostsManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/site-config", () => ({ SITE_KEY: "ccf" }));

vi.mock("next/dynamic", () => ({
  __esModule: true,
  default: () => {
    return function MockDynamicComponent() {
      return null;
    };
  },
}));

vi.mock("@/components/ui/SidePanel", () => ({
  __esModule: true,
  default: ({ isOpen, children }: { isOpen: boolean; children?: React.ReactNode }) =>
    isOpen ? <div role="dialog" aria-label="side-panel">{children}</div> : null,
}));

vi.mock("@/components/ViewSwitcher", () => ({
  __esModule: true,
  default: ({
    setViewType,
    availableViews,
  }: {
    setViewType: (view: string) => void;
    availableViews: string[];
  }) => (
    <div>
      {availableViews.map((view) => (
        <button key={view} onClick={() => setViewType(view)}>{view}</button>
      ))}
    </div>
  ),
}));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn(),
    listCmsPosts: vi.fn(),
    listCmsCategories: vi.fn(),
    listCmsTags: vi.fn(),
    createCmsPost: vi.fn(),
    patchCmsPost: vi.fn(),
  };
});

import {
  listCmsSites,
  listCmsPosts,
  listCmsCategories,
  listCmsTags,
  createCmsPost,
  patchCmsPost,
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
  id: "cat1",
  site_id: "s1",
  parent_id: null,
  slug: "devocional",
  name: "Devocional",
  description: null,
  is_active: true,
  created_at: "",
  updated_at: "",
};
const tag = {
  id: "tag1",
  site_id: "s1",
  slug: "fe",
  name: "Fe",
  is_active: true,
  created_at: "",
  updated_at: "",
};
const post = {
  id: "po1",
  site_id: "s1",
  slug: "devocional-diario",
  title: "Devocional Diario",
  excerpt: "Un resumen breve",
  content: "Contenido del devocional",
  featured_image_url: null,
  status: "draft",
  seo_json: {},
  locale: "es",
  published_at: null,
  expires_at: null,
  author_persona_id: null,
  created_by_persona_id: null,
  updated_by_persona_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  categories: [category],
  tags: [tag],
};

describe("CmsPostsManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    vi.mocked(listCmsPosts).mockResolvedValue([]);
    vi.mocked(listCmsCategories).mockResolvedValue([category]);
    vi.mocked(listCmsTags).mockResolvedValue([tag]);
  });

  it("muestra el estado vacío cuando no hay posts", async () => {
    render(<CmsPostsManagement />);

    await waitFor(() => expect(screen.getByText("No hay posts creados")).toBeInTheDocument());
  });

  it("renderiza los posts con categorías y etiquetas", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([post]);
    render(<CmsPostsManagement />);

    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());
    expect(screen.getByText("/devocional-diario")).toBeInTheDocument();
    expect(screen.getByText("Devocional")).toBeInTheDocument();
    expect(screen.getByText("Fe")).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
  });

  it("filtra por búsqueda", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([
      post,
      { ...post, id: "po2", slug: "oracion", title: "Oración matinal" },
    ]);
    render(<CmsPostsManagement />);
    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Buscar posts..."), {
      target: { value: "oracion" },
    });

    expect(screen.queryByText("Devocional Diario")).not.toBeInTheDocument();
    expect(screen.getByText("Oración matinal")).toBeInTheDocument();
  });

  it("crea un post vía quick add como borrador", async () => {
    render(<CmsPostsManagement />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /nuevo post/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /nuevo post/i }));
    fireEvent.change(screen.getByPlaceholderText("Título del nuevo post (Enter para crear)"), {
      target: { value: "Bienvenida" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() =>
      expect(createCmsPost).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ title: "Bienvenida", slug: "bienvenida", status: "draft" }),
        "test-token",
      ),
    );
  });

  it("archiva un post tras confirmar desde el panel", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([post]);
    render(<CmsPostsManagement />);
    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Archivar post"));
    const confirm = screen.getAllByRole("button", { name: /^archivar$/i }).at(-1);
    expect(confirm).toBeDefined();
    fireEvent.click(confirm!);

    await waitFor(() =>
      expect(patchCmsPost).toHaveBeenCalledWith(
        "ccf",
        "devocional-diario",
        { status: "archived" },
        "test-token",
      ),
    );
  });

  it("restaura un post archivado a borrador", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([{ ...post, status: "archived" }]);
    render(<CmsPostsManagement />);
    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Restaurar a borrador"));

    await waitFor(() =>
      expect(patchCmsPost).toHaveBeenCalledWith(
        "ccf",
        "devocional-diario",
        { status: "draft" },
        "test-token",
      ),
    );
  });

  it("edita un post desde el panel lateral", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([post]);
    vi.mocked(patchCmsPost).mockResolvedValue({ ...post, title: "Devocional Actualizado" });
    render(<CmsPostsManagement />);
    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Devocional Diario"));
    const titleInput = screen.getByDisplayValue("Devocional Diario");
    fireEvent.change(titleInput, { target: { value: "Devocional Actualizado" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await waitFor(() =>
      expect(patchCmsPost).toHaveBeenCalledWith(
        "ccf",
        "devocional-diario",
        expect.objectContaining({ title: "Devocional Actualizado", status: "draft" }),
        "test-token",
      ),
    );
  });

  it("publica un post desde el editor a pantalla completa", async () => {
    vi.mocked(listCmsPosts).mockResolvedValue([post]);
    vi.mocked(patchCmsPost).mockResolvedValue({ ...post, status: "published" });
    render(<CmsPostsManagement />);
    await waitFor(() => expect(screen.getByText("Devocional Diario")).toBeInTheDocument());

    // Abre el editor del post y pasa a pantalla completa.
    fireEvent.click(screen.getByText("Devocional Diario"));
    fireEvent.click(screen.getByTitle("Modo pantalla completa (Ctrl+Shift+F)"));

    const overlay = screen.getByRole("dialog", { name: /editor de post a pantalla completa/i });
    fireEvent.click(within(overlay).getByRole("button", { name: /^publicar$/i }));

    await waitFor(() =>
      expect(patchCmsPost).toHaveBeenCalledWith(
        "ccf",
        "devocional-diario",
        expect.objectContaining({ status: "published", title: "Devocional Diario" }),
        "test-token",
      ),
    );
  });

  it("muestra el banner de error cuando la carga falla", async () => {
    vi.mocked(listCmsPosts).mockRejectedValue(new Error("boom"));
    render(<CmsPostsManagement />);

    await waitFor(() =>
      expect(screen.getByText("No se pudieron cargar los posts.")).toBeInTheDocument(),
    );
  });
});

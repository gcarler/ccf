import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsPagesManagement from "./page";

const mockUseAuth = vi.fn();
const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/site-config", () => ({ SITE_KEY: "ccf" }));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

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

vi.mock("@/components/ui/UniversalCalendarView", () => ({
  __esModule: true,
  default: () => null,
}));
vi.mock("@/components/ui/UniversalGanttView", () => ({
  __esModule: true,
  default: () => null,
}));
vi.mock("@/components/ui/UniversalWikiView", () => ({
  __esModule: true,
  default: () => null,
}));
vi.mock("@/components/ui/OptimizedImage", () => ({
  __esModule: true,
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}));

vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn(),
    listCmsPages: vi.fn(),
    createCmsPage: vi.fn(),
    patchCmsPage: vi.fn(),
    workflowCmsPage: vi.fn(),
  };
});

import {
  listCmsSites,
  listCmsPages,
  createCmsPage,
  workflowCmsPage,
} from "@/lib/cms/v2";
import { toast } from "sonner";

const site = {
  id: "s1",
  site_key: "ccf",
  name: "CCF",
  base_path: "/",
  is_active: true,
  created_at: "",
  updated_at: "",
};
const page = {
  id: "p1",
  site_id: "s1",
  slug: "inicio",
  title: "Inicio",
  status: "draft",
  seo_json: {},
  published_version_id: null,
  publish_at: null,
  expires_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("CmsPagesManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ token: "test-token", user: { role: "admin" } });
    vi.mocked(listCmsSites).mockResolvedValue([site]);
    vi.mocked(listCmsPages).mockResolvedValue([]);
    window.open = vi.fn();
  });

  it("muestra el estado vacío cuando no hay páginas", async () => {
    render(<CmsPagesManagement />);

    await waitFor(() => expect(screen.getByText("No hay paginas creadas")).toBeInTheDocument());
  });

  it("renderiza las páginas en grid con su estado", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);

    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());
    expect(screen.getByText("/inicio")).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
  });

  it("filtra por búsqueda", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([
      page,
      { ...page, id: "p2", slug: "nosotros", title: "Nosotros", status: "published" },
    ]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Buscar paginas..."), {
      target: { value: "nosotros" },
    });

    expect(screen.queryByText("Inicio")).not.toBeInTheDocument();
    expect(screen.getByText("Nosotros")).toBeInTheDocument();
  });

  it("crea una página vía quick add con slug derivado", async () => {
    render(<CmsPagesManagement />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /nueva pagina/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /nueva pagina/i }));
    fireEvent.change(
      screen.getByPlaceholderText("Titulo de la nueva pagina (Enter para crear)"),
      { target: { value: "Mi Pagina" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /^guardar$/i }));

    await waitFor(() =>
      expect(createCmsPage).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({ title: "Mi Pagina", slug: "mi-pagina" }),
        "test-token",
      ),
    );
  });

  it("archiva una página tras confirmar el modal", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Archivar pagina"));
    expect(screen.getByText("¿Archivar página?")).toBeInTheDocument();

    const confirm = screen.getAllByRole("button", { name: /^archivar$/i }).at(-1);
    expect(confirm).toBeDefined();
    fireEvent.click(confirm!);

    await waitFor(() =>
      expect(workflowCmsPage).toHaveBeenCalledWith(
        "ccf",
        "inicio",
        "archive",
        "Archivada desde gestion de paginas",
        "test-token",
      ),
    );
  });

  it("restaura una página archivada desde la fila", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([{ ...page, status: "archived" }]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByTitle("Restaurar a borrador"));

    await waitFor(() =>
      expect(workflowCmsPage).toHaveBeenCalledWith(
        "ccf",
        "inicio",
        "revert_draft",
        "Restaurada desde archivo",
        "test-token",
      ),
    );
  });

  it("archiva en bloque las páginas seleccionadas desde la vista table", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([
      page,
      { ...page, id: "p2", slug: "nosotros", title: "Nosotros" },
    ]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    // La barra de acciones en bloque vive en la vista table.
    fireEvent.click(screen.getByRole("button", { name: "table" }));
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBeGreaterThanOrEqual(3);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);

    fireEvent.click(screen.getByRole("button", { name: /archivar seleccion/i }));
    expect(screen.getByText("¿Archivar 2 páginas?")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /archivar todas/i }));

    await waitFor(() => expect(workflowCmsPage).toHaveBeenCalledTimes(2));
    expect(workflowCmsPage).toHaveBeenCalledWith(
      "ccf",
      "inicio",
      "archive",
      "Archivada desde seleccion multiple",
      "test-token",
    );
    expect(workflowCmsPage).toHaveBeenCalledWith(
      "ccf",
      "nosotros",
      "archive",
      "Archivada desde seleccion multiple",
      "test-token",
    );
  });

  it("navega al detalle al hacer clic en la página", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Inicio"));

    expect(routerPush).toHaveBeenCalledWith("/plataforma/cms/builder?site=ccf&page=inicio&mode=content");
  });

  it("abre el editor de contenido desde el botón Editar contenido", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^editar contenido$/i }));

    expect(routerPush).toHaveBeenCalledWith(
      "/plataforma/cms/builder?site=ccf&page=inicio&mode=content",
    );
  });

  it("abre la vista previa en una ventana nueva", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /preview/i }));

    expect(window.open).toHaveBeenCalledWith(
      expect.stringContaining("/plataforma/cms/preview"),
      "_blank",
    );
  });

  it("cambia a vista board agrupando por estado", async () => {
    vi.mocked(listCmsPages).mockResolvedValue([page]);
    render(<CmsPagesManagement />);
    await waitFor(() => expect(screen.getByText("Inicio")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "board" }));

    expect(screen.getByText("En revision")).toBeInTheDocument();
    expect(screen.getByText("Archivado")).toBeInTheDocument();
  });

  it("avisa de sesión expirada cuando la carga responde 401", async () => {
    vi.mocked(listCmsPages).mockRejectedValue({ status: 401 });
    render(<CmsPagesManagement />);

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Sesión expirada. Inicia sesión nuevamente."),
    );
  });
});

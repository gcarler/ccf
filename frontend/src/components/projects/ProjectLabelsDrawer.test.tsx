import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ProjectLabelsDrawer } from "./ProjectLabelsDrawer";
import { apiFetch } from "@/lib/http";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "fake-jwt-token",
    user: { id: "u-1", name: "Admin" },
    isAuthenticated: true,
  }),
}));

vi.mock("@/context/ProjectUpdateContext", () => ({
  useOptionalProjectUpdate: () => ({
    project: { id: "p-1", title: "Test Project" },
    tasks: [
      { id: "t-1", title: "Actividad 1", labels: ["Diseño", "Urgente"] },
      { id: "t-2", title: "Actividad 2", labels: ["Urgente"] },
    ],
    phases: [],
    activities: [],
    loading: false,
    reloadProject: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    updateProject: vi.fn(),
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

function renderDrawer(ui: React.ReactElement) {
  return render(<SidebarLayerProvider>{ui}</SidebarLayerProvider>);
}

describe("ProjectLabelsDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "Backend", task_count: 3 },
      { name: "Frontend", task_count: 5 },
    ]);
  });

  it("renders labels fetched from API and context", async () => {
    renderDrawer(
      <ProjectLabelsDrawer
        projectId="p-1"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText("Gestor de Etiquetas")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Backend")).toBeInTheDocument();
      expect(screen.getByText("Frontend")).toBeInTheDocument();
    });

    expect(screen.getByText("3 actividades")).toBeInTheDocument();
    expect(screen.getByText("5 actividades")).toBeInTheDocument();
  });

  it("renders in embedded mode without crashing", async () => {
    const { container } = renderDrawer(
      <ProjectLabelsDrawer
        projectId="p-1"
        embedded={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Backend")).toBeInTheDocument();
    });

    expect(container.querySelector("form")).toBeInTheDocument();
  });

  it("creates a new label locally and notifies user", async () => {
    renderDrawer(
      <ProjectLabelsDrawer
        projectId="p-1"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Backend")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText("Ej: Urgente, Frontend, Pastoral...");
    fireEvent.change(input, { target: { value: "Infraestructura" } });

    const createBtn = screen.getByRole("button", { name: /Crear/i });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(screen.getByText("Infraestructura")).toBeInTheDocument();
    });
  });

  it("handles inline rename of a label", async () => {
    vi.mocked(apiFetch).mockImplementation((_url: string, opts?: { method?: string }) => {
      if (opts?.method === "PATCH") {
        return Promise.resolve([
          { name: "Backend Core", task_count: 3 },
          { name: "Frontend", task_count: 5 },
        ]);
      }
      return Promise.resolve([
        { name: "Backend", task_count: 3 },
        { name: "Frontend", task_count: 5 },
      ]);
    });

    renderDrawer(
      <ProjectLabelsDrawer
        projectId="p-1"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Backend")).toBeInTheDocument();
    });

    // Click edit on Backend
    const renameBtn = screen.getByRole("button", { name: "Renombrar etiqueta Backend" });
    fireEvent.click(renameBtn);

    // Edit input should appear
    const editInput = screen.getByDisplayValue("Backend");
    fireEvent.change(editInput, { target: { value: "Backend Core" } });

    // Click save
    const saveBtn = screen.getByRole("button", { name: "Guardar nombre" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/projects/p-1/labels",
        expect.objectContaining({
          method: "PATCH",
          body: { old_name: "Backend", new_name: "Backend Core" },
        })
      );
    });
  });

  it("handles inline delete without any AlertDialog/modals", async () => {
    vi.mocked(apiFetch).mockImplementation((_url: string, opts?: { method?: string }) => {
      if (opts?.method === "DELETE") {
        return Promise.resolve([
          { name: "Frontend", task_count: 5 },
        ]);
      }
      return Promise.resolve([
        { name: "Backend", task_count: 3 },
        { name: "Frontend", task_count: 5 },
      ]);
    });

    renderDrawer(
      <ProjectLabelsDrawer
        projectId="p-1"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Backend")).toBeInTheDocument();
    });

    // Click delete on Backend
    const deleteBtn = screen.getByRole("button", { name: "Eliminar etiqueta Backend" });
    fireEvent.click(deleteBtn);

    // Inline confirmation text should appear
    expect(screen.getByText(/¿Eliminar la etiqueta "Backend"\?/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();

    const confirmDeleteBtn = screen.getByRole("button", { name: "Sí, eliminar" });
    fireEvent.click(confirmDeleteBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/projects/p-1/labels?name=Backend",
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });
});

describe("ProjectLabelsDrawer — Gobernanza de Taxonomía PMI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("presenta el diagnóstico de taxonomía PMI con conteos de uso y las 4 dimensiones", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "Riesgo Sala", task_count: 1 },
      { name: "Revisión DoD", task_count: 0 },
      { name: "Hito Contabilidad", task_count: 2 },
      { name: "Urgente", task_count: 4 },
    ]);

    renderDrawer(
      <ProjectLabelsDrawer projectId="p-1" isOpen={true} onClose={vi.fn()} />
    );

    const summary = await screen.findByTestId("labels-pmi-taxonomy-summary");
    const text = () => summary.textContent ?? "";

    // Clasificación por Dimensión PMI (riesgo > calidad > hito > operativa);
    // contexto agrega Diseño y Urgente (2 operativas)
    expect(text()).toMatch(/Riesgo\s*\/\s*Bloqueo:\s*1/);
    expect(text()).toMatch(/Calidad\s*\/\s*DoD:\s*1/);
    expect(text()).toMatch(/Hito\s*\/\s*Entregable:\s*1/);
    expect(text()).toMatch(/Operativa:\s*2/);

    // Con uso: Riesgo(1), Hito(2), Urgente(4) y Diseño(1); sin uso: Revisión DoD → 1 huérfana
    expect(text()).toMatch(/4\s+en uso/);
    expect(text()).toMatch(/1\s+sin uso\s*\/\s*huérfanas/);
  });

  it("siembra las 4 etiquetas canónicas PMI en 1 clic vía labels-pmi-seed-btn", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "Urgente", task_count: 2 },
    ]);

    renderDrawer(
      <ProjectLabelsDrawer projectId="p-1" isOpen={true} onClose={vi.fn()} />
    );

    await screen.findByText("Urgente");
    const seedBtn = screen.getByTestId("labels-pmi-seed-btn");
    expect(screen.queryByText("PMI: Hito Crítico")).not.toBeInTheDocument();

    fireEvent.click(seedBtn);

    // Las 4 canónicas aparecen en el catálogo local persistido y en la lista
    await waitFor(() => {
      expect(screen.getByText("PMI: Hito Crítico")).toBeInTheDocument();
    });
    expect(screen.getByText("PMI: Control Calidad DoD")).toBeInTheDocument();
    expect(screen.getByText("PMI: Riesgo / Bloqueo")).toBeInTheDocument();
    expect(screen.getByText("PMI: Entregable Principal")).toBeInTheDocument();

    const stored = JSON.parse(localStorage.getItem("projectLabelsCatalog:p-1") ?? "[]");
    for (const canonical of [
      "PMI: Hito Crítico",
      "PMI: Control Calidad DoD",
      "PMI: Riesgo / Bloqueo",
      "PMI: Entregable Principal",
    ]) {
      expect(stored).toContain(canonical);
    }
  });

  it("filtra las etiquetas por uso con labels-usage-filter", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "Arcaico", task_count: 0 },
      { name: "Backend", task_count: 3 },
    ]);

    renderDrawer(
      <ProjectLabelsDrawer projectId="p-1" isOpen={true} onClose={vi.fn()} />
    );

    const filter = await screen.findByTestId("labels-usage-filter");
    // Contexto: Arcaico(0), Backend(3), Diseño(1), Urgente(1) → todos visibles con "Todas"
    expect(screen.getByText("Arcaico")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();

    // "Sin Uso": solo la huérfana Arcaico
    fireEvent.click(within(filter).getByRole("button", { name: "Sin Uso" }));
    expect(screen.getByText("Arcaico")).toBeInTheDocument();
    expect(screen.queryByText("Backend")).not.toBeInTheDocument();

    // "En Uso": solo etiquetas con actividad asociada
    fireEvent.click(within(filter).getByRole("button", { name: "En Uso" }));
    expect(screen.getByText("Backend")).toBeInTheDocument();
    expect(screen.queryByText("Arcaico")).not.toBeInTheDocument();

    // Retorno a "Todas": catálogo completo
    fireEvent.click(within(filter).getByRole("button", { name: "Todas" }));
    expect(screen.getByText("Arcaico")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
  });
});

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

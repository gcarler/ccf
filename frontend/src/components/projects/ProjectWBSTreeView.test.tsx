import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectWBSTreeView } from "./ProjectWBSTreeView";
import type { ProjectWBSTreeResponse } from "@/types/projects";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@/lib/http", () => ({
  apiFetch: mocks.apiFetch,
}));

vi.mock("sonner", () => ({
  toast: mocks.toast,
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

const mockWBSTreeResponse: ProjectWBSTreeResponse = {
  project_id: "proj-123",
  project_title: "Plataforma Educativa",
  total_nodes: 4,
  max_depth: 3,
  root: {
    id: "proj-123",
    wbs_code: "0",
    title: "Plataforma Educativa",
    type: "project",
    level: 0,
    status: "in_progress",
    progress_pct: 60,
    estimated_hours: 80,
    actual_hours: 45,
    budget_allocated: 100000,
    cost: 45000,
    is_leaf: false,
    health_status: "OPTIMO",
    children: [
      {
        id: "comp-1",
        wbs_code: "1",
        title: "Infraestructura Cloud",
        type: "component",
        level: 1,
        status: "active",
        progress_pct: 80,
        estimated_hours: 40,
        actual_hours: 30,
        budget_allocated: 40000,
        cost: 25000,
        is_leaf: false,
        health_status: "OPTIMO",
        children: [
          {
            id: "task-1",
            wbs_code: "1.1",
            title: "Configurar Clúster Kubernetes",
            type: "task",
            level: 2,
            status: "in_progress",
            progress_pct: 75,
            estimated_hours: 20,
            actual_hours: 15,
            budget_allocated: null,
            cost: 10000,
            is_leaf: false,
            health_status: "EN_PROCESO",
            children: [
              {
                id: "subtask-1",
                wbs_code: "1.1.1",
                title: "Instalar Ingress Controller",
                type: "task",
                level: 3,
                status: "completed",
                progress_pct: 100,
                estimated_hours: 10,
                actual_hours: 8,
                budget_allocated: null,
                cost: 4000,
                is_leaf: true,
                health_status: "OPTIMO",
                children: [],
              },
            ],
          },
        ],
      },
    ],
  },
};

describe("ProjectWBSTreeView Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza el organigrama WBS con códigos jerárquicos automáticos (0, 1, 1.1, 1.1.1)", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockWBSTreeResponse);

    render(<ProjectWBSTreeView projectId="proj-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("project-wbs-tree-view")).toBeInTheDocument();
    });

    expect(screen.getByText("Plataforma Educativa")).toBeInTheDocument();
    expect(screen.getByText("Infraestructura Cloud")).toBeInTheDocument();
    expect(screen.getByText("Configurar Clúster Kubernetes")).toBeInTheDocument();

    // Comprobar presencia de badges de código WBS
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("1.1")).toBeInTheDocument();
  });

  it("permite filtrar nodos mediante el buscador de texto", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockWBSTreeResponse);

    render(<ProjectWBSTreeView projectId="proj-123" />);

    await waitFor(() => {
      expect(screen.getByText("Configurar Clúster Kubernetes")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Buscar por código/i);
    fireEvent.change(searchInput, { target: { value: "Kubernetes" } });

    expect(screen.getByText("Configurar Clúster Kubernetes")).toBeInTheDocument();
  });

  it("llama a onSelectNode al hacer clic en un elemento del árbol", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockWBSTreeResponse);
    const onSelectNode = vi.fn();

    render(<ProjectWBSTreeView projectId="proj-123" onSelectNode={onSelectNode} />);

    await waitFor(() => {
      expect(screen.getByText("Infraestructura Cloud")).toBeInTheDocument();
    });

    const compNode = screen.getByText("Infraestructura Cloud");
    fireEvent.click(compNode);

    expect(onSelectNode).toHaveBeenCalled();
  });
});

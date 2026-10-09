import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TaskDimensionsSection from "./TaskDimensionsSection";
import type { ProjectTaskRecord, TaskDimensionsDetail } from "@/types/projects";

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

const mockTask: ProjectTaskRecord = {
  id: "task-101",
  project_id: "proj-123",
  title: "Desarrollo del Backend",
  status: "in_progress",
  priority: "high",
  estimated_hours: 20,
  physical_progress_pct: 40,
  subtasks: [],
};

const mockDimensionsResponse: TaskDimensionsDetail = {
  task_id: "task-101",
  project_id: "proj-123",
  title: "Desarrollo del Backend",
  status: "in_progress",
  priority: "high",
  time: {
    estimated_hours: 20,
    actual_hours: 12,
    start_date: "2026-10-01T00:00:00Z",
    due_date: "2026-10-15T00:00:00Z",
    duration_days: 15,
    subtasks_estimated_hours: 0,
    total_estimated_hours: 20,
  },
  progress: {
    physical_progress_pct: 40,
    rolled_up_progress_pct: 40,
    is_leaf: true,
    subtasks_count: 0,
    completed_subtasks_count: 0,
    weight_basis: "estimated_hours",
  },
  cost: {
    direct_cost: 450,
    subtasks_cost: 0,
    total_cost: 450,
    actual_cost: 350,
    planned_cost: 100,
    committed_cost: 0,
    expenses_count: 2,
  },
  expenses: [
    {
      id: "exp-1",
      project_id: "proj-123",
      task_id: "task-101",
      category: "servicios",
      description: "Servidor Redis",
      amount: 350,
      date: "2026-10-05T00:00:00Z",
      status: "paid",
      created_at: "2026-10-05T00:00:00Z",
    },
    {
      id: "exp-2",
      project_id: "proj-123",
      task_id: "task-101",
      category: "software",
      description: "API Gateway",
      amount: 100,
      date: "2026-10-06T00:00:00Z",
      status: "planned",
      created_at: "2026-10-06T00:00:00Z",
    },
  ],
};

describe("TaskDimensionsSection Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apiFetch.mockResolvedValue(mockDimensionsResponse);
  });

  it("renderiza correctamente las 3 dimensiones de control PMI", async () => {
    render(<TaskDimensionsSection task={mockTask} token="fake-token" />);

    expect(screen.getByText("3 Dimensiones PMI (Control WBS)")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("1. Tiempo y Esfuerzo")).toBeInTheDocument();
      expect(screen.getByText("2. Avance Físico Continuo")).toBeInTheDocument();
      expect(screen.getByText("3. Costos e Imputación Financiera")).toBeInTheDocument();
    });

    // Horas reales registradas
    expect(screen.getByText("12 h")).toBeInTheDocument();

    // Avance físico asignado
    expect(screen.getByText("40%")).toBeInTheDocument();

    // Costos acumulados
    expect(screen.getByText("$450,00")).toBeInTheDocument();
    expect(screen.getByText("$350,00")).toBeInTheDocument(); // Costo real (AC)
    expect(screen.getByText("Servidor Redis")).toBeInTheDocument();
  });

  it("permite actualizar el avance físico mediante los presets rápidos", async () => {
    const onUpdateMock = vi.fn();
    mocks.apiFetch
      .mockResolvedValueOnce(mockDimensionsResponse)
      .mockResolvedValueOnce({
        ...mockTask,
        physical_progress_pct: 75,
      });

    render(
      <TaskDimensionsSection
        task={mockTask}
        token="fake-token"
        onUpdate={onUpdateMock}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("75%")).toBeInTheDocument();
    });

    const preset75 = screen.getByText("75%");
    fireEvent.click(preset75);

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        "/projects/proj-123/tasks/task-101",
        expect.objectContaining({
          method: "PATCH",
          body: { physical_progress_pct: 75 },
        })
      );
      expect(mocks.toast.success).toHaveBeenCalledWith("Avance físico: 75%");
      expect(onUpdateMock).toHaveBeenCalled();
    });
  });

  it("permite actualizar las horas estimadas", async () => {
    const onUpdateMock = vi.fn();
    mocks.apiFetch
      .mockResolvedValueOnce(mockDimensionsResponse)
      .mockResolvedValueOnce({
        ...mockTask,
        estimated_hours: 30,
      });

    render(
      <TaskDimensionsSection
        task={mockTask}
        token="fake-token"
        onUpdate={onUpdateMock}
      />
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Horas Estimadas (Plan)")).toBeInTheDocument();
    });

    const input = screen.getByLabelText("Horas Estimadas (Plan)");
    fireEvent.change(input, { target: { value: "30" } });
    fireEvent.blur(input);

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        "/projects/proj-123/tasks/task-101",
        expect.objectContaining({
          method: "PATCH",
          body: { estimated_hours: 30 },
        })
      );
      expect(mocks.toast.success).toHaveBeenCalledWith("Horas estimadas actualizadas");
    });
  });
});

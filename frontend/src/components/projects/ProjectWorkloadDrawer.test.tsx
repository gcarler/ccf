import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkloadDrawer } from "./ProjectWorkloadDrawer";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({ isOpen, title, children }: { isOpen: boolean; title: string; children: ReactNode }) =>
    isOpen ? <section role="dialog" aria-label={title}>{children}</section> : null,
}));

const summary = {
  project_id: "project-1",
  total_members: 1,
  total_active_tasks: 1,
  total_completed_tasks: 0,
  total_overdue_tasks: 0,
  overloaded_members_count: 0,
  balanced_members_count: 1,
  available_members_count: 0,
  unassigned_tasks_count: 0,
  members: [
    {
      persona_id: "person-1",
      name: "Ana Pérez",
      total_tasks: 1,
      active_tasks: 1,
      completed_tasks: 0,
      overdue_tasks: 0,
      urgent_tasks: 0,
      high_tasks: 1,
      medium_tasks: 0,
      low_tasks: 0,
      capacity_status: "balanced" as const,
      workload_percent: 40,
      tasks: [
        {
          id: "task-1",
          title: "Preparar materiales",
          status: "in_progress",
          priority: "high",
          is_overdue: false,
        },
      ],
    },
  ],
};

describe("ProjectWorkloadDrawer", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
  });

  it("shows a recoverable error and retries without confusing it with an empty state", async () => {
    mocks.apiFetch
      .mockRejectedValueOnce(new Error("Temporary error"))
      .mockResolvedValueOnce(summary);

    const { container } = render(
      <ProjectWorkloadDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo cargar la distribución de carga del equipo.",
    );
    expect(screen.queryByText("No hay miembros ni tareas en este proyecto")).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Error al cargar la carga de trabajo del equipo", "error");
    expect((await axe(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: "Reintentar carga de trabajo" }));

    expect(await screen.findByText("Preparar materiales")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/workload",
      expect.objectContaining({ token: "test-token", signal: expect.any(AbortSignal) }),
    );
  });

  it("provides named keyboard controls and semantic progress indicators", async () => {
    mocks.apiFetch.mockResolvedValue(summary);
    const { container } = render(
      <ProjectWorkloadDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
        onOpenTask={vi.fn()}
      />,
    );

    expect(await screen.findByRole("progressbar", { name: "Carga de Ana Pérez" })).toHaveAttribute(
      "aria-valuenow",
      "40",
    );
    expect(screen.getByRole("button", { name: "Ocultar tareas de Ana Pérez" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("combobox", { name: "Reasignar Preparar materiales a otro colaborador" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver detalle de la tarea Preparar materiales" })).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it("can explicitly remove an assignment without colliding with the select placeholder", async () => {
    mocks.apiFetch.mockResolvedValue(summary);
    render(<ProjectWorkloadDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    const reassignment = await screen.findByRole("combobox", {
      name: "Reasignar Preparar materiales a otro colaborador",
    });
    fireEvent.change(reassignment, { target: { value: "__unassigned__" } });

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/tasks/task-1/reassign",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ new_assignee_id: null }),
      }),
    ));
  });

  it("shows the unassigned state as the current assignee instead of the placeholder", async () => {
    const unassignedSummary = {
      ...summary,
      unassigned_tasks_count: 1,
      members: [{ ...summary.members[0], persona_id: null, name: "Sin Asignar" }],
    };
    mocks.apiFetch.mockResolvedValue(unassignedSummary);

    render(<ProjectWorkloadDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    const reassignment = await screen.findByRole("combobox", {
      name: "Reasignar Preparar materiales a otro colaborador",
    });
    expect(reassignment).toHaveValue("__unassigned__");
    expect(reassignment).toHaveDisplayValue("Sin Asignar");
  });

  it("renders a true empty state when the project has no workload members", async () => {
    mocks.apiFetch.mockResolvedValue({ ...summary, total_members: 0, members: [] });

    render(<ProjectWorkloadDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(await screen.findByText("No hay miembros ni tareas en este proyecto")).toBeInTheDocument();
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledTimes(1));
  });
});

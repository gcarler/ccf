/**
 * S6 (rev_ui_13102026.md §5) — Optimistic UI con rollback en Kanban.
 *
 * `updateTask` es el SOT de mutación de tareas que usa el Kanban
 * (ProjectKanbanBoard → useProjectUpdate → useProjectPageData.updateTask).
 * Este test blinda la semántica comprometida por el plan pro:
 *
 * 1. El cambio de estado se aplica OPTIMISTAMENTE al state local SIN
 *    esperar la red (la tarjeta ya aparece en la columna destino).
 * 2. Si el PATCH falla, el hook hace toast.error y recarga del servidor,
 *    que revierte el estado optimista (rollback observable).
 * 3. Si el PATCH es exitoso, la recarga del servidor confirma el estado
 *    final (last-write-wins del servidor).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup, waitFor } from "@testing-library/react";
import React from "react";
import type { ProjectTaskRecord } from "@/types/projects";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { id: "u1" }, loading: false, hasPermission: () => true }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { useProjectPageData } from "@/hooks/useProjectPageData";

const TASK_ID = "task-1";
const SERVER_STATUS = "todo";

function serverTask(status: string): ProjectTaskRecord {
  return {
    id: TASK_ID,
    project_id: "proj-1",
    title: "Tarea kanban",
    status,
    priority: "medium",
  };
}

let pendingPatchResolve: (() => void) | null = null;
const taskOnServer = vi.fn(() => SERVER_STATUS);

/** Enruta apiFetch por endpoint como haría el backend real. */
function routeApiFetch(opts: { patchFails?: boolean; holdPatch?: boolean }) {
  vi.mocked(apiFetch).mockImplementation(
    (url: string, init?: { method?: string }) => {
      if (url === "/projects/proj-1") {
        return Promise.resolve({ id: "proj-1", title: "Proyecto S6" });
      }
      if (url === "/projects/proj-1/tasks") {
        return Promise.resolve([serverTask(taskOnServer())]);
      }
      if (url.startsWith("/projects/activities")) {
        return Promise.resolve([]);
      }
      if (url === "/projects/proj-1/phases") {
        return Promise.resolve([]);
      }
      if (url === "/projects/tasks/task-1" && init?.method === "PATCH") {
        if (opts.patchFails) return Promise.reject(new Error("network down"));
        if (opts.holdPatch) {
          return new Promise<void>((resolve) => {
            pendingPatchResolve = () => resolve();
          });
        }
        return Promise.resolve(serverTask("in_progress"));
      }
      return Promise.resolve([]);
    }
  );
}

function TaskStatusProbe() {
  const pageData = useProjectPageData("proj-1");
  const task = pageData.tasks.find((t) => t.id === TASK_ID);
  return (
    <div>
      <span data-testid="task-status">{task?.status ?? ""}</span>
      <span data-testid="tasks-loaded">{String(pageData.tasks.length > 0)}</span>
      <button
        type="button"
        data-testid="move-btn"
        onClick={() => {
          void pageData.updateTask(TASK_ID, { status: "in_progress" });
        }}
      >
        mover
      </button>
    </div>
  );
}

/** Monta el harness y espera la carga inicial (tasks presentes). */
async function mountHarness(opts: { patchFails?: boolean; holdPatch?: boolean } = {}) {
  pendingPatchResolve = null;
  routeApiFetch(opts);
  render(<TaskStatusProbe />);
  await screen.findByTestId("tasks-loaded");
  await waitFor(() => expect(screen.getByTestId("tasks-loaded")).toHaveTextContent("true"));
  expect(screen.getByTestId("task-status")).toHaveTextContent(SERVER_STATUS);
}

describe("useProjectPageData.updateTask — semántica optimista Kanban (S6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    taskOnServer.mockReturnValue(SERVER_STATUS);
  });
  afterEach(() => {
    cleanup();
  });

  it("aplica el cambio OPTIMISTAMENTE sin esperar el PATCH (UI inmediata)", async () => {
    await mountHarness({ holdPatch: true });

    act(() => {
      screen.getByTestId("move-btn").click();
    });

    // El estado local ya es 'in_progress' aunque el PATCH sigue pendiente.
    expect(screen.getByTestId("task-status")).toHaveTextContent("in_progress");

    // El servidor confirma 'todo': la recarga post-PATCH lo repone.
    await act(async () => {
      pendingPatchResolve?.();
    });
    await waitFor(() => expect(screen.getByTestId("task-status")).toHaveTextContent(SERVER_STATUS));
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("hace rollback con toast.error cuando el PATCH falla", async () => {
    await mountHarness({ patchFails: true });

    act(() => {
      screen.getByTestId("move-btn").click();
    });

    // Optimista: primero se movió...
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
        "/projects/tasks/task-1",
        expect.objectContaining({ method: "PATCH" })
      )
    );

    // ...y al fallar, la recarga del servidor revierte el estado optimista.
    await waitFor(() => expect(screen.getByTestId("task-status")).toHaveTextContent(SERVER_STATUS));
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("Error al actualizar tarea");
  });
});

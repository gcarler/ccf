import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectTimeTrackingDrawer } from "./ProjectTimeTrackingDrawer";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({ isOpen, title, children }: { isOpen: boolean; title: string; children: ReactNode }) =>
    isOpen ? <section aria-label={title}>{children}</section> : null,
}));

const log = {
  id: "log-1",
  project_id: "project-1",
  persona_id: "person-1",
  persona_name: "Ana Pérez",
  hours: 1.5,
  date: "2026-10-04T12:00:00Z",
  description: "Preparación de materiales",
  is_billable: true,
  created_at: "2026-10-04T12:00:00Z",
  updated_at: "2026-10-04T12:00:00Z",
};

const summary = {
  project_id: "project-1",
  total_hours: 1.5,
  billable_hours: 1.5,
  non_billable_hours: 0,
  total_logs: 1,
  by_task: [],
  by_member: [],
};

describe("ProjectTimeTrackingDrawer delete confirmation", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
    mocks.apiFetch.mockImplementation((path: string) =>
      path.endsWith("/time-tracking-summary") ? Promise.resolve(summary) : Promise.resolve([log]),
    );
  });

  it("requires drawer confirmation and lets the user cancel before deleting", async () => {
    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar registro de 1.50 horas: Preparación de materiales" }));

    expect(await screen.findByRole("complementary", { name: "Eliminar registro de tiempo" })).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Eliminar registro de tiempo" })).not.toBeInTheDocument());
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);
    expect(screen.getByText("Preparación de materiales")).toBeInTheDocument();
  });

  it("executes the soft-delete only after confirmation", async () => {
    let deleted = false;
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/time-tracking-summary")) return Promise.resolve(summary);
      if (options?.method === "DELETE") {
        deleted = true;
        return Promise.resolve({ ok: true });
      }
      return Promise.resolve(deleted ? [] : [log]);
    });

    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar registro de 1.50 horas: Preparación de materiales" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/time-logs/log-1",
      expect.objectContaining({ method: "DELETE" }),
    ));
    expect(mocks.addToast).toHaveBeenCalledWith("Registro de tiempo eliminado", "info");
  });

  it("keeps the confirmation and time log when deletion fails", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/time-tracking-summary")) return Promise.resolve(summary);
      if (options?.method === "DELETE") return Promise.reject(new Error("Servicio no disponible"));
      return Promise.resolve([log]);
    });

    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar registro de 1.50 horas: Preparación de materiales" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    expect(await screen.findByRole("complementary", { name: "Eliminar registro de tiempo" })).toBeInTheDocument();
    expect(screen.getByText("Preparación de materiales")).toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Error al eliminar el registro", "error");
  });

  it("displays EDT synchronization notice and task hours breakdown in summary view", async () => {
    mocks.apiFetch.mockImplementation((path: string) =>
      path.endsWith("/time-tracking-summary")
        ? Promise.resolve({
            ...summary,
            by_task: [
              {
                task_id: "task-1",
                task_title: "Montaje de sonido",
                total_hours: 6.5,
                logs_count: 3,
              },
            ],
          })
        : Promise.resolve([log]),
    );

    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(
      await screen.findByText(/Sincronización automática con horas reales \(actual_hours\) y avance físico EDT/i),
    ).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    expect(await screen.findByText(/Sincronización por Tarea \(actual_hours vs Estimado y Avance Físico\)/i)).toBeInTheDocument();
    expect(screen.getByText("Montaje de sonido")).toBeInTheDocument();
    expect(screen.getByText("6.50h")).toBeInTheDocument();
  });

  it("calculates earned effort, LEI and typical and atypical EAC forecasts with task variances", async () => {
    const effortSummary = {
      ...summary,
      total_hours: 16,
      estimated_hours_total: 30,
      physical_progress_pct: 50,
    };
    mocks.apiFetch.mockImplementation((path: string) =>
      path.endsWith("/time-tracking-summary") ? Promise.resolve(effortSummary) : Promise.resolve([log]),
    );

    render(
      <ProjectTimeTrackingDrawer
        projectId="project-1"
        isOpen
        onClose={vi.fn()}
        tasks={[
          { id: "task-1", title: "Diseño", estimated_hours: 20, actual_hours: 16, physical_progress_pct: 50 },
          { id: "task-2", title: "Instalación", estimated_hours: 10, actual_hours: 8, physical_progress_pct: 50 },
        ]}
      />,
    );

    expect(await screen.findByRole("heading", {
      name: "Diagnóstico PMI de Esfuerzo Devengado (Earned Effort & Burn Rate — Vol. 4 & 5)",
    })).toBeInTheDocument();
    const diagnosis = screen.getByRole("region", {
      name: "Diagnóstico PMI de Esfuerzo Devengado (Earned Effort & Burn Rate — Vol. 4 & 5)",
    });
    expect(within(diagnosis).getByText("30.00h")).toBeInTheDocument();
    expect(within(diagnosis).getByText("15.00h")).toBeInTheDocument();
    expect(within(diagnosis).getByText("16.00h")).toBeInTheDocument();
    expect(within(diagnosis).getByText("0.94")).toBeInTheDocument();
    expect(within(diagnosis).getByText("-1.00h")).toBeInTheDocument();
    expect(within(diagnosis).getByText("32.00h")).toBeInTheDocument();
    expect(within(diagnosis).getByText("31.00h")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Alerta de sobrecosto de esfuerzo / baja productividad horaria");
    expect(within(diagnosis).getByText("Diseño")).toBeInTheDocument();
    expect(within(diagnosis).getByText(/Desvío -4.00h/)).toBeInTheDocument();
    expect(within(diagnosis).getByText("Instalación")).toBeInTheDocument();
  });
});

describe("ProjectTimeTrackingDrawer — actualizaciones optimistas (H-PROJ-UI-04)", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
  });

  it("pinta el registro creado de inmediato sin refetch completo tras el POST", async () => {
    const created = {
      ...log,
      id: "log-2",
      hours: 2,
      description: "Trabajo dedicado",
      date: "2026-10-27T10:00:00Z",
    };
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === "POST") return Promise.resolve(created);
      if (path.endsWith("/time-tracking-summary")) return Promise.resolve(summary);
      return Promise.resolve([log]);
    });
    const countLogGets = () =>
      mocks.apiFetch.mock.calls.filter(([path, opts]) =>
        String(path).endsWith("/time-logs")
        && !((opts as { method?: string } | undefined)?.method)
      ).length;

    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    await screen.findByText("Preparación de materiales");
    const getCallsBefore = countLogGets();

    fireEvent.click(screen.getByRole("button", { name: "Entrada Manual" }));
    fireEvent.submit(
      screen.getByRole("button", { name: "Guardar Entrada de Tiempo" }).closest("form")!
    );

    // Optimismo: la fila aparece sin refetch posterior del listado.
    await waitFor(() => expect(screen.getByText("Trabajo dedicado")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Historial (2)" })).toBeInTheDocument();
    expect(countLogGets()).toBe(getCallsBefore);
    expect(mocks.addToast).toHaveBeenCalledWith("Registro de tiempo creado con éxito", "success");
  });

  it("restaura el registro en la lista cuando el DELETE falla (rollback)", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/time-tracking-summary")) return Promise.resolve(summary);
      if (options?.method === "DELETE") return Promise.reject(new Error("Servicio no disponible"));
      return Promise.resolve([log]);
    });

    render(<ProjectTimeTrackingDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Historial (1)" }));
    await screen.findByText("Preparación de materiales");
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar registro de 1.50 horas: Preparación de materiales" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith("Error al eliminar el registro", "error"));
    expect(screen.getByText("Preparación de materiales")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Historial (1)" })).toBeInTheDocument();
  });
});

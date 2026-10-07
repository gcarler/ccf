import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
});

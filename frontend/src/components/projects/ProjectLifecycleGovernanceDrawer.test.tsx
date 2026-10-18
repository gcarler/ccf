import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectLifecycleGovernanceDrawer } from "@/components/projects/ProjectLifecycleGovernanceDrawer";

const apiFetch = vi.fn();

vi.mock("@/lib/http", () => ({ apiFetch: (...args: unknown[]) => apiFetch(...args) }));
vi.mock("@/components/ui/RightPanel", () => ({
  default: ({ children, open, title }: { children: ReactNode; open: boolean; title: string }) => open ? <div role="dialog" aria-label={title}>{children}</div> : null,
}));

const stakeholder = {
  id: "stakeholder-1",
  project_id: "project-1",
  persona_id: null,
  display_name: "Comité de obra",
  role_title: "Comité",
  organization_or_ministry: "Infraestructura",
  power_level: 5,
  interest_level: 4,
  quadrant: "manage_closely",
  engagement_level: "supportive",
  management_strategy: "Reunión semanal",
};

describe("ProjectLifecycleGovernanceDrawer", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    apiFetch.mockImplementation((path: string, options?: RequestInit) => {
      if (path.endsWith("/charter") && options?.method === "PUT") {
        return Promise.resolve({ ...JSON.parse(String(options.body)), authorized_by: "persona-1", authorized_at: "2026-10-18T00:00:00Z" });
      }
      if (path.endsWith("/charter")) return Promise.resolve({});
      if (path.endsWith("/stakeholders") && options?.method === "POST") return Promise.resolve(stakeholder);
      if (path.endsWith("/stakeholders")) return Promise.resolve([]);
      if (path.endsWith("/closure/finalize")) return Promise.resolve({ ...JSON.parse(String(options?.body)), closure_status: "closed", closed_by: "persona-1", closed_at: "2026-10-18T00:00:00Z" });
      if (path.endsWith("/closure")) return Promise.resolve({});
      return Promise.resolve({});
    });
  });

  it("loads project governance and formally authorizes the charter", async () => {
    render(<ProjectLifecycleGovernanceDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Acta de Constitución")).toBeInTheDocument();
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/charter"));
    fireEvent.change(screen.getByLabelText("Enfoque de desarrollo"), { target: { value: "agile" } });
    fireEvent.change(screen.getByLabelText("Tipología PMO"), { target: { value: "supportive" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/charter", expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining('"development_approach":"agile"'),
    })));
    fireEvent.click(screen.getByRole("button", { name: "Autorizar formalmente" }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/charter", expect.objectContaining({ method: "PUT" })));
    expect(await screen.findByText(/Autorizada/)).toBeInTheDocument();
  });

  it("adds an interested party and displays the calculated power-interest quadrant", async () => {
    render(<ProjectLifecycleGovernanceDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Matriz de Interesados" }));
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Comité de obra" } });
    fireEvent.click(screen.getByRole("button", { name: /Agregar$/ }));
    expect(await screen.findByText("Comité de obra")).toBeInTheDocument();
    const listItem = screen.getByText("Comité de obra").closest("li");
    expect(listItem).not.toBeNull();
    expect(within(listItem as HTMLElement).getByText("manage closely")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/stakeholders", expect.objectContaining({ method: "POST" }));
  });

  it("finalizes closure after both acceptance and reconciliation are checked", async () => {
    render(<ProjectLifecycleGovernanceDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("tab", { name: "Cierre y Lecciones" }));
    fireEvent.click(screen.getByLabelText("Entregables aceptados y verificados"));
    fireEvent.click(screen.getByLabelText("Conciliación financiera completada"));
    fireEvent.click(screen.getByRole("button", { name: "Finalizar cierre formal" }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/closure/finalize", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText(/Proyecto cerrado/)).toBeInTheDocument();
  });
});

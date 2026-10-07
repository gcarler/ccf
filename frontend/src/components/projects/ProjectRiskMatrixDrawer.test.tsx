import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectRiskMatrixDrawer } from "./ProjectRiskMatrixDrawer";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({ isOpen, title, children }: { isOpen: boolean; title: string; children: ReactNode }) =>
    isOpen ? <section aria-label={title}>{children}</section> : null,
}));
vi.mock("@/components/ui/PersonaSelect", () => ({
  default: ({ value, onChange }: { value: string | null; onChange: (value: string | null) => void }) => (
    <select
      aria-label="Responsable del riesgo"
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value || null)}
    >
      <option value="">Sin asignar</option>
      <option value="persona-1">Ana de la sede</option>
    </select>
  ),
}));

const risk = {
  id: "risk-1",
  project_id: "project-1",
  title: "Riesgo de prueba",
  category: "tecnico",
  probability: 3,
  impact: 3,
  severity_score: 9,
  severity_level: "medium",
  owner_id: "persona-1",
  owner_name: "Ana de la sede",
  status: "active",
  created_at: "2026-10-04T12:00:00Z",
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("ProjectRiskMatrixDrawer owner flow", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      return Promise.resolve([]);
    });
  });

  it("uses declared semantic text tokens for summary content", async () => {
    render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    await screen.findByText("Total Registrados");
    const totalCount = screen.getByText("Total Registrados").parentElement?.parentElement?.querySelector(".text-2xl");
    expect(totalCount).toHaveStyle({ color: "hsl(var(--text-primary))" });
    expect(screen.getByText("Total Registrados").parentElement?.className).toContain("text-[hsl(var(--text-primary))]");
    expect(document.querySelector(".text-muted")).not.toBeInTheDocument();
    expect(document.querySelector('[aria-label="Matriz RAID de Riesgos y Supuestos"]')?.innerHTML).not.toMatch(
      /--(?:text-main|foreground|muted-foreground|destructive-foreground)/,
    );
  });

  it("submits the selected risk owner on create", async () => {
    const { container } = render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Registrar Riesgo" }));
    expect((await axe(container)).violations).toEqual([]);
    fireEvent.change(screen.getByPlaceholderText(/ej\. Fallo en el servidor/), {
      target: { value: "Riesgo con responsable" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Responsable del riesgo" }), {
      target: { value: "persona-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar Riesgo" }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/risks",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"owner_id":"persona-1"'),
      }),
    ));
  });

  it("allows clearing the owner when editing a risk", async () => {
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      return Promise.resolve([risk]);
    });
    render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    fireEvent.click(await screen.findByTitle("Editar riesgo"));
    fireEvent.change(screen.getByRole("combobox", { name: "Responsable del riesgo" }), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Actualizar Riesgo" }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/risks/risk-1",
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"owner_id":null'),
      }),
    ));
  });

  it("clears the previous project's risks while the next project loads", async () => {
    const nextRisks = deferred<typeof risk[]>();
    const nextSummary = deferred<{ matrix_5x5: never[] }>();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.includes("/project-1/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      if (path.includes("/project-1/risks")) return Promise.resolve([risk]);
      if (path.includes("/project-2/risks-summary")) return nextSummary.promise;
      return nextRisks.promise;
    });
    const view = render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Riesgo de prueba")).toBeInTheDocument();

    view.rerender(<ProjectRiskMatrixDrawer projectId="project-2" isOpen onClose={vi.fn()} />);

    expect(screen.queryByText("Riesgo de prueba")).not.toBeInTheDocument();
    nextRisks.resolve([{ ...risk, id: "risk-2", title: "Riesgo proyecto dos" }]);
    nextSummary.resolve({ matrix_5x5: [] });
    expect(await screen.findByText("Riesgo proyecto dos")).toBeInTheDocument();
  });

  it("ignores a late response from the previous project", async () => {
    const oldRisks = deferred<typeof risk[]>();
    const oldSummary = deferred<{ matrix_5x5: never[] }>();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.includes("/project-1/risks-summary")) return oldSummary.promise;
      if (path.includes("/project-1/risks")) return oldRisks.promise;
      if (path.includes("/project-2/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      return Promise.resolve([{ ...risk, id: "risk-2", title: "Riesgo proyecto dos" }]);
    });
    const view = render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    view.rerender(<ProjectRiskMatrixDrawer projectId="project-2" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Riesgo proyecto dos")).toBeInTheDocument();
    oldRisks.resolve([risk]);
    oldSummary.resolve({ matrix_5x5: [] });

    await waitFor(() => expect(screen.getByText("Riesgo proyecto dos")).toBeInTheDocument());
    expect(screen.queryByText("Riesgo de prueba")).not.toBeInTheDocument();
  });

  it("keeps a failed lookup separate from an empty matrix and retries successfully", async () => {
    let attempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      attempts += 1;
      return attempts === 1 ? Promise.reject(new Error("offline")) : Promise.resolve([]);
    });
    render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo cargar la matriz de riesgos.");
    expect(screen.queryByText("No hay riesgos registrados con estos filtros")).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Error al cargar la matriz de riesgos", "error");

    fireEvent.click(screen.getByRole("button", { name: "Reintentar carga" }));

    expect(await screen.findByText("No hay riesgos registrados con estos filtros")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("requires explicit confirmation before deleting a risk", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      if (options?.method === "DELETE") return Promise.resolve({ ok: true });
      return Promise.resolve([risk]);
    });
    render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Eliminar riesgo Riesgo de prueba" }));
    expect(await screen.findByRole("complementary", { name: "Eliminar riesgo" })).toHaveTextContent("Riesgo de prueba");
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Eliminar riesgo" })).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Eliminar riesgo Riesgo de prueba" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar riesgo" }));
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/risks/risk-1",
      expect.objectContaining({ method: "DELETE", token: "test-token" }),
    ));
  });

  it("keeps the risk and confirmation drawer available after a failed deletion", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/risks-summary")) return Promise.resolve({ matrix_5x5: [] });
      if (options?.method === "DELETE") return Promise.reject(new Error("offline"));
      return Promise.resolve([risk]);
    });
    render(<ProjectRiskMatrixDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Eliminar riesgo Riesgo de prueba" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar riesgo" }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith("Error al eliminar el riesgo", "error"));
    expect(screen.getByText("Riesgo de prueba")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Eliminar riesgo" })).toBeInTheDocument();
  });
});

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectBudgetDrawer } from "./ProjectBudgetDrawer";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({ isOpen, title, children }: { isOpen: boolean; title: string; children: ReactNode }) =>
    isOpen ? <section aria-label={title}>{children}</section> : null,
}));

const expense = {
  id: "expense-1",
  project_id: "project-1",
  category: "materials",
  description: "Factura de pintura",
  amount: 24.5,
  date: "2026-10-04T12:00:00Z",
  receipt_url: "https://example.org/receipt/24",
  status: "planned" as const,
  created_at: "2026-10-04T12:00:00Z",
};

const summary = {
  project_id: "project-1",
  budget_allocated: 1000,
  budget_spent: 0,
  remaining_budget: 1000,
  burn_rate_percent: 0,
  total_expenses_count: 1,
  planned_amount: 24.5,
  committed_amount: 0,
  paid_amount: 0,
  by_category: { materials: 24.5 },
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("ProjectBudgetDrawer", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.addToast.mockClear();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/budget-summary")) return Promise.resolve(summary);
      return Promise.resolve([expense]);
    });
  });

  it("sends null when a user removes an expense receipt", async () => {
    const { container } = render(
      <ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );
    expect(await screen.findByText("Factura de pintura")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Editar gasto: Factura de pintura" }));
    fireEvent.change(screen.getByDisplayValue("https://example.org/receipt/24"), {
      target: { value: "" },
    });

    expect((await axe(container)).violations).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/expenses/expense-1",
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"receipt_url":null'),
      }),
    ));
    expect(mocks.addToast).toHaveBeenCalledWith("Partida de gasto actualizada", "success");
  });

  it("uses a declared semantic text token for expense descriptions", async () => {
    render(<ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(await screen.findByText("Factura de pintura")).toHaveStyle({
      color: "hsl(var(--text-secondary))",
    });
  });

  it("keeps a failed load distinct from the empty state and retries", async () => {
    let expenseAttempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/budget-summary")) return Promise.resolve(summary);
      expenseAttempts += 1;
      return expenseAttempts === 1
        ? Promise.reject(new Error("Servicio temporalmente no disponible"))
        : Promise.resolve([expense]);
    });

    const { container } = render(
      <ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo cargar la información presupuestaria.",
    );
    expect(screen.queryByText("No se encontraron partidas de gasto registradas.")).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Error al cargar la información presupuestaria", "error");
    expect((await axe(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: "Reintentar carga presupuestaria" }));

    expect(await screen.findByText("Factura de pintura")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not show a late response from the previous project", async () => {
    const previousExpenses = deferred<typeof expense[]>();
    const previousSummary = deferred<typeof summary>();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.includes("project-1") && path.endsWith("/budget-summary")) return previousSummary.promise;
      if (path.includes("project-1")) return previousExpenses.promise;
      if (path.endsWith("/budget-summary")) return Promise.resolve({ ...summary, project_id: "project-2" });
      return Promise.resolve([{ ...expense, id: "expense-2", project_id: "project-2", description: "Gasto del proyecto dos" }]);
    });

    const view = render(
      <ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/expenses",
      expect.anything(),
    ));

    view.rerender(<ProjectBudgetDrawer projectId="project-2" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Gasto del proyecto dos")).toBeInTheDocument();

    await act(async () => {
      previousExpenses.resolve([expense]);
      previousSummary.resolve(summary);
      await Promise.resolve();
    });

    expect(screen.getByText("Gasto del proyecto dos")).toBeInTheDocument();
    expect(screen.queryByText("Factura de pintura")).not.toBeInTheDocument();
  });

  it("requires a drawer confirmation before deleting an expense", async () => {
    let deleted = false;
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/budget-summary")) return Promise.resolve(summary);
      if (options?.method === "DELETE") {
        deleted = true;
        return Promise.resolve({ ok: true });
      }
      return Promise.resolve(deleted ? [] : [expense]);
    });

    render(<ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Factura de pintura")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Eliminar gasto: Factura de pintura" }));
    expect(await screen.findByRole("complementary", { name: "Eliminar partida de gasto" })).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("complementary", { name: "Eliminar partida de gasto" })).not.toBeInTheDocument());
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar gasto: Factura de pintura" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/expenses/expense-1",
      expect.objectContaining({ method: "DELETE" }),
    ));
    expect(await screen.findByText("No se encontraron partidas de gasto registradas.")).toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Partida eliminada", "info");
  });

  it("keeps the confirmation open and the expense visible when delete fails", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/budget-summary")) return Promise.resolve(summary);
      if (options?.method === "DELETE") return Promise.reject(new Error("Servicio no disponible"));
      return Promise.resolve([expense]);
    });

    render(<ProjectBudgetDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText("Factura de pintura")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar gasto: Factura de pintura" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    expect(await screen.findByRole("complementary", { name: "Eliminar partida de gasto" })).toBeInTheDocument();
    expect(screen.getByText("Factura de pintura")).toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith("Error al eliminar la partida", "error");
  });
});

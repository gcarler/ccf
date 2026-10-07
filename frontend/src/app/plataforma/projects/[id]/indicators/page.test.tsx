import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { axe } from "jest-axe";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import type { ProjectIndicator } from "@/types/projects";
import ProjectIndicatorsPage from "./page";

const mocks = vi.hoisted(() => ({ projectId: "project-1", toastError: vi.fn() }));

vi.mock("next/navigation", () => ({ useParams: () => ({ id: mocks.projectId }) }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
vi.mock("@/components/projects/ProjectIndicatorsDrawer", () => ({ ProjectIndicatorsDrawer: () => null }));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError } }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function indicator(id: string, projectId: string, name: string): ProjectIndicator {
  return {
    id,
    project_id: projectId,
    name,
    level: "PRODUCTO_PRINCIPAL",
    calculation_type: "ABSOLUTO_ACUMULADO",
    baseline_value: 0,
    target_value: 10,
    current_value: 0,
    frequency: "mensual",
    period_targets: {},
    crema_evaluation: {},
    created_at: "2026-10-04T00:00:00Z",
    updated_at: "2026-10-04T00:00:00Z",
  };
}

describe("ProjectIndicatorsPage loading recovery", () => {
  beforeEach(() => {
    mocks.projectId = "project-1";
    vi.clearAllMocks();
  });

  it("keeps API failure distinct from a successful empty response and retries", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ title: "Proyecto de prueba" })
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ title: "Proyecto de prueba" })
      .mockResolvedValueOnce([]);

    const { container } = render(<ProjectIndicatorsPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar los indicadores");
    expect((await axe(container)).violations).toEqual([]);
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(screen.queryByText("Sin indicadores configurados")).not.toBeInTheDocument();
    expect(screen.queryByText("Total Indicadores")).not.toBeInTheDocument();
    expect(mocks.toastError).toHaveBeenCalledWith("Error al cargar indicadores MGA");

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Sin indicadores configurados")).toBeInTheDocument();
  });

  it("ignores responses from the previous project after switching routes", async () => {
    const projectATitle = deferred<{ title: string }>();
    const projectAIndicators = deferred<ProjectIndicator[]>();
    const projectBTitle = deferred<{ title: string }>();
    const projectBIndicators = deferred<ProjectIndicator[]>();
    const responses = new Map<string, Promise<unknown>>([
      ["/projects/project-a", projectATitle.promise],
      ["/projects/project-a/advanced-indicators", projectAIndicators.promise],
      ["/projects/project-b", projectBTitle.promise],
      ["/projects/project-b/advanced-indicators", projectBIndicators.promise],
    ]);
    vi.mocked(apiFetch).mockImplementation(async <T,>(path: string): Promise<T> => {
      return (await responses.get(path)) as T;
    });

    mocks.projectId = "project-a";
    const { rerender } = render(<ProjectIndicatorsPage />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2));

    mocks.projectId = "project-b";
    rerender(<ProjectIndicatorsPage />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(4));

    await act(async () => {
      projectBTitle.resolve({ title: "Proyecto B" });
      projectBIndicators.resolve([indicator("indicator-b", "project-b", "Indicador B")]);
    });
    expect(await screen.findByText("Indicador B")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyecto B" })).toBeInTheDocument();

    await act(async () => {
      projectATitle.resolve({ title: "Proyecto A" });
      projectAIndicators.resolve([indicator("indicator-a", "project-a", "Indicador A")]);
    });

    expect(screen.getByText("Indicador B")).toBeInTheDocument();
    expect(screen.queryByText("Indicador A")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Proyecto B" })).toBeInTheDocument();
  });
});

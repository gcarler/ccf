import React from "react";
import { render, screen, within } from "@testing-library/react";
import { axe } from "jest-axe";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { apiFetch } from "@/lib/http";
import { ProjectIndicatorsDrawer } from "./ProjectIndicatorsDrawer";

const mocks = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError, success: vi.fn() } }));

function renderDrawer() {
  return render(
    <SidebarLayerProvider>
      <ProjectIndicatorsDrawer projectId="project-1" isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectIndicatorsDrawer loading recovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not report an empty list after a failed request and can recover by retrying", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([]);

    const { container } = renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar los indicadores");
    expect((await axe(container)).violations).toEqual([]);
    expect(screen.queryByText("No hay indicadores en este nivel")).not.toBeInTheDocument();
    expect(screen.queryByText("Total Ind.")).not.toBeInTheDocument();
    expect(mocks.toastError).toHaveBeenCalledWith("Error al cargar indicadores MGA del proyecto");

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("No hay indicadores en este nivel")).toBeInTheDocument();
    expect(screen.getByText(/Cree indicadores de resultado/)).toHaveClass(
      "text-[hsl(var(--text-secondary))]",
    );
  });

  it("keeps indicator deletion confirmation open when the server rejects the request", async () => {
    const user = userEvent.setup();
    const indicator = {
      id: "indicator-1",
      project_id: "project-1",
      name: "Familias acompañadas",
      level: "producto",
      calculation_type: "manual",
      baseline_value: 0,
      target_value: 10,
      current_value: 2,
      frequency: "monthly",
      period_targets: {},
      crema_evaluation: {},
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(apiFetch)
      .mockResolvedValueOnce([indicator])
      .mockRejectedValueOnce(new Error("offline"));

    renderDrawer();

    await screen.findByText("Familias acompañadas");
    await user.click(screen.getByTitle("Eliminar indicador"));
    const deleteDialog = await screen.findByRole("dialog", { name: "Panel" });
    const confirmButton = within(deleteDialog).getByRole("button", { name: "Eliminar indicador" });
    expect(within(deleteDialog).getByText(/borrará también su historial de avance/)).toBeInTheDocument();

    await user.click(confirmButton);

    expect(within(deleteDialog).getByText(/borrará también su historial de avance/)).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/advanced-indicators/indicator-1",
      expect.objectContaining({ method: "DELETE", token: "test-token" }),
    );
    expect(mocks.toastError).toHaveBeenCalledWith("Error al eliminar indicador");
  });
});

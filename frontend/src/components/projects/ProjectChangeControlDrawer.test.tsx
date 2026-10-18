import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { ProjectChangeControlDrawer } from "./ProjectChangeControlDrawer";
import type { ChangeRequestListResponse } from "./ProjectChangeControlDrawer";

const mocks = vi.hoisted(() => ({ addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const pendingCr = {
  id: "cr-1",
  project_id: "project-1",
  title: "Ampliar reportería EDT 3",
  justification: "El patrocinador exige reportería adicional.",
  change_type: "scope",
  cost_impact_delta: 0,
  schedule_impact_days: 5,
  scope_impact_summary: "Nuevas salidas de primer nivel.",
  status: "pending_ccb",
  requested_by: "user-1",
  reviewed_by: null,
  review_notes: null,
  created_at: "2026-10-18T00:00:00Z",
  reviewed_at: null,
  resulting_baseline_id: null,
};

const approvedCr = {
  ...pendingCr,
  id: "cr-2",
  title: "Ampliación de presupuesto",
  justification: "Subida de costos de licencias.",
  change_type: "budget",
  cost_impact_delta: 1500,
  schedule_impact_days: 0,
  status: "approved",
  reviewed_by: "user-2",
  review_notes: "Justificación técnica validada por el Comité.",
  resulting_baseline_id: "baseline-9",
};

const emptyResponse: ChangeRequestListResponse = {
  project_id: "project-1",
  items: [],
  summary: {
    pending_ccb: 0,
    approved: 0,
    rejected: 0,
    approved_cost_impact_total: 0,
    approved_schedule_impact_days_total: 0,
    pending_cost_impact_total: 0,
    pending_schedule_impact_days_total: 0,
  },
};

function renderDrawer() {
  return render(
    <SidebarLayerProvider>
      <ProjectChangeControlDrawer projectId="project-1" isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectChangeControlDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra estado vacío con doctrina PMI cuando no hay solicitudes", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(emptyResponse);
    const { container } = renderDrawer();

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/projects/project-1/change-requests", expect.objectContaining({ token: "test-token" })));
    expect(
      await screen.findByText(/Sin solicitudes de cambio registradas/)
    ).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it("usa exclusivamente tokens semánticos en las tarjetas del Comité", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...emptyResponse,
      items: [pendingCr, approvedCr],
      summary: {
        pending_ccb: 1,
        approved: 1,
        rejected: 0,
        approved_cost_impact_total: 1500,
        approved_schedule_impact_days_total: 5,
        pending_cost_impact_total: 0,
        pending_schedule_impact_days_total: 5,
      },
    });
    renderDrawer();

    const list = await screen.findByTestId("cr-list");
    expect(list).toBeInTheDocument();
    expect(list.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(list.innerHTML).toContain("--text-primary");
    expect(list.innerHTML).toContain("--warning-text");
    expect(list.innerHTML).not.toMatch(/bg-(blue|gray|red|green|amber)-\d/);
  });

  it("crea una Solicitud de Cambio Formal con el contrato del backend", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce(emptyResponse).mockResolvedValueOnce(emptyResponse);
    renderDrawer();

    await user.click(await screen.findByRole("button", { name: /Nueva Solicitud de Cambio/ }));
    await user.type(screen.getByLabelText("Título de la solicitud *"), "Ampliar reportería EDT 3");
    await user.type(screen.getByLabelText("Justificación *"), "El patrocinador exige reportería adicional.");
    await user.selectOptions(screen.getByLabelText("Tipo de cambio"), "scope");
    await user.type(screen.getByLabelText("Impacto en cronograma (Δdías)"), "5");
    await user.type(screen.getByLabelText("Resumen de impacto en alcance (opcional)"), "Nuevas salidas.");
    expect((await axe(screen.getByTestId("new-cr-form"))).violations).toEqual([]);

    await user.click(screen.getByRole("button", { name: /Registrar solicitud pendiente del Comité/ }));

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([url, opts]) =>
            url === "/projects/project-1/change-requests" &&
            (opts as RequestInit | undefined)?.method === "POST" &&
            (opts as RequestInit | undefined)?.body ===
              JSON.stringify({
                title: "Ampliar reportería EDT 3",
                justification: "El patrocinador exige reportería adicional.",
                change_type: "scope",
                cost_impact_delta: 0,
                schedule_impact_days: 5,
                scope_impact_summary: "Nuevas salidas.",
              }),
        ),
      ).toBe(true),
    );
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Solicitud registrada", type: "success" }));
  });

  it("registra el dictamen con acta y notifica el Re-baseline automático", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ ...emptyResponse, items: [pendingCr] })
      .mockResolvedValueOnce({ ...emptyResponse, items: [approvedCr] });
    renderDrawer();

    await screen.findByTestId("cr-card-cr-1");
    await user.type(screen.getByLabelText(/Acta del dictamen/), "Justificación técnica validada.");
    await user.click(screen.getByRole("button", { name: /Aprobar con Re-baseline/ }));

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([url, opts]) =>
            url === "/projects/project-1/change-requests/cr-1/decide" &&
            (opts as RequestInit | undefined)?.method === "POST" &&
            (opts as RequestInit | undefined)?.body ===
              JSON.stringify({
                decision: "approved",
                review_notes: "Justificación técnica validada.",
              }),
        ),
      ).toBe(true),
    );
    expect(mocks.addToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Cambio aprobado", type: "success" }),
    );
  });

  it("exige el acta de justificación técnica antes del dictamen", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce({ ...emptyResponse, items: [pendingCr] });
    renderDrawer();

    await screen.findByTestId("cr-card-cr-1");
    await user.click(screen.getByRole("button", { name: /Aprobar con Re-baseline/ }));

    expect(mocks.addToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Acta requerida", type: "warning" }),
    );
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });

  it("mueve la propuesta aprobada a la lista con su Re-baseline vinculado", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...emptyResponse,
      items: [approvedCr],
      summary: {
        pending_ccb: 0,
        approved: 1,
        rejected: 0,
        approved_cost_impact_total: 1500,
        approved_schedule_impact_days_total: 0,
        pending_cost_impact_total: 0,
        pending_schedule_impact_days_total: 0,
      },
    });
    renderDrawer();

    expect(await screen.findByText(/Re-baseline automático generado/)).toBeInTheDocument();
    expect(screen.getByText(/Justificación técnica validada por el Comité/)).toBeInTheDocument();
  });
});

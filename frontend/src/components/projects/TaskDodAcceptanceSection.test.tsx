import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import TaskDodAcceptanceSection from "./TaskDodAcceptanceSection";
import type { ProjectTaskRecord } from "@/types/projects";

const mocks = vi.hoisted(() => ({ addToast: vi.fn() }));

vi.mock("@/context/ToastContext", async () => {
  const actual = await vi.importActual<typeof import("@/context/ToastContext")>("@/context/ToastContext");
  return { ...actual, useToast: () => ({ addToast: mocks.addToast }) };
});
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const task = {
  id: "task-1",
  project_id: "project-1",
  title: "Entregable Reportería",
} as unknown as ProjectTaskRecord;

const notRecorded = {
  task_id: "task-1",
  status: "not_recorded",
  specification_met: false,
  tests_no_critical_failures: false,
  evidence_archived: false,
  supervisor_sign_off: false,
  coq_classification: null,
  coq_amount: null,
  accepted_by: null,
  accepted_by_name: null,
  accepted_at: null,
};

function renderSection() {
  return render(
    <SidebarLayerProvider>
      <TaskDodAcceptanceSection task={task} token="test-token" />
    </SidebarLayerProvider>,
  );
}

describe("TaskDodAcceptanceSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("carga el estado inicial (not_recorded) desde dod-status", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(notRecorded);
    renderSection();

    expect(await screen.findByLabelText("Especificación técnica cumplida")).not.toBeChecked();
    expect(screen.getByLabelText("Pruebas sin fallos críticos")).not.toBeChecked();
    expect(screen.getByLabelText("Evidencia archivada")).not.toBeChecked();
    expect(screen.getByLabelText("Firma del supervisor (Acta de recepción)")).not.toBeChecked();
    expect(screen.getByRole("button", { name: /Guardar verificación/ })).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/tasks/task-1/dod-status",
      expect.objectContaining({ token: "test-token" }),
    );
  });

  it("guarda la verificación completa con el contrato del backend y notifica aceptación", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(notRecorded)
      .mockResolvedValueOnce({ status: "accepted" })
      .mockResolvedValueOnce({
        ...notRecorded,
        status: "accepted",
        specification_met: true,
        tests_no_critical_failures: true,
        evidence_archived: true,
        supervisor_sign_off: true,
        coq_classification: "prevention",
        coq_amount: 250,
        accepted_by: "persona-1",
        accepted_by_name: "Ana Torres",
      });

    renderSection();
    await screen.findByLabelText("Especificación técnica cumplida");

    await user.click(screen.getByLabelText("Especificación técnica cumplida"));
    await user.click(screen.getByLabelText("Pruebas sin fallos críticos"));
    await user.click(screen.getByLabelText("Evidencia archivada"));
    await user.click(screen.getByLabelText("Firma del supervisor (Acta de recepción)"));
    await user.type(screen.getByLabelText("Monto CoQ ($)"), "250");
    await user.click(screen.getByRole("button", { name: /Guardar verificación/ }));

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([url, opts]) =>
            url === "/projects/project-1/tasks/task-1/dod-acceptance" &&
            (opts as RequestInit | undefined)?.method === "POST" &&
            (opts as RequestInit | undefined)?.body ===
              JSON.stringify({
                specification_met: true,
                tests_no_critical_failures: true,
                evidence_archived: true,
                supervisor_sign_off: true,
                coq_classification: "prevention",
                coq_amount: 250,
              }),
        ),
      ).toBe(true),
    );
    expect(mocks.addToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Entregable aceptado", type: "success" }),
    );
  });

  it("muestra quién aceptó y cuándo cuando el entregable está aceptado", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      ...notRecorded,
      status: "accepted",
      specification_met: true,
      tests_no_critical_failures: true,
      evidence_archived: true,
      supervisor_sign_off: true,
      accepted_by: "persona-9",
      accepted_by_name: "Ana Torres",
      accepted_at: "2026-10-18T10:00:00Z",
    });
    renderSection();

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Entregable aceptado."),
    );
    expect(screen.getByRole("status")).toHaveTextContent("Aceptado por");
    expect(screen.getByRole("status")).toHaveTextContent("Ana Torres");
    expect(screen.getByRole("status")).toHaveTextContent("2026");
  });

  it("muestra un mensaje de error cuando no se puede cargar el estado DoD", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("network down"));
    renderSection();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo cargar el estado de aceptación del entregable.",
    );
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("guarda el DoD pendiente cuando falta la firma del supervisor", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(notRecorded)
      .mockResolvedValueOnce({ status: "pending" })
      .mockResolvedValueOnce({
        ...notRecorded,
        status: "pending",
        specification_met: true,
        tests_no_critical_failures: true,
        evidence_archived: true,
        supervisor_sign_off: false,
      });

    renderSection();
    await screen.findByLabelText("Especificación técnica cumplida");

    await user.type(screen.getByLabelText("Monto CoQ ($)"), "0");
    await user.click(screen.getByRole("button", { name: /Guardar verificación/ }));

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([url, opts]) =>
            url === "/projects/project-1/tasks/task-1/dod-acceptance" &&
            (opts as RequestInit | undefined)?.method === "POST" &&
            (opts as RequestInit | undefined)?.body ===
              JSON.stringify({
                specification_met: false,
                tests_no_critical_failures: false,
                evidence_archived: false,
                supervisor_sign_off: false,
                coq_classification: "prevention",
                coq_amount: 0,
              }),
        ),
      ).toBe(true),
    );
    expect(mocks.addToast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Verificación guardada", type: "info" }),
    );
  });
});

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { ProjectAutomationsDrawer } from "./ProjectAutomationsDrawer";
import type { AutomationExecutionResult, ProjectAutomationRule, ProjectTaskRecord } from "@/types/projects";

const mocks = vi.hoisted(() => ({ addToast: vi.fn() }));

vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/context/ToastContext", () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const rule: ProjectAutomationRule = {
  id: "rule-1",
  project_id: "project-1",
  name: "Revisar prioridades altas",
  description: "Avisar al completar",
  trigger_event: "task_completed",
  condition_data: { priority: "high" },
  action_type: "notify_assignee",
  action_data: {},
  is_active: true,
  execution_count: 0,
  created_at: "2026-10-04T00:00:00Z",
  updated_at: "2026-10-04T00:00:00Z",
};

function renderDrawer(tasks: ProjectTaskRecord[] = []) {
  return render(
    <SidebarLayerProvider>
      <ProjectAutomationsDrawer projectId="project-1" isOpen onClose={vi.fn()} tasks={tasks} />
    </SidebarLayerProvider>,
  );
}

async function openBuilder(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: /Crear primera regla/ }));
  return screen.findByLabelText("Nombre de la regla *");
}

describe("ProjectAutomationsDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses only defined semantic text tokens in the automation builder", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([]);
    const { container } = renderDrawer();

    await user.click(await screen.findByRole("button", { name: /Crear primera regla/ }));
    await screen.findByLabelText("Nombre de la regla *");

    const builder = container.querySelector("form");
    expect(builder).not.toBeNull();
    expect(builder?.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(builder?.innerHTML).toContain("--text-primary");
    expect(builder?.innerHTML).toContain("--text-secondary");
    expect(builder?.innerHTML).toContain("--warning-muted");
    expect(builder?.innerHTML).toContain("--warning-text");
  });

  it("discloses that saved rules are not automatically dispatched yet", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([]);
    renderDrawer();

    expect(await screen.findByRole("status")).toHaveTextContent(
      "los cambios de tareas todavía no disparan su ejecución automática",
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "La pestaña «Vista previa» solo simula resultados y no aplica acciones.",
    );
  });

  it("creates a follow-up rule with the backend contract payload", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([]).mockResolvedValueOnce({ ...rule, name: "Seguimiento" });
    const { container } = renderDrawer();

    await openBuilder(user);
    await user.type(screen.getByLabelText("Nombre de la regla *"), "Seguimiento");
    await user.type(screen.getByLabelText("Descripción (opcional)"), "Cerrar tareas urgentes");
    await user.selectOptions(screen.getByLabelText("Prioridad de la tarea"), "urgent");
    await user.selectOptions(screen.getByLabelText("Estado de la tarea"), "completed");
    await user.click(screen.getByRole("button", { name: /Crear tarea de seguimiento/ }));
    await user.type(screen.getByLabelText("Título de la nueva tarea"), "Validar cierre");
    await user.clear(screen.getByLabelText("Plazo (días de duración)"));
    await user.type(screen.getByLabelText("Plazo (días de duración)"), "5");
    expect((await axe(container)).violations).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Crear Automatización" }));

    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith(
      "/projects/project-1/automations",
      expect.objectContaining({
        token: "test-token",
        method: "POST",
        body: JSON.stringify({
          project_id: "project-1",
          name: "Seguimiento",
          description: "Cerrar tareas urgentes",
          trigger_event: "task_completed",
          condition_data: { priority: "urgent", status: "completed" },
          action_type: "create_followup_task",
          action_data: { title: "Validar cierre", duration_days: 5, priority: "medium" },
          is_active: true,
        }),
      }),
    ));
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Automatización creada", type: "success" }));
  });

  it("distinguishes load failure from an empty list and retries successfully", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([rule]);
    renderDrawer();

    expect(await screen.findByRole("alert")).toHaveTextContent("No se cargaron las automatizaciones");
    expect(screen.queryByText("Sin automatizaciones configuradas")).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Error de conexión", type: "error" }));

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Revisar prioridades altas")).toBeInTheDocument();
  });

  it("requires confirmation before soft deleting an automation rule", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([rule]).mockResolvedValueOnce(undefined);
    renderDrawer();

    expect(await screen.findByText("Revisar prioridades altas")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Eliminar regla Revisar prioridades altas" }));
    expect(await screen.findByRole("complementary", { name: "Eliminar automatización" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Revisar prioridades altas")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Eliminar regla Revisar prioridades altas" }));
    await user.click(await screen.findByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith(
      "/projects/project-1/automations/rule-1",
      expect.objectContaining({ token: "test-token", method: "DELETE" }),
    ));
    await waitFor(() => expect(screen.queryByText("Revisar prioridades altas")).not.toBeInTheDocument());
  });

  it("keeps the confirmation open and the rule intact when deletion fails", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([rule]).mockRejectedValueOnce(new Error("offline"));
    renderDrawer();

    await screen.findByText("Revisar prioridades altas");
    await user.click(screen.getByRole("button", { name: "Eliminar regla Revisar prioridades altas" }));
    await user.click(await screen.findByRole("button", { name: "Eliminar" }));

    expect(await screen.findByRole("complementary", { name: "Eliminar automatización" })).toBeInTheDocument();
    expect(screen.getByText("Revisar prioridades altas")).toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Error al eliminar", type: "error" }));
  });

  it("persists a rule's active state only after PATCH succeeds", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([rule]).mockResolvedValueOnce({ ...rule, is_active: false });
    renderDrawer();

    await user.click(await screen.findByRole("button", { name: "Activa" }));
    expect(await screen.findByRole("button", { name: "Pausada" })).toBeInTheDocument();
    expect(apiFetch).toHaveBeenLastCalledWith(
      "/projects/project-1/automations/rule-1",
      expect.objectContaining({ token: "test-token", method: "PATCH", body: JSON.stringify({ is_active: false }) }),
    );
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Automatización pausada", type: "info" }));
  });

  it("does not change the visible active state when PATCH fails", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockResolvedValueOnce([rule]).mockRejectedValueOnce(new Error("offline"));
    renderDrawer();

    await user.click(await screen.findByRole("button", { name: "Activa" }));
    expect(screen.getByRole("button", { name: "Activa" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pausada" })).not.toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Error al actualizar", type: "error" }));
  });

  it("previews automation effects without confirmation or persistence", async () => {
    const user = userEvent.setup();
    const task: ProjectTaskRecord = {
      id: "task-1", project_id: "project-1", title: "Preparar retiro", status: "completed", priority: "high",
    };
    const results: AutomationExecutionResult[] = [{
      rule_id: rule.id, rule_name: rule.name, action_type: rule.action_type, status: "would_execute", details: "Se generaría una notificación",
    }];
    vi.mocked(apiFetch).mockResolvedValueOnce([]).mockResolvedValueOnce(results);
    renderDrawer([task]);

    await user.click(await screen.findByRole("button", { name: "Vista previa" }));
    await user.click(screen.getByRole("button", { name: "Previsualizar: tarea completada" }));

    await screen.findByText("Resultado de la vista previa");
    expect(screen.queryByRole("complementary", { name: "Confirmar ejecución de reglas" })).not.toBeInTheDocument();
    expect(apiFetch).toHaveBeenLastCalledWith(
      "/projects/project-1/automations/evaluate",
      expect.objectContaining({
        token: "test-token",
        method: "POST",
        body: JSON.stringify({
          trigger_event: "task_completed",
          task_id: "task-1",
          dry_run: true,
          context_data: { task_title: "Preparar retiro", priority: "high", status: "completed" },
        }),
      }),
    );
    expect(screen.getByText("Se generaría una notificación")).toBeInTheDocument();
    expect(screen.getByText("Se ejecutaría")).toBeInTheDocument();
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({ title: "Vista previa completada", type: "info" }));
  });
});

import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjectContextPanel from "./ProjectContextPanel";
import { ProjectUpdateProvider, type ProjectUpdateContextValue } from "@/context/ProjectUpdateContext";
import { createMockProject, createMockTask } from "@/test-utils/factories";

vi.mock("@/components/projects/ProjectChatPanel", () => ({
  default: ({ projectId }: { projectId: string }) => <div>Chat del proyecto {projectId}</div>,
}));

vi.mock("@/components/projects/ProjectActivityFeed", () => ({
  default: ({ activities }: { activities: unknown[] }) => <div>Actividad del proyecto ({activities.length})</div>,
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "token-1" }),
}));

const socketMock = vi.hoisted(() => ({
  onEvent: null as ((payload: unknown) => void) | null,
  calls: [] as Array<{ enabled?: boolean; rooms?: string[]; token?: string | null }>,
}));

vi.mock("@/hooks/useWorkspaceSocket", () => ({
  useWorkspaceSocket: (options: { enabled?: boolean; rooms?: string[]; token?: string | null; onEvent?: (payload: unknown) => void }) => {
    socketMock.onEvent = options.onEvent ?? null;
    socketMock.calls.push({ enabled: options.enabled, rooms: options.rooms, token: options.token });
    return { status: options.enabled ? "open" : "idle" };
  },
}));

const projectInboxMock = vi.hoisted(() => ({
  items: [
    {
      id: "task-task-open",
      type: "task_assigned",
      user: "Ana",
      content: "Te asignaron una tarea",
      project: "Proyecto CCF",
      project_id: "project-1",
      task_id: "task-open",
      task_title: "Tarea de prueba",
      is_read: false,
      created_at: "2026-08-01T12:00:00Z",
    },
  ],
  markAsRead: vi.fn(async () => undefined),
  refresh: vi.fn(async () => undefined),
}));

vi.mock("@/hooks/useProjectInbox", () => ({
  useProjectInbox: () => ({
    items: projectInboxMock.items,
    unreadCount: projectInboxMock.items.filter((item) => !item.is_read).length,
    loading: false,
    error: null,
    refresh: projectInboxMock.refresh,
    markAsRead: projectInboxMock.markAsRead,
  }),
}));

vi.mock("@/hooks/useNotifications", () => ({
  useNotifications: () => ({
    notifications: [
      { id: "notification-1", read: false },
      { id: "notification-2", read: true },
    ],
    loading: false,
    error: null,
    refresh: vi.fn(async () => undefined),
    markRead: vi.fn(async () => undefined),
    markAllRead: vi.fn(async () => undefined),
  }),
}));

function renderPanel(
  overrides: Partial<ProjectUpdateContextValue> = {},
  panelProps: React.ComponentProps<typeof ProjectContextPanel> = {},
) {
  const value: ProjectUpdateContextValue = {
    project: createMockProject({ id: "project-1", title: "Proyecto CCF", description: "Descripción del proyecto" }),
    tasks: [
      createMockTask({ id: "task-open", status: "todo" }),
      createMockTask({ id: "task-done", status: "completed" }),
    ],
    phases: [],
    activities: [{
      id: "activity-1",
      kind: "task_created",
      project_id: "project-1",
      project_title: "Proyecto CCF",
      description: "Tarea creada",
      created_at: "2026-08-01T12:00:00Z",
    }],
    loading: false,
    reloadProject: vi.fn(async () => undefined),
    updateTask: vi.fn(async () => undefined),
    createTask: vi.fn(async () => true),
    deleteTask: vi.fn(async () => undefined),
    updateProject: vi.fn(async () => undefined),
    ...overrides,
  };

  return render(
    <ProjectUpdateProvider value={value}>
      <ProjectContextPanel {...panelProps} />
    </ProjectUpdateProvider>,
  );
}

describe("ProjectContextPanel", () => {
  const TABS_STORAGE_KEY = "workspace:project_context_tabs_order";
  const getTabIds = () => screen.getAllByRole("tab").map((tab) => tab.id);

  beforeEach(() => {
    socketMock.onEvent = null;
    socketMock.calls = [];
    projectInboxMock.refresh.mockClear();
    projectInboxMock.markAsRead.mockClear();
    window.localStorage.clear();
  });

  it("renders the default chat tab and keeps the inbox socket disabled in Chat", () => {
    renderPanel();

    expect(socketMock.calls.at(-1)).toEqual({ enabled: false, rooms: ["project_project-1"], token: "token-1" });
    expect(screen.getByRole("complementary", { name: "Contexto del proyecto" })).toBeInTheDocument();
    expect(screen.getByText("Proyecto CCF")).toBeInTheDocument();
    expect(screen.getByText("1 abiertas")).toBeInTheDocument();
    expect(screen.getByText("Chat del proyecto project-1")).toBeInTheDocument();

    const chatTab = screen.getByRole("tab", { name: "Chat" });
    expect(chatTab).toHaveAttribute("aria-selected", "true");
    expect(chatTab).toHaveAttribute("aria-controls", "project-context-panel");
  });

  it("switches between activity and details without leaving the workspace", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole("tab", { name: "Historia" }));
    expect(screen.getByText("Actividad del proyecto (1)")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Historia" })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: "Detalles" }));
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("Completadas")).toBeInTheDocument();
    expect(screen.getByText("Descripción del proyecto")).toBeInTheDocument();
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", "project-context-tab-details");
  });

  it("uses high-contrast semantic text tokens for detail labels and values", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole("tab", { name: "Detalles" }));

    expect(screen.getByText("Total")).toHaveClass("text-[hsl(var(--text-secondary))]");
    expect(screen.getByText("2")).toHaveClass("text-[hsl(var(--text-primary))]");
    expect(screen.getByText("Estado")).toHaveClass("text-[hsl(var(--text-secondary))]");
    expect(screen.getByText("Descripción")).toHaveClass("text-[hsl(var(--text-secondary))]");
    expect(screen.getByText("Descripción del proyecto")).toHaveClass("text-[hsl(var(--text-primary))]");
  });

  it("shows PMI scope, schedule, and BAC diagnostics in Details", async () => {
    const user = userEvent.setup();
    renderPanel({
      project: createMockProject({ id: "project-1", title: "Proyecto CCF", budget_allocated: 1000 }),
      tasks: [
        createMockTask({ id: "task-done", status: "done", priority: "medium", due_date: "2020-01-01", budget_allocated: 200 }),
        createMockTask({ id: "task-blocked", status: "blocked", priority: "high", due_date: "2020-01-01", budget_allocated: 300 }),
        createMockTask({ id: "task-urgent", status: "todo", priority: "urgent", due_date: "2999-01-01", budget_allocated: 100 }),
        createMockTask({ id: "task-active", status: "in_progress", priority: "medium", due_date: "2999-01-01", budget_allocated: 200 }),
      ],
    });

    await user.click(screen.getByRole("tab", { name: "Detalles" }));
    const diagnosis = screen.getByTestId("context-pmi-triple-constraint");
    expect(diagnosis).toHaveTextContent("25% completado");
    expect(diagnosis).toHaveTextContent("1 de 4 paquetes completados");
    expect(diagnosis).toHaveTextContent("2 bloqueados o urgentes abiertos");
    expect(diagnosis).toHaveTextContent("1 actividad vencida abierta");
    expect(diagnosis).toHaveTextContent("Alerta de Atraso");
    expect(diagnosis).toHaveTextContent("Reserva por Distribuir");
    expect(diagnosis).toHaveTextContent("Distribuido: $800");
    expect(diagnosis).toHaveTextContent("BAC: $1.000");
  });

  it("distinguishes a balanced EDT budget from allocation that exceeds BAC", async () => {
    const user = userEvent.setup();
    const task = createMockTask({ id: "budgeted", status: "todo", budget_allocated: 1000 });
    const firstRender = renderPanel({
      project: createMockProject({ id: "project-1", budget_allocated: 1000 }),
      tasks: [task],
    });
    await user.click(screen.getByRole("tab", { name: "Detalles" }));
    expect(screen.getByTestId("context-pmi-triple-constraint")).toHaveTextContent("Cronograma en Regla");
    expect(screen.getByTestId("context-pmi-triple-constraint")).toHaveTextContent("Presupuesto Cuadrado");

    firstRender.unmount();
    renderPanel({
      project: createMockProject({ id: "project-1", budget_allocated: 900 }),
      tasks: [task],
    });
    await user.click(screen.getByRole("tab", { name: "Detalles" }));
    expect(screen.getByTestId("context-pmi-triple-constraint")).toHaveTextContent("Exceso sobre BAC");
  });

  it("renders project inbox items, marks them read, and opens the related task", async () => {
    const user = userEvent.setup();
    const onOpenTask = vi.fn();
    render(
      <ProjectUpdateProvider value={{
        project: createMockProject({ id: "project-1", title: "Proyecto CCF" }),
        tasks: [createMockTask({ id: "task-open", title: "Tarea de prueba" })],
        phases: [],
        activities: [],
        loading: false,
        reloadProject: vi.fn(async () => undefined),
        updateTask: vi.fn(async () => undefined),
        createTask: vi.fn(async () => true),
        deleteTask: vi.fn(async () => undefined),
        updateProject: vi.fn(async () => undefined),
      }}>
        <ProjectContextPanel onOpenTask={onOpenTask} />
      </ProjectUpdateProvider>,
    );

    await user.click(screen.getByRole("tab", { name: /Inbox/ }));
    expect(screen.getByText("Te asignaron una tarea")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Inbox/ })).toHaveTextContent("1");

    await user.click(screen.getByRole("button", { name: "Abrir tarea" }));
    expect(projectInboxMock.markAsRead).toHaveBeenCalledWith("task-task-open");
    expect(onOpenTask).toHaveBeenCalledWith(expect.objectContaining({ id: "task-open" }));
  });

  it("refreshes the project inbox for realtime events from the active project", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByRole("tab", { name: /Inbox/ }));
    expect(socketMock.calls.at(-1)).toEqual({ enabled: true, rooms: ["project_project-1"], token: "token-1" });

    socketMock.onEvent?.({
      event: "project_message",
      project_id: "project-1",
      message: { id: "message-1" },
    });
    expect(projectInboxMock.refresh).toHaveBeenCalledTimes(1);

    socketMock.onEvent?.({
      event: "notification:new",
      body: { project_id: "other-project" },
    });
    expect(projectInboxMock.refresh).toHaveBeenCalledTimes(1);
  });

  it("shows the global unread notification count as a workspace link", () => {
    renderPanel();

    expect(screen.getByRole("link", { name: "Abrir notificaciones, 1 sin leer" })).toHaveAttribute(
      "href",
      "/plataforma/inbox",
    );
  });

  it("supports keyboard navigation across context tabs", async () => {
    const user = userEvent.setup();
    renderPanel();

    const chatTab = screen.getByRole("tab", { name: "Chat" });
    chatTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Inbox/ })).toHaveFocus();
    expect(screen.getByRole("tab", { name: /Inbox/ })).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Historia" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Historia" })).toHaveAttribute("aria-selected", "true");
  });

  it("allows toggling expand to full width (extender todo/restaurar)", async () => {
    const user = userEvent.setup();
    renderPanel();

    const aside = screen.getByRole("complementary", { name: "Contexto del proyecto" });
    expect(aside).not.toHaveClass("w-full flex-1 max-w-full");

    const expandBtn = screen.getByRole("button", { name: "Extender a toda la pantalla" });
    await user.click(expandBtn);

    expect(aside).toHaveClass("w-full flex-1 max-w-full");

    const restoreBtn = screen.getByRole("button", { name: "Restaurar tamaño normal del panel" });
    await user.click(restoreBtn);

    expect(aside).not.toHaveClass("w-full flex-1 max-w-full");
  });

  it("renders the manual resize handle when not maximized", () => {
    renderPanel();
    expect(screen.getByRole("separator", { name: "Ajustar ancho del contexto" })).toBeInTheDocument();
  });

  it("allows minimizing and restoring the panel", async () => {
    const user = userEvent.setup();
    renderPanel();

    const minimizeBtn = screen.getByRole("button", { name: "Minimizar panel de contexto" });
    await user.click(minimizeBtn);

    const restoreBtn = screen.getByRole("button", { name: "Restaurar panel de contexto" });
    expect(restoreBtn).toBeInTheDocument();

    await user.click(restoreBtn);
    expect(screen.getByRole("button", { name: "Minimizar panel de contexto" })).toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderPanel({}, { onClose });

    const closeBtn = screen.getByRole("button", { name: "Cerrar panel de contexto" });
    await user.click(closeBtn);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders and triggers project tools in the Herramientas tab when tools are provided", async () => {
    const user = userEvent.setup();
    const onSelectDrive = vi.fn();
    renderPanel(
      {},
      {
        tools: [
          { key: "drive", label: "Drive", onSelect: onSelectDrive },
          { key: "kpis", label: "KPIs", onSelect: vi.fn() },
        ],
      },
    );

    // Orden por defecto 1°Chat 2°Inbox 3°Herramientas 4°Detalles 5°Historia, Chat activa (TKT-PRO-SCROLLBARS-AND-MOVABLE-TABS-01)
    expect(getTabIds()).toEqual([
      "project-context-tab-chat",
      "project-context-tab-inbox",
      "project-context-tab-tools",
      "project-context-tab-details",
      "project-context-tab-activity",
    ]);
    expect(screen.getByRole("tab", { name: "Chat" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Herramientas" })).toHaveAttribute("aria-selected", "false");

    const toolsTab = screen.getByRole("tab", { name: "Herramientas" });
    await user.click(toolsTab);
    expect(toolsTab).toHaveAttribute("aria-selected", "true");

    const driveBtn = screen.getByRole("button", { name: "Drive" });
    await user.click(driveBtn);
    expect(onSelectDrive).toHaveBeenCalledTimes(1);

    const search = screen.getByTestId("context-tools-search");
    await user.type(search, "kpi");
    expect(screen.getByRole("button", { name: "KPIs" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Drive" })).not.toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "sin coincidencias");
    expect(screen.getByText("No hay herramientas con esa etiqueta.")).toBeInTheDocument();
  });

  it("reorders tabs by drag & drop (Historia al primer lugar) and persists the custom order", () => {
    renderPanel({}, { tools: [{ key: "drive", label: "Drive", onSelect: vi.fn() }] });

    const historia = screen.getByRole("tab", { name: "Historia" });
    const chat = screen.getByRole("tab", { name: "Chat" });

    fireEvent.dragStart(historia, { dataTransfer: new MockDataTransfer("activity") });
    fireEvent.dragOver(chat, { dataTransfer: new MockDataTransfer("activity") });
    fireEvent.drop(chat, { dataTransfer: new MockDataTransfer("activity") });
    fireEvent.dragEnd(historia, { dataTransfer: new MockDataTransfer("activity") });

    // Las demás pestañas siguen su curso manteniendo su secuencia relativa (splice)
    expect(getTabIds()).toEqual([
      "project-context-tab-activity",
      "project-context-tab-chat",
      "project-context-tab-inbox",
      "project-context-tab-tools",
      "project-context-tab-details",
    ]);
    expect(JSON.parse(window.localStorage.getItem(TABS_STORAGE_KEY) ?? "null")).toEqual([
      "activity",
      "chat",
      "inbox",
      "tools",
      "details",
    ]);
  });

  it("reorders tabs with the keyboard (Alt+ArrowLeft) and persists the custom order", () => {
    renderPanel({}, { tools: [{ key: "drive", label: "Drive", onSelect: vi.fn() }] });

    fireEvent.keyDown(screen.getByRole("tab", { name: /Inbox/ }), {
      key: "ArrowLeft",
      altKey: true,
      shiftKey: false,
      ctrlKey: false,
      metaKey: false,
    });

    expect(getTabIds()).toEqual([
      "project-context-tab-inbox",
      "project-context-tab-chat",
      "project-context-tab-tools",
      "project-context-tab-details",
      "project-context-tab-activity",
    ]);
    expect(JSON.parse(window.localStorage.getItem(TABS_STORAGE_KEY) ?? "null")).toEqual([
      "inbox",
      "chat",
      "tools",
      "details",
      "activity",
    ]);
  });

  it("hydrates the custom tab order from localStorage and activates the user's first tab by default", () => {
    window.localStorage.setItem(
      TABS_STORAGE_KEY,
      JSON.stringify(["activity", "chat", "inbox", "tools", "details"]),
    );

    renderPanel({}, { tools: [{ key: "drive", label: "Drive", onSelect: vi.fn() }] });

    expect(getTabIds()).toEqual([
      "project-context-tab-activity",
      "project-context-tab-chat",
      "project-context-tab-inbox",
      "project-context-tab-tools",
      "project-context-tab-details",
    ]);
    // La primera pestaña colocada por el usuario gana como activa por defecto
    expect(screen.getByRole("tab", { name: "Historia" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Chat" })).toHaveAttribute("aria-selected", "false");
  });

  it("ignores corrupted localStorage orders and falls back to the default sequence", () => {
    window.localStorage.setItem(TABS_STORAGE_KEY, "no-json{{");

    renderPanel({}, { tools: [{ key: "drive", label: "Drive", onSelect: vi.fn() }] });

    expect(getTabIds()).toEqual([
      "project-context-tab-chat",
      "project-context-tab-inbox",
      "project-context-tab-tools",
      "project-context-tab-details",
      "project-context-tab-activity",
    ]);
    expect(screen.getByRole("tab", { name: "Chat" })).toHaveAttribute("aria-selected", "true");
  });

  it("shows a primary-token drop indicator on the drop target while dragging", () => {
    renderPanel();

    const historia = screen.getByRole("tab", { name: "Historia" });
    const chat = screen.getByRole("tab", { name: "Chat" });

    fireEvent.dragStart(historia, { dataTransfer: new MockDataTransfer("activity") });
    fireEvent.dragOver(chat, { dataTransfer: new MockDataTransfer("activity") });

    expect(chat.className).toContain("outline-[hsl(var(--primary))]");
    expect(screen.getByRole("tab", { name: "Historia" }).className).toContain("cursor-grab");
  });
});

class MockDataTransfer {
  private values = new Map<string, string>();
  constructor(initial?: string) {
    if (initial) this.setData("text/plain", initial);
  }
  setData(type: string, value: string) {
    this.values.set(type, value);
  }
  getData(type: string) {
    return this.values.get(type) ?? "";
  }
}

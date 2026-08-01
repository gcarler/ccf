import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
  calls: [] as Array<{ enabled?: boolean; rooms?: string[] }>,
}));

vi.mock("@/hooks/useWorkspaceSocket", () => ({
  useWorkspaceSocket: (options: { enabled?: boolean; rooms?: string[]; onEvent?: (payload: unknown) => void }) => {
    socketMock.onEvent = options.onEvent ?? null;
    socketMock.calls.push({ enabled: options.enabled, rooms: options.rooms });
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

function renderPanel(overrides: Partial<ProjectUpdateContextValue> = {}) {
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
      <ProjectContextPanel />
    </ProjectUpdateProvider>,
  );
}

describe("ProjectContextPanel", () => {
  beforeEach(() => {
    socketMock.onEvent = null;
    socketMock.calls = [];
    projectInboxMock.refresh.mockClear();
    projectInboxMock.markAsRead.mockClear();
  });

  it("renders the default chat tab and keeps the inbox socket disabled in Chat", () => {
    renderPanel();

    expect(socketMock.calls.at(-1)).toEqual({ enabled: false, rooms: ["project_project-1"] });
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

    await user.click(screen.getByRole("tab", { name: "Actividad" }));
    expect(screen.getByText("Actividad del proyecto (1)")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Actividad" })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: "Detalles" }));
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("Completadas")).toBeInTheDocument();
    expect(screen.getByText("Descripción del proyecto")).toBeInTheDocument();
    expect(screen.getByRole("tabpanel")).toHaveAttribute("aria-labelledby", "project-context-tab-details");
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
    expect(socketMock.calls.at(-1)).toEqual({ enabled: true, rooms: ["project_project-1"] });

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
    expect(screen.getByRole("tab", { name: "Actividad" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Actividad" })).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Detalles" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Detalles" })).toHaveAttribute("aria-selected", "true");
  });
});

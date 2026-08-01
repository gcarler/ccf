import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import { useProjectInbox } from "./useProjectInbox";

const mockAuth = vi.hoisted(() => ({ token: "token-1" as string | null }));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

const inboxRows = [
  {
    id: "task-task-1",
    type: "task_assigned",
    user: "Ana",
    content: "Te asignaron una tarea",
    project: "Proyecto CCF",
    project_id: "project-1",
    task_id: "task-1",
    task_title: "Preparar agenda",
    is_read: false,
    created_at: "2026-08-01T12:00:00Z",
  },
  {
    id: "comment-comment-1",
    type: "comment",
    user: "Luis",
    content: "Nuevo comentario",
    project: "Otro proyecto",
    project_id: "project-2",
    task_id: null,
    task_title: null,
    is_read: false,
    created_at: "2026-08-01T11:00:00Z",
  },
  {
    id: "comment-comment-2",
    type: "comment",
    user: "Marta",
    content: "Comentario leído",
    project: "Proyecto CCF",
    project_id: "project-1",
    task_id: null,
    task_title: null,
    is_read: true,
    created_at: "2026-08-01T10:00:00Z",
  },
];

describe("useProjectInbox", () => {
  beforeEach(() => {
    mockAuth.token = "token-1";
    vi.mocked(apiFetch).mockReset();
    vi.mocked(apiFetch).mockResolvedValue(inboxRows);
  });

  it("filters the unified inbox to the active project and derives unread count", async () => {
    const { result } = renderHook(() => useProjectInbox("project-1"));

    await waitFor(() => expect(result.current.items).toHaveLength(2));

    expect(result.current.items).toHaveLength(2);
    expect(result.current.items.every((item) => item.project_id === "project-1")).toBe(true);
    expect(result.current.unreadCount).toBe(1);
    expect(apiFetch).toHaveBeenCalledWith("/projects/inbox", expect.objectContaining({
      token: "token-1",
      cache: "no-store",
      query: { limit: 200 },
      signal: expect.any(AbortSignal),
    }));
  });

  it("marks an unread item optimistically and persists the read marker", async () => {
    const { result } = renderHook(() => useProjectInbox("project-1"));
    await waitFor(() => expect(result.current.items).toHaveLength(2));

    vi.mocked(apiFetch).mockResolvedValueOnce({});
    await act(async () => {
      await result.current.markAsRead("task-task-1");
    });

    expect(result.current.items.find((item) => item.id === "task-task-1")?.is_read).toBe(true);
    expect(result.current.unreadCount).toBe(0);
    expect(apiFetch).toHaveBeenLastCalledWith("/projects/inbox/task-task-1/read", {
      method: "POST",
      token: "token-1",
      body: { is_read: true },
    });
  });

  it("restores the previous state when marking an item as read fails", async () => {
    const { result } = renderHook(() => useProjectInbox("project-1"));
    await waitFor(() => expect(result.current.items).toHaveLength(2));

    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("network"));
    await act(async () => {
      await result.current.markAsRead("task-task-1");
    });

    expect(result.current.items.find((item) => item.id === "task-task-1")?.is_read).toBe(false);
    expect(result.current.error).toBe("No se pudo marcar el elemento como leído.");
  });

  it("preserves optimistic read state when a stale refresh resolves during a pending mutation", async () => {
    const { result } = renderHook(() => useProjectInbox("project-1"));
    await waitFor(() => expect(result.current.items).toHaveLength(2));

    let resolveMutation: (() => void) | undefined;
    vi.mocked(apiFetch).mockImplementation((path) => {
      if (String(path).endsWith("/read")) {
        return new Promise((resolve) => {
          resolveMutation = () => resolve({});
        });
      }
      return Promise.resolve([
        { ...inboxRows[0], is_read: false },
        { ...inboxRows[2], is_read: true },
      ]);
    });

    act(() => {
      void result.current.markAsRead("task-task-1");
    });
    await waitFor(() => {
      expect(result.current.items.find((item) => item.id === "task-task-1")?.is_read).toBe(true);
    });

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.items.find((item) => item.id === "task-task-1")?.is_read).toBe(true);

    await act(async () => {
      resolveMutation?.();
    });
  });

  it("does not fetch without an authenticated project context", async () => {
    mockAuth.token = null;
    const { result } = renderHook(() => useProjectInbox("project-1"));

    await waitFor(() => expect(result.current.items).toEqual([]));

    expect(result.current.items).toEqual([]);
    expect(apiFetch).not.toHaveBeenCalled();
  });
});

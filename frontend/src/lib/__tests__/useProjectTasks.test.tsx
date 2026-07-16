import React, { createContext, useContext, ReactNode } from "react";
import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useProjectTasks } from "@/hooks/useProjectTasks";
import * as http from "@/lib/http";

let apiFetchSpy: MockInstance<Parameters<typeof http.apiFetch>, ReturnType<typeof http.apiFetch>>;

interface AuthContextType {
  token: string | null;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({ token: "test-token", loading: false });

function AuthProvider({ children }: { children: ReactNode }) {
  return <AuthContext.Provider value={{ token: "test-token", loading: false }}>{children}</AuthContext.Provider>;
}

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => useContext(AuthContext),
  AuthProvider,
}));

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useProjectTasks", () => {
  beforeEach(() => {
    apiFetchSpy = vi.spyOn(http, "apiFetch");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should fetch tasks on demand", async () => {
    const tasks = [
      { id: "1", title: "Task 1", status: "todo", priority: "medium" },
      { id: "2", title: "Task 2", status: "in_progress", priority: "high" },
    ];
    apiFetchSpy.mockResolvedValueOnce(tasks);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.fetchTasks("project-1");
    });

    expect(result.current.tasks).toEqual(tasks);
    expect(result.current.loading).toBe(false);
    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/project-1/tasks", { token: "test-token" });
  });

  it("should create a task and add it to the list", async () => {
    const newTask = { id: "3", title: "New Task", status: "todo", priority: "medium" };
    apiFetchSpy.mockResolvedValueOnce(newTask);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.createTask("project-1", { title: "New Task" });
    });

    expect(result.current.tasks).toEqual([newTask]);
    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/project-1/tasks", {
      method: "POST",
      token: "test-token",
      body: { title: "New Task" },
    });
  });

  it("should update a task optimistically on success", async () => {
    const tasks = [{ id: "1", title: "Task 1", status: "todo", priority: "medium" }];
    apiFetchSpy.mockResolvedValueOnce(tasks);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.fetchTasks("project-1");
    });

    apiFetchSpy.mockResolvedValueOnce({ id: "1", status: "completed" });

    await act(async () => {
      await result.current.updateTask("1", { status: "completed" });
    });

    await waitFor(() => {
      expect(result.current.tasks[0].status).toBe("completed");
    });
  });

  it("should rollback an optimistic update on error", async () => {
    const tasks = [{ id: "1", title: "Task 1", status: "todo", priority: "medium" }];
    apiFetchSpy.mockResolvedValueOnce(tasks);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.fetchTasks("project-1");
    });

    apiFetchSpy.mockRejectedValueOnce(new Error("Network error"));

    await act(async () => {
      await result.current.updateTask("1", { status: "completed" });
    });

    await waitFor(() => {
      expect(result.current.tasks[0].status).toBe("todo");
    });
    expect(result.current.error).toBe("No se pudo actualizar la tarea.");
  });

  it("should delete a task and remove it from the list", async () => {
    const tasks = [{ id: "1", title: "Task 1", status: "todo", priority: "medium" }];
    apiFetchSpy.mockResolvedValueOnce(tasks);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.fetchTasks("project-1");
    });

    apiFetchSpy.mockResolvedValueOnce({});

    await act(async () => {
      await result.current.deleteTask("1");
    });

    expect(result.current.tasks).toEqual([]);
    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/tasks/1", {
      method: "DELETE",
      token: "test-token",
    });
  });

  it("should move a task by updating its status", async () => {
    const tasks = [{ id: "1", title: "Task 1", status: "todo", priority: "medium" }];
    apiFetchSpy.mockResolvedValueOnce(tasks);

    const { result } = renderHook(() => useProjectTasks(), { wrapper });

    await act(async () => {
      await result.current.fetchTasks("project-1");
    });

    apiFetchSpy.mockResolvedValueOnce({ id: "1", status: "in_progress" });

    await act(async () => {
      await result.current.moveTask("1", "in_progress");
    });

    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/tasks/1", {
      method: "PATCH",
      token: "test-token",
      body: { status: "in_progress" },
    });
  });
});

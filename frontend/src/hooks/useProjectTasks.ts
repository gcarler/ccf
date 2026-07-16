"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import type { ProjectTaskRecord } from "@/types/projects";

export interface CreateTaskPayload {
  title: string;
  description?: string | null;
  status?: string;
  priority?: string;
  assignee_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  parent_id?: string | null;
  labels?: string[];
}

export interface UpdateTaskPayload {
  title?: string;
  description?: string | null;
  status?: string;
  priority?: string;
  assignee_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  labels?: string[];
}

interface UseProjectTasksOptions {
  projectId?: string;
  onError?: (message: string) => void;
}

interface UseProjectTasksReturn {
  tasks: ProjectTaskRecord[];
  setTasks: React.Dispatch<React.SetStateAction<ProjectTaskRecord[]>>;
  loading: boolean;
  error: string | null;
  fetchTasks: (projectId: string) => Promise<void>;
  createTask: (projectId: string, payload: CreateTaskPayload) => Promise<ProjectTaskRecord | null>;
  updateTask: (taskId: string, payload: UpdateTaskPayload, options?: { optimistic?: boolean }) => Promise<ProjectTaskRecord | null>;
  deleteTask: (taskId: string) => Promise<boolean>;
  moveTask: (taskId: string, newStatus: string) => Promise<ProjectTaskRecord | null>;
}

export function useProjectTasks(options: UseProjectTasksOptions = {}): UseProjectTasksReturn {
  const { projectId, onError } = options;
  const { token } = useAuth();
  const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback(
    (message: string) => {
      setError(message);
      onError?.(message);
    },
    [onError]
  );

  const fetchTasks = useCallback(
    async (projectId: string) => {
      if (!token) {
        handleError("Debes iniciar sesión para ver las tareas.");
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<ProjectTaskRecord[]>(`/projects/${projectId}/tasks`, { token });
        setTasks(Array.isArray(data) ? data : []);
      } catch (err) {
        handleError("No se pudieron cargar las tareas.");
      } finally {
        setLoading(false);
      }
    },
    [token, handleError]
  );

  // Auto-fetch when projectId or fetchTasks changes
  useEffect(() => {
    if (projectId) {
      fetchTasks(projectId);
    }
  }, [projectId, fetchTasks]);

  const createTask = useCallback(
    async (projectId: string, payload: CreateTaskPayload): Promise<ProjectTaskRecord | null> => {
      if (!token) {
        handleError("Debes iniciar sesión para crear tareas.");
        return null;
      }
      try {
        const created = await apiFetch<ProjectTaskRecord>(`/projects/${projectId}/tasks`, {
          method: "POST",
          token,
          body: payload,
        });
        setTasks((prev) => [created, ...prev]);
        return created;
      } catch (err) {
        handleError("No se pudo crear la tarea.");
        return null;
      }
    },
    [token, handleError]
  );

  const updateTask = useCallback(
    async (
      taskId: string,
      payload: UpdateTaskPayload,
      { optimistic = true }: { optimistic?: boolean } = {}
    ): Promise<ProjectTaskRecord | null> => {
      if (!token) {
        handleError("Debes iniciar sesión para actualizar tareas.");
        return null;
      }

      const previousTasks = [...tasks];
      const taskIndex = tasks.findIndex((t) => t.id === taskId);
      const previousTask = taskIndex >= 0 ? tasks[taskIndex] : null;

      if (optimistic && previousTask) {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, ...payload } : t))
        );
      }

      try {
        const updated = await apiFetch<ProjectTaskRecord>(`/projects/tasks/${taskId}`, {
          method: "PATCH",
          token,
          body: payload,
        });
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, ...updated } : t))
        );
        return updated;
      } catch (err) {
        if (optimistic) {
          setTasks(previousTasks);
        }
        handleError("No se pudo actualizar la tarea.");
        return null;
      }
    },
    [token, tasks, handleError]
  );

  const deleteTask = useCallback(
    async (taskId: string): Promise<boolean> => {
      if (!token) {
        handleError("Debes iniciar sesión para eliminar tareas.");
        return false;
      }
      try {
        await apiFetch(`/projects/tasks/${taskId}`, {
          method: "DELETE",
          token,
        });
        setTasks((prev) => prev.filter((t) => t.id !== taskId));
        return true;
      } catch (err) {
        handleError("No se pudo eliminar la tarea.");
        return false;
      }
    },
    [token, handleError]
  );

  const moveTask = useCallback(
    async (taskId: string, newStatus: string): Promise<ProjectTaskRecord | null> => {
      return updateTask(taskId, { status: newStatus }, { optimistic: true });
    },
    [updateTask]
  );

  return {
    tasks,
    setTasks,
    loading,
    error,
    fetchTasks,
    createTask,
    updateTask,
    deleteTask,
    moveTask,
  };
}

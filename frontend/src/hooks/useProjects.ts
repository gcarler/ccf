"use client";

import { useCallback, useState } from "react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import type { ProjectRecord } from "@/types/projects";

export interface UpdateProjectPayload {
  title?: string;
  description?: string | null;
  status?: string;
  owner_id?: string | null;
  color?: string | null;
  icon?: string | null;
  /** PMI §4.x — Gobernanza del ciclo de vida del proyecto. */
  health_status?: string | null;
  progress_mode?: string;
  due_date?: string | null;
  start_date?: string | null;
  budget_allocated?: number | null;
  budget_executed?: number | null;
}

export function useProjects() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateProject = useCallback(
    async (
      projectId: string,
      payload: UpdateProjectPayload
    ): Promise<ProjectRecord | null> => {
      if (!token) {
        setError("Debes iniciar sesión para actualizar proyectos.");
        return null;
      }
      setLoading(true);
      setError(null);
      try {
        const updated = await apiFetch<ProjectRecord>(`/projects/${projectId}`, {
          method: "PATCH",
          token,
          body: payload,
        });
        return updated;
      } catch (err) {
        setError("No se pudo actualizar el proyecto.");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const deleteProject = useCallback(
    async (projectId: string): Promise<boolean> => {
      if (!token) {
        setError("Debes iniciar sesión para eliminar proyectos.");
        return false;
      }
      setLoading(true);
      setError(null);
      try {
        await apiFetch(`/projects/${projectId}`, {
          method: "DELETE",
          token,
        });
        return true;
      } catch (err) {
        setError("No se pudo eliminar el proyecto.");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  /** PMI §4.7 — Cierre del proyecto: estado 'completed'. */
  const completeProject = useCallback(
    (projectId: string) => updateProject(projectId, { status: 'completed' }),
    [updateProject]
  );

  /** PMI §4.7 — Archivado del proyecto: estado 'archived' (soft, no hard delete). */
  const archiveProject = useCallback(
    (projectId: string) => updateProject(projectId, { status: 'archived' }),
    [updateProject]
  );

  return {
    updateProject,
    deleteProject,
    completeProject,
    archiveProject,
    loading,
    error,
  };
}

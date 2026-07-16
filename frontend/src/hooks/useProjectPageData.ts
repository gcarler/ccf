"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { ProjectActivityItem, ProjectTaskRecord, ProjectRecord } from '@/types/projects';
import type { PhaseDef } from '@/context/ProjectUpdateContext';

/**
 * SOT de datos + mutaciones del detalle del proyecto. Encapsula todo el
 * fetching inicial (Promise.all de /projects/{id}, /projects/{id}/tasks,
 * /projects/activities, /projects/{id}/phases) y los handlers que el
 * ProjectUpdateProvider expone al resto de vistas.
 *
 * Después de `PARCIAL-PAGE-001` (2026-07-16), `page.tsx` consume este hook
 * y queda como orquestador (auth + router + UI shell). El provider recibe
 * el objeto plano que este hook retorna.
 *
 * Lo que NO vive aquí (queda en `page.tsx` por ser UI/coordination):
 *  - viewType (view switcher state)
 *  - selectedTask (TaskDetailPanel coordination + URL sync)
 *  - showTaskModal / showProjectSettings / whiteboardOpen / showPhaseManager (drawers)
 *  - confirmAction (delete-project confirm)
 */

export interface CreateTaskInput {
    title: string;
    description?: string | null;
    priority: string;
    status: string;
    assignee_id?: string | null;
    due_date?: string | null;
}

export interface UseProjectPageDataResult {
    // Data (consumed by context provider value)
    project: ProjectRecord | null;
    tasks: ProjectTaskRecord[];
    phases: PhaseDef[];
    activities: ProjectActivityItem[];
    loading: boolean;

    // Mutations (consumed by context value)
    reloadProject: () => Promise<void>;
    createTask: (data: CreateTaskInput) => Promise<boolean>;
    updateProject: (patch: Partial<ProjectRecord>) => Promise<void>;
    updateTask: (taskId: string, patch: Partial<ProjectTaskRecord>) => Promise<void>;
    deleteTask: (taskId: string) => Promise<void>;

    // Local UI helpers (consumed only by the page shell)
    error: string | null;
    reloadKey: number;
    bumpReloadKey: () => void;
}

export function useProjectPageData(id: string): UseProjectPageDataResult {
    const { token, loading: authLoading } = useAuth();
    const [project, setProject] = useState<ProjectRecord | null>(null);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [phases, setPhases] = useState<PhaseDef[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    const loadProject = useCallback(async () => {
        if (!id) {
            setLoading(false);
            setError('No se encontró el proyecto.');
            return;
        }
        if (!token) {
            setLoading(false);
            setError('Debes iniciar sesión para ver este proyecto.');
            return;
        }
        try {
            setError(null);
            setLoading(true);
            const [projData, tasksData, activityRows, phasesData] = await Promise.all([
                apiFetch<ProjectRecord>(`/projects/${id}`, { token }),
                apiFetch<ProjectTaskRecord[]>(`/projects/${id}/tasks`, { token }).catch(() => []),
                apiFetch<ProjectActivityItem[]>(`/projects/activities?project_id=${id}&limit=20`, { token }).catch(() => []),
                apiFetch<PhaseDef[]>(`/projects/${id}/phases`, { token }).catch(() => []),
            ]);
            setProject(projData);
            setTasks(Array.isArray(tasksData) ? tasksData : []);
            setActivities(Array.isArray(activityRows) ? activityRows : []);
            // PEND-QUALITY-PHASE-SYNC-001 (2026-07-16): si el API devuelve
            // ``[]`` se reemplaza el state de phases para evitar arrastrar
            // columnas stale del proyecto anterior o de la última carga.
            setPhases(Array.isArray(phasesData) ? phasesData : []);
            window.dispatchEvent(new CustomEvent('project-updated', { detail: { projectId: id } }));
        } catch (err) {
            setProject(null);
            setTasks([]);
            setActivities([]);
            setPhases([]);
            setError('No se pudo cargar el proyecto.');
            toast.error('Error al cargar detalle del proyecto');
        } finally {
            setLoading(false);
        }
    }, [id, token]);

    useEffect(() => {
        if (!authLoading) loadProject();
    }, [authLoading, loadProject, reloadKey]);

    const createTask = useCallback(async (data: CreateTaskInput): Promise<boolean> => {
        if (!token || !id) return false;
        // PEND-QUALITY-TASK-CREATE-001 (2026-07-16): bloquea creación local
        // antes del round-trip al backend para evitar errores de validación
        // (la vista list pasa ``title: ''`` literal desde
        // ``ProjectViewsContent``). El backend también rechaza title vacío
        // vía ``ProjectTaskBase.title`` ``min_length=1`` + strip.
        const title = (data.title ?? '').trim();
        if (!title) {
            toast.error('Ingresa un título para la tarea');
            return false;
        }
        try {
            await apiFetch(`/projects/${id}/tasks`, {
                method: 'POST', token, body: { ...data, title },
            });
            toast.success('Tarea creada');
            await loadProject();
            return true;
        } catch {
            toast.error('Error al crear tarea');
            return false;
        }
    }, [id, token, loadProject]);

    const updateProject = useCallback(async (patch: Partial<ProjectRecord>) => {
        if (!token || !id) return;
        try {
            await apiFetch(`/projects/${id}`, {
                method: 'PATCH', token, body: patch,
            });
            await loadProject();
        } catch {
            toast.error('Error al actualizar proyecto');
        }
    }, [id, token, loadProject]);

    const updateTask = useCallback(async (taskId: string, patch: Partial<ProjectTaskRecord>) => {
        setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, ...patch } : t)));
        if (!token) return;
        try {
            await apiFetch(`/projects/tasks/${taskId}`, {
                method: 'PATCH', token, body: patch,
            });
            await loadProject();
        } catch {
            toast.error('Error al actualizar tarea');
            await loadProject();
        }
    }, [token, loadProject]);

    const deleteTask = useCallback(async (taskId: string) => {
        setTasks((prev) => prev.filter((t) => t.id !== taskId));
        if (!token) return;
        try {
            await apiFetch(`/projects/tasks/${taskId}`, {
                method: 'DELETE', token,
            });
            await loadProject();
        } catch {
            await loadProject();
        }
    }, [token, loadProject]);

    const bumpReloadKey = useCallback(() => {
        setReloadKey((k) => k + 1);
    }, []);

    return useMemo(() => ({
        project, tasks, phases, activities, loading,
        reloadProject: loadProject,
        createTask, updateProject, updateTask, deleteTask,
        error, reloadKey, bumpReloadKey,
    }), [
        project, tasks, phases, activities, loading,
        loadProject, createTask, updateProject, updateTask, deleteTask,
        error, reloadKey, bumpReloadKey,
    ]);
}

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/http";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import type { ProjectTaskRecord, ProjectTimeLog, ProjectTimeLogCreate } from "@/types/projects";
import { Clock, Plus, Trash2, ChevronUp } from "lucide-react";

interface TaskTimeTrackingSectionProps {
  task: ProjectTaskRecord;
  token: string | null;
  onActivityCreated?: () => void;
}

export default function TaskTimeTrackingSection({
  task,
  token,
  onActivityCreated,
}: TaskTimeTrackingSectionProps) {
  const [logs, setLogs] = useState<ProjectTimeLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [hours, setHours] = useState("1.0");
  const [description, setDescription] = useState("");
  const [isBillable, setIsBillable] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingLogId, setDeletingLogId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  const fetchLogs = useCallback(async () => {
    if (!token || !task.id || !task.project_id) return;
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<ProjectTimeLog[]>(
        `/projects/${task.project_id}/tasks/${task.id}/time-logs`,
        { token }
      );
      setLogs(Array.isArray(data) ? data : []);
    } catch {
      setError("No se pudieron cargar los registros de tiempo.");
    } finally {
      setLoading(false);
    }
  }, [task.id, task.project_id, token]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleCreateLog = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedHours = parseFloat(hours);
    if (isNaN(parsedHours) || parsedHours <= 0) {
      setError("Ingresa un número válido de horas (> 0)");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const payload: ProjectTimeLogCreate = {
        task_id: task.id,
        hours: Math.round(parsedHours * 100) / 100,
        description: description.trim() || `Trabajo en ${task.title}`,
        is_billable: isBillable,
        date: new Date().toISOString(),
      };
      await apiFetch<ProjectTimeLog>(`/projects/${task.project_id}/time-logs`, {
        method: "POST",
        token,
        body: JSON.stringify(payload),
      });
      setDescription("");
      setHours("1.0");
      setShowAddForm(false);
      fetchLogs();
      onActivityCreated?.();
    } catch {
      setError("Error al registrar tiempo");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLog = async (logId: string) => {
    if (!token) return;
    setDeletingLogId(logId);
    setError(null);
    try {
      await apiFetch(`/projects/${task.project_id}/time-logs/${logId}`, {
        method: "DELETE",
        token,
      });
      fetchLogs();
      onActivityCreated?.();
    } catch {
      setError("No se pudo eliminar el registro de tiempo.");
      throw new Error("No se pudo eliminar el registro de tiempo.");
    } finally {
      setDeletingLogId(null);
    }
  };

  const requestDeleteLog = (log: ProjectTimeLog) => {
    setConfirmAction({
      title: "Eliminar registro de tiempo",
      description: `Se eliminarán las ${log.hours.toFixed(2)} horas registradas${log.description ? ` para «${log.description}»` : ""}. Esta acción lo quitará del historial de la tarea.`,
      confirmLabel: "Eliminar registro",
      destructive: true,
      onConfirm: () => handleDeleteLog(log.id),
    });
  };

  const totalHours = logs.reduce((acc, l) => acc + (l.hours || 0), 0);

  return (
    <section aria-labelledby="task-time-tracking-heading" className="px-4 py-3 border-b border-[hsl(var(--border))]">
      <div className="flex items-center justify-between mb-2">
        <h3 id="task-time-tracking-heading" className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
          <Clock size={11} /> Tiempo Dedicado
          {totalHours > 0 && (
            <span
              className="ml-1 px-1.5 py-0.5 rounded font-bold font-mono text-3xs"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                color: "hsl(var(--primary))",
              }}
            >
              {totalHours.toFixed(2)}h
            </span>
          )}
        </h3>

        <button
          type="button"
          onClick={() => setShowAddForm((v) => !v)}
          aria-expanded={showAddForm}
          aria-controls="task-time-log-form"
          aria-label={showAddForm ? "Cancelar registro de horas" : "Registrar horas"}
          className="text-2xs font-bold uppercase tracking-wide flex items-center gap-1 transition-all opacity-80 hover:opacity-100"
          style={{ color: "hsl(var(--primary))" }}
        >
          {showAddForm ? (
            <>
              <ChevronUp size={12} /> Cancelar
            </>
          ) : (
            <>
              <Plus size={12} /> Registrar Horas
            </>
          )}
        </button>
      </div>

      {error && !showAddForm && (
        <p role="alert" className="mb-2 text-3xs" style={{ color: "hsl(var(--destructive))" }}>
          {error}
        </p>
      )}

      {/* Mini formulario de registro rápido */}
      {showAddForm && (
        <form
          id="task-time-log-form"
          onSubmit={handleCreateLog}
          className="p-3 mb-3 rounded-lg border text-xs space-y-2.5"
          style={{
            backgroundColor: "hsl(var(--surface-2))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="task-time-log-hours" className="block text-3xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Horas dedicadas *
              </label>
              <input
                id="task-time-log-hours"
                type="number"
                step="0.25"
                min="0.1"
                required
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                className="w-full py-1.5 px-2 rounded border text-xs"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>
            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-1.5 cursor-pointer text-3xs font-medium">
                <input
                  id="task-time-log-billable"
                  type="checkbox"
                  checked={isBillable}
                  onChange={(e) => setIsBillable(e.target.checked)}
                  style={{ accentColor: "hsl(var(--primary))" }}
                />
                <span>Facturable</span>
              </label>
            </div>
          </div>

          <div>
            <label htmlFor="task-time-log-description" className="block text-3xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
              Descripción de lo realizado
            </label>
            <input
              id="task-time-log-description"
              type="text"
              placeholder="Detalle breve del trabajo..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full py-1.5 px-2 rounded border text-xs"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--foreground))",
              }}
            />
          </div>

          {error && (
            <p role="alert" className="text-3xs" style={{ color: "hsl(var(--destructive))" }}>
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-2.5 py-1 rounded text-2xs font-semibold"
              style={{ color: "hsl(var(--text-secondary))" }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              aria-busy={saving}
              className="px-3 py-1 rounded text-2xs font-bold shadow-sm transition-all"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              {saving ? "Guardando…" : "Guardar Registro"}
            </button>
          </div>
        </form>
      )}

      {/* Lista de registros en esta tarea */}
      {loading ? (
        <div role="status" aria-live="polite" className="py-2 text-center text-3xs" style={{ color: "hsl(var(--text-secondary))" }}>
          Cargando registros...
        </div>
      ) : logs.length === 0 ? (
        <p className="text-2xs italic text-[hsl(var(--muted-foreground))]">
          No hay registros de tiempo en esta tarea aún.
        </p>
      ) : (
        <div className="space-y-1.5">
          {logs.map((log) => (
            <div
              key={log.id}
              className="flex items-center justify-between p-2 rounded-lg border text-2xs"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <div className="min-w-0 flex-1 pr-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-[hsl(var(--foreground))] truncate max-w-[120px]">
                    {log.persona_name || "Colaborador"}
                  </span>
                  <span
                    className="px-1 py-0.2 rounded text-3xs font-semibold"
                    style={{
                      backgroundColor: log.is_billable
                        ? "hsl(var(--success) / 0.15)"
                        : "hsl(var(--surface-1))",
                      color: log.is_billable
                        ? "hsl(var(--success))"
                        : "hsl(var(--text-secondary))",
                    }}
                  >
                    {log.is_billable ? "Facturable" : "No fact."}
                  </span>
                </div>
                <p className="text-[hsl(var(--muted-foreground))] truncate">
                  {log.description || "Sin descripción"}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className="font-bold font-mono px-1.5 py-0.5 rounded text-3xs"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    color: "hsl(var(--primary))",
                  }}
                >
                  {log.hours.toFixed(2)}h
                </span>
                <button
                  type="button"
                  onClick={() => requestDeleteLog(log)}
                  disabled={deletingLogId === log.id}
                  aria-label={`Eliminar registro de ${log.hours.toFixed(2)} horas${log.description ? `: ${log.description}` : ""}`}
                  aria-busy={deletingLogId === log.id}
                  className="opacity-50 hover:opacity-100 transition-opacity"
                  style={{ color: "hsl(var(--destructive))" }}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
    </section>
  );
}

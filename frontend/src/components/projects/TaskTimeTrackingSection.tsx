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
  const effectiveActualHours = totalHours > 0 ? totalHours : (task.actual_hours ?? 0);
  const estimatedHours = task.estimated_hours ?? 0;
  const reportedPhysicalProgress = task.physical_progress_pct ?? task.progress_pct ?? (task.status === "done" || task.status === "completed" ? 100 : null);
  const physicalProgressImpact =
    estimatedHours > 0 && reportedPhysicalProgress === null
      ? Math.min(100, Math.round((effectiveActualHours / estimatedHours) * 100))
      : null;
  const earnedEffortProgress = Number.isFinite(reportedPhysicalProgress as number)
    ? Math.min(100, Math.max(0, reportedPhysicalProgress as number))
    : 0;
  const earnedHours = estimatedHours * earnedEffortProgress / 100;
  const laborEfficiencyIndex = effectiveActualHours > 0 && estimatedHours > 0
    ? earnedHours / effectiveActualHours
    : null;
  const estimateToCompleteHours = Math.max(0, estimatedHours - earnedHours);
  const estimateAtCompletionHours = effectiveActualHours + estimateToCompleteHours;
  const billableHours = logs.reduce((sum, log) => sum + (log.is_billable ? log.hours : 0), 0);
  const nonBillableHours = logs.reduce((sum, log) => sum + (log.is_billable ? 0 : log.hours), 0);
  const isOverEffort = effectiveActualHours > estimatedHours && estimatedHours > 0;

  return (
    <section aria-labelledby="task-time-tracking-heading" className="px-4 py-3 border-b border-[hsl(var(--border))]">
      <div className="flex items-center justify-between mb-2">
        <h3 id="task-time-tracking-heading" className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
          <Clock size={11} /> Tiempo Dedicado
          {effectiveActualHours > 0 && (
            <span
              className="ml-1 px-1.5 py-0.5 rounded font-bold font-mono text-2xs"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                color: "hsl(var(--primary))",
              }}
            >
              {effectiveActualHours.toFixed(2)}h
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

      {/* Sincronización automática con actual_hours vs estimated_hours e impacto en avance físico */}
      <div
        className="mb-2.5 rounded-lg border px-2.5 py-2 text-2xs space-y-1.5"
        style={{
          backgroundColor: "hsl(var(--surface-2))",
          borderColor: "hsl(var(--border))",
        }}
      >
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-[hsl(var(--muted-foreground))]">
            Sincronización EDT: <strong className="text-[hsl(var(--foreground))]">{effectiveActualHours.toFixed(2)}h reales</strong> / {estimatedHours.toFixed(2)}h estimadas
          </span>
          <span
            className="font-bold px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              color: "hsl(var(--primary))",
            }}
          >
            {reportedPhysicalProgress !== null ? `${reportedPhysicalProgress}%` : physicalProgressImpact !== null ? `${physicalProgressImpact}%` : "No reportado"}
          </span>
        </div>
        {estimatedHours > 0 && (
          <div
            className="w-full h-1.5 rounded-full overflow-hidden"
            style={{ backgroundColor: "hsl(var(--surface-1))" }}
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${physicalProgressImpact !== null ? Math.min(100, Math.max(0, physicalProgressImpact)) : 0}%`,
                backgroundColor: "hsl(var(--primary))",
              }}
            />
          </div>
        )}
      </div>

      {(estimatedHours > 0 || effectiveActualHours > 0) && (
        <section
          data-testid="task-time-pmi-effort-diagnosis"
          aria-label="Diagnóstico PMI de esfuerzo ganado"
          className="mb-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5"
        >
          <h4 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            Diagnóstico PMI de Esfuerzo Ganado
          </h4>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Horas Ganadas (EV_h)</p>
              <p data-testid="task-time-pmi-ev-hours" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{earnedHours.toFixed(2)}h</p>
            </div>
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Eficiencia Laboral (LEI)</p>
              <p data-testid="task-time-pmi-lei" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{laborEfficiencyIndex === null ? "—" : laborEfficiencyIndex.toFixed(2)}</p>
            </div>
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Esfuerzo Restante (ETC_h)</p>
              <p data-testid="task-time-pmi-etc-hours" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{estimateToCompleteHours.toFixed(2)}h</p>
            </div>
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Pronóstico a la Conclusión (EAC_h)</p>
              <p data-testid="task-time-pmi-eac-hours" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{estimateAtCompletionHours.toFixed(2)}h</p>
            </div>
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Horas Facturables (logs)</p>
              <p data-testid="task-time-pmi-billable-hours" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{billableHours.toFixed(2)}h</p>
            </div>
            <div className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-1.5">
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Horas No Facturables (logs)</p>
              <p data-testid="task-time-pmi-non-billable-hours" className="text-xs font-bold tabular-nums text-[hsl(var(--text-primary))]">{nonBillableHours.toFixed(2)}h</p>
            </div>
          </div>
          {isOverEffort && (
            <p
              role="alert"
              data-testid="task-time-pmi-over-effort-alert"
              className="mt-2 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] px-2.5 py-2 text-2xs font-semibold text-[hsl(var(--warning-text))]"
            >
              Exceso de Esfuerzo EDT: las horas reales superan las estimadas.
            </p>
          )}
        </section>
      )}

      {error && !showAddForm && (
        <p role="alert" className="mb-2 text-2xs" style={{ color: "hsl(var(--destructive))" }}>
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
              <label htmlFor="task-time-log-hours" className="block text-2xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
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
              <label className="flex items-center gap-1.5 cursor-pointer text-2xs font-medium">
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
            <label htmlFor="task-time-log-description" className="block text-2xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
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
            <p role="alert" className="text-2xs" style={{ color: "hsl(var(--destructive))" }}>
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
        <div role="status" aria-live="polite" className="py-2 text-center text-2xs" style={{ color: "hsl(var(--text-secondary))" }}>
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
                    className="px-1 py-0.5 rounded text-2xs font-semibold"
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
                  className="font-bold font-mono px-1.5 py-0.5 rounded text-2xs"
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

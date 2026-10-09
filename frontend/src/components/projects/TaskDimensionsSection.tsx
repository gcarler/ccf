"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/http";
import type {
  ProjectTaskRecord,
  TaskDimensionsDetail,
  ProjectExpense,
} from "@/types/projects";
import {
  Clock,
  Percent,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Layers,
  ChevronDown,
  ChevronUp,
  Save,
  CheckCircle2,
  Receipt,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

interface TaskDimensionsSectionProps {
  task: ProjectTaskRecord;
  token: string | null;
  onUpdate?: (updatedTask: ProjectTaskRecord) => void;
  onActivityCreated?: () => void;
}

export default function TaskDimensionsSection({
  task,
  token,
  onUpdate,
  onActivityCreated,
}: TaskDimensionsSectionProps) {
  const [dimensions, setDimensions] = useState<TaskDimensionsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  // Estados locales para edición rápida
  const [estimatedHours, setEstimatedHours] = useState<number>(
    task.estimated_hours ?? 0
  );
  const [physicalProgress, setPhysicalProgress] = useState<number>(
    task.physical_progress_pct ?? 0
  );
  const [savingField, setSavingField] = useState<string | null>(null);

  // Sincronizar estado local si cambia la prop task
  useEffect(() => {
    setEstimatedHours(task.estimated_hours ?? 0);
    setPhysicalProgress(task.physical_progress_pct ?? 0);
  }, [task.id, task.estimated_hours, task.physical_progress_pct]);

  // Cargar dimensiones y roll-up desde el backend
  const fetchDimensions = useCallback(async () => {
    if (!task?.id || !task?.project_id || !token) return;
    setLoading(true);
    try {
      const data = await apiFetch<TaskDimensionsDetail>(
        `/projects/${task.project_id}/tasks/${task.id}/dimensions`,
        { token }
      );
      if (data) {
        setDimensions(data);
        if (data.time) {
          setEstimatedHours(data.time.estimated_hours);
        }
        if (data.progress) {
          setPhysicalProgress(data.progress.physical_progress_pct);
        }
      }
    } catch {
      // Si el endpoint específico falla, usar valores del record
    } finally {
      setLoading(false);
    }
  }, [task?.id, task?.project_id, token]);

  useEffect(() => {
    void fetchDimensions();
  }, [fetchDimensions]);

  // Guardar cambios de Horas Estimadas
  const handleSaveHours = async () => {
    if (!token || !task) return;
    const hours = Math.max(0, Number(estimatedHours) || 0);
    setSavingField("hours");
    try {
      const updated = await apiFetch<ProjectTaskRecord>(
        `/projects/${task.project_id}/tasks/${task.id}`,
        {
          method: "PATCH",
          token,
          body: { estimated_hours: hours },
        }
      );
      if (updated) {
        onUpdate?.(updated);
        toast.success("Horas estimadas actualizadas");
        onActivityCreated?.();
        void fetchDimensions();
      }
    } catch {
      toast.error("No se pudo actualizar las horas estimadas");
    } finally {
      setSavingField(null);
    }
  };

  // Guardar cambios de Avance Físico
  const handleSaveProgress = async (newPct: number) => {
    if (!token || !task) return;
    const clamped = Math.max(0, Math.min(100, Math.round(newPct * 10) / 10));
    setPhysicalProgress(clamped);
    setSavingField("progress");
    try {
      const updated = await apiFetch<ProjectTaskRecord>(
        `/projects/${task.project_id}/tasks/${task.id}`,
        {
          method: "PATCH",
          token,
          body: { physical_progress_pct: clamped },
        }
      );
      if (updated) {
        onUpdate?.(updated);
        toast.success(`Avance físico: ${clamped}%`);
        onActivityCreated?.();
        void fetchDimensions();
      }
    } catch {
      toast.error("No se pudo actualizar el avance físico");
    } finally {
      setSavingField(null);
    }
  };

  const isLeaf = dimensions?.progress?.is_leaf ?? (!task.subtasks || task.subtasks.length === 0);
  const rolledUpProgress = dimensions?.progress?.rolled_up_progress_pct ?? physicalProgress;
  const actualCost = dimensions?.cost?.actual_cost ?? 0;
  const totalCost = dimensions?.cost?.total_cost ?? 0;
  const actualHours = dimensions?.time?.actual_hours ?? 0;
  const isOverworked = estimatedHours > 0 && actualHours > estimatedHours;
  const expensesList: ProjectExpense[] = dimensions?.expenses ?? [];

  return (
    <section className="px-4 py-3 border-b border-[hsl(var(--border))] space-y-3">
      {/* Header del acordeón */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors cursor-pointer"
        >
          <Sparkles size={12} className="text-[hsl(var(--primary))]" />
          <span>3 Dimensiones PMI (Control WBS)</span>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {loading && (
          <span className="text-2xs text-[hsl(var(--muted-foreground))] animate-pulse">
            Sincronizando...
          </span>
        )}
      </div>

      {expanded && (
        <div className="space-y-3 pt-1">
          {/* ── Dimensión 1: Tiempo y Esfuerzo ────────────────────────────── */}
          <div className="p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold flex items-center gap-1.5 text-[hsl(var(--foreground))]">
                <Clock size={13} className="text-[hsl(var(--primary))]" />
                1. Tiempo y Esfuerzo
              </span>
              {isOverworked && (
                <span className="inline-flex items-center gap-1 text-2xs font-semibold px-1.5 py-0.5 rounded bg-[hsl(var(--destructive))/0.15] text-[hsl(var(--destructive))] border border-[hsl(var(--destructive))/0.3]">
                  <AlertTriangle size={10} />
                  Desvío en horas
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {/* Horas Estimadas (editable) */}
              <div className="flex flex-col gap-1">
                <label
                  htmlFor={`task-est-hours-${task.id}`}
                  className="text-2xs text-[hsl(var(--muted-foreground))]"
                >
                  Horas Estimadas (Plan)
                </label>
                <div className="flex items-center gap-1">
                  <input
                    id={`task-est-hours-${task.id}`}
                    type="number"
                    min="0"
                    step="0.5"
                    value={estimatedHours}
                    onChange={(e) => setEstimatedHours(Number(e.target.value))}
                    onBlur={handleSaveHours}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.currentTarget.blur();
                      }
                    }}
                    className="w-full px-2 py-1 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                  />
                  <button
                    type="button"
                    onClick={handleSaveHours}
                    disabled={savingField === "hours"}
                    title="Guardar horas"
                    className="p-1 rounded bg-[hsl(var(--surface-3))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))] transition-colors cursor-pointer"
                  >
                    <Save size={12} />
                  </button>
                </div>
              </div>

              {/* Horas Reales (desde time-logs) */}
              <div className="flex flex-col gap-1">
                <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                  Horas Reales Registradas
                </span>
                <div className="px-2 py-1 text-xs font-semibold rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] flex items-center justify-between">
                  <span>{actualHours} h</span>
                  {estimatedHours > 0 && (
                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                      / {estimatedHours} h
                    </span>
                  )}
                </div>
              </div>
            </div>

            {dimensions?.time?.subtasks_estimated_hours &&
              dimensions.time.subtasks_estimated_hours > 0 ? (
                <div className="text-2xs text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                  <Layers size={11} />
                  <span>
                    Subtareas acumulan:{" "}
                    <strong>{dimensions.time.subtasks_estimated_hours} h</strong>{" "}
                    (Total paquete: {dimensions.time.total_estimated_hours} h)
                  </span>
                </div>
              ) : null}
          </div>

          {/* ── Dimensión 2: Avance Físico Continuo ──────────────────────── */}
          <div className="p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold flex items-center gap-1.5 text-[hsl(var(--foreground))]">
                <Percent size={13} className="text-[hsl(var(--primary))]" />
                2. Avance Físico Continuo
              </span>

              {isLeaf ? (
                <span className="text-2xs font-semibold px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] border border-[hsl(var(--border))]">
                  Paquete Hoja
                </span>
              ) : (
                <span className="text-2xs font-semibold px-1.5 py-0.5 rounded bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] border border-[hsl(var(--primary))/0.3] flex items-center gap-1">
                  <Layers size={10} />
                  Roll-Up EDT ({dimensions?.progress?.completed_subtasks_count ?? 0}/
                  {dimensions?.progress?.subtasks_count ?? 0} completas)
                </span>
              )}
            </div>

            {/* Valor numérico y barra de progreso */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <label
                  htmlFor={isLeaf ? `task-physical-progress-${task.id}` : undefined}
                  className="text-[hsl(var(--muted-foreground))]"
                >
                  {isLeaf ? "Avance físico asignado:" : "Avance físico consolidado:"}
                </label>
                <span className="font-bold text-[hsl(var(--foreground))]">
                  {isLeaf ? `${physicalProgress}%` : `${rolledUpProgress}%`}
                </span>
              </div>

              {/* Barra de progreso */}
              <div className="h-2 w-full rounded-full bg-[hsl(var(--surface-3))] overflow-hidden">
                <div
                  className={clsx(
                    "h-full transition-all duration-300 rounded-full",
                    (isLeaf ? physicalProgress : rolledUpProgress) >= 100
                      ? "bg-[hsl(var(--success))]"
                      : (isLeaf ? physicalProgress : rolledUpProgress) > 50
                      ? "bg-[hsl(var(--primary))]"
                      : "bg-[hsl(var(--warning))]"
                  )}
                  style={{
                    width: `${Math.min(
                      100,
                      isLeaf ? physicalProgress : rolledUpProgress
                    )}%`,
                  }}
                />
              </div>

              {/* Controles para paquete hoja: slider y presets */}
              {isLeaf && (
                <div className="pt-1 space-y-2">
                  <input
                    id={`task-physical-progress-${task.id}`}
                    name={`task-physical-progress-${task.id}`}
                    aria-label="Porcentaje de avance físico continuo"
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={physicalProgress}
                    onChange={(e) => setPhysicalProgress(Number(e.target.value))}
                    onMouseUp={(e) =>
                      handleSaveProgress(Number(e.currentTarget.value))
                    }
                    onTouchEnd={(e) =>
                      handleSaveProgress(Number(e.currentTarget.value))
                    }
                    className="w-full accent-[hsl(var(--primary))] cursor-pointer h-1.5 bg-[hsl(var(--surface-3))] rounded-lg"
                  />

                  {/* Presets rápidos */}
                  <div className="flex items-center justify-between gap-1">
                    {[0, 25, 50, 75, 100].map((preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => handleSaveProgress(preset)}
                        className={clsx(
                          "px-2 py-0.5 text-2xs font-medium rounded border transition-colors cursor-pointer",
                          physicalProgress === preset
                            ? "bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]"
                            : "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))]"
                        )}
                      >
                        {preset}%
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Dimensión 3: Costos e Imputación Financiera ──────────────── */}
          <div className="p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold flex items-center gap-1.5 text-[hsl(var(--foreground))]">
                <DollarSign size={13} className="text-[hsl(var(--primary))]" />
                3. Costos e Imputación Financiera
              </span>
              <span className="text-xs font-bold text-[hsl(var(--foreground))]">
                ${totalCost.toLocaleString("es-ES", { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-2xs">
              <div className="p-1.5 rounded bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                <span className="text-[hsl(var(--muted-foreground))] block">
                  Costo Real (AC):
                </span>
                <span className="font-semibold text-[hsl(var(--success))]">
                  ${actualCost.toLocaleString("es-ES", { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="p-1.5 rounded bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                <span className="text-[hsl(var(--muted-foreground))] block">
                  Planificado / Comprometido:
                </span>
                <span className="font-semibold text-[hsl(var(--warning))]">
                  $
                  {(
                    (dimensions?.cost?.planned_cost ?? 0) +
                    (dimensions?.cost?.committed_cost ?? 0)
                  ).toLocaleString("es-ES", { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* Listado de partidas asociadas */}
            {expensesList.length > 0 ? (
              <div className="space-y-1 pt-1">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                  <Receipt size={10} /> Gastos asignados ({expensesList.length})
                </span>
                <div className="max-h-32 overflow-y-auto space-y-1 pr-1">
                  {expensesList.map((exp) => (
                    <div
                      key={exp.id}
                      className="p-1.5 rounded text-2xs bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-between"
                    >
                      <div className="flex flex-col overflow-hidden mr-2">
                        <span className="font-medium text-[hsl(var(--foreground))] truncate">
                          {exp.description || exp.category}
                        </span>
                        <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                          {exp.date ? new Date(exp.date).toLocaleDateString("es-ES") : "Sin fecha"}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={clsx(
                            "px-1 py-0.5 rounded text-2xs font-semibold uppercase",
                            exp.status === "paid"
                              ? "bg-[hsl(var(--success))/0.15] text-[hsl(var(--success))]"
                              : exp.status === "committed"
                              ? "bg-[hsl(var(--warning))/0.15] text-[hsl(var(--warning))]"
                              : "bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]"
                          )}
                        >
                          {exp.status === "paid"
                            ? "Pagado"
                            : exp.status === "committed"
                            ? "Comprometido"
                            : "Plan"}
                        </span>
                        <span className="font-semibold text-[hsl(var(--foreground))]">
                          ${exp.amount.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-2xs text-[hsl(var(--muted-foreground))] italic text-center py-1">
                Sin gastos imputados directamente a este paquete de trabajo.
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

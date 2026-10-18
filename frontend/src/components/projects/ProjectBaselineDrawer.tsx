"use client";

import React, { useState, useEffect, useCallback, useId } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { ProjectBaseline } from "@/types/projects";
import { Layers, Clock, Plus, History, Sparkles, AlertTriangle, Send } from "lucide-react";
import clsx from "clsx";

interface Props {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onBaselineUpdated?: () => void;
  currentBac?: number | null;
}

export function ProjectBaselineDrawer({
  projectId,
  isOpen,
  onClose,
  onBaselineUpdated,
  currentBac,
}: Props) {
  const { token } = useAuth();
  const { addToast } = useToast();
  const formId = useId();

  const [loading, setLoading] = useState(false);
  const [latestBaseline, setLatestBaseline] = useState<ProjectBaseline | null>(null);
  const [baselinesHistory, setBaselinesHistory] = useState<ProjectBaseline[]>([]);
  const [latestLoadError, setLatestLoadError] = useState(false);
  const [historyLoadError, setHistoryLoadError] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [baselineName, setBaselineName] = useState("");
  const [baselineDescription, setBaselineDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [submittingCCB, setSubmittingCCB] = useState(false);
  const [ccbRequestSubmitted, setCcbRequestSubmitted] = useState(false);

  const fetchBaselineData = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      setLoading(true);
      setLatestLoadError(false);
      setHistoryLoadError(false);
      const [latestResult, historyResult] = await Promise.allSettled([
        apiFetch<ProjectBaseline | null>(`/projects/${projectId}/baseline`, { token }),
        apiFetch<ProjectBaseline[]>(`/projects/${projectId}/baselines`, { token }),
      ]);
      if (latestResult.status === "fulfilled") {
        setLatestBaseline(latestResult.value);
      } else {
        setLatestLoadError(true);
      }
      if (historyResult.status === "fulfilled") {
        setBaselinesHistory(Array.isArray(historyResult.value) ? historyResult.value : []);
      } else {
        setHistoryLoadError(true);
      }
      if (latestResult.status === "rejected" || historyResult.status === "rejected") {
        addToast({
          title: "No se pudo actualizar el historial de línea base",
          description: "Parte de la información no está disponible. Reintenta la consulta.",
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  }, [addToast, projectId, token]);

  useEffect(() => {
    if (isOpen) {
      fetchBaselineData();
      setShowCreateForm(false);
      setBaselineName("");
      setBaselineDescription("");
      setCcbRequestSubmitted(false);
    }
  }, [isOpen, fetchBaselineData]);

  const handleCreateBaseline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId) return;

    const name = baselineName.trim() || `Línea Base ${baselinesHistory.length + 1}`;

    try {
      setSaving(true);
      await apiFetch(`/projects/${projectId}/baseline`, {
        method: "POST",
        token,
        body: {
          name,
          description: baselineDescription.trim() || null,
        },
      });

      addToast({
        title: "Línea Base congelada",
        description: `Se registró '${name}' como instantánea planificada del proyecto.`,
      });

      await fetchBaselineData();
      setShowCreateForm(false);
      setBaselineName("");
      setBaselineDescription("");
      onBaselineUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al congelar línea base";
      addToast({
        title: "Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const totalVariance = latestBaseline?.total_variance_days ?? 0;
  const comparisons = latestBaseline?.comparisons || [];
  const baselineBac =
    latestBaseline?.snapshot_data?.bac ??
    latestBaseline?.snapshot_data?.budget_allocated ??
    null;
  const bacDelta =
    baselineBac !== null && currentBac !== undefined && currentBac !== null
      ? currentBac - baselineBac
      : null;
  const frozenScopeCount = latestBaseline?.snapshot_data?.tasks_count ?? comparisons.length;
  const scopeDelta = comparisons.length - frozenScopeCount;
  const delayedTasksCount = comparisons.filter((comparison) => comparison.variance_days > 0).length;
  const onTimeOrAheadTasksCount = comparisons.length - delayedTasksCount;
  const scopeDeviation = scopeDelta !== 0;
  const scheduleDeviation = totalVariance > 0;
  const costDeviation = bacDelta !== null && bacDelta !== 0;
  const hasPMBDeviation = Boolean(latestBaseline && (scopeDeviation || scheduleDeviation || costDeviation));

  const handleRequestRebaseline = async () => {
    if (!token || !projectId || !latestBaseline || !hasPMBDeviation || submittingCCB) return;

    const scopeImpact = scopeDelta === 0
      ? `Sin diferencia: ${frozenScopeCount} paquetes congelados y ${comparisons.length} tareas auditadas.`
      : `${scopeDelta > 0 ? "Adición" : "Eliminación"} de ${Math.abs(scopeDelta)} entregable(s): ${frozenScopeCount} paquetes congelados frente a ${comparisons.length} tareas auditadas.`;
    const costDeltaDescription = bacDelta === null
      ? "BAC delta no disponible."
      : `delta BAC ${bacDelta > 0 ? "+" : ""}$${bacDelta.toLocaleString("es-CO")}.`;
    const description = [
      `Desvío acumulado del cronograma: ${totalVariance} días (${delayedTasksCount} tareas con atraso; ${onTimeOrAheadTasksCount} en fecha o adelantadas).`,
      `Impacto en alcance: ${scopeImpact}`,
      `BAC congelado: ${baselineBac === null ? "no disponible" : `$${baselineBac.toLocaleString("es-CO")}`}; BAC actual: ${currentBac === undefined || currentBac === null ? "no disponible" : `$${currentBac.toLocaleString("es-CO")}`}; ${costDeltaDescription}`,
    ].join(" ");

    try {
      setSubmittingCCB(true);
      await apiFetch(`/projects/${projectId}/change-requests`, {
        method: "POST",
        token,
        body: {
          title: "Solicitud de Re-baseline PMB por desviación detectada",
          description,
          justification: "Alineación formal de la PMB bajo Control Integrado de Cambios PMI",
          change_type: "integrated",
          cost_impact_delta: Math.max(0, bacDelta ?? 0),
          scope_impact_summary: scopeImpact,
          scope_impact: scopeImpact,
          schedule_impact_days: Math.max(0, totalVariance),
          cost_impact: Math.max(0, bacDelta ?? 0),
        },
      });

      addToast({
        title: "Solicitud radicada ante el CCB",
        description: "La PMB aprobada permanece vigente hasta que el Comité de Control de Cambios apruebe la solicitud.",
      });
      setCcbRequestSubmitted(true);
    } catch (error: unknown) {
      addToast({
        title: "No se pudo radicar la solicitud",
        description: error instanceof Error ? error.message : "Intenta nuevamente más tarde.",
        variant: "destructive",
      });
    } finally {
      setSubmittingCCB(false);
    }
  };

  return (
    <RightPanel
      title="Línea Base y Control de Varianza (Gantt)"
      open={isOpen}
      onClose={onClose}
      width={520}
    >
      <div className="flex flex-col h-full space-y-5 p-5 text-[hsl(var(--foreground))] overflow-y-auto">
        {(latestLoadError || historyLoadError) && (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[hsl(var(--destructive))]/40 bg-[hsl(var(--destructive))]/10 p-3"
            role="alert"
            aria-live="assertive"
          >
            <p className="text-xs text-[hsl(var(--destructive))]">
              {latestLoadError && historyLoadError
                ? "No se pudo consultar la línea base ni su historial."
                : latestLoadError
                  ? "No se pudo confirmar si existe una línea base."
                  : "No se pudo cargar el historial de líneas base."}
            </p>
            <button
              type="button"
              onClick={() => void fetchBaselineData()}
              disabled={loading}
              className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-2xs font-bold text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3))] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Consultando..." : "Reintentar carga"}
            </button>
          </div>
        )}

        {/* Banner de Concepto */}
        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-start gap-3 shadow-xs">
          <div className="p-2.5 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] shrink-0">
            <Layers size={20} />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
              Instantánea de Cronograma (Baseline)
            </h4>
            <p className="text-2xs text-[hsl(var(--muted-foreground))] mt-1 leading-relaxed">
              Congela las fechas planificadas para comparar en tiempo real contra los avances reales en la vista Gantt y detectar desvíos temporales.
            </p>
          </div>
        </div>

        {/* Resumen de Varianza General */}
        {latestBaseline ? (
          <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] shadow-xs space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-2xs uppercase font-extrabold tracking-widest text-[hsl(var(--muted-foreground))]">
                    Línea Base Activa
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-2xs font-extrabold uppercase border bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]">
                    Activa en Motor EVM
                  </span>
                </div>
                <h3 className="text-sm font-extrabold text-[hsl(var(--foreground))] mt-0.5">
                  {latestBaseline.name}
                </h3>
              </div>
              <span
                className={clsx(
                  "px-2.5 py-1 rounded-full text-2xs font-extrabold tracking-wider uppercase border",
                  totalVariance > 0
                    ? "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]"
                    : "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                )}
              >
                {totalVariance > 0 ? `+${totalVariance}d Desvío Acumulado` : "A Tiempo / Sin Desvíos"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-[hsl(var(--border))]/50 text-2xs">
              <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                <span className="text-2xs text-[hsl(var(--muted-foreground))] block font-medium">Congelado el:</span>
                <span className="font-bold text-[hsl(var(--foreground))]">
                  {new Date(latestBaseline.created_at).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                <span className="text-2xs text-[hsl(var(--muted-foreground))] block font-medium">Tareas Auditadas:</span>
                <span className="font-bold text-[hsl(var(--foreground))]">
                  {comparisons.length} tareas
                </span>
              </div>
            </div>

            {(baselineBac !== null || (currentBac !== undefined && currentBac !== null)) && (
              <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-[hsl(var(--border))]/50 text-2xs">
                <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                  <span className="text-2xs text-[hsl(var(--muted-foreground))] block font-medium">
                    BAC Línea Base (Congelado):
                  </span>
                  <span className="font-bold text-[hsl(var(--foreground))]">
                    ${(baselineBac ?? 0).toLocaleString("es-CO")}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                  <span className="text-2xs text-[hsl(var(--muted-foreground))] block font-medium">
                    {currentBac !== undefined && currentBac !== null ? "BAC Actual vs Línea Base:" : "Avance al Congelar:"}
                  </span>
                  {currentBac !== undefined && currentBac !== null ? (
                    <span
                      className={clsx(
                        "font-bold",
                        bacDelta && bacDelta > 0
                          ? "text-[hsl(var(--warning))]"
                          : "text-[hsl(var(--success))]"
                      )}
                    >
                      ${currentBac.toLocaleString("es-CO")}
                      {bacDelta !== null && bacDelta !== 0
                        ? ` (${bacDelta > 0 ? "+" : "-"}$${Math.abs(bacDelta).toLocaleString("es-CO")})`
                        : " (Sin cambio)"}
                    </span>
                  ) : (
                    <span className="font-bold text-[hsl(var(--foreground))]">
                      {latestBaseline.snapshot_data?.progress_percentage ?? 0}%
                    </span>
                  )}
                </div>
              </div>
            )}

            <section
              aria-labelledby="pmb-integrity-title"
              className="rounded-xl border p-3.5 space-y-3"
              style={{ backgroundColor: "hsl(var(--surface-2))", borderColor: "hsl(var(--border))" }}
            >
              <div className="flex items-start gap-2.5">
                <Layers size={17} className="mt-0.5 shrink-0 text-[hsl(var(--primary))]" />
                <div>
                  <h4 id="pmb-integrity-title" className="text-xs font-extrabold text-[hsl(var(--foreground))]">
                    Diagnóstico de Integridad PMB (Alcance × Cronograma × Costo — PMI Vol. 3 & 6)
                  </h4>
                  <p className="mt-1 text-2xs text-[hsl(var(--muted-foreground))]">
                    Una línea base aprobada solo puede cambiarse mediante control integrado de cambios.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="rounded-lg border p-2.5" style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--border))" }}>
                  <p className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">Alcance · Scope</p>
                  <p className="mt-1 text-xs font-semibold text-[hsl(var(--foreground))]">{frozenScopeCount} congelados · {comparisons.length} auditados</p>
                  <p className={clsx("mt-1 text-2xs font-bold", scopeDeviation ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--success))]")}>
                    {scopeDeviation ? `${scopeDelta > 0 ? "+" : ""}${scopeDelta} entregable(s) · Scope Creep` : "Sin variación de alcance"}
                  </p>
                </div>
                <div className="rounded-lg border p-2.5" style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--border))" }}>
                  <p className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">Cronograma · Schedule</p>
                  <p className="mt-1 text-xs font-semibold text-[hsl(var(--foreground))]">Desvío acumulado: {totalVariance} días</p>
                  <p className="mt-1 text-2xs text-[hsl(var(--muted-foreground))]">{delayedTasksCount} con atraso · {onTimeOrAheadTasksCount} en fecha o adelantadas</p>
                </div>
                <div className="rounded-lg border p-2.5" style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--border))" }}>
                  <p className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">Costo · BAC</p>
                  <p className="mt-1 text-xs font-semibold text-[hsl(var(--foreground))]">Base: {baselineBac === null ? "—" : `$${baselineBac.toLocaleString("es-CO")}`}</p>
                  <p className="mt-1 text-2xs text-[hsl(var(--muted-foreground))]">Actual: {currentBac === undefined || currentBac === null ? "—" : `$${currentBac.toLocaleString("es-CO")}`}</p>
                  <p className={clsx("mt-1 text-2xs font-bold", costDeviation ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--success))]")}>
                    Delta: {bacDelta === null ? "No disponible" : `${bacDelta > 0 ? "+" : ""}$${bacDelta.toLocaleString("es-CO")}`}
                  </p>
                </div>
              </div>

              {hasPMBDeviation && (
                <div
                  role="alert"
                  className="space-y-2 rounded-lg border p-3"
                  style={{ backgroundColor: "hsl(var(--warning-muted))", borderColor: "hsl(var(--warning) / 0.35)" }}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[hsl(var(--warning))]" />
                    <div>
                      <p className="text-xs font-extrabold text-[hsl(var(--warning-text))]">Desviación sobre la PMB Detectada — Requiere Control Integrado de Cambios (CCB)</p>
                      <p className="mt-1 text-2xs text-[hsl(var(--text-primary))]">
                        Ninguna línea base aprobada debe alterarse sin una Solicitud de Cambio (CR) aprobada por el CCB.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleRequestRebaseline()}
                    disabled={submittingCCB || ccbRequestSubmitted}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
                    style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--warning) / 0.45)", color: "hsl(var(--text-primary))" }}
                  >
                    <Send size={14} />
                    {submittingCCB
                      ? "Radicando solicitud..."
                      : ccbRequestSubmitted
                      ? "Solicitud radicada ante el CCB"
                      : "Radicar Solicitud de Re-baseline al CCB"}
                  </button>
                </div>
              )}
            </section>
          </div>
        ) : loading ? (
          <div
            className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 p-5"
            role="status"
            aria-label="Cargando línea base"
          >
            <div className="h-4 w-2/5 animate-pulse rounded bg-[hsl(var(--surface-3))]" />
            <div className="h-3 w-4/5 animate-pulse rounded bg-[hsl(var(--surface-3))]" />
          </div>
        ) : !latestLoadError ? (
            <div className="p-5 text-center rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 space-y-2">
              <Clock className="mx-auto text-[hsl(var(--muted-foreground))]" size={28} />
              <p className="text-xs font-bold text-[hsl(var(--foreground))]">Sin Línea Base Registrada</p>
              <p className="text-2xs text-[hsl(var(--muted-foreground))] max-w-xs mx-auto">
                No has congelado aún una versión planificada del cronograma para este proyecto.
              </p>
            </div>
        ) : null}

        {/* Botón / Formulario para Congelar Nueva Línea Base */}
        {!showCreateForm ? (
          <button
            onClick={() => setShowCreateForm(true)}
            className="w-full py-2.5 px-4 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider hover:opacity-90 active:scale-98 transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            <Plus size={14} /> Congelar Nueva Línea Base
          </button>
        ) : (
          <form
            onSubmit={handleCreateBaseline}
            className="p-4 rounded-xl border border-[hsl(var(--primary))]/30 bg-[hsl(var(--surface-2))] space-y-3.5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                <Sparkles size={14} /> Nueva Instantánea Planificada
              </span>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="text-2xs font-bold text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] cursor-pointer"
              >
                Cancelar
              </button>
            </div>

            <div className="space-y-1">
              <label htmlFor={`${formId}-name`} className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Nombre de la Línea Base
              </label>
              <input
                id={`${formId}-name`}
                type="text"
                value={baselineName}
                onChange={(e) => setBaselineName(e.target.value)}
                placeholder={`Línea Base ${baselinesHistory.length + 1}`}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>

            <div className="space-y-1">
              <label htmlFor={`${formId}-description`} className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Descripción / Motivo del Congelamiento (Opcional)
              </label>
              <textarea
                id={`${formId}-description`}
                value={baselineDescription}
                onChange={(e) => setBaselineDescription(e.target.value)}
                placeholder="Ej: Aprobación del comité ministerial para inicio de obra..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-2 px-3 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 cursor-pointer"
            >
              {saving ? "Guardando instantánea..." : "Confirmar y Congelar Cronograma"}
            </button>
          </form>
        )}

        {/* Tabla Comparativa de Tareas (Planificado vs Real) */}
        {comparisons.length > 0 && (
          <div className="space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center justify-between">
              <span>Desglose de Varianza por Tarea</span>
              <span className="text-2xs font-semibold lowercase">
                {comparisons.filter((c) => c.variance_days > 0).length} con retraso
              </span>
            </h4>

            <div className="space-y-2">
              {comparisons.map((c) => {
                const isDelayed = c.variance_days > 0;
                const isAhead = c.variance_days < 0;

                const baseDueStr = c.baseline_due ? c.baseline_due.slice(0, 10) : "S/F";
                const curDueStr = c.current_due ? c.current_due.slice(0, 10) : "S/F";

                return (
                  <div
                    key={c.task_id}
                    className="p-3 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--border))]/80 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-[hsl(var(--foreground))] truncate">
                        {c.title}
                      </span>
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-2xs font-extrabold tracking-tight shrink-0",
                          isDelayed
                            ? "bg-[hsl(var(--destructive))]/15 text-[hsl(var(--destructive))]"
                            : isAhead
                            ? "bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))]"
                            : "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]"
                        )}
                      >
                        {isDelayed
                          ? `+${c.variance_days}d Retraso`
                          : isAhead
                          ? `${c.variance_days}d Adelanto`
                          : "A Tiempo"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-2xs text-[hsl(var(--muted-foreground))]">
                      <div>
                        <span className="text-2xs font-semibold block uppercase">Línea Base:</span>
                        <span className="font-medium text-[hsl(var(--foreground))]">
                          {baseDueStr} ({c.baseline_duration}d)
                        </span>
                      </div>
                      <div>
                        <span className="text-2xs font-semibold block uppercase">Cronograma Real:</span>
                        <span className="font-medium text-[hsl(var(--foreground))]">
                          {curDueStr} ({c.current_duration}d)
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Historial de Instantáneas Anteriores */}
        {historyLoadError && baselinesHistory.length === 0 && (
          <p className="text-2xs text-[hsl(var(--destructive))]" role="status">
            El historial no está disponible hasta que se recupere la consulta.
          </p>
        )}

        {baselinesHistory.length > 0 && (
          <div className="pt-3 border-t border-[hsl(var(--border))] space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
              <History size={14} /> Historial de Instantáneas ({baselinesHistory.length})
            </h4>
            <div className="space-y-1.5">
              {baselinesHistory.map((b, idx) => {
                const isActiveInEvm = latestBaseline ? b.id === latestBaseline.id : idx === 0;
                const snapBac = b.snapshot_data?.bac ?? b.snapshot_data?.budget_allocated;
                return (
                  <div
                    key={b.id}
                    className={clsx(
                      "px-3 py-2 rounded-lg border flex items-center justify-between gap-2 text-2xs",
                      isActiveInEvm
                        ? "bg-[hsl(var(--primary))]/5 border-[hsl(var(--primary))]/30"
                        : "bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]"
                    )}
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-[hsl(var(--foreground))]">{b.name}</span>
                      {isActiveInEvm && (
                        <span className="px-1.5 py-0.5 rounded text-2xs font-extrabold uppercase bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))]">
                          EVM Activa
                        </span>
                      )}
                      {snapBac !== undefined && snapBac !== null && (
                        <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                          BAC: ${snapBac.toLocaleString("es-CO")}
                        </span>
                      )}
                    </div>
                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                      {new Date(b.created_at).toLocaleDateString("es-ES", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </RightPanel>
  );
}

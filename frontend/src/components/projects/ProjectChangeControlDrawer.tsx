"use client";

import React, { useCallback, useEffect, useState } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { CcbAndQualitySummary } from "@/types/projects";
import {
  CheckCircle2,
  Clock,
  FileText,
  GitCommitHorizontal,
  Gavel,
  Plus,
  RefreshCw,
  XCircle,
} from "lucide-react";
import clsx from "clsx";

interface ProjectChangeControlDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

interface ChangeRequestRecord {
  id: string;
  project_id: string;
  title: string;
  justification: string;
  change_type: string;
  cost_impact_delta: number;
  schedule_impact_days: number;
  scope_impact_summary: string | null;
  status: string;
  requested_by: string;
  reviewed_by: string | null;
  review_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
  resulting_baseline_id: string | null;
}

interface ChangeRequestSummary {
  pending_ccb: number;
  approved: number;
  rejected: number;
  approved_cost_impact_total: number;
  approved_schedule_impact_days_total: number;
  pending_cost_impact_total: number;
  pending_schedule_impact_days_total: number;
}

export interface ChangeRequestListResponse {
  project_id: string;
  items: ChangeRequestRecord[];
  summary: ChangeRequestSummary;
}

const CHANGE_TYPES = [
  { id: "scope", label: "Alcance" },
  { id: "schedule", label: "Cronograma" },
  { id: "budget", label: "Presupuesto" },
  { id: "integrated", label: "Integrado" },
];

const STATUS_META: Record<string, { label: string; icon: React.ElementType; className: string }> = {
  pending_ccb: {
    label: "Pendiente CCB",
    icon: Clock,
    className: "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning-text))] border-[hsl(var(--warning))]/40",
  },
  approved: {
    label: "Aprobado",
    icon: CheckCircle2,
    className: "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] border-[hsl(var(--success))]/40",
  },
  rejected: {
    label: "Rechazado",
    icon: XCircle,
    className: "bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))] border-[hsl(var(--destructive))]/40",
  },
};

const formatMoney = (value: number): string =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);

export function ProjectChangeControlDrawer({ projectId, isOpen, onClose }: ProjectChangeControlDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [data, setData] = useState<ChangeRequestListResponse | null>(null);
  const [qualitySummary, setQualitySummary] = useState<CcbAndQualitySummary | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);

  // Formulario de nueva Solicitud de Cambio Formal (análisis de Triple Restricción)
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [justification, setJustification] = useState("");
  const [changeType, setChangeType] = useState<"scope" | "schedule" | "budget" | "integrated">("integrated");
  const [costImpactDelta, setCostImpactDelta] = useState("0");
  const [scheduleImpactDays, setScheduleImpactDays] = useState("0");
  const [scopeImpactSummary, setScopeImpactSummary] = useState("");
  // Dictamen del Comité
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});

  const loadChangeRequests = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setLoadError(null);
    // Carga en paralelo: el fallo del resumen de calidad NO debe romper el listado de CRs.
    const [changeRequestsResult, qualityResult] = await Promise.allSettled([
      apiFetch<ChangeRequestListResponse>(`/projects/${projectId}/change-requests`, {
        token,
      }),
      apiFetch<CcbAndQualitySummary>(`/projects/${projectId}/quality-summary`, { token }),
    ]);
    try {
      if (changeRequestsResult.status === "fulfilled") {
        setData(changeRequestsResult.value);
      } else {
        setLoadError("No se pudo cargar el Control de Cambios del proyecto.");
      }
      setQualitySummary(qualityResult.status === "fulfilled" ? qualityResult.value : null);
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    if (isOpen) {
      void loadChangeRequests();
    }
  }, [isOpen, loadChangeRequests]);

  const resetForm = () => {
    setTitle("");
    setJustification("");
    setChangeType("integrated");
    setCostImpactDelta("0");
    setScheduleImpactDays("0");
    setScopeImpactSummary("");
  };

  const handleCreateCr = async () => {
    if (!token || !title.trim() || !justification.trim()) return;
    setSubmitting(true);
    try {
      await apiFetch(`/projects/${projectId}/change-requests`, {
        token,
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          justification: justification.trim(),
          change_type: changeType,
          cost_impact_delta: Number(costImpactDelta) || 0,
          schedule_impact_days: Number(scheduleImpactDays) || 0,
          scope_impact_summary: scopeImpactSummary.trim() || null,
        }),
      });
      addToast({
        title: "Solicitud registrada",
        message: "La Solicitud de Cambio Formal quedó pendiente del Comité (trazabilidad inmutable).",
        type: "success",
      });
      resetForm();
      setShowForm(false);
      await loadChangeRequests();
    } catch {
      addToast({
        title: "Error al registrar",
        message: "No se pudo crear la Solicitud de Cambio Formal.",
        type: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDecide = async (crId: string, decision: "approved" | "rejected") => {
    if (!token) return;
    const reviewNotes = (decisionNotes[crId] || "").trim();
    if (!reviewNotes) {
      addToast({
        title: "Acta requerida",
        message: "El dictamen del Comité exige la justificación técnica en el acta.",
        type: "warning",
      });
      return;
    }
    setDecidingId(crId);
    try {
      await apiFetch(`/projects/${projectId}/change-requests/${crId}/decide`, {
        token,
        method: "POST",
        body: JSON.stringify({ decision, review_notes: reviewNotes }),
      });
      addToast({
        title: decision === "approved" ? "Cambio aprobado" : "Cambio rechazado",
        message:
          decision === "approved"
            ? "Se aplicó el impacto y se generó el Re-baseline automático de la línea base."
            : "El BAC y el cronograma se mantienen; el acta registró la justificación técnica.",
        type: decision === "approved" ? "success" : "info",
      });
      await loadChangeRequests();
    } catch {
      addToast({
        title: "Error en el dictamen",
        message: "No se pudo registrar el dictamen del Comité de Control de Cambios.",
        type: "error",
      });
    } finally {
      setDecidingId(null);
    }
  };

  const summary = data?.summary;

  return (
    <RightPanel
      title="Control Integrado de Cambios (CCB)"
      subtitle="PMI Vol. 6 §5 — Dictamen formal del Comité · PMI Vol. 6 §4 — Criterios de Aceptación"
      open={isOpen}
      onClose={onClose}
      width={560}
    >
      <div className="flex flex-col h-full space-y-4">
        {loadError && (
          <div
            className="flex items-center justify-between gap-3 rounded-xl border border-[hsl(var(--destructive))]/40 bg-[hsl(var(--destructive))]/10 p-3"
            role="alert"
          >
            <p className="text-xs text-[hsl(var(--destructive))]">{loadError}</p>
            <button
              onClick={() => void loadChangeRequests()}
              className="shrink-0 rounded-lg bg-[hsl(var(--primary))] p-1.5 text-[hsl(var(--primary-foreground))]"
              aria-label="Reintentar carga del control de cambios"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        )}

        {/* Resumen de Control de Cambios */}
        <div className="grid grid-cols-3 gap-2" data-testid="ccb-summary">
          {[
            {
              label: "Pendientes CCB",
              value: summary ? String(summary.pending_ccb) : "—",
              extra: summary
                ? `${formatMoney(summary.pending_cost_impact_total)} · ${summary.pending_schedule_impact_days_total} d`
                : undefined,
              className: "border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10",
              valueClass: "text-[hsl(var(--warning-text))]",
            },
            {
              label: "Aprobados",
              value: summary ? String(summary.approved) : "—",
              extra: summary
                ? `${formatMoney(summary.approved_cost_impact_total)} · ${summary.approved_schedule_impact_days_total} d`
                : undefined,
              className: "border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10",
              valueClass: "text-[hsl(var(--success))]",
            },
            {
              label: "Rechazados",
              value: summary ? String(summary.rejected) : "—",
              extra: undefined,
              className: "border-[hsl(var(--destructive))]/40 bg-[hsl(var(--destructive))]/10",
              valueClass: "text-[hsl(var(--destructive))]",
            },
          ].map((card) => (
            <div key={card.label} className={clsx("rounded-xl border p-3", card.className)}>
              <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                {card.label}
              </p>
              <p className={clsx("text-xl font-black", card.valueClass)}>{card.value}</p>
              {card.extra && <p className="text-2xs text-[hsl(var(--text-secondary))]">{card.extra}</p>}
            </div>
          ))}
        </div>

        {/* Auditoría de Calidad PMI — DoD 4/4 y Costo de Calidad (CoQ, Regla 1:10:100) */}
        {qualitySummary && (
          <div
            data-testid="quality-audit-panel"
            className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 space-y-2"
          >
            <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              Auditoría de Calidad PMI: Definition of Done (DoD 4/4) y Costo de Calidad (CoQ — Regla 1:10:100)
            </p>

            <div className="flex flex-wrap items-center justify-between gap-1 text-xs">
              <span className="text-[hsl(var(--text-secondary))]">Cobertura DoD de paquetes de trabajo</span>
              <span className="font-bold text-[hsl(var(--text-primary))]">
                {qualitySummary.dod_signed_off_count}/{qualitySummary.total_leaf_tasks} firmados ({qualitySummary.dod_completion_rate_pct}%) · {qualitySummary.dod_all_four_met_count} con 4/4
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10 p-2">
                <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--success))]">
                  Costo de Conformidad
                </p>
                <p className="text-xs font-black text-[hsl(var(--text-primary))]">
                  {formatMoney(qualitySummary.total_cost_of_conformance)}
                </p>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  {qualitySummary.coq_conformance_ratio_pct}% del CoQ · Prevención + Evaluación
                </p>
              </div>
              <div className="rounded-lg border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 p-2">
                <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--warning-text))]">
                  Costo de No Conformidad
                </p>
                <p className="text-xs font-black text-[hsl(var(--text-primary))]">
                  {formatMoney(qualitySummary.total_cost_of_non_conformance)}
                </p>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Fallas internas (retrabajo) + fallas externas
                </p>
              </div>
            </div>

            {qualitySummary.total_cost_of_non_conformance > qualitySummary.total_cost_of_conformance ? (
              <p
                role="alert"
                data-testid="coq-diagnosis"
                className="rounded-lg bg-[hsl(var(--destructive))]/10 px-2 py-1.5 text-2xs font-bold text-[hsl(var(--destructive))]"
              >
                Alerta CoQ: El costo de retrabajo/fallas supera la inversión en prevención y evaluación
              </p>
            ) : (
              <p
                role="status"
                data-testid="coq-diagnosis"
                className="rounded-lg bg-[hsl(var(--success))]/10 px-2 py-1.5 text-2xs font-bold text-[hsl(var(--success))]"
              >
                Óptimo CoQ: Inversión preventiva saludable
              </p>
            )}
          </div>
        )}

        <button
          onClick={() => setShowForm((prev) => !prev)}
          className="flex items-center justify-center gap-1.5 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-xs font-bold text-[hsl(var(--primary-foreground))] shadow-sm transition-all hover:opacity-90"
        >
          <Plus size={14} />
          <span>{showForm ? "Cancelar nueva solicitud" : "Nueva Solicitud de Cambio"}</span>
        </button>

        {showForm && (
          <form
            data-testid="new-cr-form"
            className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4"
            onSubmit={(e) => {
              e.preventDefault();
              void handleCreateCr();
            }}
          >
            <p className="text-2xs rounded-md bg-[hsl(var(--info))]/10 p-2 font-semibold text-[hsl(var(--info))]">
              Análisis de impactos en la Triple Restricción (Alcance · Cronograma · Costo). La solicitud queda
              con trazabilidad inmutable.
            </p>

            <div>
              <label htmlFor="cr-title" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                Título de la solicitud *
              </label>
              <input
                id="cr-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
                required
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
                placeholder="p. ej., Ampliación de reportería del EDT 3"
              />
            </div>

            <div>
              <label htmlFor="cr-justification" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                Justificación *
              </label>
              <textarea
                id="cr-justification"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                required
                rows={3}
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
                placeholder="Justificación del cambio registrada en el acta"
              />
            </div>

            <div>
              <label htmlFor="cr-type" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                Tipo de cambio
              </label>
              <select
                id="cr-type"
                value={changeType}
                onChange={(e) => setChangeType(e.target.value as "scope" | "schedule" | "budget" | "integrated")}
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
              >
                {CHANGE_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="cr-cost" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                  Impacto en costo (Δ$)
                </label>
                <input
                  id="cr-cost"
                  type="number"
                  step="any"
                  value={costImpactDelta}
                  onChange={(e) => setCostImpactDelta(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
                />
              </div>
              <div>
                <label htmlFor="cr-days" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                  Impacto en cronograma (Δdías)
                </label>
                <input
                  id="cr-days"
                  type="number"
                  value={scheduleImpactDays}
                  onChange={(e) => setScheduleImpactDays(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
                />
              </div>
            </div>

            <div>
              <label htmlFor="cr-scope" className="text-xs font-bold text-[hsl(var(--text-primary))]">
                Resumen de impacto en alcance (opcional)
              </label>
              <textarea
                id="cr-scope"
                value={scopeImpactSummary}
                onChange={(e) => setScopeImpactSummary(e.target.value)}
                rows={2}
                className="mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))]"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !title.trim() || !justification.trim()}
              className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-xs font-bold text-[hsl(var(--primary-foreground))] shadow-sm disabled:opacity-50"
            >
              {submitting ? "Registrando…" : "Registrar solicitud pendiente del Comité"}
            </button>
          </form>
        )}

        {/* Lista de solicitudes */}
        <div className="flex-1 space-y-3 overflow-y-auto pr-1" data-testid="cr-list">
          {loading && !data ? (
            <div className="space-y-2" role="status" aria-label="Cargando solicitudes">
              {[0, 1].map((i) => (
                <div
                  key={i}
                  className="h-20 animate-pulse rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
                />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[hsl(var(--border))] p-6 text-center">
              <FileText size={28} className="mx-auto text-[hsl(var(--text-secondary))]" />
              <p className="mt-2 text-xs font-semibold text-[hsl(var(--text-secondary))]">
                Sin solicitudes de cambio registradas. Todo cambio de alcance, tiempo o costo debe formalizarse
                ante el Comité (PMI Vol. 6 §5).
              </p>
            </div>
          ) : (
            data.items.map((cr) => {
              const meta = STATUS_META[cr.status] ?? STATUS_META.pending_ccb;
              const StatusIcon = meta.icon;
              return (
                <article
                  key={cr.id}
                  className={clsx("rounded-xl border p-3", meta.className)}
                  data-testid={`cr-card-${cr.id}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="truncate text-xs font-black text-[hsl(var(--text-primary))]">{cr.title}</h4>
                      <p className="mt-0.5 line-clamp-2 text-2xs text-[hsl(var(--text-secondary))]">
                        {cr.justification}
                      </p>
                    </div>
                    <span className="flex shrink-0 items-center gap-1 text-2xs font-black uppercase tracking-wider">
                      <StatusIcon size={12} />
                      {meta.label}
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap gap-2 text-2xs font-bold text-[hsl(var(--text-secondary))]">
                    <span className="inline-flex items-center gap-1">
                      <GitCommitHorizontal size={12} />
                      {cr.change_type}
                    </span>
                    <span>
                      Δ$ {formatMoney(cr.cost_impact_delta)}
                    </span>
                    <span>
                      Δ {cr.schedule_impact_days} días
                    </span>
                  </div>

                  {cr.status === "pending_ccb" && (
                    <div className="mt-3 space-y-2 border-t border-[hsl(var(--border))] pt-2">
                      <label htmlFor={`cr-notes-${cr.id}`} className="sr-only">
                        Acta del dictamen para {cr.title}
                      </label>
                      <textarea
                        id={`cr-notes-${cr.id}`}
                        rows={2}
                        value={decisionNotes[cr.id] || ""}
                        onChange={(e) =>
                          setDecisionNotes((prev) => ({ ...prev, [cr.id]: e.target.value }))
                        }
                        placeholder="Acta con la justificación técnica del dictamen"
                        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-2xs text-[hsl(var(--text-primary))]"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => void handleDecide(cr.id, "approved")}
                          disabled={decidingId === cr.id}
                          className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-[hsl(var(--success))] px-3 py-1.5 text-2xs font-bold text-white disabled:opacity-50"
                        >
                          <Gavel size={12} />
                          Aprobar con Re-baseline
                        </button>
                        <button
                          onClick={() => void handleDecide(cr.id, "rejected")}
                          disabled={decidingId === cr.id}
                          className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-[hsl(var(--destructive))] px-3 py-1.5 text-2xs font-bold text-white disabled:opacity-50"
                        >
                          <XCircle size={12} />
                          Rechazar
                        </button>
                      </div>
                    </div>
                  )}

                  {cr.status === "approved" && cr.resulting_baseline_id && (
                    <p className="mt-2 text-2xs text-[hsl(var(--success))]">
                      Re-baseline automático generado tras la aprobación.
                    </p>
                  )}
                  {cr.review_notes && cr.status !== "pending_ccb" && (
                    <p className="mt-2 rounded-md bg-[hsl(var(--surface-1))] p-2 text-2xs text-[hsl(var(--text-secondary))]">
                      <span className="font-bold">Acta:</span> {cr.review_notes}
                    </p>
                  )}
                </article>
              );
            })
          )}
        </div>
      </div>
    </RightPanel>
  );
}

export default ProjectChangeControlDrawer;

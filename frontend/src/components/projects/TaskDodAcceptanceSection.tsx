"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { useToast } from "@/context/ToastContext";
import { CheckCircle2, ClipboardCheck, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import type { ProjectTaskRecord } from "@/types/projects";

interface TaskDodAcceptanceSectionProps {
  task: ProjectTaskRecord;
  token: string | null;
}

interface DodStatusRecord {
  task_id: string;
  status: "not_recorded" | "pending" | "accepted";
  specification_met: boolean;
  tests_no_critical_failures: boolean;
  evidence_archived: boolean;
  supervisor_sign_off: boolean;
  coq_classification: string | null;
  coq_amount: number | null;
  accepted_by: string | null;
  accepted_by_name: string | null;
  accepted_at: string | null;
}

interface DodAcceptancePayload {
  specification_met: boolean;
  tests_no_critical_failures: boolean;
  evidence_archived: boolean;
  supervisor_sign_off: boolean;
  coq_classification: "prevention" | "appraisal" | "internal_failure" | "external_failure";
  coq_amount: number | null;
}

const DOD_CRITERIA = [
  { key: "specification_met", label: "Especificación técnica cumplida" },
  { key: "tests_no_critical_failures", label: "Pruebas sin fallos críticos" },
  { key: "evidence_archived", label: "Evidencia archivada" },
  { key: "supervisor_sign_off", label: "Firma del supervisor (Acta de recepción)" },
] as const;

const COQ_OPTIONS = [
  { id: "prevention", label: "Prevención" },
  { id: "appraisal", label: "Evaluación e inspección" },
  { id: "internal_failure", label: "Falla interna" },
  { id: "external_failure", label: "Falla externa" },
] as const;

const formatAcceptedDate = (iso: string): string =>
  new Date(iso).toLocaleString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

export default function TaskDodAcceptanceSection({ task, token }: TaskDodAcceptanceSectionProps) {
  const { addToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [status, setStatus] = useState<DodStatusRecord["status"]>("not_recorded");
  const [acceptedByName, setAcceptedByName] = useState<string | null>(null);
  const [acceptedAt, setAcceptedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [specificationMet, setSpecificationMet] = useState(false);
  const [testsNoCriticalFailures, setTestsNoCriticalFailures] = useState(false);
  const [evidenceArchived, setEvidenceArchived] = useState(false);
  const [supervisorSignOff, setSupervisorSignOff] = useState(false);
  const [coqClassification, setCoqClassification] = useState<"prevention" | "appraisal" | "internal_failure" | "external_failure">("prevention");
  const [coqAmount, setCoqAmount] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const loadDoDStatus = useCallback(async () => {
    if (!token || !task.id || !task.project_id) {
      setLoading(false);
      return;
    }
    setLoadError(null);
    setLoading(true);
    try {
      const data = await apiFetch<DodStatusRecord>(
        `/projects/${task.project_id}/tasks/${task.id}/dod-status`,
        { token },
      );
      if (data && typeof data === "object" && !Array.isArray(data)) {
        setStatus(data.status ?? "not_recorded");
        setAcceptedByName(data.accepted_by_name ?? null);
        setAcceptedAt(data.accepted_at ?? null);
        setSpecificationMet(Boolean(data.specification_met));
        setTestsNoCriticalFailures(Boolean(data.tests_no_critical_failures));
        setEvidenceArchived(Boolean(data.evidence_archived));
        setSupervisorSignOff(Boolean(data.supervisor_sign_off));
        if (data.coq_classification) {
          setCoqClassification(data.coq_classification as typeof coqClassification);
        }
        setCoqAmount(data.coq_amount === null || data.coq_amount === undefined ? "" : String(data.coq_amount));
      }
    } catch {
      setLoadError("No se pudo cargar el estado de aceptación del entregable.");
    } finally {
      setLoading(false);
    }
  }, [task.id, task.project_id, token]);

  useEffect(() => {
    void loadDoDStatus();
  }, [loadDoDStatus]);

  const criteriaBooleans: Record<(typeof DOD_CRITERIA)[number]["key"], boolean> = {
    specification_met: specificationMet,
    tests_no_critical_failures: testsNoCriticalFailures,
    evidence_archived: evidenceArchived,
    supervisor_sign_off: supervisorSignOff,
  };

  const handleSave = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!token || !task.id || !task.project_id) return;
    const parsedAmount = coqAmount.trim() === "" ? null : Number(coqAmount);
    if (parsedAmount !== null && (!Number.isFinite(parsedAmount) || parsedAmount < 0)) {
      setFormError("Ingresa un monto CoQ válido (número ≥ 0).");
      return;
    }
    setFormError(null);
    setSaving(true);

    const payload: DodAcceptancePayload = {
      specification_met: specificationMet,
      tests_no_critical_failures: testsNoCriticalFailures,
      evidence_archived: evidenceArchived,
      supervisor_sign_off: supervisorSignOff,
      coq_classification: coqClassification,
      coq_amount: parsedAmount,
    };

    try {
      await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/dod-acceptance`, {
        token,
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (
        specificationMet &&
        testsNoCriticalFailures &&
        evidenceArchived &&
        supervisorSignOff
      ) {
        addToast({
          title: "Entregable aceptado",
          message: "DoD completo: el entregable quedó aceptado con firma del supervisor (PMI Vol. 6 §4).",
          type: "success",
        });
      } else {
        addToast({
          title: "Verificación guardada",
          message: "El DoD quedó registrado como pendiente de aceptación formal.",
          type: "info",
        });
      }
      await loadDoDStatus();
    } catch {
      setFormError("No se pudo guardar la verificación del entregable.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section
      data-testid="task-dod-acceptance"
      className="px-4 py-3 border-b border-[hsl(var(--border))]"
      aria-label="Criterios de aceptación del entregable (DoD)"
    >
      <p className="mb-2 flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
        <ShieldCheck size={11} />
        Aceptación del entregable (DoD · PMI Vol. 6 §4)
      </p>

      {loadError && (
        <div
          className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-[hsl(var(--destructive))]/40 bg-[hsl(var(--destructive))]/10 px-3 py-2"
          role="alert"
        >
          <span className="text-2xs text-[hsl(var(--destructive))]">{loadError}</span>
          <button
            onClick={() => void loadDoDStatus()}
            className="text-2xs font-semibold text-[hsl(var(--primary))] hover:underline"
          >
            Reintentar
          </button>
        </div>
      )}

      {loading ? (
        <div className="space-y-2" role="status" aria-label="Cargando verificación DoD">
          <div className="h-4 w-3/4 animate-pulse rounded bg-[hsl(var(--surface-2))]" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-[hsl(var(--surface-2))]" />
        </div>
      ) : (
        <>
          {status === "accepted" && (
            <div
              className="mb-2 flex items-center gap-2 rounded-lg border border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10 px-3 py-2"
              role="status"
            >
              <CheckCircle2 size={14} className="shrink-0 text-[hsl(var(--success))]" />
              <div className="text-2xs text-[hsl(var(--text-primary))]">
                <span className="font-bold text-[hsl(var(--success))]">Entregable aceptado.</span>{" "}
                {acceptedByName && (
                  <span>
                    Aceptado por <span className="font-semibold">{acceptedByName}</span>
                    {acceptedAt ? ` el ${formatAcceptedDate(acceptedAt)}` : ""}
                  </span>
                )}
              </div>
            </div>
          )}
          {status === "pending" && (
            <p className="mb-2 text-2xs font-semibold text-[hsl(var(--warning-text))]">
              <ClipboardCheck size={12} className="mr-1 inline" />
              DoD registrado<strong> pendiente</strong>: faltan criterios o la firma del supervisor.
            </p>
          )}

          <form onSubmit={(e) => void handleSave(e)} className="space-y-2">
            <fieldset className="space-y-1.5">
              <legend className="sr-only">Criterios canónicos del DoD</legend>
              {DOD_CRITERIA.map((criterion) => {
                const inputId = `dod-${criterion.key}`;
                return (
                  <label
                    key={criterion.key}
                    htmlFor={inputId}
                    className="flex cursor-pointer items-center gap-2 text-xs text-[hsl(var(--text-primary))]"
                  >
                    <input
                      id={inputId}
                      type="checkbox"
                      checked={criteriaBooleans[criterion.key]}
                      onChange={(e) => {
                        const setters: Record<
                          (typeof DOD_CRITERIA)[number]["key"],
                          (v: boolean) => void
                        > = {
                          specification_met: setSpecificationMet,
                          tests_no_critical_failures: setTestsNoCriticalFailures,
                          evidence_archived: setEvidenceArchived,
                          supervisor_sign_off: setSupervisorSignOff,
                        };
                        setters[criterion.key](e.target.checked);
                      }}
                      className="size-4 rounded border-[hsl(var(--border))] accent-[hsl(var(--primary))]"
                    />
                    {criterion.label}
                  </label>
                );
              })}
            </fieldset>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <label className="block text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                Clasificación CoQ
                <select
                  value={coqClassification}
                  onChange={(e) =>
                    setCoqClassification(
                      e.target.value as "prevention" | "appraisal" | "internal_failure" | "external_failure",
                    )
                  }
                  className={clsx(
                    "mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]",
                    "px-2 py-1.5 text-xs text-[hsl(var(--text-primary))]",
                  )}
                >
                  {COQ_OPTIONS.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                Monto CoQ ($)
                <input
                  id="dod-coq-amount"
                  type="number"
                  min="0"
                  step="any"
                  value={coqAmount}
                  onChange={(e) => setCoqAmount(e.target.value)}
                  placeholder="0"
                  className={clsx(
                    "mt-1 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]",
                    "px-2 py-1.5 text-xs text-[hsl(var(--text-primary))]",
                  )}
                />
              </label>
            </div>

            {formError && (
              <p className="text-2xs text-[hsl(var(--destructive))]" role="alert">
                {formError}
              </p>
            )}

            <button
              type="button"
              onClick={(e) => void handleSave(e)}
              disabled={saving}
              className="rounded-lg bg-[hsl(var(--primary))] px-3 py-1.5 text-2xs font-bold text-[hsl(var(--primary-foreground))] shadow-sm transition-all hover:opacity-90 disabled:opacity-50"
            >
              <ClipboardCheck size={12} className="mr-1 inline" />
              {saving ? "Guardando…" : "Guardar verificación"}
            </button>
          </form>
        </>
      )}
    </section>
  );
}

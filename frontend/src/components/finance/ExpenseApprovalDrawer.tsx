"use client";

import React, { useState } from "react";
import SidePanel from "@/components/ui/SidePanel";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import clsx from "clsx";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Send,
  Building2,
  Banknote,
  Receipt,
  AlertCircle,
  FileCheck,
  Loader2,
} from "lucide-react";

export interface ExpenseItem {
  id: string;
  expense_date: string;
  category: string;
  description: string;
  amount: number | string;
  currency: string;
  vendor?: string | null;
  receipt_url?: string | null;
  is_reimbursable?: boolean;
}

export interface ApprovalHistoryEntry {
  from_status?: string;
  to_status?: string;
  step?: string;
  actor_id?: string;
  actor_name?: string;
  timestamp?: string;
  notes?: string;
}

export interface ExpenseReport {
  id: string;
  description: string;
  status: string;
  approval_step?: string;
  total_amount: number | string;
  currency: string;
  rejection_reason?: string | null;
  created_at: string;
  submitted_at?: string | null;
  approved_at?: string | null;
  reimbursed_at?: string | null;
  items?: ExpenseItem[];
  approval_history?: ApprovalHistoryEntry[];
}

interface ExpenseApprovalDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  report: ExpenseReport | null;
  onUpdated?: () => void;
}

export default function ExpenseApprovalDrawer({
  isOpen,
  onClose,
  report,
  onUpdated,
}: ExpenseApprovalDrawerProps) {
  const { token } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [disburseMethod, setDisburseMethod] = useState<"caja_menor" | "transferencia">("caja_menor");
  const [disburseNotes, setDisburseNotes] = useState("");

  if (!report) return null;

  const currentStep = report.approval_step || report.status;
  const isRejected = currentStep === "rejected" || report.status === "rejected";
  const isDisbursed = currentStep === "disbursed" || report.status === "disbursed";

  const handleAction = async (endpoint: string, payload?: Record<string, unknown>, successMsg?: string) => {
    if (!token) {
      toast.error("Sesión no válida");
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch(`/finance-suite/expense-reports/${report.id}/${endpoint}`, {
        method: "POST",
        token,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      toast.success(successMsg || "Operación completada exitosamente");
      setRejecting(false);
      setRejectReason("");
      if (onUpdated) onUpdated();
      onClose();
    } catch (err: unknown) {
      const errorObj = err as { detail?: string; message?: string };
      const msg = errorObj?.detail || errorObj?.message || "Error al procesar la solicitud";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = () => {
    handleAction("submit", {}, "Informe enviado a revisión pastoral");
  };

  const handlePastorApprove = () => {
    handleAction("pastor-approve", { notes: "Aval pastoral de sede otorgado" }, "Informe avalado y remitido a administración central");
  };

  const handleCentralApprove = () => {
    handleAction("central-approve", { notes: "Autorizado por tesorería central" }, "Informe autorizado para desembolso");
  };

  const handleDisburse = () => {
    handleAction(
      "disburse",
      {
        payment_method: disburseMethod,
        notes: disburseNotes || undefined,
      },
      `Desembolso efectuado exitosamente vía ${disburseMethod === "caja_menor" ? "Caja Menor" : "Transferencia Bancaria"}`
    );
  };

  const handleReject = () => {
    if (!rejectReason.trim() || rejectReason.trim().length < 5) {
      toast.error("Debe ingresar un motivo detallado de rechazo (mínimo 5 caracteres)");
      return;
    }
    handleAction("reject", { reason: rejectReason.trim() }, "Informe de gastos rechazado");
  };

  const stepsList = [
    { key: "draft", label: "Borrador" },
    { key: "pastor_review", label: "Revisión Pastoral" },
    { key: "central_authorization", label: "Autorización Central" },
    { key: "approved", label: "Aprobado" },
    { key: "disbursed", label: "Desembolsado" },
  ];

  const getStepIndex = (step: string) => {
    if (step === "draft") return 0;
    if (step === "pastor_review" || step === "submitted") return 1;
    if (step === "central_authorization") return 2;
    if (step === "approved") return 3;
    if (step === "disbursed") return 4;
    return -1;
  };

  const activeStepIdx = getStepIndex(currentStep);

  return (
    <SidePanel
      isOpen={isOpen}
      onClose={onClose}
      title="Aprobación de Gastos de Sede"
      subtitle={`Folio #${report.id.slice(0, 8)} · Multi-nivel`}
      width="w-[540px]"
    >
      <div className="space-y-6 text-sm text-[hsl(var(--text-primary))] pb-8">
        {/* Status Stepper */}
        <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
          <p className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">
            Circuito de Aprobación Ministerial
          </p>
          {isRejected ? (
            <div className="p-3 rounded-lg bg-[hsl(var(--destructive)/0.1)] border border-[hsl(var(--destructive)/0.2)] text-[hsl(var(--destructive))] flex items-center gap-2">
              <XCircle className="size-5 shrink-0" />
              <div>
                <p className="font-semibold text-xs">Gasto Rechazado</p>
                <p className="text-2xs opacity-90 mt-0.5">{report.rejection_reason || "Sin motivo registrado"}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between relative">
              <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-[hsl(var(--border))] -translate-y-1/2 z-0" />
              {stepsList.map((st, idx) => {
                const isPassed = activeStepIdx >= idx;
                const isCurrent = activeStepIdx === idx;
                return (
                  <div key={st.key} className="relative z-10 flex flex-col items-center">
                    <div
                      className={clsx(
                        "size-6 rounded-full flex items-center justify-center text-3xs font-bold transition-all",
                        isPassed
                          ? "bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] ring-2 ring-[hsl(var(--primary)/0.2)]"
                          : "bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]",
                        isCurrent && "ring-4 ring-[hsl(var(--primary)/0.3)] scale-110"
                      )}
                    >
                      {idx + 1}
                    </div>
                    <span
                      className={clsx(
                        "text-3xs mt-1.5 font-medium whitespace-nowrap",
                        isPassed ? "text-[hsl(var(--text-primary))]" : "text-[hsl(var(--text-secondary))]"
                      )}
                    >
                      {st.label}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Overview Details */}
        <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-2xs uppercase tracking-wide text-[hsl(var(--text-secondary))] font-semibold">Concepto</p>
              <h3 className="font-semibold text-base text-[hsl(var(--text-primary))] mt-0.5">{report.description}</h3>
            </div>
            <div className="text-right">
              <p className="text-2xs uppercase tracking-wide text-[hsl(var(--text-secondary))] font-semibold">Total a Liquidar</p>
              <p className="font-mono font-bold text-lg text-[hsl(var(--primary))] mt-0.5">
                ${Number(report.total_amount || 0).toLocaleString("es-CO")} {report.currency}
              </p>
            </div>
          </div>
        </div>

        {/* Itemized expenses */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
            <Receipt className="size-3.5" /> Comprobantes y Desglose ({report.items?.length || 0})
          </p>
          <div className="divide-y divide-[hsl(var(--border))] rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden">
            {report.items && report.items.length > 0 ? (
              report.items.map((item) => (
                <div key={item.id} className="p-3 flex items-center justify-between gap-3 text-xs">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[hsl(var(--text-primary))] truncate">{item.description}</p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                      {item.category} · {item.vendor || "Sin proveedor"} · {item.expense_date}
                    </p>
                  </div>
                  <span className="font-mono font-semibold text-[hsl(var(--text-primary))]">
                    ${Number(item.amount).toLocaleString("es-CO")} {item.currency}
                  </span>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-[hsl(var(--text-secondary))]">
                No hay renglones de gasto registrados
              </div>
            )}
          </div>
        </div>

        {/* Audit Trail */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
            <Clock className="size-3.5" /> Traza de Auditoría Inmutable
          </p>
          <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 space-y-3">
            {report.approval_history && report.approval_history.length > 0 ? (
              report.approval_history.map((entry, idx) => (
                <div key={idx} className="flex items-start gap-2.5 text-xs">
                  <div className="mt-1 size-2 rounded-full bg-[hsl(var(--primary))] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-[hsl(var(--text-primary))]">{entry.actor_name || "Usuario"}</span>
                      <span className="text-3xs text-[hsl(var(--text-secondary))]">
                        {entry.timestamp ? new Date(entry.timestamp).toLocaleString("es-CO") : "—"}
                      </span>
                    </div>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                      Transición: <span className="font-mono">{entry.from_status}</span> <ArrowRight className="inline size-2.5" /> <span className="font-mono text-[hsl(var(--primary))]">{entry.to_status}</span>
                    </p>
                    {entry.notes && (
                      <p className="text-2xs italic text-[hsl(var(--text-secondary))] mt-1 bg-[hsl(var(--surface-2))] p-1.5 rounded">
                        &ldquo;{entry.notes}&rdquo;
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-2xs text-[hsl(var(--text-secondary))] text-center py-2">
                Sin movimientos de auditoría registrados
              </p>
            )}
          </div>
        </div>

        {/* Rejection Form view if rejecting */}
        {rejecting && (
          <div className="p-4 rounded-xl bg-[hsl(var(--destructive)/0.05)] border border-[hsl(var(--destructive)/0.2)] space-y-3">
            <p className="text-xs font-bold text-[hsl(var(--destructive))] flex items-center gap-1.5">
              <AlertCircle className="size-4" /> Motivo del Rechazo de Fondos
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Explique las inconsistencias observadas en los comprobantes o presupuesto..."
              rows={3}
              className="w-full text-xs p-2.5 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--destructive))]"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setRejecting(false)}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={submitting}
                className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-[hsl(var(--destructive))] text-[hsl(var(--text-inverse))] hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5"
              >
                {submitting && <Loader2 className="size-3 animate-spin" />}
                Confirmar Rechazo
              </button>
            </div>
          </div>
        )}

        {/* Disburse form if approved */}
        {currentStep === "approved" && !rejecting && (
          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] space-y-3">
            <p className="text-xs font-bold text-[hsl(var(--primary))] flex items-center gap-1.5">
              <Banknote className="size-4" /> Desembolso de Fondos Ministerial
            </p>
            <div className="space-y-1.5">
              <label className="text-2xs font-semibold uppercase text-[hsl(var(--text-secondary))]">
                Canal de Desembolso Interno
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setDisburseMethod("caja_menor")}
                  className={clsx(
                    "p-2.5 rounded-lg border text-left text-xs font-medium transition-all flex items-center gap-2",
                    disburseMethod === "caja_menor"
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))]"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))]"
                  )}
                >
                  <Banknote className="size-4 shrink-0" />
                  <div>
                    <p className="font-bold">Caja Menor</p>
                    <p className="text-3xs opacity-80">Efectivo Sede</p>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setDisburseMethod("transferencia")}
                  className={clsx(
                    "p-2.5 rounded-lg border text-left text-xs font-medium transition-all flex items-center gap-2",
                    disburseMethod === "transferencia"
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))]"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))]"
                  )}
                >
                  <Building2 className="size-4 shrink-0" />
                  <div>
                    <p className="font-bold">Transferencia</p>
                    <p className="text-3xs opacity-80">Bancaria Interna</p>
                  </div>
                </button>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-2xs font-semibold uppercase text-[hsl(var(--text-secondary))]">
                Notas de Comprobante / Egreso
              </label>
              <input
                type="text"
                value={disburseNotes}
                onChange={(e) => setDisburseNotes(e.target.value)}
                placeholder="Ej. Cheque No. 49102 o Recibo de caja #82..."
                className="w-full text-xs p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>
          </div>
        )}

        {/* Action Buttons bar */}
        {!rejecting && !isRejected && !isDisbursed && (
          <div className="pt-2 flex items-center justify-between gap-3 border-t border-[hsl(var(--border))]">
            {/* Rejection button available during pastor review, central authorization, or approved */}
            {currentStep !== "draft" ? (
              <button
                type="button"
                onClick={() => setRejecting(true)}
                disabled={submitting}
                className="px-3.5 py-2 text-xs font-semibold rounded-xl text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] transition-all flex items-center gap-1.5"
              >
                <XCircle className="size-4" /> Rechazar
              </button>
            ) : <div />}

            <div className="flex items-center gap-2">
              {currentStep === "draft" && (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-1.5"
                >
                  {submitting ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
                  Enviar a Revisión Pastoral
                </button>
              )}

              {currentStep === "pastor_review" && (
                <button
                  type="button"
                  onClick={handlePastorApprove}
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-1.5"
                >
                  {submitting ? <Loader2 className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                  Avalar como Pastor de Sede
                </button>
              )}

              {currentStep === "central_authorization" && (
                <button
                  type="button"
                  onClick={handleCentralApprove}
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-1.5"
                >
                  {submitting ? <Loader2 className="size-3.5 animate-spin" /> : <FileCheck className="size-3.5" />}
                  Autorizar (Tesorería Central)
                </button>
              )}

              {currentStep === "approved" && (
                <button
                  type="button"
                  onClick={handleDisburse}
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-1.5"
                >
                  {submitting ? <Loader2 className="size-3.5 animate-spin" /> : <Banknote className="size-3.5" />}
                  Efectuar Desembolso
                </button>
              )}
            </div>
          </div>
        )}

        {isDisbursed && (
          <div className="p-3 rounded-xl bg-[hsl(var(--success-muted))] border border-[hsl(var(--success)/0.2)] text-[hsl(var(--success))] text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="size-4 shrink-0" />
            <span>Fondo totalmente liquidado y desembolsado a la sede.</span>
          </div>
        )}
      </div>
    </SidePanel>
  );
}

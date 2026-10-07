"use client";

import React, { useState, useEffect, useCallback, useId, useRef } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import { getSafeProjectLink } from "@/lib/projects/safeProjectLink";
import type { ProjectExpense, ProjectBudgetSummary } from "@/types/projects";
import {
  Wallet,
  Plus,
  Trash2,
  Edit2,
  DollarSign,
  TrendingDown,
  Calendar,
  Save,
  X,
  ExternalLink,
  CheckCircle2,
  Clock,
  FileText,
  PieChart,
} from "lucide-react";

interface ProjectBudgetDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  budgetAllocated?: number | null;
  onBudgetUpdated?: () => void;
}

const EXPENSE_CATEGORIES = [
  { id: "materials", label: "Materiales y Suministros" },
  { id: "services", label: "Servicios y Contratistas" },
  { id: "logistics", label: "Logística y Transporte" },
  { id: "honorarios", label: "Honorarios Profesionales" },
  { id: "catering", label: "Alimentación y Eventos" },
  { id: "marketing", label: "Difusión y Medios" },
  { id: "general", label: "Gastos Generales" },
];

const STATUS_CONFIG = {
  planned: {
    label: "Planificado",
    color: "hsl(var(--text-secondary))",
    bg: "hsl(var(--surface-2))",
    border: "hsl(var(--border))",
    icon: Clock,
  },
  committed: {
    label: "Comprometido",
    color: "hsl(var(--warning))",
    bg: "hsl(var(--warning) / 0.12)",
    border: "hsl(var(--warning) / 0.3)",
    icon: TrendingDown,
  },
  paid: {
    label: "Pagado",
    color: "hsl(var(--success))",
    bg: "hsl(var(--success) / 0.12)",
    border: "hsl(var(--success) / 0.3)",
    icon: CheckCircle2,
  },
};

export function ProjectBudgetDrawer({
  projectId,
  isOpen,
  onClose,
  budgetAllocated = 0,
  onBudgetUpdated,
}: ProjectBudgetDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();
  const fieldId = useId();
  const requestSequence = useRef(0);

  const [expenses, setExpenses] = useState<ProjectExpense[]>([]);
  const [summary, setSummary] = useState<ProjectBudgetSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  // Filtros
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  // Formulario
  const [formData, setFormData] = useState<{
    category: string;
    description: string;
    amount: number;
    date: string;
    receipt_url: string;
    status: "planned" | "committed" | "paid";
  }>({
    category: "general",
    description: "",
    amount: 0,
    date: new Date().toISOString().split("T")[0],
    receipt_url: "",
    status: "planned",
  });

  const fetchData = useCallback(async () => {
    const requestId = ++requestSequence.current;
    if (!projectId || !token) return;
    setLoading(true);
    setLoadError(false);
    try {
      const [expData, sumData] = await Promise.all([
        apiFetch<ProjectExpense[]>(`/projects/${projectId}/expenses`, { token }),
        apiFetch<ProjectBudgetSummary>(`/projects/${projectId}/budget-summary`, { token }),
      ]);
      if (requestId !== requestSequence.current) return;
      setExpenses(expData || []);
      setSummary(sumData);
    } catch {
      if (requestId !== requestSequence.current) return;
      setLoadError(true);
      addToast("Error al cargar la información presupuestaria", "error");
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [projectId, token, addToast]);

  useEffect(() => {
    if (isOpen) {
      setExpenses([]);
      setSummary(null);
      void fetchData();
      setIsCreating(false);
      setEditingId(null);
    }
    return () => {
      requestSequence.current += 1;
    };
  }, [isOpen, fetchData]);

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.amount || formData.amount <= 0) {
      addToast("El monto debe ser mayor a 0", "warning");
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await apiFetch(`/projects/${projectId}/expenses/${editingId}`, {
          method: "PATCH",
          token,
          body: JSON.stringify({
            category: formData.category,
            description: formData.description,
            amount: Number(formData.amount),
            date: formData.date ? new Date(formData.date).toISOString() : undefined,
            receipt_url: formData.receipt_url || null,
            status: formData.status,
          }),
        });
        addToast("Partida de gasto actualizada", "success");
      } else {
        await apiFetch(`/projects/${projectId}/expenses`, {
          method: "POST",
          token,
          body: JSON.stringify({
            category: formData.category,
            description: formData.description,
            amount: Number(formData.amount),
            date: formData.date ? new Date(formData.date).toISOString() : undefined,
            receipt_url: formData.receipt_url || null,
            status: formData.status,
          }),
        });
        addToast("Gasto registrado exitosamente", "success");
      }

      setIsCreating(false);
      setEditingId(null);
      setFormData({
        category: "general",
        description: "",
        amount: 0,
        date: new Date().toISOString().split("T")[0],
        receipt_url: "",
        status: "planned",
      });
      fetchData();
      onBudgetUpdated?.();
    } catch {
      addToast("Error al guardar la partida de gasto", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (exp: ProjectExpense) => {
    setEditingId(exp.id);
    setIsCreating(true);
    setFormData({
      category: exp.category || "general",
      description: exp.description || "",
      amount: exp.amount || 0,
      date: exp.date ? exp.date.split("T")[0] : new Date().toISOString().split("T")[0],
      receipt_url: exp.receipt_url || "",
      status: exp.status || "planned",
    });
  };

  const handleDelete = async (expenseId: string) => {
    try {
      await apiFetch(`/projects/${projectId}/expenses/${expenseId}`, {
        method: "DELETE",
        token,
      });
      addToast("Partida eliminada", "info");
      await fetchData();
      onBudgetUpdated?.();
    } catch (error) {
      addToast("Error al eliminar la partida", "error");
      throw error;
    }
  };

  const requestDelete = (expense: ProjectExpense) => {
    setConfirmAction({
      title: "Eliminar partida de gasto",
      description: `¿Seguro que deseas eliminar “${expense.description || expense.category}”? Esta acción es lógica y la partida dejará de contar en el presupuesto.`,
      confirmLabel: "Eliminar",
      destructive: true,
      onConfirm: () => handleDelete(expense.id),
    });
  };

  const handleStatusChange = async (expenseId: string, newStatus: "planned" | "committed" | "paid") => {
    try {
      await apiFetch(`/projects/${projectId}/expenses/${expenseId}`, {
        method: "PATCH",
        token,
        body: JSON.stringify({ status: newStatus }),
      });
      addToast(`Estado cambiado a ${STATUS_CONFIG[newStatus].label}`, "success");
      fetchData();
      onBudgetUpdated?.();
    } catch {
      addToast("Error al actualizar el estado", "error");
    }
  };

  const filteredExpenses = expenses.filter((e) => {
    if (filterStatus !== "all" && e.status !== filterStatus) return false;
    if (filterCategory !== "all" && e.category !== filterCategory) return false;
    return true;
  });

  const burnRate = summary?.burn_rate_percent ?? 0;
  const burnColor =
    burnRate > 90
      ? "hsl(var(--destructive))"
      : burnRate > 70
      ? "hsl(var(--warning))"
      : "hsl(var(--success))";

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Control Presupuestario y Partidas de Gasto"
      className="w-full max-w-2xl"
    >
      <div className="flex flex-col gap-5 p-6 text-sm" style={{ color: "hsl(var(--text-primary))" }}>
        {/* KPI CARDS & RESUMEN FINANCIERO */}
        <div
          className="rounded-xl p-5 border"
          style={{
            backgroundColor: "hsl(var(--surface-1))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: "hsl(var(--border))" }}>
            <div className="flex items-center gap-2">
              <Wallet className="w-5 h-5" style={{ color: "hsl(var(--primary))" }} />
              <span className="font-semibold text-base">Estado de Fondos</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: "hsl(var(--surface-2))" }}>
              <PieChart className="w-3.5 h-3.5" style={{ color: burnColor }} />
              <span>Quema: {burnRate.toFixed(1)}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4">
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Asignado</span>
              <span className="text-base font-bold">
                ${(summary?.budget_allocated ?? budgetAllocated ?? 0).toLocaleString("es-CO")}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Desembolsado</span>
              <span className="text-base font-bold" style={{ color: "hsl(var(--success))" }}>
                ${(summary?.paid_amount ?? 0).toLocaleString("es-CO")}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Comprometido</span>
              <span className="text-base font-bold" style={{ color: "hsl(var(--warning))" }}>
                ${(summary?.committed_amount ?? 0).toLocaleString("es-CO")}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Disponible</span>
              <span className="text-base font-bold" style={{ color: "hsl(var(--primary))" }}>
                ${(summary?.remaining_budget ?? 0).toLocaleString("es-CO")}
              </span>
            </div>
          </div>

          {/* Barra de progreso de quema */}
          <div className="mt-4">
            <div
              className="w-full h-2.5 rounded-full overflow-hidden"
              style={{ backgroundColor: "hsl(var(--surface-2))" }}
            >
              <div
                className="h-full transition-all duration-300 rounded-full"
                style={{
                  width: `${Math.min(100, Math.max(0, burnRate))}%`,
                  backgroundColor: burnColor,
                }}
              />
            </div>
          </div>
        </div>

        {/* BOTÓN REGISTRAR GASTO */}
        {!isCreating && (
          <div className="flex justify-between items-center">
            <span className="font-semibold text-sm">
              Partidas y Egresos ({filteredExpenses.length})
            </span>
            <button
              onClick={() => {
                setIsCreating(true);
                setEditingId(null);
                setFormData({
                  category: "general",
                  description: "",
                  amount: 0,
                  date: new Date().toISOString().split("T")[0],
                  receipt_url: "",
                  status: "planned",
                });
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-opacity hover:opacity-90"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              <Plus className="w-4 h-4" />
              <span>Registrar Gasto</span>
            </button>
          </div>
        )}

        {/* FORMULARIO DE CREACIÓN/EDICIÓN */}
        {isCreating && (
          <form
            onSubmit={handleCreateOrUpdate}
            className="rounded-xl p-5 border flex flex-col gap-4 animate-in fade-in"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--primary) / 0.4)",
            }}
          >
            <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: "hsl(var(--border))" }}>
              <span className="font-semibold text-sm">
                {editingId ? "Editar Partida de Gasto" : "Nuevo Registro de Gasto"}
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                }}
                className="p-1 rounded-md cursor-pointer hover:opacity-80"
                style={{ color: "hsl(var(--text-secondary))" }}
                aria-label="Cerrar formulario de gasto"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor={`${fieldId}-amount`} className="block text-xs font-medium mb-1">Monto ($)*</label>
                <input
                  id={`${fieldId}-amount`}
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={formData.amount || ""}
                  onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 rounded-lg border text-sm font-semibold outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                  placeholder="0.00"
                />
              </div>

              <div>
                <label htmlFor={`${fieldId}-category`} className="block text-xs font-medium mb-1">Categoría*</label>
                <select
                  id={`${fieldId}-category`}
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                >
                  {EXPENSE_CATEGORIES.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor={`${fieldId}-status`} className="block text-xs font-medium mb-1">Estado de Pago</label>
                <select
                  id={`${fieldId}-status`}
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value as "planned" | "committed" | "paid" })
                  }
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                >
                  <option value="planned">Planificado</option>
                  <option value="committed">Comprometido</option>
                  <option value="paid">Pagado / Desembolsado</option>
                </select>
              </div>

              <div>
                <label htmlFor={`${fieldId}-date`} className="block text-xs font-medium mb-1">Fecha</label>
                <input
                  id={`${fieldId}-date`}
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                />
              </div>
            </div>

            <div>
              <label htmlFor={`${fieldId}-description`} className="block text-xs font-medium mb-1">Descripción / Concepto</label>
              <input
                id={`${fieldId}-description`}
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-primary))",
                }}
                placeholder="Ej. Factura #1234 - Compra de pintura y brochas"
              />
            </div>

            <div>
              <label htmlFor={`${fieldId}-receipt-url`} className="block text-xs font-medium mb-1">URL de Factura / Comprobante (Opcional)</label>
              <input
                id={`${fieldId}-receipt-url`}
                type="url"
                value={formData.receipt_url}
                onChange={(e) => setFormData({ ...formData, receipt_url: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-primary))",
                }}
                placeholder="https://almacenamiento.ccf.org/recibos/..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                }}
                className="px-4 py-2 rounded-lg border text-xs font-medium cursor-pointer hover:opacity-80"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer hover:opacity-90 disabled:opacity-50"
                style={{
                  backgroundColor: "hsl(var(--primary))",
                  color: "hsl(var(--primary-foreground))",
                }}
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? "Guardando..." : editingId ? "Actualizar" : "Registrar"}</span>
              </button>
            </div>
          </form>
        )}

        {/* FILTROS */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Estado:</span>
            <select
              aria-label="Filtrar partidas por estado"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-2.5 py-1 rounded-lg border text-xs outline-none"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <option value="all">Todos</option>
              <option value="planned">Planificados</option>
              <option value="committed">Comprometidos</option>
              <option value="paid">Pagados</option>
            </select>
          </div>

          <div className="flex items-center gap-1">
            <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Categoría:</span>
            <select
              aria-label="Filtrar partidas por categoría"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="px-2.5 py-1 rounded-lg border text-xs outline-none"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <option value="all">Todas</option>
              {EXPENSE_CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* LISTADO DE GASTOS */}
        <div className="flex flex-col gap-2.5">
          {loadError && !loading && (
            <div
              role="alert"
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--text-primary))",
              }}
            >
              <span>No se pudo cargar la información presupuestaria.</span>
              <button
                type="button"
                onClick={fetchData}
                className="rounded-lg border px-3 py-1.5 font-medium"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--primary))",
                }}
              >
                Reintentar carga presupuestaria
              </button>
            </div>
          )}
          {loading ? (
            <div role="status" aria-label="Cargando partidas presupuestarias" className="flex flex-col gap-2.5">
              {[0, 1, 2].map((item) => (
                <div
                  key={item}
                  aria-hidden="true"
                  className="h-20 animate-pulse rounded-xl border"
                  style={{ backgroundColor: "hsl(var(--surface-2))", borderColor: "hsl(var(--border))" }}
                />
              ))}
            </div>
          ) : loadError && filteredExpenses.length === 0 ? null : filteredExpenses.length === 0 ? (
            <div
              className="p-8 text-center rounded-xl border flex flex-col items-center gap-2"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--text-secondary))",
              }}
            >
              <DollarSign className="w-8 h-8 opacity-40" />
              <span>No se encontraron partidas de gasto registradas.</span>
            </div>
          ) : (
            filteredExpenses.map((exp) => {
              const st = STATUS_CONFIG[exp.status] || STATUS_CONFIG.planned;
              const StatusIcon = st.icon;
              const catLabel =
                EXPENSE_CATEGORIES.find((c) => c.id === exp.category)?.label || exp.category;
              const receiptUrl = getSafeProjectLink(exp.receipt_url);

              return (
                <div
                  key={exp.id}
                  className="rounded-xl p-4 border flex flex-col gap-2.5 transition-all hover:shadow-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm">
                          ${exp.amount.toLocaleString("es-CO")}
                        </span>
                        <span
                          className="px-2 py-0.5 rounded-full text-xs font-medium border inline-flex items-center gap-1"
                          style={{
                            backgroundColor: st.bg,
                            color: st.color,
                            borderColor: st.border,
                          }}
                        >
                          <StatusIcon className="w-3 h-3" />
                          <span>{st.label}</span>
                        </span>
                        <span
                          className="px-2 py-0.5 rounded-full text-xs"
                          style={{
                            backgroundColor: "hsl(var(--surface-2))",
                            color: "hsl(var(--text-secondary))",
                          }}
                        >
                          {catLabel}
                        </span>
                      </div>
                      <p className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>
                        {exp.description || "Sin descripción"}
                      </p>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleEdit(exp)}
                        className="p-1.5 rounded-md cursor-pointer hover:opacity-80 transition-opacity"
                        style={{ color: "hsl(var(--text-secondary))" }}
                        title="Editar"
                        aria-label={`Editar gasto: ${exp.description || catLabel}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => requestDelete(exp)}
                        className="p-1.5 rounded-md cursor-pointer hover:opacity-80 transition-opacity"
                        style={{ color: "hsl(var(--destructive))" }}
                        title="Eliminar"
                        aria-label={`Eliminar gasto: ${exp.description || catLabel}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div
                    className="flex items-center justify-between pt-2 border-t text-xs flex-wrap gap-2"
                    style={{ borderColor: "hsl(var(--border))", color: "hsl(var(--text-secondary))" }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{exp.date ? exp.date.split("T")[0] : "Sin fecha"}</span>
                      </span>
                      {exp.creator_name && (
                        <span>Por: {exp.creator_name}</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {receiptUrl && (
                        <a
                          href={receiptUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 underline"
                          style={{ color: "hsl(var(--primary))" }}
                        >
                          <FileText className="w-3 h-3" />
                          <span>Comprobante</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}

                      {/* Transiciones rápidas de estado */}
                      {exp.status !== "paid" && (
                        <button
                          onClick={() => handleStatusChange(exp.id, "paid")}
                          className="px-2 py-0.5 rounded text-xs font-medium cursor-pointer transition-opacity hover:opacity-90"
                          style={{
                            backgroundColor: "hsl(var(--success) / 0.15)",
                            color: "hsl(var(--success))",
                          }}
                        >
                          Marcar Pagado
                        </button>
                      )}
                      {exp.status === "planned" && (
                        <button
                          onClick={() => handleStatusChange(exp.id, "committed")}
                          className="px-2 py-0.5 rounded text-xs font-medium cursor-pointer transition-opacity hover:opacity-90"
                          style={{
                            backgroundColor: "hsl(var(--warning) / 0.15)",
                            color: "hsl(var(--warning))",
                          }}
                        >
                          Comprometer
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
    </RightPanel>
  );
}

"use client";

import React, { useState, useEffect, useCallback, useId } from "react";
import RightPanel from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectComponentDetail,
  ProjectBudget100RuleValidation,
  ProjectComponentsBreakdown,
} from "@/types/projects";
import {
  Layers,
  Plus,
  Trash2,
  Edit2,
  DollarSign,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Save,
  X,
  RefreshCw,
  PieChart,
  ListTodo,
  Receipt,
  HelpCircle,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

interface ProjectComponentDrawerProps {
  projectId: string;
  projectTitle?: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

interface ComponentFormData {
  code: string;
  name: string;
  description: string;
  budget_allocated: number;
  order_index: number;
  color: string;
}

const INITIAL_FORM_DATA: ComponentFormData = {
  code: "",
  name: "",
  description: "",
  budget_allocated: 0,
  order_index: 0,
  color: "#3b82f6",
};

const COLOR_PRESETS = [
  "#3b82f6", // azul
  "#10b981", // verde
  "#f59e0b", // ámbar
  "#8b5cf6", // púrpura
  "#ec4899", // rosa
  "#06b6d4", // cian
  "#64748b", // pizarra
];

export function ProjectComponentDrawer({
  projectId,
  projectTitle = "Proyecto",
  isOpen,
  onClose,
  onUpdated,
}: ProjectComponentDrawerProps) {
  const { token } = useAuth();
  const formCodeId = useId();
  const formNameId = useId();
  const formDescId = useId();
  const formBudgetId = useId();
  const formOrderId = useId();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [components, setComponents] = useState<ProjectComponentDetail[]>([]);
  const [budgetRule, setBudgetRule] = useState<ProjectBudget100RuleValidation | null>(null);

  // Estados de interfaz del drawer
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingComponentId, setEditingComponentId] = useState<string | null>(null);
  const [deletingComponentId, setDeletingComponentId] = useState<string | null>(null);
  const [formData, setFormData] = useState<ComponentFormData>(INITIAL_FORM_DATA);

  const loadBreakdown = useCallback(async () => {
    if (!projectId || !token) return;
    setLoading(true);
    try {
      const data = await apiFetch<ProjectComponentsBreakdown>(
        `/projects/${projectId}/components-breakdown`,
        { token }
      );
      setComponents(data.components || []);
      setBudgetRule(data.budget_rule || null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al cargar componentes EDT";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    if (isOpen) {
      void loadBreakdown();
      setIsFormOpen(false);
      setEditingComponentId(null);
      setDeletingComponentId(null);
      setFormData(INITIAL_FORM_DATA);
    }
  }, [isOpen, loadBreakdown]);

  const handleStartCreate = () => {
    const nextOrder = components.length + 1;
    const nextCode = `EDT-${nextOrder}.0`;
    setFormData({
      ...INITIAL_FORM_DATA,
      code: nextCode,
      order_index: nextOrder,
    });
    setEditingComponentId(null);
    setIsFormOpen(true);
  };

  const handleStartEdit = (comp: ProjectComponentDetail) => {
    setFormData({
      code: comp.code,
      name: comp.name,
      description: comp.description || "",
      budget_allocated: comp.budget_allocated || 0,
      order_index: comp.order_index || 0,
      color: comp.color || "#3b82f6",
    });
    setEditingComponentId(comp.id);
    setIsFormOpen(true);
  };

  const handleCancelForm = () => {
    setIsFormOpen(false);
    setEditingComponentId(null);
    setFormData(INITIAL_FORM_DATA);
  };

  const handleSubmitForm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.code.trim() || !formData.name.trim()) {
      toast.error("El código y el nombre del componente son obligatorios");
      return;
    }
    if (formData.budget_allocated < 0) {
      toast.error("El presupuesto asignado no puede ser negativo");
      return;
    }

    setSaving(true);
    try {
      if (editingComponentId) {
        // Actualizar componente existente
        await apiFetch<ProjectComponentDetail>(
          `/projects/${projectId}/components/${editingComponentId}`,
          {
            method: "PATCH",
            token,
            body: JSON.stringify({
              code: formData.code.trim(),
              name: formData.name.trim(),
              description: formData.description.trim() || null,
              budget_allocated: Number(formData.budget_allocated),
              order_index: Number(formData.order_index),
              color: formData.color,
            }),
          }
        );
        toast.success("Componente EDT actualizado correctamente");
      } else {
        // Crear nuevo componente
        await apiFetch<ProjectComponentDetail>(
          `/projects/${projectId}/components`,
          {
            method: "POST",
            token,
            body: JSON.stringify({
              code: formData.code.trim(),
              name: formData.name.trim(),
              description: formData.description.trim() || null,
              budget_allocated: Number(formData.budget_allocated),
              order_index: Number(formData.order_index),
              color: formData.color,
            }),
          }
        );
        toast.success("Componente EDT creado correctamente");
      }
      setIsFormOpen(false);
      setEditingComponentId(null);
      await loadBreakdown();
      onUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al guardar el componente";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async (componentId: string) => {
    setSaving(true);
    try {
      await apiFetch(`/projects/${projectId}/components/${componentId}`, {
        method: "DELETE",
        token,
      });
      toast.success("Componente EDT eliminado y actividades desvinculadas");
      setDeletingComponentId(null);
      await loadBreakdown();
      onUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al eliminar el componente";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      width="w-full sm:max-w-2xl"
      title={
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" style={{ color: "hsl(var(--primary))" }} />
          <span className="font-semibold text-base">Estructura de Desglose (EDT Nivel 2)</span>
        </div>
      }
      subtitle={`Gestión de paquetes de trabajo y regla del 100% — ${projectTitle}`}
    >
      <div className="p-4 sm:p-6 space-y-6">
        {/* Banner de Control: Regla del 100% de Presupuesto PMI */}
        {budgetRule && (
          <div
            className="rounded-xl border p-4 transition-all"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <PieChart className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />
                <h4 className="text-sm font-semibold tracking-wide">
                  Regla del 100% del Presupuesto (PMI)
                </h4>
              </div>
              <span
                className={clsx(
                  "px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider",
                  budgetRule.status === "balanced" && "bg-success/15 text-success",
                  budgetRule.status === "under_allocated" && "bg-warning/15 text-warning",
                  budgetRule.status === "over_allocated" && "bg-destructive/15 text-destructive",
                  budgetRule.status === "no_project_budget" && "bg-surface-2 text-text-secondary"
                )}
                style={{
                  backgroundColor:
                    budgetRule.status === "balanced"
                      ? "hsl(var(--success) / 0.12)"
                      : budgetRule.status === "under_allocated"
                      ? "hsl(var(--warning) / 0.12)"
                      : budgetRule.status === "over_allocated"
                      ? "hsl(var(--destructive) / 0.12)"
                      : "hsl(var(--surface-2))",
                  color:
                    budgetRule.status === "balanced"
                      ? "hsl(var(--success))"
                      : budgetRule.status === "under_allocated"
                      ? "hsl(var(--warning))"
                      : budgetRule.status === "over_allocated"
                      ? "hsl(var(--destructive))"
                      : "hsl(var(--text-secondary))",
                }}
              >
                {budgetRule.status === "balanced"
                  ? "100% Balanceado"
                  : budgetRule.status === "under_allocated"
                  ? "Sub-asignado"
                  : budgetRule.status === "over_allocated"
                  ? "Sobre-asignado"
                  : "Sin Presupuesto"}
              </span>
            </div>

            {/* Barra de progreso de asignación */}
            <div className="space-y-1 mb-3">
              <div className="flex justify-between text-xs" style={{ color: "hsl(var(--text-secondary))" }}>
                <span>Cobertura EDT: {budgetRule.allocation_percentage}%</span>
                <span>
                  ${budgetRule.components_budget_total.toLocaleString()} / $
                  {budgetRule.project_budget_allocated.toLocaleString()}
                </span>
              </div>
              <div
                className="h-2 w-full rounded-full overflow-hidden"
                style={{ backgroundColor: "hsl(var(--surface-2))" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(budgetRule.allocation_percentage, 100)}%`,
                    backgroundColor:
                      budgetRule.status === "balanced"
                        ? "hsl(var(--success))"
                        : budgetRule.status === "under_allocated"
                        ? "hsl(var(--warning))"
                        : "hsl(var(--destructive))",
                  }}
                />
              </div>
            </div>

            {/* Resumen numérico */}
            <div
              className="grid grid-cols-3 gap-2 py-2 px-3 rounded-lg text-center text-xs"
              style={{ backgroundColor: "hsl(var(--surface-2))" }}
            >
              <div>
                <p style={{ color: "hsl(var(--text-secondary))" }}>BAC Proyecto</p>
                <p className="font-semibold text-sm">
                  ${budgetRule.project_budget_allocated.toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: "hsl(var(--text-secondary))" }}>Total Componentes</p>
                <p className="font-semibold text-sm">
                  ${budgetRule.components_budget_total.toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: "hsl(var(--text-secondary))" }}>
                  {budgetRule.budget_difference >= 0 ? "Saldo por Asignar" : "Excedente"}
                </p>
                <p
                  className="font-semibold text-sm"
                  style={{
                    color:
                      budgetRule.budget_difference === 0
                        ? "hsl(var(--success))"
                        : budgetRule.budget_difference > 0
                        ? "hsl(var(--warning))"
                        : "hsl(var(--destructive))",
                  }}
                >
                  ${Math.abs(budgetRule.budget_difference).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Recomendaciones PMI */}
            {budgetRule.recommendations.length > 0 && (
              <div className="mt-3 text-xs space-y-1" style={{ color: "hsl(var(--text-secondary))" }}>
                {budgetRule.recommendations.map((rec, i) => (
                  <p key={i} className="flex items-start gap-1.5">
                    <span className="font-bold">•</span>
                    <span>{rec}</span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Acciones principales */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: "hsl(var(--text-secondary))" }}>
              Componentes ({components.length})
            </h3>
            <button
              type="button"
              onClick={() => void loadBreakdown()}
              disabled={loading}
              className="p-1 rounded-md hover:bg-surface-2 transition-colors"
              title="Refrescar datos"
              aria-label="Refrescar datos de componentes"
            >
              <RefreshCw
                className={clsx("h-3.5 w-3.5", loading && "animate-spin")}
                style={{ color: "hsl(var(--text-secondary))" }}
              />
            </button>
          </div>
          {!isFormOpen && (
            <button
              type="button"
              onClick={handleStartCreate}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-white transition-opacity hover:opacity-90 shadow-sm"
              style={{ backgroundColor: "hsl(var(--primary))" }}
            >
              <Plus className="h-4 w-4" />
              <span>Nuevo Componente</span>
            </button>
          )}
        </div>

        {/* Formulario Deslizable de Creación / Edición */}
        {isFormOpen && (
          <form
            onSubmit={handleSubmitForm}
            className="rounded-xl border p-4 space-y-4 transition-all"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--primary) / 0.5)",
            }}
          >
            <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: "hsl(var(--border))" }}>
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <Layers className="h-4 w-4" style={{ color: "hsl(var(--primary))" }} />
                <span>{editingComponentId ? "Editar Componente EDT" : "Nuevo Componente EDT (Nivel 2)"}</span>
              </h4>
              <button
                type="button"
                onClick={handleCancelForm}
                className="p-1 rounded-md hover:bg-surface-2 text-text-secondary"
                aria-label="Cerrar formulario"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label htmlFor={formCodeId} className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Código EDT *
                </label>
                <input
                  id={formCodeId}
                  type="text"
                  required
                  placeholder="ej. EDT-1.0, CMP-01"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  className="w-full px-3 py-1.5 text-sm rounded-lg border focus:outline-none focus:ring-1"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                />
              </div>

              <div>
                <label htmlFor={formOrderId} className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Orden de Presentación
                </label>
                <input
                  id={formOrderId}
                  type="number"
                  min="0"
                  value={formData.order_index}
                  onChange={(e) => setFormData({ ...formData, order_index: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-1.5 text-sm rounded-lg border focus:outline-none focus:ring-1"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                />
              </div>
            </div>

            <div>
              <label htmlFor={formNameId} className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Nombre del Entregable / Paquete de Trabajo *
              </label>
              <input
                id={formNameId}
                type="text"
                required
                placeholder="ej. Fase de Infraestructura Tecnológica"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-1.5 text-sm rounded-lg border focus:outline-none focus:ring-1"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-primary))",
                }}
              />
            </div>

            <div>
              <label htmlFor={formBudgetId} className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Presupuesto Asignado ($ USD / Moneda Local) *
              </label>
              <div className="relative">
                <DollarSign className="absolute left-2.5 top-2 h-4 w-4" style={{ color: "hsl(var(--text-secondary))" }} />
                <input
                  id={formBudgetId}
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={formData.budget_allocated}
                  onChange={(e) =>
                    setFormData({ ...formData, budget_allocated: parseFloat(e.target.value) || 0 })
                  }
                  className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg border focus:outline-none focus:ring-1"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-primary))",
                  }}
                />
              </div>
            </div>

            <div>
              <label htmlFor={formDescId} className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Descripción del Alcance (Opcional)
              </label>
              <textarea
                id={formDescId}
                rows={2}
                placeholder="Objetivo y criterios de aceptación del componente..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-1.5 text-sm rounded-lg border focus:outline-none focus:ring-1"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-primary))",
                }}
              />
            </div>

            {/* Selector de color semántico */}
            <div>
              <span className="block text-xs font-medium mb-1.5" style={{ color: "hsl(var(--text-secondary))" }}>
                Color Distintivo
              </span>
              <div className="flex items-center gap-2">
                {COLOR_PRESETS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setFormData({ ...formData, color: c })}
                    className={clsx(
                      "h-6 w-6 rounded-full border-2 transition-transform",
                      formData.color === c ? "scale-110 border-white shadow-md" : "border-transparent"
                    )}
                    style={{ backgroundColor: c }}
                    aria-label={`Seleccionar color ${c}`}
                  />
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t" style={{ borderColor: "hsl(var(--border))" }}>
              <button
                type="button"
                onClick={handleCancelForm}
                disabled={saving}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border hover:bg-surface-2 transition-colors"
                style={{ borderColor: "hsl(var(--border))", color: "hsl(var(--text-secondary))" }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-lg text-white transition-opacity hover:opacity-90 shadow-sm"
                style={{ backgroundColor: "hsl(var(--primary))" }}
              >
                <Save className="h-4 w-4" />
                <span>{saving ? "Guardando..." : "Guardar Componente"}</span>
              </button>
            </div>
          </form>
        )}

        {/* Lista de Componentes */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-28 rounded-xl border animate-pulse"
                style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--border))" }}
              />
            ))}
          </div>
        ) : components.length === 0 ? (
          <div
            className="text-center py-10 px-4 rounded-xl border border-dashed"
            style={{ backgroundColor: "hsl(var(--surface-1))", borderColor: "hsl(var(--border))" }}
          >
            <Layers className="h-10 w-10 mx-auto mb-3 text-text-secondary" style={{ color: "hsl(var(--text-secondary))" }} />
            <h4 className="text-sm font-semibold mb-1">Sin componentes configurados</h4>
            <p className="text-xs max-w-sm mx-auto mb-4" style={{ color: "hsl(var(--text-secondary))" }}>
              Cree los paquetes de trabajo de Nivel 2 de la EDT para desglosar el alcance y controlar el valor ganado (EVM).
            </p>
            <button
              type="button"
              onClick={handleStartCreate}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-white hover:opacity-90 shadow-sm"
              style={{ backgroundColor: "hsl(var(--primary))" }}
            >
              <Plus className="h-4 w-4" />
              <span>Crear Primer Componente</span>
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {components.map((comp) => {
              const evm = comp.evm;
              const isDeleting = deletingComponentId === comp.id;

              return (
                <div
                  key={comp.id}
                  className="rounded-xl border p-4 transition-shadow hover:shadow-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  {/* Encabezado del componente */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-start gap-2.5">
                      <div
                        className="h-3 w-3 rounded-full mt-1.5 shrink-0"
                        style={{ backgroundColor: comp.color || "#3b82f6" }}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className="px-2 py-0.5 rounded text-xs font-mono font-semibold"
                            style={{
                              backgroundColor: "hsl(var(--surface-2))",
                              color: "hsl(var(--text-primary))",
                            }}
                          >
                            {comp.code}
                          </span>
                          <h4 className="text-sm font-semibold leading-tight">{comp.name}</h4>
                        </div>
                        {comp.description && (
                          <p className="text-xs mt-1 line-clamp-2" style={{ color: "hsl(var(--text-secondary))" }}>
                            {comp.description}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleStartEdit(comp)}
                        className="p-1 rounded hover:bg-surface-2 transition-colors text-text-secondary"
                        title="Editar componente"
                        aria-label={`Editar componente ${comp.code}`}
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeletingComponentId(isDeleting ? null : comp.id)}
                        className="p-1 rounded hover:bg-destructive/15 transition-colors text-destructive"
                        title="Eliminar componente"
                        aria-label={`Eliminar componente ${comp.code}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Confirmación de eliminación embebida (sin modal) */}
                  {isDeleting && (
                    <div
                      className="my-3 p-3 rounded-lg border text-xs space-y-2 animate-in fade-in"
                      style={{
                        backgroundColor: "hsl(var(--destructive) / 0.08)",
                        borderColor: "hsl(var(--destructive) / 0.3)",
                      }}
                    >
                      <div className="flex items-center gap-1.5 font-semibold text-destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <span>¿Eliminar componente [{comp.code}]?</span>
                      </div>
                      <p style={{ color: "hsl(var(--text-secondary))" }}>
                        Las tareas y gastos asociados se desvincularán sin eliminarse.
                      </p>
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setDeletingComponentId(null)}
                          className="px-2 py-1 rounded bg-surface-2 hover:bg-surface-3 text-text-secondary font-medium"
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteConfirm(comp.id)}
                          disabled={saving}
                          className="px-2.5 py-1 rounded bg-destructive text-white font-medium hover:opacity-90"
                        >
                          {saving ? "Eliminando..." : "Confirmar"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Métricas y resumen EVM */}
                  <div
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3 border-t text-xs"
                    style={{ borderColor: "hsl(var(--border))" }}
                  >
                    <div>
                      <span style={{ color: "hsl(var(--text-secondary))" }}>Presupuesto (BAC)</span>
                      <p className="font-semibold text-sm">
                        ${comp.budget_allocated.toLocaleString()}
                      </p>
                    </div>

                    <div>
                      <span style={{ color: "hsl(var(--text-secondary))" }}>Actividades</span>
                      <p className="font-semibold flex items-center gap-1">
                        <ListTodo className="h-3.5 w-3.5" style={{ color: "hsl(var(--text-secondary))" }} />
                        <span>
                          {comp.tasks_count} tarea(s) ({evm?.completed_tasks || 0} completas)
                        </span>
                      </p>
                    </div>

                    <div>
                      <span style={{ color: "hsl(var(--text-secondary))" }}>Gastos Reales (AC)</span>
                      <p className="font-semibold flex items-center gap-1">
                        <Receipt className="h-3.5 w-3.5" style={{ color: "hsl(var(--text-secondary))" }} />
                        <span>${(evm?.ac || 0).toLocaleString()}</span>
                      </p>
                    </div>

                    <div>
                      <span style={{ color: "hsl(var(--text-secondary))" }}>Avance Físico</span>
                      <p className="font-semibold flex items-center gap-1">
                        <TrendingUp className="h-3.5 w-3.5" style={{ color: "hsl(var(--primary))" }} />
                        <span>{evm?.physical_progress_pct || 0}%</span>
                      </p>
                    </div>
                  </div>

                  {/* Indicadores EVM: CPI / SPI / Gap */}
                  {evm && (
                    <div
                      className="mt-3 pt-2 border-t flex flex-wrap items-center justify-between gap-2 text-xs"
                      style={{ borderColor: "hsl(var(--border))" }}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded font-mono font-bold",
                            evm.cpi >= 1.0 ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
                          )}
                          style={{
                            backgroundColor:
                              evm.cpi >= 1.0 ? "hsl(var(--success) / 0.12)" : "hsl(var(--destructive) / 0.12)",
                            color: evm.cpi >= 1.0 ? "hsl(var(--success))" : "hsl(var(--destructive))",
                          }}
                        >
                          CPI: {evm.cpi}
                        </span>

                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded font-mono font-bold",
                            evm.spi >= 1.0 ? "bg-success/15 text-success" : "bg-warning/15 text-warning"
                          )}
                          style={{
                            backgroundColor:
                              evm.spi >= 1.0 ? "hsl(var(--success) / 0.12)" : "hsl(var(--warning) / 0.12)",
                            color: evm.spi >= 1.0 ? "hsl(var(--success))" : "hsl(var(--warning))",
                          }}
                        >
                          SPI: {evm.spi}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 text-text-secondary" style={{ color: "hsl(var(--text-secondary))" }}>
                        <span>Balance Físico-Financiero:</span>
                        <span
                          className="font-semibold"
                          style={{
                            color:
                              evm.balance_gap_pct >= 0
                                ? "hsl(var(--success))"
                                : "hsl(var(--destructive))",
                          }}
                        >
                          {evm.balance_gap_pct > 0 ? `+${evm.balance_gap_pct}%` : `${evm.balance_gap_pct}%`}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </RightPanel>
  );
}

export default ProjectComponentDrawer;

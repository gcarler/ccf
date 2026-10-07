"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { ProjectKPI } from "@/types/projects";
import { Target, Plus, Trash2, TrendingUp, CheckCircle2, AlertTriangle, AlertOctagon, Calendar, Save, X, Sparkles } from "lucide-react";
import clsx from "clsx";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";

interface ProjectKpiDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onKpisUpdated?: () => void;
}

const CATEGORIES = [
  { id: "impact", label: "Impacto", color: "hsl(var(--primary))" },
  { id: "operational", label: "Operativo", color: "hsl(var(--info))" },
  { id: "financial", label: "Financiero", color: "hsl(var(--warning))" },
  { id: "quality", label: "Calidad", color: "hsl(var(--success))" },
];

export function ProjectKpiDrawer({
  projectId,
  isOpen,
  onClose,
  onKpisUpdated,
}: ProjectKpiDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [kpis, setKpis] = useState<ProjectKPI[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [, setEditingId] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  // Form state
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    target_value: 100,
    current_value: 0,
    unit: "%",
    category: "impact",
    due_date: "",
  });

  const fetchKpis = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      setLoading(true);
      const data = await apiFetch<ProjectKPI[]>(`/projects/${projectId}/kpis`, { token });
      setKpis(Array.isArray(data) ? data : []);
    } catch {
      addToast({
        title: "Error al cargar indicadores",
        description: "No se pudieron obtener los KPIs del proyecto.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [projectId, token, addToast]);

  useEffect(() => {
    if (isOpen) {
      fetchKpis();
      setIsCreating(false);
      setEditingId(null);
    }
  }, [isOpen, fetchKpis]);

  const handleCreateKpi = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      addToast({
        title: "Título requerido",
        description: "Por favor ingresa un nombre para el indicador.",
        variant: "destructive",
      });
      return;
    }

    try {
      setSaving(true);
      await apiFetch(`/projects/${projectId}/kpis`, {
        method: "POST",
        token,
        body: {
          title: formData.title.trim(),
          description: formData.description.trim() || null,
          target_value: Number(formData.target_value) || 1,
          current_value: Number(formData.current_value) || 0,
          unit: formData.unit.trim() || "unidades",
          category: formData.category,
          due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null,
        },
      });

      addToast({
        title: "Indicador creado",
        description: `El KPI '${formData.title}' ha sido registrado exitosamente.`,
        variant: "success",
      });

      setFormData({
        title: "",
        description: "",
        target_value: 100,
        current_value: 0,
        unit: "%",
        category: "impact",
        due_date: "",
      });
      setIsCreating(false);
      await fetchKpis();
      onKpisUpdated?.();
    } catch {
      addToast({
        title: "Error al crear indicador",
        description: "Ocurrió un error al intentar registrar el KPI.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateValue = async (kpi: ProjectKPI, newValue: number) => {
    const clamped = Math.max(0, newValue);
    try {
      await apiFetch(`/projects/${projectId}/kpis/${kpi.id}`, {
        method: "PATCH",
        token,
        body: { current_value: clamped },
      });

      setKpis((prev) =>
        prev.map((item) => (item.id === kpi.id ? { ...item, current_value: clamped } : item))
      );
      onKpisUpdated?.();
    } catch {
      addToast({
        title: "Error de actualización",
        description: "No se pudo actualizar el avance del indicador.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteKpi = async (kpiId: string) => {
    try {
      await apiFetch(`/projects/${projectId}/kpis/${kpiId}`, {
        method: "DELETE",
        token,
      });

      addToast({
        title: "Indicador eliminado",
        description: "El KPI ha sido removido del proyecto.",
        variant: "default",
      });

      setKpis((prev) => prev.filter((k) => k.id !== kpiId));
      onKpisUpdated?.();
    } catch {
      addToast({
        title: "Error al eliminar",
        description: "No se pudo eliminar el indicador.",
        variant: "destructive",
      });
      throw new Error("No se pudo eliminar el indicador.");
    }
  };

  const requestDeleteKpi = (kpi: ProjectKPI) => {
    setConfirmAction({
      title: "Eliminar indicador",
      description: `¿Confirmas eliminar el KPI “${kpi.title}” del proyecto? Se quitará del seguimiento de metas e informes.`,
      destructive: true,
      confirmLabel: "Eliminar indicador",
      onConfirm: () => handleDeleteKpi(kpi.id),
    });
  };

  const getStatusBadge = (current: number, target: number) => {
    const pct = target > 0 ? (current / target) * 100 : 0;
    if (pct >= 100) {
      return {
        label: "Completado",
        icon: CheckCircle2,
        color: "text-[hsl(var(--success))]",
        bg: "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30",
        barColor: "bg-[hsl(var(--success))]",
      };
    }
    if (pct >= 70) {
      return {
        label: "En Camino",
        icon: TrendingUp,
        color: "text-[hsl(var(--primary))]",
        bg: "bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30",
        barColor: "bg-[hsl(var(--primary))]",
      };
    }
    if (pct >= 40) {
      return {
        label: "En Riesgo",
        icon: AlertTriangle,
        color: "text-[hsl(var(--warning))]",
        bg: "bg-[hsl(var(--warning))]/10 border-[hsl(var(--warning))]/30",
        barColor: "bg-[hsl(var(--warning))]",
      };
    }
    return {
      label: "Crítico",
      icon: AlertOctagon,
      color: "text-[hsl(var(--destructive))]",
      bg: "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30",
      barColor: "bg-[hsl(var(--destructive))]",
    };
  };

  return (
    <RightPanel
      title="Indicadores y KPIs del Proyecto"
      open={isOpen}
      onClose={onClose}
      width={440}
    >
      <div className="flex flex-col h-full space-y-4 p-4 text-[hsl(var(--text-primary))]">
        {/* Header Summary */}
        <div className="flex items-center justify-between p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
              <Target size={20} />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))]">
                Metas Operativas
              </h4>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">
                {kpis.length} {kpis.length === 1 ? "indicador activo" : "indicadores activos"}
              </p>
            </div>
          </div>
          {!isCreating && (
            <button
              onClick={() => setIsCreating(true)}
              className="px-2.5 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow-sm"
            >
              <Plus size={14} /> Nuevo KPI
            </button>
          )}
        </div>

        {/* Create KPI Form */}
        {isCreating && (
          <form
            onSubmit={handleCreateKpi}
            className="p-3.5 rounded-xl border border-[hsl(var(--primary))]/30 bg-[hsl(var(--surface-2))] space-y-3 animate-in fade-in slide-in-from-top-2 duration-200"
          >
            <div className="flex items-center justify-between pb-1 border-b border-[hsl(var(--border))]">
              <span className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                <Sparkles size={14} /> Registrar Nuevo KPI
              </span>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="p-1 rounded text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]"
              >
                <X size={14} />
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                Título del Indicador *
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Ej. Tasa de conversión, Familias alcanzadas..."
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                  Meta *
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  value={formData.target_value}
                  onChange={(e) => setFormData({ ...formData, target_value: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                  Actual
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.current_value}
                  onChange={(e) => setFormData({ ...formData, current_value: Number(e.target.value) })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                  Unidad
                </label>
                <input
                  type="text"
                  value={formData.unit}
                  onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                  placeholder="%, pers, $"
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                  Categoría
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                >
                  {CATEGORIES.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">
                  Fecha Límite
                </label>
                <input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow"
              >
                <Save size={13} /> {saving ? "Guardando..." : "Guardar KPI"}
              </button>
            </div>
          </form>
        )}

        {/* List of KPIs */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-28 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] animate-pulse"
                />
              ))}
            </div>
          ) : kpis.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-[hsl(var(--border))] rounded-xl bg-[hsl(var(--surface-2))]/50">
              <Target size={36} className="text-[hsl(var(--text-secondary))]/50 mb-2" />
              <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))]">
                Sin indicadores configurados
              </p>
              <p className="text-2xs text-[hsl(var(--text-secondary))] mt-1 max-w-xs">
                Establece metas cuantitativas (asistencia, presupuesto, cobertura) para monitorear el impacto del proyecto.
              </p>
            </div>
          ) : (
            kpis.map((kpi) => {
              const status = getStatusBadge(kpi.current_value, kpi.target_value);
              const StatusIcon = status.icon;
              const pct = kpi.target_value > 0
                ? Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100))
                : 0;

              return (
                <div
                  key={kpi.id}
                  className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary))]/40 transition-all shadow-sm space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 rounded text-3xs font-black uppercase tracking-wider bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]">
                          {CATEGORIES.find((c) => c.id === kpi.category)?.label || kpi.category}
                        </span>
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border flex items-center gap-1",
                            status.bg,
                            status.color
                          )}
                        >
                          <StatusIcon size={11} /> {status.label}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] pt-1">
                        {kpi.title}
                      </h4>
                    </div>

                    <button
                      onClick={() => requestDeleteKpi(kpi)}
                      aria-label={`Eliminar KPI ${kpi.title}`}
                      className="p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))]/10 transition-colors"
                      title="Eliminar KPI"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>

                  {kpi.description && (
                    <p className="text-2xs text-[hsl(var(--text-secondary))] line-clamp-2">
                      {kpi.description}
                    </p>
                  )}

                  {/* Progress values and bar */}
                  <div className="space-y-1 pt-1">
                    <div className="flex items-center justify-between text-2xs">
                      <span className="font-bold text-[hsl(var(--text-primary))]">
                        {kpi.current_value.toLocaleString()} / {kpi.target_value.toLocaleString()}{" "}
                        <span className="text-[hsl(var(--text-secondary))] font-normal">
                          {kpi.unit}
                        </span>
                      </span>
                      <span className={clsx("font-black tracking-tight", status.color)}>
                        {pct}%
                      </span>
                    </div>

                    <div className="h-2 w-full rounded-full bg-[hsl(var(--surface-3))] overflow-hidden">
                      <div
                        className={clsx("h-full rounded-full transition-all duration-500", status.barColor)}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>

                  {/* Quick Increment Controls */}
                  <div className="flex items-center justify-between pt-1 border-t border-[hsl(var(--border))]/60">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleUpdateValue(kpi, kpi.current_value - 1)}
                        className="px-2 py-0.5 rounded text-3xs font-bold border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] active:scale-95"
                      >
                        -1
                      </button>
                      <button
                        onClick={() => handleUpdateValue(kpi, kpi.current_value + 1)}
                        className="px-2 py-0.5 rounded text-3xs font-bold border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-3))] active:scale-95"
                      >
                        +1
                      </button>
                      <button
                        onClick={() => handleUpdateValue(kpi, kpi.current_value + 10)}
                        className="px-2 py-0.5 rounded text-3xs font-bold border border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/10 active:scale-95"
                      >
                        +10
                      </button>
                    </div>

                    {kpi.due_date && (
                      <span className="text-3xs text-[hsl(var(--text-secondary))] flex items-center gap-1">
                        <Calendar size={11} />
                        {new Date(kpi.due_date).toLocaleDateString("es-ES", {
                          day: "numeric",
                          month: "short",
                        })}
                      </span>
                    )}
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

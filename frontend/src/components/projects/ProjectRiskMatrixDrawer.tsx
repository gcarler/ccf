"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { ProjectRisk, ProjectRiskSummary } from "@/types/projects";
import {
  ShieldAlert,
  Plus,
  Trash2,
  Edit2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  Flame,
  X,
  Save,
  Activity,
  Layers,
  HelpCircle,
} from "lucide-react";
import clsx from "clsx";

interface ProjectRiskMatrixDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onRiskUpdated?: () => void;
}

const RISK_CATEGORIES = [
  { id: "tecnico", label: "Técnico / Infraestructura" },
  { id: "logistico", label: "Logístico / Proveedores" },
  { id: "financiero", label: "Financiero / Presupuesto" },
  { id: "reputacional", label: "Reputacional / Imagen" },
  { id: "operativo", label: "Operativo / Equipo" },
  { id: "legal", label: "Legal / Normativo" },
  { id: "otro", label: "Otro" },
];

const SEVERITY_LEVELS = {
  critical: {
    label: "Crítico",
    min: 15,
    max: 25,
    color: "hsl(var(--destructive))",
    bg: "hsl(var(--destructive) / 0.12)",
    border: "hsl(var(--destructive) / 0.35)",
  },
  high: {
    label: "Alto",
    min: 10,
    max: 14,
    color: "hsl(28 90% 55%)",
    bg: "hsl(28 90% 55% / 0.12)",
    border: "hsl(28 90% 55% / 0.35)",
  },
  medium: {
    label: "Medio",
    min: 5,
    max: 9,
    color: "hsl(var(--warning))",
    bg: "hsl(var(--warning) / 0.12)",
    border: "hsl(var(--warning) / 0.35)",
  },
  low: {
    label: "Bajo",
    min: 1,
    max: 4,
    color: "hsl(var(--success))",
    bg: "hsl(var(--success) / 0.12)",
    border: "hsl(var(--success) / 0.35)",
  },
};

const STATUS_CONFIG = {
  active: {
    label: "Activo / Latente",
    color: "hsl(var(--warning))",
    bg: "hsl(var(--warning) / 0.12)",
    border: "hsl(var(--warning) / 0.3)",
    icon: Clock,
  },
  mitigated: {
    label: "Mitigado / Controlado",
    color: "hsl(var(--success))",
    bg: "hsl(var(--success) / 0.12)",
    border: "hsl(var(--success) / 0.3)",
    icon: CheckCircle2,
  },
  occurred: {
    label: "Ocurrido / Materializado",
    color: "hsl(var(--destructive))",
    bg: "hsl(var(--destructive) / 0.12)",
    border: "hsl(var(--destructive) / 0.3)",
    icon: Flame,
  },
};

export function ProjectRiskMatrixDrawer({
  projectId,
  isOpen,
  onClose,
  onRiskUpdated,
}: ProjectRiskMatrixDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [risks, setRisks] = useState<ProjectRisk[]>([]);
  const [summary, setSummary] = useState<ProjectRiskSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedCell, setSelectedCell] = useState<{ p: number; i: number } | null>(null);

  // Filtros
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  // Formulario
  const [formData, setFormData] = useState<{
    title: string;
    category: string;
    probability: number;
    impact: number;
    mitigation_plan: string;
    contingency_plan: string;
    status: "active" | "mitigated" | "occurred";
  }>({
    title: "",
    category: "tecnico",
    probability: 3,
    impact: 3,
    mitigation_plan: "",
    contingency_plan: "",
    status: "active",
  });

  const fetchData = useCallback(async () => {
    if (!projectId || !token) return;
    setLoading(true);
    try {
      const [risksData, sumData] = await Promise.all([
        apiFetch<ProjectRisk[]>(`/projects/${projectId}/risks`, { token }),
        apiFetch<ProjectRiskSummary>(`/projects/${projectId}/risks-summary`, { token }),
      ]);
      setRisks(risksData || []);
      setSummary(sumData);
    } catch {
      addToast("Error al cargar la matriz de riesgos", "error");
    } finally {
      setLoading(false);
    }
  }, [projectId, token, addToast]);

  useEffect(() => {
    if (isOpen) {
      fetchData();
      setIsCreating(false);
      setEditingId(null);
      setSelectedCell(null);
    }
  }, [isOpen, fetchData]);

  const liveSeverity = formData.probability * formData.impact;
  const getSeverityMeta = (score: number) => {
    if (score >= 15) return SEVERITY_LEVELS.critical;
    if (score >= 10) return SEVERITY_LEVELS.high;
    if (score >= 5) return SEVERITY_LEVELS.medium;
    return SEVERITY_LEVELS.low;
  };
  const liveMeta = getSeverityMeta(liveSeverity);

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      addToast("El título del riesgo es obligatorio", "warning");
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await apiFetch(`/projects/${projectId}/risks/${editingId}`, {
          method: "PATCH",
          token,
          body: JSON.stringify({
            title: formData.title.trim(),
            category: formData.category,
            probability: Number(formData.probability),
            impact: Number(formData.impact),
            mitigation_plan: formData.mitigation_plan || null,
            contingency_plan: formData.contingency_plan || null,
            status: formData.status,
          }),
        });
        addToast("Riesgo actualizado con éxito", "success");
      } else {
        await apiFetch(`/projects/${projectId}/risks`, {
          method: "POST",
          token,
          body: JSON.stringify({
            title: formData.title.trim(),
            category: formData.category,
            probability: Number(formData.probability),
            impact: Number(formData.impact),
            mitigation_plan: formData.mitigation_plan || null,
            contingency_plan: formData.contingency_plan || null,
            status: formData.status,
          }),
        });
        addToast("Riesgo registrado en la matriz RAID", "success");
      }
      setIsCreating(false);
      setEditingId(null);
      resetForm();
      fetchData();
      onRiskUpdated?.();
    } catch {
      addToast("Error al guardar el riesgo", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (risk: ProjectRisk) => {
    setEditingId(risk.id);
    setIsCreating(true);
    setFormData({
      title: risk.title,
      category: risk.category || "tecnico",
      probability: risk.probability || 3,
      impact: risk.impact || 3,
      mitigation_plan: risk.mitigation_plan || "",
      contingency_plan: risk.contingency_plan || "",
      status: risk.status || "active",
    });
  };

  const handleDelete = async (riskId: string) => {
    try {
      await apiFetch(`/projects/${projectId}/risks/${riskId}`, {
        method: "DELETE",
        token,
      });
      addToast("Riesgo eliminado de la matriz", "success");
      fetchData();
      onRiskUpdated?.();
    } catch {
      addToast("Error al eliminar el riesgo", "error");
    }
  };

  const handleConvertToTask = async (riskId: string) => {
    setConvertingId(riskId);
    try {
      await apiFetch(`/projects/${projectId}/risks/${riskId}/convert-to-task`, {
        method: "POST",
        token,
      });
      addToast("Riesgo convertido a Tarea de Contingencia inmediata", "success");
      fetchData();
      onRiskUpdated?.();
    } catch {
      addToast("Error al convertir riesgo en tarea", "error");
    } finally {
      setConvertingId(null);
    }
  };

  const resetForm = () => {
    setFormData({
      title: "",
      category: "tecnico",
      probability: 3,
      impact: 3,
      mitigation_plan: "",
      contingency_plan: "",
      status: "active",
    });
  };

  // Filtrado de riesgos
  const filteredRisks = risks.filter((r) => {
    if (filterStatus !== "all" && r.status !== filterStatus) return false;
    if (filterCategory !== "all" && r.category !== filterCategory) return false;
    if (selectedCell && (r.probability !== selectedCell.p || r.impact !== selectedCell.i)) return false;
    return true;
  });

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Matriz RAID de Riesgos y Supuestos"
      description="Gestión preventiva de amenazas, matriz de calor 5x5 y activación de planes de contingencia."
      width="max-w-3xl"
    >
      <div className="space-y-6 pb-12">
        {/* RESUMEN DE SEVERIDAD */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--surface-2))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center justify-between text-xs text-muted font-medium">
              <span>Total Registrados</span>
              <Layers className="w-4 h-4 opacity-70" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--text-main))" }}>
              {summary?.total_risks ?? risks.length}
            </div>
            <div className="text-[11px] text-muted mt-1">
              {summary?.active_risks ?? 0} activos / latentes
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--destructive) / 0.08)",
              borderColor: "hsl(var(--destructive) / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(var(--destructive))" }}>
              <span>Críticos (15-25)</span>
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--destructive))" }}>
              {summary?.critical_count ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(var(--destructive) / 0.8)" }}>
              Atención prioritaria
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(28 90% 55% / 0.08)",
              borderColor: "hsl(28 90% 55% / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(28 90% 55%)" }}>
              <span>Altos (10-14)</span>
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(28 90% 55%)" }}>
              {summary?.high_count ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(28 90% 55% / 0.8)" }}>
              Mitigación en curso
            </div>
          </div>

          <div
            className="p-3.5 rounded-xl border flex flex-col justify-between"
            style={{
              backgroundColor: "hsl(var(--success) / 0.08)",
              borderColor: "hsl(var(--success) / 0.25)",
            }}
          >
            <div className="flex items-center justify-between text-xs font-semibold" style={{ color: "hsl(var(--success))" }}>
              <span>Mitigados</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold mt-2" style={{ color: "hsl(var(--success))" }}>
              {summary?.mitigated_risks ?? 0}
            </div>
            <div className="text-[11px] font-medium mt-1" style={{ color: "hsl(var(--success) / 0.8)" }}>
              Bajo control
            </div>
          </div>
        </div>

        {/* MATRIZ RAID 5X5 INTERACTIVA */}
        <div
          className="p-4 rounded-xl border"
          style={{
            backgroundColor: "hsl(var(--surface-1))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" style={{ color: "hsl(var(--primary))" }} />
              <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--text-main))" }}>
                Matriz de Calor de Severidad (5×5)
              </h3>
            </div>
            {selectedCell && (
              <button
                onClick={() => setSelectedCell(null)}
                className="text-xs px-2 py-0.5 rounded border flex items-center gap-1 transition-colors"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-muted))",
                }}
              >
                <span>Filtro P{selectedCell.p}×I{selectedCell.i} activo</span>
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          <div className="text-[11px] text-muted mb-2 flex items-center justify-between">
            <span>Eje Vertical: Probabilidad (1=Muy Baja → 5=Muy Alta)</span>
            <span>Eje Horizontal: Impacto (1=Leve → 5=Catastrófico)</span>
          </div>

          {/* Grilla 5x5 */}
          <div className="grid grid-cols-5 gap-1.5 text-center">
            {[5, 4, 3, 2, 1].map((p) =>
              [1, 2, 3, 4, 5].map((i) => {
                const score = p * i;
                const meta = getSeverityMeta(score);
                const cell = summary?.matrix_5x5?.find(
                  (c) => c.probability === p && c.impact === i
                );
                const count = cell ? cell.count : risks.filter((r) => r.probability === p && r.impact === i).length;
                const isSelected = selectedCell?.p === p && selectedCell?.i === i;

                return (
                  <button
                    key={`p${p}-i${i}`}
                    type="button"
                    onClick={() => {
                      if (isSelected) {
                        setSelectedCell(null);
                      } else {
                        setSelectedCell({ p, i });
                      }
                    }}
                    className={clsx(
                      "p-2 rounded-lg border flex flex-col items-center justify-center transition-all cursor-pointer relative",
                      isSelected && "ring-2 ring-offset-1"
                    )}
                    style={{
                      backgroundColor: count > 0 ? meta.bg : "hsl(var(--surface-2) / 0.5)",
                      borderColor: isSelected ? meta.color : meta.border,
                      ringColor: meta.color,
                    }}
                    title={`Probabilidad: ${p}, Impacto: ${i}, Severidad: ${score}/25 (${meta.label})`}
                  >
                    <span className="text-[10px] font-medium opacity-60 leading-none">
                      {p}×{i}
                    </span>
                    <span
                      className="text-xs font-bold leading-tight mt-0.5"
                      style={{ color: count > 0 ? meta.color : "hsl(var(--text-muted))" }}
                    >
                      {count > 0 ? `${count}` : score}
                    </span>
                    {count > 0 && (
                      <span
                        className="w-1.5 h-1.5 rounded-full absolute top-1 right-1"
                        style={{ backgroundColor: meta.color }}
                      />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* BARRA DE HERRAMIENTAS Y BOTÓN NUEVO */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border focus:outline-none"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--text-main))",
              }}
            >
              <option value="all">Todos los estados</option>
              <option value="active">Activos</option>
              <option value="mitigated">Mitigados</option>
              <option value="occurred">Ocurridos</option>
            </select>

            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border focus:outline-none"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--text-main))",
              }}
            >
              <option value="all">Todas las categorías</option>
              {RISK_CATEGORIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {!isCreating && (
            <button
              onClick={() => {
                resetForm();
                setEditingId(null);
                setIsCreating(true);
              }}
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-opacity hover:opacity-90"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              <Plus className="w-4 h-4" />
              <span>Registrar Riesgo</span>
            </button>
          )}
        </div>

        {/* FORMULARIO DE CREACIÓN O EDICIÓN */}
        {isCreating && (
          <form
            onSubmit={handleCreateOrUpdate}
            className="p-4 rounded-xl border space-y-4 animate-in fade-in duration-200"
            style={{
              backgroundColor: "hsl(var(--surface-2))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center justify-between border-b pb-2" style={{ borderColor: "hsl(var(--border))" }}>
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" style={{ color: "hsl(var(--primary))" }} />
                <h4 className="text-sm font-semibold" style={{ color: "hsl(var(--text-main))" }}>
                  {editingId ? "Editar Riesgo de la Matriz" : "Registrar Nuevo Riesgo"}
                </h4>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                  resetForm();
                }}
                className="text-muted hover:opacity-80"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Título / Amenaza Identificada *
                </label>
                <input
                  type="text"
                  required
                  placeholder="ej. Fallo en el servidor de backups o retraso de materiales"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Categoría
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                >
                  {RISK_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Estado
                </label>
                <select
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value as "active" | "mitigated" | "occurred" })
                  }
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                >
                  <option value="active">Activo / Latente</option>
                  <option value="mitigated">Mitigado / Controlado</option>
                  <option value="occurred">Ocurrido / Materializado</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Probabilidad (1 a 5)
                </label>
                <select
                  value={formData.probability}
                  onChange={(e) => setFormData({ ...formData, probability: Number(e.target.value) })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                >
                  <option value={1}>1 - Muy Baja (&lt;10%)</option>
                  <option value={2}>2 - Baja (10-30%)</option>
                  <option value={3}>3 - Media (30-60%)</option>
                  <option value={4}>4 - Alta (60-85%)</option>
                  <option value={5}>5 - Muy Alta (&gt;85%)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Impacto (1 a 5)
                </label>
                <select
                  value={formData.impact}
                  onChange={(e) => setFormData({ ...formData, impact: Number(e.target.value) })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                >
                  <option value={1}>1 - Leve / Despreciable</option>
                  <option value={2}>2 - Menor (Bajo impacto)</option>
                  <option value={3}>3 - Moderado (Retraso manejable)</option>
                  <option value={4}>4 - Mayor (Peligro de plazos/costos)</option>
                  <option value={5}>5 - Crítico / Catastrófico</option>
                </select>
              </div>
            </div>

            {/* SEVERIDAD EN VIVO */}
            <div
              className="p-3 rounded-lg border flex items-center justify-between"
              style={{
                backgroundColor: liveMeta.bg,
                borderColor: liveMeta.border,
              }}
            >
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4" style={{ color: liveMeta.color }} />
                <span className="text-xs font-medium" style={{ color: liveMeta.color }}>
                  Severidad Resultante: <strong>{liveSeverity}/25</strong> ({liveMeta.label})
                </span>
              </div>
              <span
                className="text-[11px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider"
                style={{
                  backgroundColor: liveMeta.color,
                  color: "hsl(var(--surface-1))",
                }}
              >
                {liveMeta.label}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Plan de Mitigación (Prevención)
                </label>
                <textarea
                  rows={2}
                  placeholder="Acciones preventivas para evitar o reducir el riesgo..."
                  value={formData.mitigation_plan}
                  onChange={(e) => setFormData({ ...formData, mitigation_plan: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none resize-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "hsl(var(--text-main))" }}>
                  Plan de Contingencia (Reacción)
                </label>
                <textarea
                  rows={2}
                  placeholder="Qué hacer inmediatamente si el riesgo se materializa..."
                  value={formData.contingency_plan}
                  onChange={(e) => setFormData({ ...formData, contingency_plan: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-lg border focus:outline-none resize-none"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--text-main))",
                  }}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                  resetForm();
                }}
                className="text-xs px-3 py-1.5 rounded-lg border transition-colors hover:opacity-80"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-muted))",
                }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 text-xs font-medium px-4 py-1.5 rounded-lg transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{
                  backgroundColor: "hsl(var(--primary))",
                  color: "hsl(var(--primary-foreground))",
                }}
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? "Guardando..." : editingId ? "Actualizar Riesgo" : "Guardar Riesgo"}</span>
              </button>
            </div>
          </form>
        )}

        {/* LISTADO DE RIESGOS */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-medium" style={{ color: "hsl(var(--text-muted))" }}>
            <span>Riesgos Encontrados ({filteredRisks.length})</span>
            {selectedCell && (
              <span>
                Filtro por celda P={selectedCell.p}, I={selectedCell.i}
              </span>
            )}
          </div>

          {loading ? (
            <div className="space-y-2 py-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-20 rounded-xl animate-pulse"
                  style={{ backgroundColor: "hsl(var(--surface-2))" }}
                />
              ))}
            </div>
          ) : filteredRisks.length === 0 ? (
            <div
              className="p-8 text-center rounded-xl border"
              style={{
                backgroundColor: "hsl(var(--surface-1))",
                borderColor: "hsl(var(--border))",
              }}
            >
              <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-40" style={{ color: "hsl(var(--text-muted))" }} />
              <p className="text-sm font-medium" style={{ color: "hsl(var(--text-main))" }}>
                No hay riesgos registrados con estos filtros
              </p>
              <p className="text-xs text-muted mt-1">
                La matriz RAID ayuda a anticipar contingencias y proteger el proyecto.
              </p>
            </div>
          ) : (
            filteredRisks.map((risk) => {
              const sev = (risk.probability || 1) * (risk.impact || 1);
              const meta = getSeverityMeta(sev);
              const statusCfg = STATUS_CONFIG[risk.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.active;
              const StatusIcon = statusCfg.icon;

              return (
                <div
                  key={risk.id}
                  className="p-4 rounded-xl border space-y-3 transition-colors hover:border-opacity-80"
                  style={{
                    backgroundColor: "hsl(var(--surface-1))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* BADGE SEVERIDAD */}
                        <span
                          className="text-[11px] font-bold px-2 py-0.5 rounded-full border inline-flex items-center gap-1"
                          style={{
                            backgroundColor: meta.bg,
                            color: meta.color,
                            borderColor: meta.border,
                          }}
                        >
                          <Flame className="w-3 h-3" />
                          <span>
                            {meta.label} ({sev}/25)
                          </span>
                        </span>

                        {/* BADGE ESTADO */}
                        <span
                          className="text-[11px] font-medium px-2 py-0.5 rounded-full border inline-flex items-center gap-1"
                          style={{
                            backgroundColor: statusCfg.bg,
                            color: statusCfg.color,
                            borderColor: statusCfg.border,
                          }}
                        >
                          <StatusIcon className="w-3 h-3" />
                          <span>{statusCfg.label}</span>
                        </span>

                        <span
                          className="text-[11px] px-2 py-0.5 rounded-md text-muted"
                          style={{ backgroundColor: "hsl(var(--surface-2))" }}
                        >
                          {RISK_CATEGORIES.find((c) => c.id === risk.category)?.label || risk.category}
                        </span>
                      </div>

                      <h4 className="text-sm font-semibold mt-1" style={{ color: "hsl(var(--text-main))" }}>
                        {risk.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleEdit(risk)}
                        className="p-1.5 rounded-lg text-muted hover:opacity-100 transition-colors"
                        style={{ backgroundColor: "hsl(var(--surface-2))" }}
                        title="Editar riesgo"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(risk.id)}
                        className="p-1.5 rounded-lg hover:opacity-100 transition-colors"
                        style={{
                          backgroundColor: "hsl(var(--destructive) / 0.1)",
                          color: "hsl(var(--destructive))",
                        }}
                        title="Eliminar riesgo"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* DETALLES DE PLANES */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {risk.mitigation_plan && (
                      <div
                        className="p-2.5 rounded-lg border"
                        style={{
                          backgroundColor: "hsl(var(--surface-2))",
                          borderColor: "hsl(var(--border))",
                        }}
                      >
                        <span className="font-semibold block text-[11px] mb-0.5 text-muted">
                          Plan de Mitigación:
                        </span>
                        <p style={{ color: "hsl(var(--text-main))" }}>{risk.mitigation_plan}</p>
                      </div>
                    )}

                    {risk.contingency_plan && (
                      <div
                        className="p-2.5 rounded-lg border"
                        style={{
                          backgroundColor: "hsl(var(--surface-2))",
                          borderColor: "hsl(var(--border))",
                        }}
                      >
                        <span className="font-semibold block text-[11px] mb-0.5 text-muted">
                          Plan de Contingencia:
                        </span>
                        <p style={{ color: "hsl(var(--text-main))" }}>{risk.contingency_plan}</p>
                      </div>
                    )}
                  </div>

                  {/* ACCIÓN DE CONVERSIÓN A TAREA */}
                  <div className="flex items-center justify-between pt-1 border-t text-[11px] text-muted" style={{ borderColor: "hsl(var(--border))" }}>
                    <span>
                      P: <strong>{risk.probability}/5</strong> | I: <strong>{risk.impact}/5</strong>
                      {risk.owner_name && ` • Resp: ${risk.owner_name}`}
                    </span>

                    {risk.status !== "occurred" ? (
                      <button
                        onClick={() => handleConvertToTask(risk.id)}
                        disabled={convertingId === risk.id}
                        className="inline-flex items-center gap-1 font-semibold px-2.5 py-1 rounded-md transition-opacity hover:opacity-90 disabled:opacity-50"
                        style={{
                          backgroundColor: "hsl(var(--primary) / 0.12)",
                          color: "hsl(var(--primary))",
                        }}
                        title="Convierte este riesgo en una tarea ministerial de contingencia inmediata"
                      >
                        <ArrowRight className="w-3 h-3" />
                        <span>{convertingId === risk.id ? "Convirtiendo..." : "Materializado → Crear Tarea"}</span>
                      </button>
                    ) : (
                      <span className="font-medium text-xs inline-flex items-center gap-1" style={{ color: "hsl(var(--destructive))" }}>
                        <Flame className="w-3.5 h-3.5" />
                        <span>Incidencia activa</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </RightPanel>
  );
}

"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectIndicator,
  ProjectIndicatorRecord,
  ProjectIndicatorCreate,
  ProjectIndicatorRecordCreate,
  CremaValidationResult,
  MgaIndicatorLevel,
  MgaCalculationType,
} from "@/types/projects";
import { BarChart3, TrendingUp, Plus, Trash2, Edit2, CheckCircle2, AlertTriangle, Clock, ExternalLink, Save, Check, RotateCw, Sparkles, Award, Layers, FileCheck2, Activity, History, Sliders } from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

interface ProjectIndicatorsDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onIndicatorUpdated?: () => void;
}

const MGA_LEVELS: { id: MgaIndicatorLevel; label: string; desc: string }[] = [
  { id: "RESULTADO_EFICACIA", label: "Resultado / Eficacia", desc: "Impacto y logro de objetivos de largo plazo del proyecto" },
  { id: "PRODUCTO_PRINCIPAL", label: "Producto Principal", desc: "Entregables tangibles directos derivados de las actividades" },
  { id: "PRODUCTO_SECUNDARIO", label: "Producto Secundario", desc: "Entregables complementarios y de soporte operativo" },
  { id: "GESTION_PROCESO", label: "Gestión / Proceso", desc: "Eficiencia de ejecución de procesos y cumplimiento de hitos" },
  { id: "EFICIENCIA", label: "Eficiencia", desc: "Optimización de costos, recursos y rendimiento operativo" },
  { id: "CALIDAD", label: "Calidad", desc: "Satisfacción, apego a estándares y estándares ministeriales" },
];

const CALCULATION_TYPES: { id: MgaCalculationType; label: string }[] = [
  { id: "ABSOLUTO_ACUMULADO", label: "Absoluto Acumulado (Suma de unidades)" },
  { id: "PORCENTAJE_PROPORCION", label: "Porcentaje / Proporción (%)" },
  { id: "TASA_VARIACION", label: "Tasa de Variación (Crecimiento %)" },
  { id: "COSTO_EFICIENCIA", label: "Costo Eficiencia (Gasto por unidad)" },
];

const FREQUENCIES = [
  { id: "mensual", label: "Mensual" },
  { id: "trimestral", label: "Trimestral" },
  { id: "semestral", label: "Semestral" },
  { id: "anual", label: "Anual" },
  { id: "por_hito", label: "Por Hito / Fase" },
];

export function ProjectIndicatorsDrawer({
  projectId,
  isOpen,
  onClose,
  onIndicatorUpdated,
}: ProjectIndicatorsDrawerProps) {
  const { token } = useAuth();

  const [activeTab, setActiveTab] = useState<"list" | "form" | "record">("list");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [validatingCrema, setValidatingCrema] = useState(false);
  const [indicators, setIndicators] = useState<ProjectIndicator[]>([]);
  const [selectedLevelFilter, setSelectedLevelFilter] = useState<string>("ALL");
  const [expandedIndicatorId, setExpandedIndicatorId] = useState<string | null>(null);

  // Form State para Crear / Editar Indicador
  const [editingId, setEditingId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [level, setLevel] = useState<MgaIndicatorLevel>("PRODUCTO_PRINCIPAL");
  const [calculationType, setCalculationType] = useState<MgaCalculationType>("PORCENTAJE_PROPORCION");
  const [unitOfMeasure, setUnitOfMeasure] = useState("%");
  const [baselineValue, setBaselineValue] = useState("0");
  const [targetValue, setTargetValue] = useState("100");
  const [frequency, setFrequency] = useState("mensual");
  const [cremaResult, setCremaResult] = useState<CremaValidationResult | null>(null);

  // Form State para Reporte Periódico de SPI
  const [targetIndicator, setTargetIndicator] = useState<ProjectIndicator | null>(null);
  const [recordPeriod, setRecordPeriod] = useState("");
  const [recordTarget, setRecordTarget] = useState("");
  const [recordActual, setRecordActual] = useState("");
  const [recordNotes, setRecordNotes] = useState("");
  const [recordEvidenceUrl, setRecordEvidenceUrl] = useState("");

  const loadIndicators = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    try {
      const data = await apiFetch<ProjectIndicator[]>(
        `/projects/${projectId}/advanced-indicators`,
        { token }
      );
      if (Array.isArray(data)) {
        setIndicators(data);
      }
    } catch {
      toast.error("Error al cargar indicadores MGA del proyecto");
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    if (isOpen) {
      void loadIndicators();
    }
  }, [isOpen, loadIndicators]);

  // Ejecución del Asistente CREMA en Tiempo Real
  const handleValidateCrema = async () => {
    if (!token || !projectId || !name.trim()) {
      toast.error("Ingrese el nombre del indicador para ejecutar el asistente CREMA");
      return;
    }
    setValidatingCrema(true);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim(),
        level,
        calculation_type: calculationType,
        unit_of_measure: unitOfMeasure.trim(),
        target_value: parseFloat(targetValue) || 0,
        frequency,
      };
      const res = await apiFetch<CremaValidationResult>(
        `/projects/${projectId}/indicators/validate-crema`,
        {
          method: "POST",
          body: JSON.stringify(payload),
          token,
        }
      );
      setCremaResult(res);
      toast.success(`Evaluación CREMA completada: ${res.score}/100 pts (${res.status})`);
    } catch {
      toast.error("Error al evaluar con el asistente CREMA");
    } finally {
      setValidatingCrema(false);
    }
  };

  const resetForm = () => {
    setEditingId(null);
    setCode("");
    setName("");
    setDescription("");
    setLevel("PRODUCTO_PRINCIPAL");
    setCalculationType("PORCENTAJE_PROPORCION");
    setUnitOfMeasure("%");
    setBaselineValue("0");
    setTargetValue("100");
    setFrequency("mensual");
    setCremaResult(null);
  };

  const handleEditClick = (ind: ProjectIndicator) => {
    setEditingId(ind.id);
    setCode(ind.code || "");
    setName(ind.name);
    setDescription(ind.description || "");
    setLevel((ind.level as MgaIndicatorLevel) || "PRODUCTO_PRINCIPAL");
    setCalculationType((ind.calculation_type as MgaCalculationType) || "PORCENTAJE_PROPORCION");
    setUnitOfMeasure(ind.unit_of_measure || "");
    setBaselineValue(String(ind.baseline_value || 0));
    setTargetValue(String(ind.target_value || 0));
    setFrequency(ind.frequency || "mensual");
    if (ind.crema_evaluation && typeof ind.crema_evaluation === "object" && "criteria" in ind.crema_evaluation) {
      setCremaResult(ind.crema_evaluation as CremaValidationResult);
    } else {
      setCremaResult(null);
    }
    setActiveTab("form");
  };

  const handleSaveIndicator = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId) return;

    if (!name.trim()) {
      toast.error("El nombre del indicador es obligatorio");
      return;
    }

    setSubmitting(true);
    try {
      const payload: ProjectIndicatorCreate = {
        code: code.trim() || undefined,
        name: name.trim(),
        description: description.trim() || undefined,
        level,
        calculation_type: calculationType,
        unit_of_measure: unitOfMeasure.trim() || undefined,
        baseline_value: parseFloat(baselineValue) || 0,
        target_value: parseFloat(targetValue) || 0,
        frequency,
        crema_score: cremaResult?.score,
        crema_evaluation: cremaResult || undefined,
      };

      if (editingId) {
        await apiFetch(`/projects/${projectId}/advanced-indicators/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
          token,
        });
        toast.success("Indicador actualizado exitosamente");
      } else {
        await apiFetch(`/projects/${projectId}/advanced-indicators`, {
          method: "POST",
          body: JSON.stringify(payload),
          token,
        });
        toast.success("Indicador creado con evaluación CREMA");
      }

      resetForm();
      setActiveTab("list");
      void loadIndicators();
      onIndicatorUpdated?.();
    } catch {
      toast.error("Error al guardar indicador");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteIndicator = async (indicatorId: string) => {
    if (!token || !projectId) return;
    if (!window.confirm("¿Está seguro de eliminar este indicador?")) return;

    try {
      await apiFetch(`/projects/${projectId}/advanced-indicators/${indicatorId}`, {
        method: "DELETE",
        token,
      });
      toast.success("Indicador eliminado");
      void loadIndicators();
      onIndicatorUpdated?.();
    } catch {
      toast.error("Error al eliminar indicador");
    }
  };

  const handleOpenRecordModal = (ind: ProjectIndicator) => {
    setTargetIndicator(ind);
    setRecordPeriod("");
    setRecordTarget(String(ind.target_value || ""));
    setRecordActual("");
    setRecordNotes("");
    setRecordEvidenceUrl("");
    setActiveTab("record");
  };

  const handleSaveRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId || !targetIndicator) return;

    if (!recordPeriod.trim()) {
      toast.error("Indique el período de la medición (ej: 2026-Q1)");
      return;
    }

    setSubmitting(true);
    try {
      const payload: ProjectIndicatorRecordCreate = {
        period: recordPeriod.trim(),
        target_value: parseFloat(recordTarget) || 0,
        actual_value: parseFloat(recordActual) || 0,
        notes: recordNotes.trim() || undefined,
        evidence_url: recordEvidenceUrl.trim() || undefined,
      };

      const rec = await apiFetch<ProjectIndicatorRecord>(
        `/projects/${projectId}/indicators/${targetIndicator.id}/records`,
        {
          method: "POST",
          body: JSON.stringify(payload),
          token,
        }
      );

      const spiVal = rec.spi !== null && rec.spi !== undefined ? rec.spi : 1.0;
      toast.success(`Medición guardada: SPI = ${spiVal}`);
      setActiveTab("list");
      setTargetIndicator(null);
      void loadIndicators();
      onIndicatorUpdated?.();
    } catch {
      toast.error("Error al registrar medición periódica");
    } finally {
      setSubmitting(false);
    }
  };

  // Métricas Consolidadas y Semáforo SPI
  const filteredIndicators = useMemo(() => {
    if (selectedLevelFilter === "ALL") return indicators;
    return indicators.filter((i) => i.level === selectedLevelFilter);
  }, [indicators, selectedLevelFilter]);

  const spiStats = useMemo(() => {
    let optimal = 0;
    let warning = 0;
    let critical = 0;
    let totalScore = 0;
    let scoredCount = 0;

    indicators.forEach((i) => {
      if (i.last_spi !== null && i.last_spi !== undefined) {
        if (i.last_spi >= 1.0) optimal++;
        else if (i.last_spi >= 0.8) warning++;
        else critical++;
      }
      if (i.crema_score !== null && i.crema_score !== undefined) {
        totalScore += i.crema_score;
        scoredCount++;
      }
    });

    const avgCrema = scoredCount > 0 ? Math.round(totalScore / scoredCount) : 0;
    return { optimal, warning, critical, avgCrema };
  }, [indicators]);

  // SPI calculado en vivo en el formulario de reporte
  const calculatedSpi = useMemo(() => {
    const t = parseFloat(recordTarget) || 0;
    const a = parseFloat(recordActual) || 0;
    if (t > 0) return Math.round((a / t) * 100) / 100;
    return 1.0;
  }, [recordTarget, recordActual]);

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Indicadores MGA & Semáforo CREMA"
      width={780}
    >
      <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]">
        {/* Encabezado y Navegación de Pestañas */}
        <div className="px-5 pt-3 pb-3 border-b border-[hsl(var(--border))] space-y-3 bg-[hsl(var(--surface-2))]/50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold flex items-center gap-2">
                <BarChart3 size={18} className="text-[hsl(var(--primary))]" />
                Metodología General Ajustada (MGA) & CREMA
              </h2>
              <p className="text-3xs text-[hsl(var(--muted-foreground))]">
                Monitoreo riguroso de eficacia, productos y semáforo SPI de avance periódico
              </p>
            </div>
            <div className="flex items-center gap-1.5 bg-[hsl(var(--surface-1))] p-1 rounded-lg border border-[hsl(var(--border))]">
              <span className="text-3xs font-semibold px-2 text-[hsl(var(--muted-foreground))]">
                Calidad CREMA:
              </span>
              <span
                className={clsx(
                  "text-2xs font-extrabold px-2 py-0.5 rounded",
                  spiStats.avgCrema >= 85
                    ? "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]"
                    : spiStats.avgCrema >= 70
                    ? "bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))]"
                    : "bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))]"
                )}
              >
                {spiStats.avgCrema}/100
              </span>
            </div>
          </div>

          {/* Resumen Semáforo SPI Superior */}
          <div className="grid grid-cols-4 gap-2 pt-1">
            <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                <Activity size={16} />
              </div>
              <div>
                <p className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">Total Ind.</p>
                <p className="text-xs font-black">{indicators.length}</p>
              </div>
            </div>

            <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]">
                <CheckCircle2 size={16} />
              </div>
              <div>
                <p className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">SPI ≥ 1.0 (Óptimo)</p>
                <p className="text-xs font-black text-[hsl(var(--success))]">{spiStats.optimal}</p>
              </div>
            </div>

            <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))]">
                <AlertTriangle size={16} />
              </div>
              <div>
                <p className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">SPI 0.8-0.99</p>
                <p className="text-xs font-black text-[hsl(var(--warning))]">{spiStats.warning}</p>
              </div>
            </div>

            <div className="p-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))]">
                <TrendingUp size={16} className="rotate-180" />
              </div>
              <div>
                <p className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">SPI &lt; 0.80 (Riesgo)</p>
                <p className="text-xs font-black text-[hsl(var(--destructive))]">{spiStats.critical}</p>
              </div>
            </div>
          </div>

          {/* Selector de Pestañas */}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={() => {
                resetForm();
                setActiveTab("list");
              }}
              className={clsx(
                "px-3 py-1.5 rounded-md text-2xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5",
                activeTab === "list"
                  ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                  : "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))]"
              )}
            >
              <BarChart3 size={13} /> Matriz MGA ({indicators.length})
            </button>
            <button
              onClick={() => {
                resetForm();
                setActiveTab("form");
              }}
              className={clsx(
                "px-3 py-1.5 rounded-md text-2xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5",
                activeTab === "form"
                  ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                  : "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))]"
              )}
            >
              <Plus size={13} /> {editingId ? "Editar Indicador" : "Nuevo Indicador & Asistente CREMA"}
            </button>
            {targetIndicator && (
              <button
                onClick={() => setActiveTab("record")}
                className={clsx(
                  "px-3 py-1.5 rounded-md text-2xs font-bold uppercase tracking-wider transition-all flex items-center gap-1.5",
                  activeTab === "record"
                    ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                    : "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))]"
                )}
              >
                <Clock size={13} /> Reportar Medición SPI
              </button>
            )}
          </div>
        </div>

        {/* Contenido Principal */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* TAB 1: LISTADO DE INDICADORES Y SEMÁFORO SPI */}
          {activeTab === "list" && (
            <div className="space-y-4">
              {/* Filtro por Nivel MGA */}
              <div className="flex items-center justify-between gap-2 overflow-x-auto pb-1">
                <div className="flex items-center gap-1.5 text-2xs">
                  <span className="text-[hsl(var(--muted-foreground))] font-semibold flex items-center gap-1">
                    <Sliders size={12} /> Nivel:
                  </span>
                  <button
                    onClick={() => setSelectedLevelFilter("ALL")}
                    className={clsx(
                      "px-2.5 py-1 rounded-md text-3xs font-bold uppercase transition-all",
                      selectedLevelFilter === "ALL"
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                        : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))]"
                    )}
                  >
                    Todos ({indicators.length})
                  </button>
                  {MGA_LEVELS.map((lvl) => {
                    const count = indicators.filter((i) => i.level === lvl.id).length;
                    return (
                      <button
                        key={lvl.id}
                        onClick={() => setSelectedLevelFilter(lvl.id)}
                        className={clsx(
                          "px-2 py-1 rounded-md text-3xs font-semibold whitespace-nowrap transition-all",
                          selectedLevelFilter === lvl.id
                            ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                            : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))]"
                        )}
                      >
                        {lvl.label.split("/")[0]} ({count})
                      </button>
                    );
                  })}
                </div>
                <button
                  onClick={() => loadIndicators()}
                  className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] transition-colors"
                  title="Recargar indicadores"
                >
                  <RotateCw size={14} className={clsx(loading && "animate-spin")} />
                </button>
              </div>

              {loading ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-[hsl(var(--muted-foreground))]">
                  <RotateCw size={24} className="animate-spin text-[hsl(var(--primary))]" />
                  <p className="text-xs font-semibold">Cargando indicadores y cálculo de SPI...</p>
                </div>
              ) : filteredIndicators.length === 0 ? (
                <div className="py-12 px-4 rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 flex flex-col items-center justify-center text-center gap-3">
                  <div className="p-3 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                    <BarChart3 size={28} />
                  </div>
                  <div className="max-w-xs">
                    <h3 className="text-xs font-bold">No hay indicadores en este nivel</h3>
                    <p className="text-3xs text-[hsl(var(--muted-foreground))] mt-1">
                      Cree indicadores de resultado o producto con la metodología MGA y califíquelos con el Asistente CREMA.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      resetForm();
                      setActiveTab("form");
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide hover:opacity-90 transition-all flex items-center gap-1.5"
                  >
                    <Plus size={13} /> Crear Primer Indicador
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredIndicators.map((ind) => {
                    const isExpanded = expandedIndicatorId === ind.id;
                    const spi = ind.last_spi;
                    const progress =
                      ind.target_value > 0
                        ? Math.min(100, Math.round((ind.current_value / ind.target_value) * 100))
                        : 0;

                    return (
                      <div
                        key={ind.id}
                        className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 hover:bg-[hsl(var(--surface-2))] transition-all overflow-hidden"
                      >
                        <div className="p-4 space-y-3">
                          {/* Fila Superior: Código, Nivel MGA y Score CREMA */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono text-3xs font-extrabold px-2 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))]">
                                {ind.code || "IND"}
                              </span>
                              <span className="text-3xs font-bold px-2 py-0.5 rounded bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
                                {ind.level}
                              </span>
                              <span className="text-3xs text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                                <Clock size={11} /> {ind.frequency}
                              </span>
                            </div>

                            <div className="flex items-center gap-1.5">
                              {ind.crema_score !== null && ind.crema_score !== undefined && (
                                <span
                                  className={clsx(
                                    "text-3xs font-extrabold px-2 py-0.5 rounded-full flex items-center gap-1 border",
                                    ind.crema_score >= 85
                                      ? "bg-[hsl(var(--success))]/15 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                                      : ind.crema_score >= 70
                                      ? "bg-[hsl(var(--primary))]/15 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]"
                                      : "bg-[hsl(var(--warning))]/15 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]"
                                  )}
                                  title="Calificación metodológica CREMA"
                                >
                                  <Sparkles size={10} /> CREMA: {ind.crema_score}/100
                                </span>
                              )}

                              {/* Semáforo SPI */}
                              <div
                                className={clsx(
                                  "text-3xs font-black px-2 py-0.5 rounded-full flex items-center gap-1 border",
                                  spi === null || spi === undefined
                                    ? "bg-[hsl(var(--surface-3))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]"
                                    : spi >= 1.0
                                    ? "bg-[hsl(var(--success))]/20 border-[hsl(var(--success))]/40 text-[hsl(var(--success))]"
                                    : spi >= 0.8
                                    ? "bg-[hsl(var(--warning))]/20 border-[hsl(var(--warning))]/40 text-[hsl(var(--warning))]"
                                    : "bg-[hsl(var(--destructive))]/20 border-[hsl(var(--destructive))]/40 text-[hsl(var(--destructive))]"
                                )}
                              >
                                {spi === null || spi === undefined ? (
                                  <>Sin registros SPI</>
                                ) : (
                                  <>
                                    <span
                                      className={clsx(
                                        "w-2 h-2 rounded-full",
                                        spi >= 1.0
                                          ? "bg-[hsl(var(--success))]"
                                          : spi >= 0.8
                                          ? "bg-[hsl(var(--warning))]"
                                          : "bg-[hsl(var(--destructive))]"
                                      )}
                                    />
                                    SPI: {spi.toFixed(2)}
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Título y Descripción */}
                          <div>
                            <h4 className="text-xs font-bold text-[hsl(var(--foreground))]">{ind.name}</h4>
                            {ind.description && (
                              <p className="text-3xs text-[hsl(var(--muted-foreground))] mt-0.5 line-clamp-2">
                                {ind.description}
                              </p>
                            )}
                          </div>

                          {/* Barra de Progreso y Metas */}
                          <div className="space-y-1.5 pt-1">
                            <div className="flex items-center justify-between text-3xs font-semibold">
                              <span className="text-[hsl(var(--muted-foreground))]">
                                Avance Actual:{" "}
                                <strong className="text-[hsl(var(--foreground))]">
                                  {ind.current_value} {ind.unit_of_measure}
                                </strong>
                              </span>
                              <span>
                                Meta:{" "}
                                <strong className="text-[hsl(var(--foreground))]">
                                  {ind.target_value} {ind.unit_of_measure}
                                </strong>{" "}
                                ({progress}%)
                              </span>
                            </div>
                            <div className="h-2 w-full bg-[hsl(var(--surface-3))] rounded-full overflow-hidden border border-[hsl(var(--border))]">
                              <div
                                className={clsx(
                                  "h-full transition-all duration-500 rounded-full",
                                  progress >= 100
                                    ? "bg-[hsl(var(--success))]"
                                    : progress >= 50
                                    ? "bg-[hsl(var(--primary))]"
                                    : "bg-[hsl(var(--warning))]"
                                )}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>

                          {/* Acciones y Botones */}
                          <div className="pt-2 border-t border-[hsl(var(--border))]/60 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleOpenRecordModal(ind)}
                                className="px-2.5 py-1 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-3xs font-bold uppercase tracking-wider hover:opacity-90 transition-all flex items-center gap-1 shadow-sm"
                              >
                                <Plus size={11} /> Medir Avance
                              </button>
                              <button
                                onClick={() =>
                                  setExpandedIndicatorId(isExpanded ? null : ind.id)
                                }
                                className="px-2.5 py-1 rounded-md bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] text-3xs font-semibold border border-[hsl(var(--border))] transition-all flex items-center gap-1"
                              >
                                <History size={11} /> Historial ({ind.records_count || 0})
                              </button>
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleEditClick(ind)}
                                className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                                title="Editar indicador"
                              >
                                <Edit2 size={13} />
                              </button>
                              <button
                                onClick={() => handleDeleteIndicator(ind.id)}
                                className="p-1 rounded hover:bg-[hsl(var(--destructive))]/15 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))]"
                                title="Eliminar indicador"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Desglose de Historial de Mediciones (Expandible) */}
                        {isExpanded && (
                          <div className="px-4 pb-4 pt-2 bg-[hsl(var(--surface-1))] border-t border-[hsl(var(--border))] space-y-2">
                            <div className="flex items-center justify-between">
                              <h5 className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                                <History size={12} /> Registro de Mediciones Periódicas (SPI)
                              </h5>
                              <span className="text-3xs text-[hsl(var(--muted-foreground))]">
                                Responsable: {ind.creator_name || "Sistema"}
                              </span>
                            </div>

                            {(!ind.records || ind.records.length === 0) ? (
                              <p className="text-3xs text-[hsl(var(--muted-foreground))] py-2 italic text-center">
                                No hay mediciones periódicas reportadas aún para este indicador.
                              </p>
                            ) : (
                              <div className="space-y-1.5">
                                {ind.records.map((rec) => (
                                  <div
                                    key={rec.id}
                                    className="p-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-between text-3xs"
                                  >
                                    <div className="flex items-center gap-2">
                                      <span className="font-bold text-[hsl(var(--foreground))] px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))]">
                                        {rec.period}
                                      </span>
                                      <span className="text-[hsl(var(--muted-foreground))]">
                                        Meta: {rec.target_value} | Real:{" "}
                                        <strong className="text-[hsl(var(--foreground))]">
                                          {rec.actual_value}
                                        </strong>
                                      </span>
                                      {rec.notes && (
                                        <span className="text-[hsl(var(--muted-foreground))] truncate max-w-xs">
                                          — {rec.notes}
                                        </span>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                      {rec.evidence_url && (
                                        <a
                                          href={rec.evidence_url}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="text-[hsl(var(--primary))] hover:underline flex items-center gap-0.5"
                                        >
                                          <ExternalLink size={10} /> Evidencia
                                        </a>
                                      )}
                                      <span
                                        className={clsx(
                                          "px-2 py-0.5 rounded font-black",
                                          (rec.spi || 1) >= 1.0
                                            ? "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]"
                                            : (rec.spi || 1) >= 0.8
                                            ? "bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))]"
                                            : "bg-[hsl(var(--destructive))]/15 text-[hsl(var(--destructive))]"
                                        )}
                                      >
                                        SPI: {(rec.spi || 1).toFixed(2)}
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FORMULARIO Y ASISTENTE METODOLÓGICO CREMA */}
          {activeTab === "form" && (
            <form onSubmit={handleSaveIndicator} className="space-y-4">
              <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold flex items-center gap-1.5 text-[hsl(var(--foreground))]">
                    <Layers size={14} className="text-[hsl(var(--primary))]" />
                    {editingId ? "Editar Indicador MGA" : "Definición Metodológica del Indicador MGA"}
                  </h3>
                  <button
                    type="button"
                    onClick={handleValidateCrema}
                    disabled={validatingCrema}
                    className="px-2.5 py-1 rounded-md bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/25 text-3xs font-extrabold uppercase tracking-wide border border-[hsl(var(--primary))]/30 transition-all flex items-center gap-1.5"
                  >
                    <Sparkles size={12} className={clsx(validatingCrema && "animate-spin")} />
                    {validatingCrema ? "Auditando..." : "Auditar Criterios CREMA"}
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-1 space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Código (Opcional)
                    </label>
                    <input
                      type="text"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="ej: IND-001"
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="col-span-2 space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Nombre del Indicador *
                    </label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="ej: Porcentaje de miembros capacitados en liderazgo"
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    Descripción / Justificación Metodológica
                  </label>
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Detalle el objetivo que persigue este indicador y su relevancia para la sede..."
                    className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Nivel MGA Canónico *
                    </label>
                    <select
                      value={level}
                      onChange={(e) => setLevel(e.target.value as MgaIndicatorLevel)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      {MGA_LEVELS.map((lvl) => (
                        <option key={lvl.id} value={lvl.id}>
                          {lvl.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Tipo de Cálculo MGA *
                    </label>
                    <select
                      value={calculationType}
                      onChange={(e) =>
                        setCalculationType(e.target.value as MgaCalculationType)
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      {CALCULATION_TYPES.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3">
                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Unidad Medida *
                    </label>
                    <input
                      type="text"
                      value={unitOfMeasure}
                      onChange={(e) => setUnitOfMeasure(e.target.value)}
                      placeholder="%, personas, USD"
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Línea Base
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={baselineValue}
                      onChange={(e) => setBaselineValue(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Meta Proyecto *
                    </label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={targetValue}
                      onChange={(e) => setTargetValue(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Periodicidad *
                    </label>
                    <select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                      {FREQUENCIES.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* PANEL DEL ASISTENTE CREMA */}
              {cremaResult && (
                <div className="p-4 rounded-xl border border-[hsl(var(--primary))]/30 bg-[hsl(var(--primary))]/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Award size={18} className="text-[hsl(var(--primary))]" />
                      <h4 className="text-xs font-bold text-[hsl(var(--foreground))]">
                        Diagnóstico Metodológico CREMA (MGA / BID)
                      </h4>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-3xs font-bold uppercase text-[hsl(var(--muted-foreground))]">
                        Estado:
                      </span>
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-3xs font-extrabold uppercase",
                          cremaResult.status === "EXCELENTE"
                            ? "bg-[hsl(var(--success))]/20 text-[hsl(var(--success))]"
                            : cremaResult.status === "BUENO"
                            ? "bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]"
                            : "bg-[hsl(var(--warning))]/20 text-[hsl(var(--warning))]"
                        )}
                      >
                        {cremaResult.status} ({cremaResult.score}/100)
                      </span>
                    </div>
                  </div>

                  <p className="text-3xs text-[hsl(var(--foreground))]/80">{cremaResult.summary}</p>

                  {/* Tarjetas de los 5 criterios C, R, E, M, A */}
                  <div className="grid grid-cols-5 gap-2 pt-1">
                    {Object.entries(cremaResult.criteria).map(([key, detail]) => (
                      <div
                        key={key}
                        className={clsx(
                          "p-2 rounded-lg border text-3xs space-y-1",
                          detail.passed
                            ? "bg-[hsl(var(--surface-1))] border-[hsl(var(--success))]/30"
                            : "bg-[hsl(var(--surface-1))] border-[hsl(var(--warning))]/40"
                        )}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span>{key} ({detail.score}/20)</span>
                          {detail.passed ? (
                            <Check size={12} className="text-[hsl(var(--success))]" />
                          ) : (
                            <AlertTriangle size={12} className="text-[hsl(var(--warning))]" />
                          )}
                        </div>
                        <p className="text-3xs font-semibold text-[hsl(var(--muted-foreground))] truncate">
                          {detail.name || key}
                        </p>
                        {detail.recommendations && detail.recommendations.length > 0 && (
                          <p className="text-3xs text-[hsl(var(--warning))] line-clamp-2">
                            {detail.recommendations[0]}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Botones de Acción */}
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    resetForm();
                    setActiveTab("list");
                  }}
                  className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] text-2xs font-semibold text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wider hover:opacity-90 transition-all flex items-center gap-1.5 shadow-md"
                >
                  <Save size={13} className={clsx(submitting && "animate-spin")} />
                  {submitting ? "Guardando..." : editingId ? "Actualizar Indicador" : "Crear Indicador con Sello CREMA"}
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: REPORTE DE MEDICIÓN PERIÓDICA (SPI) */}
          {activeTab === "record" && targetIndicator && (
            <form onSubmit={handleSaveRecord} className="space-y-4">
              <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold flex items-center gap-1.5 text-[hsl(var(--foreground))]">
                    <Clock size={14} className="text-[hsl(var(--primary))]" />
                    Reportar Medición Periódica & Cálculo SPI
                  </h3>
                  <span className="font-mono text-3xs font-bold px-2 py-0.5 rounded bg-[hsl(var(--surface-3))]">
                    {targetIndicator.code || "IND"}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] space-y-1">
                  <p className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-semibold">Indicador:</p>
                  <p className="text-xs font-bold">{targetIndicator.name}</p>
                  <p className="text-3xs text-[hsl(var(--muted-foreground))]">
                    Unidad: <strong>{targetIndicator.unit_of_measure}</strong> | Meta Global:{" "}
                    <strong>{targetIndicator.target_value}</strong>
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Período *
                    </label>
                    <input
                      type="text"
                      required
                      value={recordPeriod}
                      onChange={(e) => setRecordPeriod(e.target.value)}
                      placeholder="ej: 2026-Q1, 2026-M04"
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Meta del Período *
                    </label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={recordTarget}
                      onChange={(e) => setRecordTarget(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                      Valor Real Alcanzado *
                    </label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={recordActual}
                      onChange={(e) => setRecordActual(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                  </div>
                </div>

                {/* Previsualización SPI en Tiempo Real */}
                <div
                  className={clsx(
                    "p-3 rounded-lg border flex items-center justify-between",
                    calculatedSpi >= 1.0
                      ? "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                      : calculatedSpi >= 0.8
                      ? "bg-[hsl(var(--warning))]/10 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]"
                      : "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Activity size={16} />
                    <div>
                      <p className="text-3xs uppercase font-extrabold tracking-wider">
                        Índice de Desempeño (SPI = Real / Meta):
                      </p>
                      <p className="text-xs font-bold">
                        {calculatedSpi >= 1.0
                          ? "Cumplimiento Óptimo / En Cronograma"
                          : calculatedSpi >= 0.8
                          ? "Alerta Moderada / Retraso Leve"
                          : "Alerta Crítica / Subejecución Severa"}
                      </p>
                    </div>
                  </div>
                  <span className="text-base font-black">{calculatedSpi.toFixed(2)}</span>
                </div>

                <div className="space-y-1">
                  <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    URL de Evidencia o Respaldo (Google Drive, Acta, etc.)
                  </label>
                  <input
                    type="url"
                    value={recordEvidenceUrl}
                    onChange={(e) => setRecordEvidenceUrl(e.target.value)}
                    placeholder="https://..."
                    className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    Observaciones y Justificación Cualitativa
                  </label>
                  <textarea
                    rows={2}
                    value={recordNotes}
                    onChange={(e) => setRecordNotes(e.target.value)}
                    placeholder="Factores que facilitaron o retrasaron el cumplimiento de la meta..."
                    className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                  />
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("list");
                    setTargetIndicator(null);
                  }}
                  className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] text-2xs font-semibold text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wider hover:opacity-90 transition-all flex items-center gap-1.5 shadow-md"
                >
                  <FileCheck2 size={13} className={clsx(submitting && "animate-spin")} />
                  {submitting ? "Registrando..." : "Registrar Avance Periódico"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </RightPanel>
  );
}

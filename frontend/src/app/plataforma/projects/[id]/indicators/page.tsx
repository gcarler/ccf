"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectIndicator,
  MgaIndicatorLevel,
  ProjectExecutionMatrix,
  ProjectExecutionSyncResponse,
} from "@/types/projects";
import { ProjectIndicatorsDrawer } from "@/components/projects/ProjectIndicatorsDrawer";
import { KPI_EXECUTION_SOURCES } from "@/components/projects/ProjectKpiDrawer";
import {
  BarChart3,
  TrendingUp,
  Plus,
  RotateCw,
  Activity,
  Clock,
  ChevronLeft,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Layers,
  DollarSign,
  Gauge,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";

const MGA_LEVELS: { id: MgaIndicatorLevel; label: string; desc: string }[] = [
  { id: "RESULTADO_EFICACIA", label: "Resultado / Eficacia", desc: "Impacto y logro de objetivos de largo plazo del proyecto" },
  { id: "PRODUCTO_PRINCIPAL", label: "Producto Principal", desc: "Entregables tangibles directos derivados de las actividades" },
  { id: "PRODUCTO_SECUNDARIO", label: "Producto Secundario", desc: "Entregables complementarios y de soporte operativo" },
  { id: "GESTION_PROCESO", label: "Gestión / Proceso", desc: "Eficiencia de ejecución de procesos y cumplimiento de hitos" },
  { id: "EFICIENCIA", label: "Eficiencia", desc: "Optimización de costos, recursos y rendimiento operativo" },
  { id: "CALIDAD", label: "Calidad", desc: "Satisfacción, apego a estándares y estándares ministeriales" },
];

export default function ProjectIndicatorsPage() {
  const params = useParams();
  const projectId = (params?.id as string) ?? "";
  const { token } = useAuth();

  const [loading, setLoading] = useState(true);
  const [syncingPro, setSyncingPro] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [hasLoadedIndicators, setHasLoadedIndicators] = useState(false);
  const [projectTitle, setProjectTitle] = useState("Proyecto");
  const [executionMatrix, setExecutionMatrix] = useState<ProjectExecutionMatrix | null>(null);
  const [indicators, setIndicators] = useState<ProjectIndicator[]>([]);
  const [selectedLevelFilter, setSelectedLevelFilter] = useState<string>("ALL");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const activeLoadController = useRef<AbortController | null>(null);
  const loadedProjectId = useRef<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token || !projectId) return;
    activeLoadController.current?.abort();
    const controller = new AbortController();
    activeLoadController.current = controller;
    if (loadedProjectId.current !== projectId) {
      setProjectTitle("Proyecto");
      setExecutionMatrix(null);
      setIndicators([]);
      setHasLoadedIndicators(false);
      setLoadError(false);
    }
    setLoading(true);
    try {
      const [projData, indData] = await Promise.all([
        apiFetch<{ title: string; execution_matrix?: ProjectExecutionMatrix | null }>(
          `/projects/${projectId}`,
          { token, signal: controller.signal }
        ).catch(() => ({ title: "Proyecto", execution_matrix: null })),
        apiFetch<ProjectIndicator[]>(`/projects/${projectId}/advanced-indicators`, {
          token,
          signal: controller.signal,
        }),
      ]);
      if (activeLoadController.current !== controller) return;
      setProjectTitle(projData?.title || "Proyecto");
      setExecutionMatrix(projData?.execution_matrix || null);
      if (!Array.isArray(indData)) throw new Error("Respuesta de indicadores inválida");
      setIndicators(indData);
      setLoadError(false);
      setHasLoadedIndicators(true);
      loadedProjectId.current = projectId;
    } catch {
      if (activeLoadController.current !== controller) return;
      setLoadError(true);
      toast.error("Error al cargar indicadores MGA");
    } finally {
      if (activeLoadController.current === controller) {
        activeLoadController.current = null;
        setLoading(false);
      }
    }
  }, [projectId, token]);

  useEffect(() => {
    void loadData();
    return () => {
      activeLoadController.current?.abort();
      activeLoadController.current = null;
    };
  }, [loadData]);

  const handleSyncAndSeedPro = async () => {
    if (!token || !projectId) return;
    setSyncingPro(true);
    try {
      const res = await apiFetch<ProjectExecutionSyncResponse>(
        `/projects/${projectId}/indicators/sync-execution`,
        {
          method: "POST",
          token,
          body: JSON.stringify({
            seed_pro_indicators: true,
            seed_pro_kpis: true,
          }),
        }
      );
      if (res?.execution_matrix) {
        setExecutionMatrix(res.execution_matrix);
      }
      toast.success?.(
        `Sincronización Pro completada (${res?.synced_indicators ?? 0} indicadores y ${res?.synced_kpis ?? 0} KPIs actualizados)`
      );
      await loadData();
    } catch {
      toast.error("Error al sincronizar matriz de ejecución Pro");
    } finally {
      setSyncingPro(false);
    }
  };

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

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] overflow-y-auto">
      {/* Header Superior y Breadcrumb */}
      <div
        data-workspace-toolbar
        className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 sticky top-0 z-10 backdrop-blur-md"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href={`/plataforma/projects/${projectId}`}
              className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-all flex items-center justify-center"
              title="Volver al proyecto"
            >
              <ChevronLeft size={16} />
            </Link>
            <div>
              <div className="flex items-center gap-2 text-2xs text-[hsl(var(--text-secondary))] uppercase font-bold tracking-wider">
                <Link href="/plataforma/projects" className="hover:text-[hsl(var(--primary))] transition-colors">
                  Proyectos
                </Link>
                <span>/</span>
                <Link
                  href={`/plataforma/projects/${projectId}`}
                  className="hover:text-[hsl(var(--primary))] transition-colors"
                >
                  {projectTitle}
                </Link>
                <span>/</span>
                <span className="text-[hsl(var(--text-primary))]">Indicadores y Desempeño (IDP)</span>
              </div>
              <h1 className="text-lg font-extrabold tracking-tight flex items-center gap-2 mt-0.5">
                <BarChart3 size={20} className="text-[hsl(var(--primary))]" />
                Tablero de Indicadores y Desempeño (IDP)
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleSyncAndSeedPro()}
              disabled={syncingPro}
              className="px-3 py-1.5 rounded-lg border border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] text-xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/20 active:scale-95 transition-all flex items-center gap-1.5"
            >
              <Sparkles size={14} className={clsx(syncingPro && "animate-spin")} />
              {syncingPro ? "Sincronizando..." : "Sincronizar & Sembrar 6 Pro"}
            </button>
            <button
              onClick={() => loadData()}
              aria-label="Recargar datos de indicadores"
              className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
              title="Recargar datos"
            >
              <RotateCw size={15} className={clsx(loading && "animate-spin")} />
            </button>
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-2 shadow-sm"
            >
              <Plus size={15} /> Asistente CREMA & Medición
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Tarjetas Analíticas del Semáforo SPI Superior */}
        {hasLoadedIndicators && !loadError && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] shadow-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-extrabold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Total Indicadores
                </span>
                <Activity size={18} className="text-[hsl(var(--primary))]" />
              </div>
              <p className="text-2xl font-extrabold text-[hsl(var(--text-primary))]">{indicators.length}</p>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Indicadores IDP activos</p>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--success))]/30 shadow-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-extrabold uppercase tracking-wider text-[hsl(var(--success))]">
                  🟢 SPI ≥ 1.0 (Óptimo)
                </span>
                <CheckCircle2 size={18} className="text-[hsl(var(--success))]" />
              </div>
              <p className="text-2xl font-extrabold text-[hsl(var(--success))]">{spiStats.optimal}</p>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Cumpliendo o superando metas</p>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--warning))]/30 shadow-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-extrabold uppercase tracking-wider text-[hsl(var(--warning))]">
                  🟡 SPI 0.80 - 0.99 (Alerta)
                </span>
                <AlertTriangle size={18} className="text-[hsl(var(--warning))]" />
              </div>
              <p className="text-2xl font-extrabold text-[hsl(var(--warning))]">{spiStats.warning}</p>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Desviación moderada de avance</p>
            </div>

            <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--destructive))]/30 shadow-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-extrabold uppercase tracking-wider text-[hsl(var(--destructive))]">
                  🔴 SPI &lt; 0.80 (Riesgo)
                </span>
                <TrendingUp size={18} className="rotate-180 text-[hsl(var(--destructive))]" />
              </div>
              <p className="text-2xl font-extrabold text-[hsl(var(--destructive))]">{spiStats.critical}</p>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">Subejecución o retraso crítico</p>
            </div>
          </div>
        )}

        {/* Panel de Ejecución Real: 3 Frentes + Matriz de Tributación Subtareas -> Actividades -> Componentes EDT -> Proyecto */}
        {hasLoadedIndicators && !loadError && executionMatrix && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Frente 1: Tiempo */}
              <div className="p-4 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--info))] flex items-center gap-1.5">
                    <Clock size={15} /> Frente 1 · Tiempo y Cronograma
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-2xs font-extrabold bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))]">
                    SPI {executionMatrix.frentes.tiempo.spi.toFixed(2)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-2xs">
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Avance Físico Ponderado</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.tiempo.progress_pct}%
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Horas Ejecutadas / Est.</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.tiempo.actual_hours} / {executionMatrix.frentes.tiempo.estimated_hours} h
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Eficiencia de Horas</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.tiempo.hours_efficiency_pct}%
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Hitos a Tiempo</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.tiempo.milestones_ontime_pct}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Frente 2: Financiero */}
              <div className="p-4 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--warning))] flex items-center gap-1.5">
                    <DollarSign size={15} /> Frente 2 · Financiero y Costo
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-2xs font-extrabold bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))]">
                    CPI {executionMatrix.frentes.financiero.cpi.toFixed(2)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-2xs">
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Presupuesto BAC</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      ${executionMatrix.frentes.financiero.bac.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Gasto Real AC</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      ${executionMatrix.frentes.financiero.ac.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Ejecución Presupuestal</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.financiero.burn_rate_pct}%
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Disponible</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      ${executionMatrix.frentes.financiero.remaining_budget.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Frente 3: Cruce Tiempo x Financiero EVM */}
              <div className="p-4 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                    <Gauge size={15} /> Frente 3 · Cruce Tiempo × Costo (EVM)
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-2xs font-extrabold bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))]">
                    CR {executionMatrix.frentes.cruce_evm.cr.toFixed(2)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-2xs">
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Valor Ganado (EV)</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      ${executionMatrix.frentes.cruce_evm.ev.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Proyección EAC</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      ${executionMatrix.frentes.cruce_evm.eac.toLocaleString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Brecha Físico vs Fin.</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.frentes.cruce_evm.balance_gap_pct > 0 ? "+" : ""}
                      {executionMatrix.frentes.cruce_evm.balance_gap_pct}%
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                    <p className="text-[hsl(var(--text-secondary))]">Riesgos Mitigados RAID</p>
                    <p className="text-sm font-extrabold text-[hsl(var(--text-primary))]">
                      {executionMatrix.raid_summary.mitigated_pct}%
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Matriz de Tributación: Subtareas -> Actividades -> Componentes EDT -> Proyecto */}
            {executionMatrix.rollup_hierarchy.components.length > 0 && (
              <div className="p-4 rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--text-primary))] flex items-center gap-1.5">
                      <Layers size={15} className="text-[hsl(var(--primary))]" />
                      Matriz de Tributación EDT (Subtareas → Actividades → Componentes → Proyecto)
                    </h2>
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">
                      Ponderación continua por horas estimadas en paquetes de trabajo y por presupuesto BAC en componentes EDT
                    </p>
                  </div>
                  <span className="px-2.5 py-1 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] text-2xs font-extrabold border border-[hsl(var(--primary))]/30">
                    Avance Global Roll-Up: {executionMatrix.rollup_hierarchy.overall_progress_pct}%
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {executionMatrix.rollup_hierarchy.components.map((comp) => (
                    <div
                      key={comp.component_id}
                      className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-2xs font-extrabold px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))]">
                            {comp.code}
                          </span>
                          <span className="text-xs font-bold text-[hsl(var(--text-primary))]">
                            {comp.name}
                          </span>
                        </div>
                        <span className="text-2xs font-bold text-[hsl(var(--text-secondary))]">
                          Peso BAC: {comp.budget_weight_pct}%
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-2xs text-[hsl(var(--text-secondary))]">
                        <span>
                          Físico: <strong className="text-[hsl(var(--text-primary))]">{comp.physical_progress_pct}%</strong>
                        </span>
                        <span>
                          Financiero: <strong className="text-[hsl(var(--text-primary))]">{comp.financial_progress_pct}%</strong>
                        </span>
                        <span>
                          SPI: <strong className="text-[hsl(var(--text-primary))]">{comp.spi.toFixed(2)}</strong>
                        </span>
                        <span>
                          CPI: <strong className="text-[hsl(var(--text-primary))]">{comp.cpi.toFixed(2)}</strong>
                        </span>
                        <span>
                          Act/Sub: <strong className="text-[hsl(var(--text-primary))]">{comp.activities_count}/{comp.subtasks_count}</strong>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Barra de Filtros por Nivel MGA */}
        {hasLoadedIndicators && !loadError && (
          <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-3 overflow-x-auto">
            <div className="flex items-center gap-1.5 text-2xs">
              <span className="font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider text-2xs flex items-center gap-1">
                <Sliders size={12} /> Niveles:
              </span>
              <button
                onClick={() => setSelectedLevelFilter("ALL")}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-2xs font-bold uppercase transition-all",
                  selectedLevelFilter === "ALL"
                    ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                    : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]"
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
                      "px-3 py-1.5 rounded-lg text-2xs font-semibold whitespace-nowrap transition-all",
                      selectedLevelFilter === lvl.id
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                        : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]"
                    )}
                  >
                    {lvl.label} ({count})
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                Sello Metodológico:
              </span>
              <span className="text-2xs font-extrabold px-2 py-0.5 rounded bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
                Score CREMA Promedio: {spiStats.avgCrema}/100
              </span>
            </div>
          </div>
        )}

        {/* Lista de Tarjetas de Indicadores */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-[hsl(var(--text-secondary))]">
            <RotateCw size={28} className="animate-spin text-[hsl(var(--primary))]" />
            <p className="text-xs font-semibold">Cargando tablero IDP y mediciones periódicas...</p>
          </div>
        ) : loadError ? (
          <div
            role="alert"
            className="py-16 px-4 rounded-2xl border border-[hsl(var(--destructive))]/30 bg-[hsl(var(--destructive))]/5 flex flex-col items-center justify-center text-center gap-3"
          >
            <p className="text-sm font-semibold">
              No se pudieron cargar los indicadores. No podemos confirmar que el proyecto esté vacío.
            </p>
            <button
              type="button"
              onClick={() => void loadData()}
              className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold"
            >
              Reintentar
            </button>
          </div>
        ) : filteredIndicators.length === 0 ? (
          <div className="py-16 px-4 rounded-2xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/30 flex flex-col items-center justify-center text-center gap-3">
            <div className="p-4 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
              <BarChart3 size={36} />
            </div>
            <div className="max-w-md">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">
                Sin indicadores configurados
              </h3>
              <p className="text-2xs text-[hsl(var(--text-secondary))] mt-1">
                Configure indicadores de eficacia o producto utilizando el Asistente IDP o siembre las 6 Familias Pro conectadas a la ejecución real.
              </p>
            </div>
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wider hover:opacity-90 active:scale-95 transition-all flex items-center gap-2 shadow-sm"
            >
              <Plus size={14} /> Abrir Asistente CREMA
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredIndicators.map((ind) => {
              const spi = ind.last_spi;
              const progress =
                ind.target_value > 0
                  ? Math.min(100, Math.round((ind.current_value / ind.target_value) * 100))
                  : 0;
              const isAuto = Boolean(ind.source_type && ind.source_type !== "manual");
              const sourceMeta = KPI_EXECUTION_SOURCES.find((s) => s.id === ind.source_type);

              return (
                <div
                  key={ind.id}
                  className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 p-5 space-y-4 hover:shadow-md transition-all flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-2xs font-extrabold px-2 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))]">
                          {ind.code || "IND"}
                        </span>
                        <span className="text-2xs font-bold px-2 py-0.5 rounded bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
                          {ind.level}
                        </span>
                        <span className="text-2xs text-[hsl(var(--text-secondary))] flex items-center gap-1">
                          <Clock size={11} /> {ind.frequency}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {ind.crema_score !== null && ind.crema_score !== undefined && (
                          <span
                            className={clsx(
                              "text-2xs font-extrabold px-2 py-0.5 rounded-full border",
                              ind.crema_score >= 85
                                ? "bg-[hsl(var(--success))]/15 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                                : ind.crema_score >= 70
                                ? "bg-[hsl(var(--primary))]/15 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]"
                                : "bg-[hsl(var(--warning))]/15 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]"
                            )}
                          >
                            CREMA: {ind.crema_score}/100
                          </span>
                        )}

                        <span
                          className={clsx(
                            "text-2xs font-extrabold px-2.5 py-0.5 rounded-full border flex items-center gap-1",
                            spi === null || spi === undefined
                              ? "bg-[hsl(var(--surface-3))] border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"
                              : spi >= 1.0
                              ? "bg-[hsl(var(--success))]/20 border-[hsl(var(--success))]/40 text-[hsl(var(--success))]"
                              : spi >= 0.8
                              ? "bg-[hsl(var(--warning))]/20 border-[hsl(var(--warning))]/40 text-[hsl(var(--warning))]"
                              : "bg-[hsl(var(--destructive))]/20 border-[hsl(var(--destructive))]/40 text-[hsl(var(--destructive))]"
                          )}
                        >
                          {spi === null || spi === undefined ? (
                            "Sin registros"
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
                        </span>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{ind.name}</h3>
                      {(isAuto || ind.component_name) && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          {isAuto && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] text-2xs font-bold border border-[hsl(var(--primary))]/30">
                              <Activity size={10} />
                              Auto: {sourceMeta?.label || ind.source_type}
                            </span>
                          )}
                          {ind.component_name && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] text-2xs font-bold border border-[hsl(var(--border))]">
                              <Layers size={10} />
                              EDT: {ind.component_name}
                            </span>
                          )}
                        </div>
                      )}
                      {ind.description && (
                        <p className="text-2xs text-[hsl(var(--text-secondary))] mt-1 line-clamp-2">
                          {ind.description}
                        </p>
                      )}
                    </div>

                    {/* Barra de Progreso y Metas */}
                    <div className="space-y-1.5 pt-2">
                      <div className="flex items-center justify-between text-2xs font-semibold">
                        <span className="text-[hsl(var(--text-secondary))]">
                          Avance Actual:{" "}
                          <strong className="text-[hsl(var(--text-primary))]">
                            {ind.current_value} {ind.unit_of_measure}
                          </strong>
                        </span>
                        <span>
                          Meta:{" "}
                          <strong className="text-[hsl(var(--text-primary))]">
                            {ind.target_value} {ind.unit_of_measure}
                          </strong>{" "}
                          ({progress}%)
                        </span>
                      </div>
                      <div className="h-2.5 w-full bg-[hsl(var(--surface-3))] rounded-full overflow-hidden border border-[hsl(var(--border))]">
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
                  </div>

                  <div className="pt-3 border-t border-[hsl(var(--border))] flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))]">
                    <span>
                      Mediciones: <strong>{ind.records_count || 0}</strong> | Creador:{" "}
                      {ind.creator_name || "Usuario"}
                    </span>
                    <button
                      onClick={() => setIsDrawerOpen(true)}
                      className="text-[hsl(var(--primary))] hover:underline font-bold uppercase tracking-wider"
                    >
                      Ver en Drawer &rarr;
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Drawer Lateral Deslizante Canónico */}
      <ProjectIndicatorsDrawer
        projectId={projectId}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onIndicatorUpdated={() => void loadData()}
      />
    </div>
  );
}

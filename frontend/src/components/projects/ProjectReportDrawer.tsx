"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch, apiFetchBlob } from "@/lib/http";
import type { ProjectExecutiveReportData } from "@/types/projects";
import { FileText, Download, Printer, FileSpreadsheet, AlertTriangle, Clock, DollarSign, TrendingUp, ShieldAlert, Activity, Check, RefreshCw, Sliders } from "lucide-react";
import clsx from "clsx";

interface ProjectReportDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  projectTitle?: string;
}

type TabType = "preview" | "export" | "settings";

export function ProjectReportDrawer({
  projectId,
  isOpen,
  onClose,
  projectTitle,
}: ProjectReportDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<TabType>("preview");
  const [data, setData] = useState<ProjectExecutiveReportData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [exporting, setExporting] = useState<string | null>(null);

  // Configuración de secciones a incluir en el informe
  const [includeSections, setIncludeSections] = useState({
    generalInfo: true,
    financials: true,
    risks: true,
    cpm: true,
    timeTracking: true,
    phases: true,
  });

  const loadReportData = useCallback(async () => {
    if (!projectId || !token) return;
    setLoading(true);
    try {
      const res = await apiFetch<ProjectExecutiveReportData>(
        `/projects/${projectId}/export/executive-data`,
        { token }
      );
      setData(res);
    } catch (err: any) {
      addToast({
        title: "Error al cargar reporte",
        description: err.message || "No se pudieron obtener los datos ejecutivos",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [projectId, token, addToast]);

  useEffect(() => {
    if (isOpen) {
      loadReportData();
    }
  }, [isOpen, loadReportData]);

  // Manejador de descarga de archivos (PDF / CSV)
  const handleDownloadFile = async (
    endpoint: string,
    filename: string,
    actionKey: string
  ) => {
    if (!token) return;
    setExporting(actionKey);
    try {
      const blob = await apiFetchBlob(`/projects/${projectId}/export/${endpoint}`, {
        token,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      addToast({
        title: "Descarga completada",
        description: `Se ha descargado el archivo '${filename}' exitosamente.`,
        type: "success",
      });
    } catch (err: any) {
      addToast({
        title: "Error en la exportación",
        description: err.message || "No se pudo generar el archivo solicitado",
        type: "error",
      });
    } finally {
      setExporting(null);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const proj = data?.project;
  const tasksMet = data?.tasks_metrics;
  const finKpi = data?.financial_kpis;
  const raidKpi = data?.raid_kpis;
  const cpmMet = data?.cpm_metrics;
  const timeMet = data?.time_metrics;

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center border"
            style={{
              backgroundColor: "hsl(var(--primary) / 0.12)",
              borderColor: "hsl(var(--primary) / 0.3)",
              color: "hsl(var(--primary))",
            }}
          >
            <FileText className="w-4 h-4" />
          </div>
          <span className="font-semibold text-base" style={{ color: "hsl(var(--foreground))" }}>
            Reportes y Exportación Ejecutiva
          </span>
        </div>
      }
      subtitle={
        <span className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
          {projectTitle || proj?.title || "Proyecto"} • Membrete Oficial CCF & Excel CSV
        </span>
      }
      width="w-full sm:max-w-2xl lg:max-w-4xl"
    >
      <div className="flex flex-col h-full space-y-4">
        {/* Navegación por pestañas */}
        <div
          className="flex items-center justify-between border-b pb-2"
          style={{ borderColor: "hsl(var(--border))" }}
        >
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab("preview")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5",
                activeTab === "preview"
                  ? "shadow-sm border font-semibold"
                  : "hover:bg-[hsl(var(--surface-2))]"
              )}
              style={
                activeTab === "preview"
                  ? {
                      backgroundColor: "hsl(var(--primary) / 0.12)",
                      borderColor: "hsl(var(--primary) / 0.35)",
                      color: "hsl(var(--primary))",
                    }
                  : { color: "hsl(var(--muted-foreground))" }
              }
            >
              <FileText className="w-3.5 h-3.5" />
              Previsualización Ejecutiva
            </button>

            <button
              onClick={() => setActiveTab("export")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5",
                activeTab === "export"
                  ? "shadow-sm border font-semibold"
                  : "hover:bg-[hsl(var(--surface-2))]"
              )}
              style={
                activeTab === "export"
                  ? {
                      backgroundColor: "hsl(var(--primary) / 0.12)",
                      borderColor: "hsl(var(--primary) / 0.35)",
                      color: "hsl(var(--primary))",
                    }
                  : { color: "hsl(var(--muted-foreground))" }
              }
            >
              <Download className="w-3.5 h-3.5" />
              Centro de Descargas
            </button>

            <button
              onClick={() => setActiveTab("settings")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5",
                activeTab === "settings"
                  ? "shadow-sm border font-semibold"
                  : "hover:bg-[hsl(var(--surface-2))]"
              )}
              style={
                activeTab === "settings"
                  ? {
                      backgroundColor: "hsl(var(--primary) / 0.12)",
                      borderColor: "hsl(var(--primary) / 0.35)",
                      color: "hsl(var(--primary))",
                    }
                  : { color: "hsl(var(--muted-foreground))" }
              }
            >
              <Sliders className="w-3.5 h-3.5" />
              Filtro de Secciones
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadReportData}
              disabled={loading}
              className="p-1.5 rounded-lg border transition-all hover:bg-[hsl(var(--surface-2))]"
              style={{
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--muted-foreground))",
              }}
              title="Refrescar datos del reporte"
            >
              <RefreshCw className={clsx("w-3.5 h-3.5", loading && "animate-spin")} />
            </button>

            <button
              onClick={handlePrint}
              className="px-2.5 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-all hover:bg-[hsl(var(--surface-2))]"
              style={{
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--foreground))",
              }}
            >
              <Printer className="w-3.5 h-3.5" />
              Imprimir
            </button>
          </div>
        </div>

        {/* Contenido principal según pestaña */}
        {loading && !data ? (
          <div className="flex-1 flex flex-col items-center justify-center py-16 space-y-3">
            <RefreshCw
              className="w-8 h-8 animate-spin"
              style={{ color: "hsl(var(--primary))" }}
            />
            <p className="text-sm font-medium" style={{ color: "hsl(var(--muted-foreground))" }}>
              Consolidando métricas e indicadores ejecutivos del proyecto...
            </p>
          </div>
        ) : !data ? (
          <div
            className="flex-1 flex flex-col items-center justify-center p-8 rounded-xl border text-center space-y-2"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <AlertTriangle className="w-8 h-8 text-[hsl(var(--warning))]" />
            <h4 className="font-semibold text-sm" style={{ color: "hsl(var(--foreground))" }}>
              No se pudieron cargar los datos del informe
            </h4>
            <p className="text-xs max-w-sm" style={{ color: "hsl(var(--muted-foreground))" }}>
              Verifique que el proyecto exista y que tenga permisos de lectura asignados.
            </p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto pr-1 space-y-4">
            {/* 1. PESTAÑA: PREVISUALIZACIÓN EJECUTIVA */}
            {activeTab === "preview" && (
              <div className="space-y-4">
                {/* Membrete Institucional CCF */}
                <div
                  className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm"
                  style={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  <div className="space-y-1">
                    <span
                      className="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full inline-block"
                      style={{
                        backgroundColor: "hsl(var(--primary) / 0.15)",
                        color: "hsl(var(--primary))",
                      }}
                    >
                      Comunidad Cristiana El Faro • Dirección de Proyectos
                    </span>
                    <h2
                      className="text-lg font-bold tracking-tight"
                      style={{ color: "hsl(var(--foreground))" }}
                    >
                      {proj?.title}
                    </h2>
                    <p className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      {proj?.description}
                    </p>
                  </div>

                  <div className="text-right sm:border-l sm:pl-4 space-y-0.5 shrink-0" style={{ borderColor: "hsl(var(--border))" }}>
                    <div className="text-[10px] uppercase font-semibold" style={{ color: "hsl(var(--muted-foreground))" }}>
                      Estado / Salud
                    </div>
                    <div className="text-xs font-bold capitalize flex items-center sm:justify-end gap-1.5" style={{ color: "hsl(var(--primary))" }}>
                      <span className="w-2 h-2 rounded-full bg-[hsl(var(--success))] inline-block" />
                      {proj?.status} • {proj?.health_override || "Normal"}
                    </div>
                    <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                      Líder: <span className="font-medium text-[hsl(var(--foreground))]">{proj?.owner_name}</span>
                    </div>
                  </div>
                </div>

                {/* Tarjetas KPI Super-PRO */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                  {/* Avance */}
                  <div
                    className="p-3 rounded-xl border flex flex-col justify-between"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      <span>Avance</span>
                      <TrendingUp className="w-3.5 h-3.5" style={{ color: "hsl(var(--primary))" }} />
                    </div>
                    <div className="mt-1">
                      <div className="text-lg font-bold" style={{ color: "hsl(var(--foreground))" }}>
                        {tasksMet?.completion_rate}%
                      </div>
                      <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        {tasksMet?.completed} de {tasksMet?.total} tareas
                      </div>
                    </div>
                  </div>

                  {/* Presupuesto */}
                  <div
                    className="p-3 rounded-xl border flex flex-col justify-between"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      <span>Gastado</span>
                      <DollarSign className="w-3.5 h-3.5 text-[hsl(var(--success))]" />
                    </div>
                    <div className="mt-1">
                      <div className="text-lg font-bold" style={{ color: "hsl(var(--foreground))" }}>
                        ${finKpi?.budget_spent.toLocaleString()}
                      </div>
                      <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        de ${finKpi?.budget_allocated.toLocaleString()} ({finKpi?.burn_rate_percent}%)
                      </div>
                    </div>
                  </div>

                  {/* Riesgos RAID */}
                  <div
                    className="p-3 rounded-xl border flex flex-col justify-between"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      <span>Riesgos</span>
                      <ShieldAlert className="w-3.5 h-3.5 text-[hsl(var(--destructive))]" />
                    </div>
                    <div className="mt-1">
                      <div className="text-lg font-bold text-[hsl(var(--destructive))]">
                        {raidKpi?.critical_count}
                      </div>
                      <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        críticos de {raidKpi?.total_risks} totales
                      </div>
                    </div>
                  </div>

                  {/* Ruta Crítica CPM */}
                  <div
                    className="p-3 rounded-xl border flex flex-col justify-between"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      <span>Ruta CPM</span>
                      <Activity className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
                    </div>
                    <div className="mt-1">
                      <div className="text-lg font-bold text-[hsl(var(--primary))]">
                        {cpmMet?.total_duration_days}d
                      </div>
                      <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        {cpmMet?.critical_tasks_count} tareas críticas
                      </div>
                    </div>
                  </div>

                  {/* Hojas de Horas */}
                  <div
                    className="p-3 rounded-xl border flex flex-col justify-between col-span-2 sm:col-span-1"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      <span>Horas</span>
                      <Clock className="w-3.5 h-3.5 text-[hsl(var(--warning))]" />
                    </div>
                    <div className="mt-1">
                      <div className="text-lg font-bold" style={{ color: "hsl(var(--foreground))" }}>
                        {timeMet?.total_hours}h
                      </div>
                      <div className="text-[10px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        {timeMet?.billable_hours}h facturables
                      </div>
                    </div>
                  </div>
                </div>

                {/* Sección 1: Control Presupuestario */}
                {includeSections.financials && (
                  <div
                    className="p-4 rounded-xl border space-y-3"
                    style={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-[hsl(var(--success))]" />
                        <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Control Presupuestario y Quema de Fondos
                        </h3>
                      </div>
                      <span className="text-xs font-semibold text-[hsl(var(--success))]">
                        Remanente: ${finKpi?.remaining_budget.toLocaleString()}
                      </span>
                    </div>

                    <div className="space-y-1.5">
                      <div className="w-full h-2.5 rounded-full overflow-hidden flex bg-[hsl(var(--surface-2))]">
                        <div
                          className="h-full bg-[hsl(var(--success))] transition-all duration-300"
                          style={{
                            width: `${Math.min(100, finKpi?.burn_rate_percent || 0)}%`,
                          }}
                        />
                      </div>
                      <div className="flex justify-between text-[11px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                        <span>Ejecutado: ${finKpi?.budget_spent.toLocaleString()} ({finKpi?.burn_rate_percent}%)</span>
                        <span>Asignado Total: ${finKpi?.budget_allocated.toLocaleString()}</span>
                      </div>
                    </div>

                    {finKpi?.by_category && Object.keys(finKpi.by_category).length > 0 && (
                      <div className="pt-2 border-t flex flex-wrap gap-2 text-xs" style={{ borderColor: "hsl(var(--border))" }}>
                        {Object.entries(finKpi.by_category).map(([cat, amount]) => (
                          <span
                            key={cat}
                            className="px-2.5 py-1 rounded-md border text-[11px] font-medium"
                            style={{
                              backgroundColor: "hsl(var(--surface-1))",
                              borderColor: "hsl(var(--border))",
                              color: "hsl(var(--foreground))",
                            }}
                          >
                            <span className="capitalize">{cat}:</span> ${Number(amount).toLocaleString()}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Sección 2: Matriz RAID de Riesgos */}
                {includeSections.risks && (
                  <div
                    className="p-4 rounded-xl border space-y-3"
                    style={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-[hsl(var(--destructive))]" />
                        <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Matriz RAID — Riesgos Principales
                        </h3>
                      </div>
                      <span className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                        {raidKpi?.total_risks} riesgos registrados
                      </span>
                    </div>

                    {raidKpi?.risks && raidKpi.risks.length > 0 ? (
                      <div className="divide-y" style={{ borderColor: "hsl(var(--border))" }}>
                        {raidKpi.risks.slice(0, 4).map((r) => {
                          const sev = (r.probability || 1) * (r.impact || 1);
                          return (
                            <div key={r.id} className="py-2 flex items-start justify-between gap-2 text-xs">
                              <div>
                                <span className="font-medium" style={{ color: "hsl(var(--foreground))" }}>
                                  {r.title}
                                </span>
                                <p className="text-[11px] mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
                                  Mitigación: {r.mitigation_plan || "En evaluación"}
                                </p>
                              </div>
                              <span
                                className={clsx(
                                  "px-2 py-0.5 rounded text-[10px] font-bold shrink-0",
                                  sev >= 15
                                    ? "bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))] border border-[hsl(var(--destructive))]/20"
                                    : sev >= 10
                                    ? "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))] border border-[hsl(var(--warning))]/20"
                                    : "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] border border-[hsl(var(--success))]/20"
                                )}
                              >
                                Severidad {sev}/25
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs italic" style={{ color: "hsl(var(--muted-foreground))" }}>
                        No hay riesgos registrados en el proyecto.
                      </p>
                    )}
                  </div>
                )}

                {/* Sección 3: Cronograma y Ruta Crítica */}
                {includeSections.cpm && (
                  <div
                    className="p-4 rounded-xl border space-y-3"
                    style={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-[hsl(var(--primary))]" />
                        <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Ruta Crítica (CPM) y Cronograma
                        </h3>
                      </div>
                      <span className="text-xs font-semibold text-[hsl(var(--primary))]">
                        {cpmMet?.total_duration_days} días de duración total
                      </span>
                    </div>

                    <p className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                      Tareas determinantes sin holgura (retrasar cualquiera de estas tareas retrasa la fecha de entrega):
                    </p>

                    <div className="space-y-1.5">
                      {cpmMet?.tasks && cpmMet.tasks.filter((t) => t.is_critical).length > 0 ? (
                        cpmMet.tasks
                          .filter((t) => t.is_critical)
                          .map((t) => (
                            <div
                              key={t.task_id}
                              className="px-3 py-1.5 rounded-lg border text-xs flex items-center justify-between"
                              style={{
                                backgroundColor: "hsl(var(--surface-1))",
                                borderColor: "hsl(var(--border))",
                              }}
                            >
                              <span className="font-medium" style={{ color: "hsl(var(--foreground))" }}>
                                {t.title}
                              </span>
                              <span className="text-[11px] text-[hsl(var(--primary))] font-semibold">
                                {t.duration_days} días • Holgura {t.slack_days}d
                              </span>
                            </div>
                          ))
                      ) : (
                        <p className="text-xs italic" style={{ color: "hsl(var(--muted-foreground))" }}>
                          No se han detectado tareas críticas o dependencias encadenadas.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Sección 4: Hojas de Horas */}
                {includeSections.timeTracking && (
                  <div
                    className="p-4 rounded-xl border space-y-3"
                    style={{
                      backgroundColor: "hsl(var(--card))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-[hsl(var(--warning))]" />
                        <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Distribución de Horas y Esfuerzo
                        </h3>
                      </div>
                      <span className="text-xs font-semibold text-[hsl(var(--warning))]">
                        {timeMet?.total_hours}h invertidas
                      </span>
                    </div>

                    {timeMet?.by_member && timeMet.by_member.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {timeMet.by_member.map((m) => (
                          <div
                            key={m.persona_name}
                            className="p-2.5 rounded-lg border flex items-center justify-between"
                            style={{
                              backgroundColor: "hsl(var(--surface-1))",
                              borderColor: "hsl(var(--border))",
                            }}
                          >
                            <span className="font-medium" style={{ color: "hsl(var(--foreground))" }}>
                              {m.persona_name}
                            </span>
                            <span className="text-[11px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                              <b>{m.total_hours}h</b> ({m.billable_hours}h fact.)
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs italic" style={{ color: "hsl(var(--muted-foreground))" }}>
                        Sin registros de tiempo para este proyecto.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 2. PESTAÑA: CENTRO DE DESCARGAS Y EXPORTACIÓN */}
            {activeTab === "export" && (
              <div className="space-y-4">
                <div
                  className="p-4 rounded-xl border space-y-1"
                  style={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                    Instrumentos de Exportación Disponibles
                  </h3>
                  <p className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                    Descargue directamente los paquetes oficiales de auditoría y análisis en PDF y CSV (compatibles con Excel).
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {/* Tarjeta 1: Informe Ejecutivo PDF */}
                  <div
                    className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all hover:border-[hsl(var(--primary))]"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border"
                        style={{
                          backgroundColor: "hsl(var(--primary) / 0.12)",
                          borderColor: "hsl(var(--primary) / 0.3)",
                          color: "hsl(var(--primary))",
                        }}
                      >
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Informe Ejecutivo Completo (PDF Membretado)
                        </h4>
                        <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
                          Documento formal con membrete CCF, ficha técnica, KPIs de presupuesto, matriz RAID, ruta crítica y desglose de horas.
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() =>
                        handleDownloadFile(
                          "summary-pdf",
                          `reporte_ejecutivo_${projectId}.pdf`,
                          "pdf"
                        )
                      }
                      disabled={exporting === "pdf"}
                      className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold text-white shadow-sm flex items-center justify-center gap-2 transition-all"
                      style={{ backgroundColor: "hsl(var(--primary))" }}
                    >
                      {exporting === "pdf" ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Generando PDF...
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          Descargar PDF
                        </>
                      )}
                    </button>
                  </div>

                  {/* Tarjeta 2: Tareas y Cronograma CSV */}
                  <div
                    className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all hover:border-[hsl(var(--success))]"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                      >
                        <FileSpreadsheet className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Cronograma y Tareas (Excel / CSV)
                        </h4>
                        <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
                          Tabla completa de tareas con fechas de inicio/fin, responsables, prioridades, estados y códigos de fase.
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() =>
                        handleDownloadFile(
                          "tasks-csv",
                          `tareas_proyecto_${projectId}.csv`,
                          "tasks-csv"
                        )
                      }
                      disabled={exporting === "tasks-csv"}
                      className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold text-[hsl(var(--success))] border border-[hsl(var(--success))]/40 bg-[hsl(var(--success))]/10 hover:bg-[hsl(var(--success))]/20 shadow-sm flex items-center justify-center gap-2 transition-all"
                    >
                      {exporting === "tasks-csv" ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Exportando CSV...
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          Exportar Tareas (CSV)
                        </>
                      )}
                    </button>
                  </div>

                  {/* Tarjeta 3: Libro Mayor de Gastos CSV */}
                  <div
                    className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all hover:border-[hsl(var(--primary))]"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]"
                      >
                        <DollarSign className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                          Libro Mayor de Gastos y Desembolsos (CSV)
                        </h4>
                        <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
                          Partidas financieras con montos, fechas, categorías, estados (planned/committed/paid) y enlaces a comprobantes.
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() =>
                        handleDownloadFile(
                          "expenses-csv",
                          `gastos_proyecto_${projectId}.csv`,
                          "expenses-csv"
                        )
                      }
                      disabled={exporting === "expenses-csv"}
                      className="w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))]/10 hover:bg-[hsl(var(--primary))]/20 shadow-sm flex items-center justify-center gap-2 transition-all"
                    >
                      {exporting === "expenses-csv" ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          Exportando CSV...
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          Exportar Gastos (CSV)
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 3. PESTAÑA: FILTRO Y SELECCIÓN DE SECCIONES */}
            {activeTab === "settings" && (
              <div className="space-y-4">
                <div
                  className="p-4 rounded-xl border space-y-1"
                  style={{
                    backgroundColor: "hsl(var(--card))",
                    borderColor: "hsl(var(--border))",
                  }}
                >
                  <h3 className="text-sm font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                    Configuración de Visibilidad del Informe
                  </h3>
                  <p className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
                    Seleccione los módulos que desea incluir en la vista ejecutiva y en las impresiones directas.
                  </p>
                </div>

                <div className="space-y-2">
                  {[
                    { key: "financials", label: "Módulo Financiero y Desglose Presupuestario", desc: "Incluye asignaciones, gastos pagados, saldo remanente y categorías" },
                    { key: "risks", label: "Matriz RAID de Riesgos e Incidencias", desc: "Incluye matriz de severidad 5x5 y planes de mitigación de riesgos críticos" },
                    { key: "cpm", label: "Ruta Crítica CPM y Cronograma de Holgura Cero", desc: "Incluye análisis de cadena determinante y duración total en días" },
                    { key: "timeTracking", label: "Hojas de Horas y Control de Esfuerzo", desc: "Incluye total de horas facturables y participación por colaborador" },
                  ].map((s) => {
                    const isChecked = (includeSections as any)[s.key];
                    return (
                      <div
                        key={s.key}
                        onClick={() =>
                          setIncludeSections((prev) => ({
                            ...prev,
                            [s.key]: !isChecked,
                          }))
                        }
                        className={clsx(
                          "p-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all",
                          isChecked
                            ? "bg-[hsl(var(--surface-1))] border-[hsl(var(--primary))]"
                            : "bg-[hsl(var(--card))] border-[hsl(var(--border))]"
                        )}
                      >
                        <div className="space-y-0.5">
                          <h4 className="text-xs font-semibold" style={{ color: "hsl(var(--foreground))" }}>
                            {s.label}
                          </h4>
                          <p className="text-[11px]" style={{ color: "hsl(var(--muted-foreground))" }}>
                            {s.desc}
                          </p>
                        </div>

                        <div
                          className={clsx(
                            "w-5 h-5 rounded-md border flex items-center justify-center transition-all",
                            isChecked
                              ? "bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-white"
                              : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
                          )}
                        >
                          {isChecked && <Check className="w-3.5 h-3.5" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </RightPanel>
  );
}
export default ProjectReportDrawer;

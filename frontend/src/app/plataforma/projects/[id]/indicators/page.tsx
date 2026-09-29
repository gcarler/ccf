"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type { ProjectIndicator, MgaIndicatorLevel } from "@/types/projects";
import { ProjectIndicatorsDrawer } from "@/components/projects/ProjectIndicatorsDrawer";
import { BarChart3, TrendingUp, Plus, RotateCw, Activity, Clock, ChevronLeft, Sliders, CheckCircle2, AlertTriangle } from "lucide-react";
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
  const [projectTitle, setProjectTitle] = useState("");
  const [indicators, setIndicators] = useState<ProjectIndicator[]>([]);
  const [selectedLevelFilter, setSelectedLevelFilter] = useState<string>("ALL");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const loadData = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    try {
      const [projData, indData] = await Promise.all([
        apiFetch<{ title: string }>(`/projects/${projectId}`, { token }).catch(() => ({ title: "Proyecto" })),
        apiFetch<ProjectIndicator[]>(`/projects/${projectId}/advanced-indicators`, { token }),
      ]);
      setProjectTitle(projData?.title || "Proyecto");
      if (Array.isArray(indData)) {
        setIndicators(indData);
      }
    } catch {
      toast.error("Error al cargar indicadores MGA");
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

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
    <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] overflow-y-auto">
      {/* Header Superior y Breadcrumb */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 sticky top-0 z-10 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/plataforma/projects/${projectId}`}
              className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all flex items-center justify-center"
              title="Volver al proyecto"
            >
              <ChevronLeft size={16} />
            </Link>
            <div>
              <div className="flex items-center gap-2 text-3xs text-[hsl(var(--muted-foreground))] uppercase font-bold tracking-wider">
                <Link href="/plataforma/projects" className="hover:text-[hsl(var(--primary))] transition-colors">
                  Proyectos
                </Link>
                <span>/</span>
                <Link href={`/plataforma/projects/${projectId}`} className="hover:text-[hsl(var(--primary))] transition-colors">
                  {projectTitle}
                </Link>
                <span>/</span>
                <span className="text-[hsl(var(--foreground))]">Indicadores MGA & CREMA</span>
              </div>
              <h1 className="text-lg font-black tracking-tight flex items-center gap-2 mt-0.5">
                <BarChart3 size={20} className="text-[hsl(var(--primary))]" />
                Tablero de Indicadores MGA & Semáforo SPI
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => loadData()}
              className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors"
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-3xs font-extrabold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Total Indicadores
              </span>
              <Activity size={18} className="text-[hsl(var(--primary))]" />
            </div>
            <p className="text-2xl font-black text-[hsl(var(--foreground))]">{indicators.length}</p>
            <p className="text-3xs text-[hsl(var(--muted-foreground))]">Metodología MGA vinculada</p>
          </div>

          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--success))]/30 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-3xs font-extrabold uppercase tracking-wider text-[hsl(var(--success))]">
                🟢 SPI ≥ 1.0 (Óptimo)
              </span>
              <CheckCircle2 size={18} className="text-[hsl(var(--success))]" />
            </div>
            <p className="text-2xl font-black text-[hsl(var(--success))]">{spiStats.optimal}</p>
            <p className="text-3xs text-[hsl(var(--muted-foreground))]">Cumpliendo o superando metas</p>
          </div>

          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--warning))]/30 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-3xs font-extrabold uppercase tracking-wider text-[hsl(var(--warning))]">
                🟡 SPI 0.80 - 0.99 (Alerta)
              </span>
              <AlertTriangle size={18} className="text-[hsl(var(--warning))]" />
            </div>
            <p className="text-2xl font-black text-[hsl(var(--warning))]">{spiStats.warning}</p>
            <p className="text-3xs text-[hsl(var(--muted-foreground))]">Desviación moderada de avance</p>
          </div>

          <div className="p-4 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--destructive))]/30 shadow-sm space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-3xs font-extrabold uppercase tracking-wider text-[hsl(var(--destructive))]">
                🔴 SPI &lt; 0.80 (Riesgo)
              </span>
              <TrendingUp size={18} className="rotate-180 text-[hsl(var(--destructive))]" />
            </div>
            <p className="text-2xl font-black text-[hsl(var(--destructive))]">{spiStats.critical}</p>
            <p className="text-3xs text-[hsl(var(--muted-foreground))]">Subejecución o retraso crítico</p>
          </div>
        </div>

        {/* Barra de Filtros por Nivel MGA */}
        <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-3 overflow-x-auto">
          <div className="flex items-center gap-1.5 text-2xs">
            <span className="font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wider text-3xs flex items-center gap-1">
              <Sliders size={12} /> Niveles:
            </span>
            <button
              onClick={() => setSelectedLevelFilter("ALL")}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-2xs font-bold uppercase transition-all",
                selectedLevelFilter === "ALL"
                  ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
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
                    "px-3 py-1.5 rounded-lg text-2xs font-semibold whitespace-nowrap transition-all",
                    selectedLevelFilter === lvl.id
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                      : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-3))]"
                  )}
                >
                  {lvl.label} ({count})
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-3xs font-semibold text-[hsl(var(--muted-foreground))]">
              Sello Metodológico:
            </span>
            <span className="text-2xs font-black px-2 py-0.5 rounded bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/20">
              Score CREMA Promedio: {spiStats.avgCrema}/100
            </span>
          </div>
        </div>

        {/* Lista de Tarjetas de Indicadores */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3 text-[hsl(var(--muted-foreground))]">
            <RotateCw size={28} className="animate-spin text-[hsl(var(--primary))]" />
            <p className="text-xs font-semibold">Cargando tablero MGA y mediciones periódicas...</p>
          </div>
        ) : filteredIndicators.length === 0 ? (
          <div className="py-16 px-4 rounded-2xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/30 flex flex-col items-center justify-center text-center gap-3">
            <div className="p-4 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
              <BarChart3 size={36} />
            </div>
            <div className="max-w-md">
              <h3 className="text-sm font-bold text-[hsl(var(--foreground))]">Sin indicadores configurados</h3>
              <p className="text-3xs text-[hsl(var(--muted-foreground))] mt-1">
                Configure indicadores MGA de eficacia o producto utilizando el Asistente Inteligente CREMA para garantizar cumplimiento con los lineamientos del DNP y BID.
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

              return (
                <div
                  key={ind.id}
                  className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/60 p-5 space-y-4 hover:shadow-md transition-all flex flex-col justify-between"
                >
                  <div className="space-y-3">
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

                      <div className="flex items-center gap-2">
                        {ind.crema_score !== null && ind.crema_score !== undefined && (
                          <span
                            className={clsx(
                              "text-3xs font-black px-2 py-0.5 rounded-full border",
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
                            "text-3xs font-black px-2.5 py-0.5 rounded-full border flex items-center gap-1",
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
                      <h3 className="text-sm font-bold text-[hsl(var(--foreground))]">{ind.name}</h3>
                      {ind.description && (
                        <p className="text-3xs text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">
                          {ind.description}
                        </p>
                      )}
                    </div>

                    {/* Barra de Progreso y Metas */}
                    <div className="space-y-1.5 pt-2">
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

                  <div className="pt-3 border-t border-[hsl(var(--border))] flex items-center justify-between text-3xs text-[hsl(var(--muted-foreground))]">
                    <span>
                      Mediciones: <strong>{ind.records_count || 0}</strong> | Creador: {ind.creator_name || "Usuario"}
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

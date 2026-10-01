"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  Layers,
  Mail,
  Phone,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserCheck,
  } from "lucide-react";
import { apiFetch, apiFetchBlob } from "@/lib/http";
import { toast } from "sonner";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import type {
  EventAnalyticsData,
  PostEventAnalyticsData,
  PostEventAttendeeItem,
} from "@/app/plataforma/evangelism/types";

interface AnalyticsTabProps {
  eventId: string;
  token: string | null;
}

export default function AnalyticsTab({ eventId, token }: AnalyticsTabProps) {
  const [activeView, setActiveView] = useState<"funnel" | "monthly">("funnel");
  const [postAnalytics, setPostAnalytics] = useState<PostEventAnalyticsData | null>(null);
  const [monthlyAnalytics, setMonthlyAnalytics] = useState<EventAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  // Filtro y Drawer
  const [selectedAttendee, setSelectedAttendee] = useState<PostEventAttendeeItem | null>(null);
  const [isChannelDrawerOpen, setIsChannelDrawerOpen] = useState(false);
  const [funnelFilter, setFunnelFilter] = useState<string>("all");

  // Acciones
  const [exportingCsv, setExportingCsv] = useState(false);
  const [channelingLoading, setChannelingLoading] = useState(false);
  const [channelingMessage, setChannelingMessage] = useState<string | null>(null);

  const loadData = async (signal?: AbortSignal) => {
    if (!token) return;
    setLoading(true);
    setFailed(false);
    try {
      const [postData, monthlyData] = await Promise.allSettled([
        apiFetch<PostEventAnalyticsData>(
          `/api/evangelism/events/${eventId}/post-event-analytics`,
          { token, silent: true, signal }
        ),
        apiFetch<EventAnalyticsData>(
          `/api/evangelism/events/${eventId}/analytics`,
          { token, silent: true, signal }
        ),
      ]);

      if (signal?.aborted) return;

      if (postData.status === "fulfilled") {
        setPostAnalytics(postData.value);
      }
      if (monthlyData.status === "fulfilled") {
        setMonthlyAnalytics(monthlyData.value);
      }

      if (postData.status === "rejected" && monthlyData.status === "rejected") {
        setFailed(true);
      }
    } catch {
      if (!signal?.aborted) setFailed(true);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    const abort = new AbortController();
    loadData(abort.signal);
    return () => abort.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, token]);

  // Exportar reporte ejecutivo CSV
  const handleExportCsv = async () => {
    if (!token) return;
    setExportingCsv(true);
    try {
      const blob = await apiFetchBlob(
        `/api/evangelism/events/${eventId}/export/post-event-analytics`,
        { token }
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reporte_ejecutivo_post_evento_${eventId.slice(0, 8)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error inesperado";
      toast.error("Error al descargar reporte CSV: " + msg);
    } finally {
      setExportingCsv(false);
    }
  };

  // Canalizar a CRM
  const handleChannelToCrm = async (personaIds?: string[]) => {
    if (!token) return;
    setChannelingLoading(true);
    setChannelingMessage(null);
    try {
      const res = await apiFetch<{ success: boolean; created_cases: number; message: string }>(
        `/api/evangelism/events/${eventId}/crm-channel`,
        {
          token,
          method: "POST",
          body: personaIds ? { persona_ids: personaIds } : {},
        }
      );
      setChannelingMessage(res.message);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al procesar canalización";
      setChannelingMessage(`Error: ${msg}`);
    } finally {
      setChannelingLoading(false);
    }
  };

  // Asistentes sin caso para canalización masiva
  const attendeesWithoutCase = useMemo(() => {
    if (!postAnalytics) return [];
    return postAnalytics.attendees_funnel_summary.filter(
      (a) => !a.has_crm_case && !a.crm_case_id
    );
  }, [postAnalytics]);

  // Asistentes filtrados para tabla
  const filteredAttendees = useMemo(() => {
    if (!postAnalytics) return [];
    const list = postAnalytics.attendees_funnel_summary;
    if (funnelFilter === "all") return list;
    if (funnelFilter === "no_crm") {
      return list.filter((a) => !a.has_crm_case && !a.crm_case_id);
    }
    if (funnelFilter === "new_visitors") {
      return list.filter((a) => a.is_new_visitor);
    }
    return list.filter((a) => a.current_funnel_step === funnelFilter);
  }, [postAnalytics, funnelFilter]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 space-y-3">
        <RefreshCw className="h-6 w-6 animate-spin text-[hsl(var(--primary))]" />
        <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">
          Cargando métricas post-evento y embudo ministerial...
        </p>
      </div>
    );
  }

  if (failed && !postAnalytics && !monthlyAnalytics) {
    return (
      <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-8 text-center space-y-3">
        <AlertTriangle className="h-8 w-8 mx-auto text-[hsl(var(--warning))]" />
        <h3 className="text-base font-semibold text-[hsl(var(--text-primary))]">
          No se pudo cargar la analítica del evento
        </h3>
        <p className="text-sm text-[hsl(var(--text-secondary))] max-w-md mx-auto">
          Comprueba la conexión con el servidor ministerial o reintenta la sincronización.
        </p>
        <button
          onClick={() => loadData()}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Reintentar
        </button>
      </div>
    );
  }

  const m = postAnalytics?.attendance_metrics;
  const ret = postAnalytics?.visitor_retention;
  const funnel = postAnalytics?.conversion_funnel || [];
  const crmB = postAnalytics?.crm_breakdown;

  // Badge de salud de retención
  const getHealthBadge = (status: string) => {
    switch (status) {
      case "EXCELLENT":
        return {
          label: "Excelente",
          className: "bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.2)]",
        };
      case "HEALTHY":
        return {
          label: "Saludable",
          className: "bg-[hsl(var(--info)/0.1)] text-[hsl(var(--info))] border-[hsl(var(--info)/0.2)]",
        };
      case "ATTENTION_NEEDED":
        return {
          label: "Atención Necesaria",
          className: "bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.2)]",
        };
      default:
        return {
          label: "Crítico",
          className: "bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))] border-[hsl(var(--destructive)/0.2)]",
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Barra de Controles y Subtabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[hsl(var(--border-subtle))] pb-4">
        {/* Toggle de Vistas */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))]">
          <button
            onClick={() => setActiveView("funnel")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeView === "funnel"
                ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            }`}
          >
            <Layers className="h-3.5 w-3.5 text-[hsl(var(--primary))]" />
            Embudo & Conversión CRM
            <span className="px-1.5 py-0.5 text-3xs font-bold rounded-md bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] uppercase">
              Pro
            </span>
          </button>
          <button
            onClick={() => setActiveView("monthly")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeView === "monthly"
                ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            Histórico Mensual
          </button>
        </div>

        {/* Acciones Ejecutivas */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={handleExportCsv}
            disabled={exportingCsv || !postAnalytics}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors disabled:opacity-50"
            title="Exportar reporte CSV con formato para hojas de cálculo"
          >
            <Download className="h-3.5 w-3.5 text-[hsl(var(--text-secondary))]" />
            {exportingCsv ? "Exportando..." : "Exportar CSV"}
          </button>

          <button
            onClick={() => setIsChannelDrawerOpen(true)}
            disabled={!postAnalytics || attendeesWithoutCase.length === 0}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <UserCheck className="h-3.5 w-3.5" />
            Canalizar a CRM
            {attendeesWithoutCase.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-white/20 text-3xs font-bold">
                {attendeesWithoutCase.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Banner de resultado de canalización */}
      {channelingMessage && (
        <div className="flex items-center justify-between p-3 rounded-lg border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] text-xs">
          <div className="flex items-center gap-2 text-[hsl(var(--text-primary))]">
            <CheckCircle2 className="h-4 w-4 text-[hsl(var(--success))]" />
            <span>{channelingMessage}</span>
          </div>
          <button
            onClick={() => setChannelingMessage(null)}
            className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] text-xs font-bold px-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* VISTA 1: EMBUDO & CONVERSIÓN CRM */}
      {activeView === "funnel" && postAnalytics && m && (
        <div className="space-y-6">
          {/* Tarjetas de KPIs Ejecutivos Post-Evento */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 flex flex-col justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Convocados
              </span>
              <div className="my-2">
                <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                  {m.total_registered}
                </span>
                <span className="ml-1.5 text-xs text-[hsl(var(--text-secondary))]">registrados</span>
              </div>
              <span className="text-3xs text-[hsl(var(--text-secondary))]">
                {m.total_confirmed} confirmados previos
              </span>
            </div>

            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 flex flex-col justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Asistencia Real
              </span>
              <div className="my-2">
                <span className="text-2xl font-bold text-[hsl(var(--primary))]">
                  {m.total_attended}
                </span>
                <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-3xs font-bold bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]">
                  {m.attendance_rate}%
                </span>
              </div>
              <span className="text-3xs text-[hsl(var(--text-secondary))]">efectiva en puerta</span>
            </div>

            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 flex flex-col justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Inasistencias
              </span>
              <div className="my-2">
                <span className="text-2xl font-bold text-[hsl(var(--destructive))]">
                  {m.total_absent}
                </span>
                <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-3xs font-bold bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]">
                  {m.no_show_rate}%
                </span>
              </div>
              <span className="text-3xs text-[hsl(var(--text-secondary))]">tasa no-show</span>
            </div>

            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 flex flex-col justify-between">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Walk-ins
              </span>
              <div className="my-2">
                <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                  {m.total_walk_ins}
                </span>
                <span className="ml-1.5 text-xs text-[hsl(var(--text-secondary))]">sin preregistro</span>
              </div>
              <span className="text-3xs text-[hsl(var(--text-secondary))]">acreditados en acceso</span>
            </div>

            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 flex flex-col justify-between col-span-2 sm:col-span-1">
              <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Aforo & Capacidad
              </span>
              <div className="my-2">
                <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                  {m.capacity_utilization !== null ? `${m.capacity_utilization}%` : "Libre"}
                </span>
              </div>
              <span className="text-3xs text-[hsl(var(--text-secondary))]">
                {postAnalytics.capacity_max ? `Máximo: ${postAnalytics.capacity_max}` : "Sin límite configurado"}
              </span>
            </div>
          </div>

          {/* Embudo Canónico de Conversión Ministerial (6 Etapas) */}
          <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[hsl(var(--border-subtle))] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[hsl(var(--primary))]" />
                  Embudo de Conversión Ministerial
                </h3>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                  Trazabilidad desde el pre-registro hasta la madurez y permanencia eclesial.
                </p>
              </div>
              <span className="text-2xs font-medium text-[hsl(var(--text-secondary))]">
                6 Etapas Canónicas
              </span>
            </div>

            <div className="space-y-3 pt-2">
              {funnel.map((step) => {
                const isSelected = funnelFilter === step.stage_id;
                return (
                  <div
                    key={step.stage_id}
                    onClick={() =>
                      setFunnelFilter(isSelected ? "all" : step.stage_id)
                    }
                    className={`group cursor-pointer rounded-xl border p-3.5 transition-all ${
                      isSelected
                        ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 shadow-sm"
                        : "border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--border-strong))]"
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[hsl(var(--primary))]/10 text-xs font-bold text-[hsl(var(--primary))]">
                          {step.step}
                        </span>
                        <div>
                          <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                            {step.name}
                          </span>
                          <span className="ml-2 text-2xs text-[hsl(var(--text-secondary))]">
                            ({step.pct_of_total}% del total)
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-medium text-[hsl(var(--text-secondary))] ml-9 sm:ml-0">
                        <div>
                          <span className="text-sm font-bold text-[hsl(var(--text-primary))]">
                            {step.count}
                          </span>{" "}
                          personas
                        </div>
                        {step.step > 1 && (
                          <div className="text-2xs">
                            <span className="text-[hsl(var(--success))] font-semibold">
                              {step.conversion_from_previous}%
                            </span>{" "}
                            conversión
                            <span className="mx-1 text-[hsl(var(--border-subtle))]">|</span>
                            <span className="text-[hsl(var(--destructive))] font-semibold">
                              -{step.dropoff_from_previous}%
                            </span>{" "}
                            deserción
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Barra de progreso */}
                    <div className="h-2 w-full rounded-full bg-[hsl(var(--surface-3))] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[hsl(var(--primary))] transition-all duration-500"
                        style={{ width: `${Math.max(4, step.pct_of_total)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Fila de Retención y Pipeline CRM */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Cohorte de Retención de Nuevos Visitantes */}
            {ret && (
              <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-[hsl(var(--border-subtle))] pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                      Retención de Nuevos Visitantes
                    </h3>
                  </div>
                  {(() => {
                    const b = getHealthBadge(ret.health_status);
                    return (
                      <span
                        className={`px-2 py-0.5 text-2xs font-bold rounded-full border ${b.className}`}
                      >
                        {b.label}
                      </span>
                    );
                  })()}
                </div>

                <div className="grid grid-cols-3 gap-2 py-2 text-center">
                  <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))]">
                    <span className="text-3xs uppercase tracking-wide font-semibold text-[hsl(var(--text-secondary))]">
                      30 Días
                    </span>
                    <div className="text-lg font-bold text-[hsl(var(--text-primary))] mt-1">
                      {ret.retained_30d_rate}%
                    </div>
                    <span className="text-3xs text-[hsl(var(--text-secondary))]">
                      {ret.retained_30d_count} retenidos
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))]">
                    <span className="text-3xs uppercase tracking-wide font-semibold text-[hsl(var(--text-secondary))]">
                      60 Días
                    </span>
                    <div className="text-lg font-bold text-[hsl(var(--text-primary))] mt-1">
                      {ret.retained_60d_rate}%
                    </div>
                    <span className="text-3xs text-[hsl(var(--text-secondary))]">
                      {ret.retained_60d_count} retenidos
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))]">
                    <span className="text-3xs uppercase tracking-wide font-semibold text-[hsl(var(--text-secondary))]">
                      90 Días
                    </span>
                    <div className="text-lg font-bold text-[hsl(var(--text-primary))] mt-1">
                      {ret.retained_90d_rate}%
                    </div>
                    <span className="text-3xs text-[hsl(var(--text-secondary))]">
                      {ret.retained_90d_count} retenidos
                    </span>
                  </div>
                </div>

                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Calculado sobre {ret.new_visitors_count} nuevos visitantes únicos que asistieron a este evento.
                </p>
              </div>
            )}

            {/* Desglose de Casos CRM */}
            {crmB && (
              <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-5 space-y-4">
                <div className="flex items-center justify-between border-b border-[hsl(var(--border-subtle))] pb-3">
                  <div className="flex items-center gap-2">
                    <UserCheck className="h-4 w-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                      Canalización Pastoral CRM
                    </h3>
                  </div>
                  <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                    {crmB.total_cases_created} casos activos
                  </span>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))]">
                  <div>
                    <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                      Casos Pendientes de Seguimiento
                    </span>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                      Requieren primera llamada o visita pastoral
                    </p>
                  </div>
                  <span className="text-base font-bold text-[hsl(var(--primary))]">
                    {crmB.pending_followup_count}
                  </span>
                </div>

                <div className="space-y-2">
                  <span className="text-3xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    Distribución por Etapa
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {crmB.cases_by_stage.map((s) => (
                      <div
                        key={s.stage_id}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[hsl(var(--surface-2))] border border-[hsl(var(--border-subtle))] text-2xs font-medium text-[hsl(var(--text-primary))]"
                      >
                        <span>{s.stage_name}:</span>
                        <span className="font-bold text-[hsl(var(--primary))]">
                          {s.count}
                        </span>
                      </div>
                    ))}
                    {crmB.cases_by_stage.length === 0 && (
                      <span className="text-2xs text-[hsl(var(--text-secondary))] italic">
                        Sin casos creados todavía.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Tabla de Asistentes y Trazabilidad */}
          <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[hsl(var(--border-subtle))] pb-3">
              <div>
                <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                  Detalle de Asistentes y Seguimiento
                </h3>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                  Mostrando {filteredAttendees.length} de {postAnalytics.attendees_funnel_summary.length} personas
                </p>
              </div>

              {/* Filtros rápidos */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => setFunnelFilter("all")}
                  className={`px-2.5 py-1 rounded-md text-2xs font-semibold transition-colors ${
                    funnelFilter === "all"
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                      : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  }`}
                >
                  Todos
                </button>
                <button
                  onClick={() => setFunnelFilter("no_crm")}
                  className={`px-2.5 py-1 rounded-md text-2xs font-semibold transition-colors ${
                    funnelFilter === "no_crm"
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                      : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  }`}
                >
                  Sin Caso CRM ({attendeesWithoutCase.length})
                </button>
                <button
                  onClick={() => setFunnelFilter("new_visitors")}
                  className={`px-2.5 py-1 rounded-md text-2xs font-semibold transition-colors ${
                    funnelFilter === "new_visitors"
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                      : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                  }`}
                >
                  Nuevos Visitantes
                </button>
              </div>
            </div>

            {/* Listado / Tabla */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[hsl(var(--border-subtle))] text-[hsl(var(--text-secondary))] text-2xs uppercase tracking-wider">
                    <th className="py-2.5 px-3">Persona</th>
                    <th className="py-2.5 px-3">Contacto</th>
                    <th className="py-2.5 px-3">Acreditación</th>
                    <th className="py-2.5 px-3">Ingreso Puerta</th>
                    <th className="py-2.5 px-3">Etapa Embudo</th>
                    <th className="py-2.5 px-3">Caso CRM</th>
                    <th className="py-2.5 px-3 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border-subtle))]">
                  {filteredAttendees.map((a) => (
                    <tr
                      key={a.persona_id}
                      onClick={() => setSelectedAttendee(a)}
                      className="cursor-pointer hover:bg-[hsl(var(--surface-2))] transition-colors"
                    >
                      <td className="py-2.5 px-3 font-semibold text-[hsl(var(--text-primary))]">
                        <div className="flex items-center gap-1.5">
                          {a.full_name}
                          {a.is_new_visitor && (
                            <span className="px-1.5 py-0.2 rounded text-3xs font-bold bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))]">
                              Nuevo
                            </span>
                          )}
                        </div>
                        <span className="text-3xs font-normal text-[hsl(var(--text-secondary))]">
                          {a.church_role}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-[hsl(var(--text-secondary))]">
                        <div>{a.phone || "—"}</div>
                        <div className="text-3xs">{a.email || "—"}</div>
                      </td>

                      <td className="py-2.5 px-3">
                        <span className="font-mono text-2xs font-medium text-[hsl(var(--text-secondary))]">
                          {a.registration_code || "En Puerta"}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-[hsl(var(--text-secondary))] text-2xs">
                        {a.check_in_at
                          ? new Date(a.check_in_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </td>

                      <td className="py-2.5 px-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-semibold bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                          {a.current_funnel_step_label}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-2xs">
                        {a.crm_stage_name ? (
                          <div className="flex items-center gap-1 font-medium text-[hsl(var(--text-primary))]">
                            <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))]" />
                            {a.crm_stage_name}
                          </div>
                        ) : (
                          <span className="text-[hsl(var(--text-secondary))] italic">
                            Sin caso
                          </span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAttendee(a);
                          }}
                          className="px-2 py-1 rounded text-2xs font-medium text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/10 transition-colors"
                        >
                          Ficha
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredAttendees.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-sm text-[hsl(var(--text-secondary))]">
                        No hay personas que coincidan con el filtro seleccionado.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* VISTA 2: HISTÓRICO MENSUAL */}
      {activeView === "monthly" && monthlyAnalytics && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-subtle))] rounded-xl p-4 text-center">
              <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
                Promedio Histórico
              </p>
              <h3 className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                {monthlyAnalytics.kpis.historical_avg}
              </h3>
              <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">
                Personas por sesión
              </p>
            </div>

            <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-subtle))] rounded-xl p-4 text-center">
              <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
                Tendencia de Crecimiento
              </p>
              <h3
                className={`text-2xl font-bold ${
                  monthlyAnalytics.kpis.trend_percentage > 0
                    ? "text-[hsl(var(--success))]"
                    : monthlyAnalytics.kpis.trend_percentage < 0
                    ? "text-[hsl(var(--destructive))]"
                    : "text-[hsl(var(--text-secondary))]"
                }`}
              >
                {monthlyAnalytics.kpis.trend_percentage > 0 ? "+" : ""}
                {monthlyAnalytics.kpis.trend_percentage}%
              </h3>
              <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">
                Respecto al mes anterior
              </p>
            </div>

            <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-subtle))] rounded-xl p-4 text-center">
              <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
                Mes Pico (Récord)
              </p>
              <h3 className="text-2xl font-bold text-[hsl(var(--primary))]">
                {monthlyAnalytics.kpis.peak_month.avg}
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">
                {monthlyAnalytics.kpis.peak_month.month}
              </p>
            </div>
          </div>

          <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-subtle))] rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">
              Asistencia Promedio por Mes
            </h3>
            {monthlyAnalytics.monthly_data.length === 0 ? (
              <div className="text-center py-8 text-[hsl(var(--text-secondary))] text-sm">
                No hay datos históricos suficientes para graficar.
              </div>
            ) : (
              <div className="flex items-end gap-3 h-52 mt-4 w-full overflow-x-auto pb-4 scrollbar-thin">
                {monthlyAnalytics.monthly_data.map((d) => {
                  const maxAvg = monthlyAnalytics.kpis.peak_month.avg || 1;
                  const heightPct = Math.max(8, Math.round((d.avg_attendance / maxAvg) * 100));

                  return (
                    <div
                      key={d.month}
                      className="flex-1 min-w-[50px] flex flex-col items-center gap-2 h-full justify-end group"
                    >
                      <span className="text-2xs font-bold text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]">
                        {d.avg_attendance}
                      </span>
                      <div
                        style={{ height: `${heightPct}%` }}
                        className="w-full bg-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))] border border-[hsl(var(--primary))]/40 rounded-t-md transition-all duration-300"
                        title={`${d.month}: ${d.avg_attendance} asistentes en promedio`}
                      />
                      <span className="text-3xs uppercase font-medium text-[hsl(var(--text-secondary))] truncate max-w-[50px]">
                        {d.month}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* DRAWER 1: Ficha del Participante (0 Modales Centrados) */}
      <WorkspaceDrawer
        isOpen={Boolean(selectedAttendee)}
        onClose={() => setSelectedAttendee(null)}
        title={selectedAttendee?.full_name || "Detalle del Asistente"}
        subtitle={`Acreditación: ${selectedAttendee?.registration_code || "En Puerta"}`}
      >
        {selectedAttendee && (
          <div className="space-y-6 p-4">
            {/* Cabecera de estado */}
            <div className="p-4 rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-2))] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                  Etapa en el Embudo
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                  {selectedAttendee.current_funnel_step_label}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xs text-[hsl(var(--text-secondary))]">Rol Eclesial:</span>
                <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                  {selectedAttendee.church_role}
                </span>
                {selectedAttendee.is_new_visitor && (
                  <span className="px-2 py-0.5 rounded text-3xs font-bold bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))]">
                    Nuevo Visitante
                  </span>
                )}
              </div>
            </div>

            {/* Datos de Contacto */}
            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
              <h4 className="text-xs font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wider">
                Información de Contacto
              </h4>
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                  <Phone className="h-3.5 w-3.5" />
                  <span className="font-medium text-[hsl(var(--text-primary))]">
                    {selectedAttendee.phone || "No especificado"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                  <Mail className="h-3.5 w-3.5" />
                  <span className="font-medium text-[hsl(var(--text-primary))]">
                    {selectedAttendee.email || "No especificado"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                  <Clock className="h-3.5 w-3.5" />
                  <span>
                    Ingreso:{" "}
                    {selectedAttendee.check_in_at
                      ? new Date(selectedAttendee.check_in_at).toLocaleString()
                      : "Sin registro de hora"}
                  </span>
                </div>
              </div>
            </div>

            {/* Trazabilidad CRM & Grupos */}
            <div className="rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
              <h4 className="text-xs font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wider">
                Consolidación y Grupos de Vida
              </h4>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-[hsl(var(--text-secondary))]">Caso CRM:</span>{" "}
                  {selectedAttendee.has_crm_case ? (
                    <span className="font-semibold text-[hsl(var(--success))]">
                      Asignado ({selectedAttendee.crm_stage_name})
                    </span>
                  ) : (
                    <span className="font-semibold text-[hsl(var(--warning))]">
                      Sin caso creado
                    </span>
                  )}
                </div>
                {selectedAttendee.assigned_agent_name && (
                  <div>
                    <span className="text-[hsl(var(--text-secondary))]">Responsable:</span>{" "}
                    <span className="font-medium text-[hsl(var(--text-primary))]">
                      {selectedAttendee.assigned_agent_name}
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-[hsl(var(--text-secondary))]">Grupo de Vida:</span>{" "}
                  <span className="font-medium text-[hsl(var(--text-primary))]">
                    {selectedAttendee.life_group_name || "Sin grupo asignado"}
                  </span>
                </div>
              </div>
            </div>

            {/* Botón de acción si no tiene caso */}
            {!selectedAttendee.has_crm_case && (
              <button
                onClick={() => {
                  handleChannelToCrm([selectedAttendee.persona_id]);
                  setSelectedAttendee(null);
                }}
                disabled={channelingLoading}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[hsl(var(--primary))] text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                <UserCheck className="h-4 w-4" />
                {channelingLoading
                  ? "Canalizando..."
                  : "Canalizar a Consolidación CRM Ahora"}
              </button>
            )}
          </div>
        )}
      </WorkspaceDrawer>

      {/* DRAWER 2: Canalización Masiva a CRM */}
      <WorkspaceDrawer
        isOpen={isChannelDrawerOpen}
        onClose={() => setIsChannelDrawerOpen(false)}
        title="Canalización a Consolidación CRM"
        subtitle={`Evento: ${postAnalytics?.event_name || ""}`}
      >
        <div className="space-y-6 p-4">
          <div className="p-4 rounded-xl border border-[hsl(var(--border-subtle))] bg-[hsl(var(--surface-2))] space-y-2">
            <h4 className="text-xs font-semibold text-[hsl(var(--text-primary))]">
              Integración Automática con CRM
            </h4>
            <p className="text-2xs text-[hsl(var(--text-secondary))] leading-relaxed">
              Esta acción creará un caso de consolidación pastoral en el pipeline canónico
              de la sede para todos los asistentes que aún no cuentan con seguimiento activo.
            </p>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
              Asistentes pendientes de canalización ({attendeesWithoutCase.length})
            </span>
            <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1 divide-y divide-[hsl(var(--border-subtle))]">
              {attendeesWithoutCase.map((a) => (
                <div key={a.persona_id} className="pt-2 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-medium text-[hsl(var(--text-primary))]">
                      {a.full_name}
                    </span>
                    <span className="ml-1 text-3xs text-[hsl(var(--text-secondary))]">
                      ({a.church_role})
                    </span>
                  </div>
                  <span className="text-3xs font-mono text-[hsl(var(--text-secondary))]">
                    {a.registration_code || "Puerta"}
                  </span>
                </div>
              ))}
              {attendeesWithoutCase.length === 0 && (
                <p className="text-xs text-[hsl(var(--text-secondary))] italic py-4 text-center">
                  Todos los asistentes ya cuentan con caso de consolidación en CRM.
                </p>
              )}
            </div>
          </div>

          <button
            onClick={() => {
              handleChannelToCrm();
              setIsChannelDrawerOpen(false);
            }}
            disabled={channelingLoading || attendeesWithoutCase.length === 0}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[hsl(var(--primary))] text-xs font-semibold text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50 shadow-sm"
          >
            <UserCheck className="h-4 w-4" />
            {channelingLoading
              ? "Procesando canalización..."
              : `Canalizar ${attendeesWithoutCase.length} asistentes a CRM`}
          </button>
        </div>
      </WorkspaceDrawer>
    </div>
  );
}

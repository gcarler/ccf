"use client";

import React, { useEffect, useState } from "react";
import {
  Calendar,
  CheckCircle2,
  ChevronRight,
  Download,
  HeartHandshake,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  } from "lucide-react";
import { apiFetch, apiFetchBlob } from "@/lib/http";
import EvangelismShell from "@/components/evangelism/EvangelismShell";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import type {
  AttendeeSpiritualJourneyData,
  EventCohortRetentionData,
  MinistryEvent,
  MultiSedeCohortAnalysisData,
  TemporalCohortMatrixData,
} from "@/app/plataforma/evangelism/types";

export default function CohortsRetentionPage() {
  const [activeTab, setActiveTab] = useState<"matrix" | "sedes" | "event_detail">("matrix");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Datos
  const [multiSedeData, setMultiSedeData] = useState<MultiSedeCohortAnalysisData | null>(null);
  const [matrixData, setMatrixData] = useState<TemporalCohortMatrixData | null>(null);
  const [eventsList, setEventsList] = useState<MinistryEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [eventCohortData, setEventCohortData] = useState<EventCohortRetentionData | null>(null);
  const [loadingEventCohort, setLoadingEventCohort] = useState(false);

  // Drawer de Trayectoria Espiritual
  const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null);
  const [journeyData, setJourneyData] = useState<AttendeeSpiritualJourneyData | null>(null);
  const [loadingJourney, setLoadingJourney] = useState(false);

  const loadGlobalData = async () => {
    setLoading(true);
    try {
      const [sedesRes, matrixRes, evsRes] = await Promise.all([
        apiFetch<MultiSedeCohortAnalysisData>("/evangelism/cohorts/multi-sede", { silent: true }),
        apiFetch<TemporalCohortMatrixData>("/evangelism/cohorts/matrix?months=6", { silent: true }),
        apiFetch<MinistryEvent[]>("/evangelism/events/", { silent: true }),
      ]);
      setMultiSedeData(sedesRes);
      setMatrixData(matrixRes);
      const evList = Array.isArray(evsRes) ? evsRes : [];
      setEventsList(evList);
      if (evList.length > 0 && !selectedEventId) {
        setSelectedEventId(evList[0].id);
      }
    } catch {
      // Manejo silencioso con degradación elegante
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Carga inicial única; la recarga manual vía loadGlobalData es intencional (botón de refresh).
    loadGlobalData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cargar cohorte de evento específico al cambiar de selección
  useEffect(() => {
    if (!selectedEventId) return;
    const fetchEventCohort = async () => {
      setLoadingEventCohort(true);
      try {
        const res = await apiFetch<EventCohortRetentionData>(
          `/evangelism/events/${selectedEventId}/cohort-retention`,
          { silent: true }
        );
        setEventCohortData(res);
      } catch {
        setEventCohortData(null);
      } finally {
        setLoadingEventCohort(false);
      }
    };
    fetchEventCohort();
  }, [selectedEventId]);

  // Cargar trayectoria espiritual del creyente seleccionado
  const handleOpenJourney = async (personaId: string) => {
    setSelectedPersonaId(personaId);
    setLoadingJourney(true);
    try {
      const res = await apiFetch<AttendeeSpiritualJourneyData>(
        `/evangelism/cohorts/attendees/${personaId}/spiritual-journey`,
        { silent: true }
      );
      setJourneyData(res);
    } catch {
      setJourneyData(null);
    } finally {
      setLoadingJourney(false);
    }
  };

  // Descargar exportación en CSV con UTF-8 BOM
  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const blob = await apiFetchBlob("/evangelism/cohorts/export");
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ccf_auditoria_pastoral_cohortes_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch {
      // Manejo silencioso
    } finally {
      setExporting(false);
    }
  };

  // Color de badge de retención según porcentaje
  const getRetentionColorClass = (pct: number) => {
    if (pct >= 50) return "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] border-[hsl(var(--success-border))]";
    if (pct >= 30) return "bg-[hsl(var(--info-muted))] text-[hsl(var(--info))] border-[hsl(var(--info-border))]";
    if (pct >= 15) return "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] border-[hsl(var(--warning-border))]";
    return "bg-[hsl(var(--destructive-muted))] text-[hsl(var(--destructive))] border-[hsl(var(--destructive-border))]";
  };

  // Badge de medalla para el ranking multi-sede
  const getRankBadge = (pos: number) => {
    if (pos === 1) return <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--warning-muted))] px-2 py-0.5 text-2xs font-black text-[hsl(var(--warning))]">🥇 1º Puesto</span>;
    if (pos === 2) return <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--text-secondary))]">🥈 2º Puesto</span>;
    if (pos === 3) return <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--text-muted))]">🥉 3º Puesto</span>;
    return <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">#{pos}</span>;
  };

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: "Evangelismo", href: "/plataforma/evangelism" },
        { label: "Cohortes y LTV Espiritual" },
      ]}
    >
      <main className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6">
        {/* 1. Header Maestro y Acciones */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-[hsl(var(--primary-muted))] p-1.5 text-[hsl(var(--primary))]">
                <TrendingUp className="h-5 w-5" />
              </span>
              <h1 className="text-xl font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                Cohortes de Retención & LTV Espiritual
              </h1>
            </div>
            <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
              Auditoría pastoral inter-sedes, retención temporal (30d, 60d, 90d) e índice de madurez espiritual de nuevos creyentes.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={loadGlobalData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] px-3 py-2 text-xs font-semibold text-[hsl(var(--text-primary))] shadow-sm transition hover:bg-[hsl(var(--bg-muted))]"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Actualizar</span>
            </button>
            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-xs font-semibold text-[hsl(var(--primary-foreground))] shadow transition hover:opacity-90 disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              <span>{exporting ? "Generando..." : "Exportar Informe Pastoral (CSV)"}</span>
            </button>
          </div>
        </div>

        {/* 2. Tarjetas KPI Ejecutivas Globales */}
        {multiSedeData && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* KPI 1 */}
            <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Total en Cohortes
                </span>
                <Users className="h-4 w-4 text-[hsl(var(--primary))]" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                  {multiSedeData.global_kpis.total_cohort_size}
                </span>
                <span className="text-xs text-[hsl(var(--text-secondary))]">
                  asistentes
                </span>
              </div>
              <div className="mt-2 text-2xs text-[hsl(var(--text-muted))]">
                En {multiSedeData.global_kpis.total_events} eventos de {multiSedeData.global_kpis.total_sedes} sedes
              </div>
            </div>

            {/* KPI 2 */}
            <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Retención 30 Días (Mes 1)
                </span>
                <HeartHandshake className="h-4 w-4 text-[hsl(var(--info))]" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                  {multiSedeData.global_kpis.avg_retention_30d_pct}%
                </span>
                <span className="text-xs text-[hsl(var(--text-secondary))]">
                  en Grupo de Vida
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
                <div
                  className="h-full bg-[hsl(var(--info))]"
                  style={{ width: `${Math.min(100, multiSedeData.global_kpis.avg_retention_30d_pct)}%` }}
                />
              </div>
            </div>

            {/* KPI 3 */}
            <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Retención 90 Días (Consolidada)
                </span>
                <ShieldCheck className="h-4 w-4 text-[hsl(var(--success))]" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                  {multiSedeData.global_kpis.avg_retention_90d_pct}%
                </span>
                <span className="text-xs text-[hsl(var(--text-secondary))]">
                  fidelización trimestral
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--bg-muted))]">
                <div
                  className="h-full bg-[hsl(var(--success))]"
                  style={{ width: `${Math.min(100, multiSedeData.global_kpis.avg_retention_90d_pct)}%` }}
                />
              </div>
            </div>

            {/* KPI 4 */}
            <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Madurez Espiritual (SMI)
                </span>
                <Sparkles className="h-4 w-4 text-[hsl(var(--warning))]" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-black text-[hsl(var(--text-primary))]">
                  {multiSedeData.global_kpis.global_avg_spiritual_maturity}
                </span>
                <span className="text-xs text-[hsl(var(--text-secondary))]">
                  / 100 puntos LTV
                </span>
              </div>
              <div className="mt-2 text-2xs text-[hsl(var(--text-muted))]">
                Escala holística: Decisión, Grupo, Bautismo, Academia, Servicio
              </div>
            </div>
          </div>
        )}

        {/* 3. Selector de Vistas / Pestañas */}
        <div className="flex border-b border-[hsl(var(--border-primary))] gap-6 text-xs font-bold uppercase tracking-wider">
          <button
            onClick={() => setActiveTab("matrix")}
            className={`pb-3 border-b-2 transition ${
              activeTab === "matrix"
                ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            }`}
          >
            Matriz Temporal de Cohortes
          </button>
          <button
            onClick={() => setActiveTab("sedes")}
            className={`pb-3 border-b-2 transition ${
              activeTab === "sedes"
                ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            }`}
          >
            Auditoría & Ranking Multi-Sede
          </button>
          <button
            onClick={() => setActiveTab("event_detail")}
            className={`pb-3 border-b-2 transition ${
              activeTab === "event_detail"
                ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
            }`}
          >
            Cohorte por Evento & Nómina de Creyentes
          </button>
        </div>

        {/* 4. VISTA 1: MATRIZ TEMPORAL (HEATMAP) */}
        {activeTab === "matrix" && matrixData && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                  Evolución Temporal de Cohortes (Últimos 6 Meses)
                </h3>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Seguimiento del porcentaje de personas que continúan conectadas tras su primer evento.
                </p>
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  <tr>
                    <th className="px-4 py-3">Cohorte Mensual</th>
                    <th className="px-4 py-3 text-center">Eventos</th>
                    <th className="px-4 py-3 text-center">Tamaño Cohorte</th>
                    <th className="px-4 py-3 text-center">Mes 1 (30 Días)</th>
                    <th className="px-4 py-3 text-center">Mes 2 (60 Días)</th>
                    <th className="px-4 py-3 text-center">Mes 3 (90 Días)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border-primary))] font-medium text-[hsl(var(--text-primary))]">
                  {matrixData.cohorts.map((row) => (
                    <tr key={row.cohort_key} className="transition hover:bg-[hsl(var(--bg-muted))]/40">
                      <td className="px-4 py-3.5 font-bold">
                        <div>{row.cohort_label}</div>
                        <span className="font-mono text-3xs text-[hsl(var(--text-muted))]">{row.cohort_key}</span>
                      </td>
                      <td className="px-4 py-3.5 text-center font-semibold text-[hsl(var(--text-secondary))]">
                        {row.events_count}
                      </td>
                      <td className="px-4 py-3.5 text-center font-black">
                        {row.total_cohort_size}
                      </td>

                      {/* M1: 30 Días */}
                      <td className="px-4 py-3.5 text-center">
                        <span
                          className={`inline-block w-20 rounded-md border py-1 text-xs font-bold ${getRetentionColorClass(
                            row.m1_30d.percentage
                          )}`}
                        >
                          {row.m1_30d.percentage}%
                          <span className="block text-3xs font-normal opacity-80">({row.m1_30d.count})</span>
                        </span>
                      </td>

                      {/* M2: 60 Días */}
                      <td className="px-4 py-3.5 text-center">
                        <span
                          className={`inline-block w-20 rounded-md border py-1 text-xs font-bold ${getRetentionColorClass(
                            row.m2_60d.percentage
                          )}`}
                        >
                          {row.m2_60d.percentage}%
                          <span className="block text-3xs font-normal opacity-80">({row.m2_60d.count})</span>
                        </span>
                      </td>

                      {/* M3: 90 Días */}
                      <td className="px-4 py-3.5 text-center">
                        <span
                          className={`inline-block w-20 rounded-md border py-1 text-xs font-bold ${getRetentionColorClass(
                            row.m3_90d.percentage
                          )}`}
                        >
                          {row.m3_90d.percentage}%
                          <span className="block text-3xs font-normal opacity-80">({row.m3_90d.count})</span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. VISTA 2: AUDITORÍA Y RANKING MULTI-SEDE */}
        {activeTab === "sedes" && multiSedeData && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                  Auditoría y Desempeño Inter-Sedes
                </h3>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                  Puntuación de efectividad pastoral ponderada (Retención 90d: 40%, Madurez SMI: 30%, Bautismos: 20%, Academia: 10%).
                </p>
              </div>
            </div>

            <div className="overflow-hidden rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    <tr>
                      <th className="px-4 py-3">Puesto</th>
                      <th className="px-4 py-3">Sede & Ciudad</th>
                      <th className="px-4 py-3 text-center">Eventos</th>
                      <th className="px-4 py-3 text-center">Asistentes</th>
                      <th className="px-4 py-3 text-center">Retención 30d</th>
                      <th className="px-4 py-3 text-center">Retención 90d</th>
                      <th className="px-4 py-3 text-center">Tasa Bautismo</th>
                      <th className="px-4 py-3 text-center">Tasa Academia</th>
                      <th className="px-4 py-3 text-center">SMI Medio</th>
                      <th className="px-4 py-3 text-right">Efectividad Pastoral</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border-primary))] font-medium text-[hsl(var(--text-primary))]">
                    {multiSedeData.sedes_ranking.map((s) => (
                      <tr key={s.sede_id} className="transition hover:bg-[hsl(var(--bg-muted))]/40">
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          {getRankBadge(s.rank_position)}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="font-bold text-[hsl(var(--text-primary))]">{s.sede_name}</div>
                          <div className="text-2xs text-[hsl(var(--text-secondary))] flex items-center gap-1 mt-0.5">
                            <MapPin className="h-3 w-3" /> {s.city}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-center font-semibold text-[hsl(var(--text-secondary))]">
                          {s.total_events}
                        </td>
                        <td className="px-4 py-3.5 text-center font-black">
                          {s.total_cohort_size}
                        </td>
                        <td className="px-4 py-3.5 text-center font-semibold">
                          {s.retention_30d_pct}%
                        </td>
                        <td className="px-4 py-3.5 text-center font-bold text-[hsl(var(--success))]">
                          {s.retention_90d_pct}%
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          {s.baptism_rate_pct}%
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          {s.academy_rate_pct}%
                        </td>
                        <td className="px-4 py-3.5 text-center font-bold text-[hsl(var(--warning))]">
                          {s.avg_spiritual_maturity_score}
                        </td>
                        <td className="px-4 py-3.5 text-right whitespace-nowrap">
                          <span className="rounded-lg bg-[hsl(var(--primary-muted))] px-2.5 py-1 font-black text-xs text-[hsl(var(--primary))]">
                            {s.pastoral_efficiency_score} / 100
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 6. VISTA 3: COHORTE POR EVENTO Y NÓMINA */}
        {activeTab === "event_detail" && (
          <div className="space-y-6">
            {/* Selector de Evento */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-4">
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-[hsl(var(--primary))]" />
                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    Seleccionar Evento a Auditar:
                  </label>
                  <select
                    value={selectedEventId}
                    onChange={(e) => setSelectedEventId(e.target.value)}
                    className="mt-1 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none"
                  >
                    {eventsList.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.name} ({ev.event_date ? new Date(ev.event_date).toLocaleDateString() : "Sin fecha"})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {eventCohortData && (
                <div className="text-xs text-[hsl(var(--text-secondary))] font-medium">
                  Tamaño de cohorte: <span className="font-bold text-[hsl(var(--text-primary))]">{eventCohortData.total_cohort_size} creyentes</span>
                </div>
              )}
            </div>

            {loadingEventCohort ? (
              <div className="flex h-48 items-center justify-center text-xs text-[hsl(var(--text-secondary))]">
                <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Cargando cohorte del evento...
              </div>
            ) : eventCohortData ? (
              <div className="space-y-6">
                {/* Métricas de Madurez Espiritual del Evento */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-3 text-center">
                    <div className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">Decisión de Fe</div>
                    <div className="mt-1 text-xl font-black text-[hsl(var(--primary))]">
                      {eventCohortData.spiritual_ltv_summary.decision_rate_pct}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-3 text-center">
                    <div className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">Grupo de Vida</div>
                    <div className="mt-1 text-xl font-black text-[hsl(var(--info))]">
                      {eventCohortData.spiritual_ltv_summary.group_integration_rate_pct}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-3 text-center">
                    <div className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">Bautismo en Agua</div>
                    <div className="mt-1 text-xl font-black text-[hsl(var(--success))]">
                      {eventCohortData.spiritual_ltv_summary.baptism_rate_pct}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-3 text-center">
                    <div className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">Academia</div>
                    <div className="mt-1 text-xl font-black text-[hsl(var(--warning))]">
                      {eventCohortData.spiritual_ltv_summary.academy_rate_pct}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] p-3 text-center">
                    <div className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))]">Servicio Activo</div>
                    <div className="mt-1 text-xl font-black text-[hsl(var(--primary))]">
                      {eventCohortData.spiritual_ltv_summary.service_leadership_rate_pct}%
                    </div>
                  </div>
                </div>

                {/* Tabla de Asistentes en la Cohorte */}
                <div className="overflow-hidden rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] shadow-sm">
                  <div className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 font-bold text-xs uppercase tracking-wider text-[hsl(var(--text-primary))] flex items-center justify-between">
                    <span>Nómina de Asistentes y Nivel de Madurez (LTV)</span>
                    <span className="text-2xs font-normal text-[hsl(var(--text-secondary))]">
                      {eventCohortData.attendees_cohort.length} personas evaluadas
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-secondary))] text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                        <tr>
                          <th className="px-4 py-3">Creyente</th>
                          <th className="px-4 py-3 text-center">Retención 30d</th>
                          <th className="px-4 py-3 text-center">Retención 60d</th>
                          <th className="px-4 py-3 text-center">Retención 90d</th>
                          <th className="px-4 py-3 text-center">Bautizado</th>
                          <th className="px-4 py-3 text-center">Academia</th>
                          <th className="px-4 py-3 text-center">Puntaje SMI</th>
                          <th className="px-4 py-3 text-right">Acción</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[hsl(var(--border-primary))] font-medium text-[hsl(var(--text-primary))]">
                        {eventCohortData.attendees_cohort.map((a) => (
                          <tr key={a.persona_id} className="transition hover:bg-[hsl(var(--bg-muted))]/40">
                            <td className="px-4 py-3">
                              <div className="font-bold">{a.full_name}</div>
                              <span className="font-mono text-2xs text-[hsl(var(--text-secondary))]">
                                {a.registration_code}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              {a.retained_30d ? (
                                <span className="rounded bg-[hsl(var(--success-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">Sí</span>
                              ) : (
                                <span className="text-2xs text-[hsl(var(--text-muted))]">No</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {a.retained_60d ? (
                                <span className="rounded bg-[hsl(var(--success-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">Sí</span>
                              ) : (
                                <span className="text-2xs text-[hsl(var(--text-muted))]">No</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {a.retained_90d ? (
                                <span className="rounded bg-[hsl(var(--success-muted))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">Sí</span>
                              ) : (
                                <span className="text-2xs text-[hsl(var(--text-muted))]">No</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {a.is_baptized ? "✓" : "—"}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {a.has_academy_enrollment ? "✓" : "—"}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className="rounded bg-[hsl(var(--primary-muted))] px-2 py-0.5 text-xs font-black text-[hsl(var(--primary))]">
                                {a.spiritual_maturity_score} pts ({a.maturity_level})
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => handleOpenJourney(a.persona_id)}
                                className="inline-flex items-center gap-1 rounded border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-2.5 py-1 text-2xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] transition"
                              >
                                <span>Trayectoria</span>
                                <ChevronRight className="h-3 w-3" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* ── WORKSPACE DRAWER: TRAYECTORIA ESPIRITUAL DEL CREYENTE ── */}
        <WorkspaceDrawer
          isOpen={Boolean(selectedPersonaId)}
          onClose={() => {
            setSelectedPersonaId(null);
            setJourneyData(null);
          }}
          title="Trayectoria y Crecimiento Espiritual"
          subtitle={journeyData ? journeyData.full_name : undefined}
        >
          {loadingJourney ? (
            <div className="flex h-64 items-center justify-center text-xs text-[hsl(var(--text-secondary))]">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" /> Cargando camino espiritual...
            </div>
          ) : journeyData ? (
            <div className="space-y-6 p-4 text-xs">
              {/* Resumen Superior */}
              <div className="rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-[hsl(var(--text-primary))]">
                      {journeyData.full_name}
                    </h3>
                    <div className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">
                      Rol: {journeyData.church_role || "Persona de la comunidad"} • Estado: {journeyData.spiritual_status || "Activo"}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="rounded-full bg-[hsl(var(--primary-muted))] px-3 py-1 font-black text-xs text-[hsl(var(--primary))]">
                      {journeyData.spiritual_maturity_score} / 100 PTS
                    </span>
                    <div className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mt-1">
                      Nivel: {journeyData.maturity_level}
                    </div>
                  </div>
                </div>
              </div>

              {/* Estadísticas de Participación */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 text-center">
                  <div className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">Eventos Asistidos</div>
                  <div className="mt-1 text-lg font-black text-[hsl(var(--text-primary))]">{journeyData.events_attended_count}</div>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 text-center">
                  <div className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">Reuniones de Grupo</div>
                  <div className="mt-1 text-lg font-black text-[hsl(var(--info))]">{journeyData.group_meetings_attended_count}</div>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 text-center">
                  <div className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">Cursos en Academia</div>
                  <div className="mt-1 text-lg font-black text-[hsl(var(--warning))]">{journeyData.academy_courses_count}</div>
                </div>
              </div>

              {/* Hitos Alcanzados */}
              <div>
                <h4 className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">
                  Hitos de Fe y Madurez Espiritual
                </h4>
                <div className="space-y-2">
                  {journeyData.milestones.map((m, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3"
                    >
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="h-4 w-4 text-[hsl(var(--success))]" />
                        <div>
                          <div className="font-bold text-[hsl(var(--text-primary))]">{m.title}</div>
                          {m.date && (
                            <div className="text-3xs text-[hsl(var(--text-muted))]">
                              Registrado: {new Date(m.date).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      </div>
                      <span className="font-mono text-2xs font-black text-[hsl(var(--primary))]">
                        +{m.pts} pts
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Eventos Asistidos */}
              {journeyData.events.length > 0 && (
                <div>
                  <h4 className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                    Historial de Eventos Evangelísticos
                  </h4>
                  <div className="space-y-1.5">
                    {journeyData.events.map((ev, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-2xs"
                      >
                        <span className="font-semibold text-[hsl(var(--text-primary))]">{ev.event_name}</span>
                        <span className="text-[hsl(var(--text-muted))]">
                          {ev.attended_at ? new Date(ev.attended_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </WorkspaceDrawer>
      </main>
    </EvangelismShell>
  );
}

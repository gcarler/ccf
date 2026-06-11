"use client";

import EvangelismShell from "@/components/evangelism/EvangelismShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Info,
  Loader2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ─── Types ───────────────────────────────────────────────────────────

interface KpiData {
  active_members: { value: number; delta: number };
  attendance_pct: { value: number; delta: number };
  sessions: { done: number; total: number; completion_pct: number };
  retention_pct: { value: number; delta: number };
  new_joiners: { value: number; delta: number };
  active_groups: { value: number; with_sessions: number };
}

interface TrendBucket {
  key: string;
  label: string;
  avg_pct: number | null;
  [key: string]: number | string | null;
}

interface TrendData {
  buckets: TrendBucket[];
  groups: { id: number; name: string }[];
}

interface FunnelStage {
  key: string;
  label: string;
  count: number;
  pct_of_top: number;
  avg_days_before: number | null;
}

interface HeatmapCell {
  weekday: number;
  label: string;
  sessions: number;
  present: number;
  total: number;
  pct: number | null;
}

interface Alert {
  type: string;
  severity: "high" | "medium" | "info";
  group_id?: number;
  group_name?: string;
  persona_id?: string;
  persona_name?: string;
  message: string;
  consecutive_sessions?: number;
  consecutive_absences?: number;
  members?: number;
  capacity?: number;
}

interface VelocityStage {
  role: string;
  label: string;
  avg_days: number;
  transitions: number;
  pct_of_max: number;
}

interface GroupDetail {
  id: number;
  name: string;
  code: string | null;
  leader_name: string;
  members: number;
  attendance_pct: number;
  prev_attendance_pct: number;
  attendance_delta: number;
  new_joiners: number;
  sparkline: number[];
  capacity: number;
}

// ─── Constants ───────────────────────────────────────────────────────

const PERIODS = [
  { value: "7d", label: "7 días" },
  { value: "30d", label: "30 días" },
  { value: "90d", label: "90 días" },
  { value: "180d", label: "6 meses" },
  { value: "365d", label: "1 año" },
] as const;

type Period = (typeof PERIODS)[number]["value"];

const GROUP_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#14b8a6",
];

// ─── Sub-components ───────────────────────────────────────────────────

function KpiCard({
  title,
  value,
  delta,
  sub,
  icon: Icon,
  format = "number",
}: {
  title: string;
  value: number;
  delta?: number;
  sub?: string;
  icon: React.ElementType;
  format?: "number" | "percent" | "fraction";
}) {
  const positive = delta !== undefined && delta > 0;
  const negative = delta !== undefined && delta < 0;

  const display =
    format === "percent"
      ? `${value}%`
      : format === "fraction"
      ? String(value)
      : value.toLocaleString("es-CO");

  return (
    <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {title}
        </span>
        <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-white/10">
          <Icon size={14} className="text-slate-500 dark:text-slate-400" />
        </div>
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className="text-3xl font-black text-slate-800 dark:text-slate-100 tabular-nums leading-none">
          {display}
        </span>
        {delta !== undefined && delta !== 0 && (
          <span
            className={`flex items-center gap-0.5 text-[11px] font-bold pb-0.5 ${
              positive
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-500 dark:text-red-400"
            }`}
          >
            {positive ? (
              <TrendingUp size={12} />
            ) : (
              <TrendingDown size={12} />
            )}
            {Math.abs(delta)}
            {format === "percent" ? "pp" : "%"}
          </span>
        )}
      </div>
      {sub && (
        <span className="text-[11px] text-slate-400">{sub}</span>
      )}
    </div>
  );
}

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 tracking-tight">
        {title}
      </h3>
      {sub && (
        <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>
      )}
    </div>
  );
}

function Sparkline({ data }: { data: number[] }) {
  if (!data || data.length === 0) return <span className="text-slate-400 text-[10px]">—</span>;
  const max = Math.max(...data, 1);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 24;
  const step = w / Math.max(data.length - 1, 1);
  const points = data
    .map((v, i) => `${i * step},${h - ((v - min) / range) * h}`)
    .join(" ");

  const last = data[data.length - 1];
  const prev = data[data.length - 2] ?? last;
  const up = last >= prev;

  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        fill="none"
        stroke={up ? "#10b981" : "#ef4444"}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-40">
      <Loader2 size={20} className="animate-spin text-slate-400" />
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────

export default function StrategyAnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { token } = useAuth();

  const [period, setPeriod] = useState<Period>("30d");
  const [strategyName, setStrategyName] = useState<string>("");

  const [kpis, setKpis] = useState<KpiData | null>(null);
  const [trend, setTrend] = useState<TrendData | null>(null);
  const [funnel, setFunnel] = useState<{ total_active: number; stages: FunnelStage[] } | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapCell[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [velocity, setVelocity] = useState<VelocityStage[] | null>(null);
  const [groupsDetail, setGroupsDetail] = useState<GroupDetail[] | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load strategy name
  useEffect(() => {
    if (!token || !id) return;
    apiFetch<{ name?: string; nombre?: string }>(`/evangelism/strategies/${id}`, { token })
      .then((s) => setStrategyName(s?.name || s?.nombre || "Estrategia"))
      .catch(() => {});
  }, [id, token]);

  const loadAll = useCallback(
    async (showRefreshing = false) => {
      if (!token || !id) return;
      if (showRefreshing) setRefreshing(true);
      else setLoading(true);

      const base = `/evangelism/analytics/strategy/${id}`;

      try {
        const [kpisRes, trendRes, funnelRes, heatmapRes, alertsRes, velocityRes, groupsRes] =
          await Promise.allSettled([
            apiFetch<any>(base, { token, query: { period } }),
            apiFetch<TrendData>(`${base}/trend`, { token, query: { period } }),
            apiFetch<any>(`${base}/funnel`, { token }),
            apiFetch<any>(`${base}/heatmap`, { token, query: { period } }),
            apiFetch<any>(`${base}/alerts`, { token }),
            apiFetch<any>(`${base}/velocity`, { token }),
            apiFetch<any>(`${base}/groups`, { token, query: { period } }),
          ]);

        if (kpisRes.status === "fulfilled") setKpis(kpisRes.value?.kpis ?? null);
        if (trendRes.status === "fulfilled") setTrend(trendRes.value);
        if (funnelRes.status === "fulfilled") setFunnel(funnelRes.value);
        if (heatmapRes.status === "fulfilled") setHeatmap(heatmapRes.value?.cells ?? null);
        if (alertsRes.status === "fulfilled") setAlerts(alertsRes.value?.alerts ?? null);
        if (velocityRes.status === "fulfilled") setVelocity(velocityRes.value?.stages ?? null);
        if (groupsRes.status === "fulfilled") setGroupsDetail(groupsRes.value?.groups ?? null);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [id, token, period]
  );

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ── Trend chart lines ──
  const trendLines = useMemo(() => {
    if (!trend?.groups?.length) return [];
    return trend.groups.map((g, i) => ({
      dataKey: `g_${g.id}`,
      name: g.name,
      color: GROUP_COLORS[i % GROUP_COLORS.length],
    }));
  }, [trend]);

  // ── Alert severity config ──
  const alertConfig = {
    high: { color: "text-red-600 dark:text-red-400", bg: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900/50", icon: AlertTriangle },
    medium: { color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50", icon: AlertTriangle },
    info: { color: "text-sky-600 dark:text-sky-400", bg: "bg-sky-50 dark:bg-sky-950/30 border-sky-200 dark:border-sky-900/50", icon: Info },
  };

  // ── Heatmap color ──
  function heatColor(pct: number | null) {
    if (pct === null) return "bg-slate-100 dark:bg-white/5 text-slate-400";
    if (pct >= 85) return "bg-emerald-500 text-white";
    if (pct >= 70) return "bg-emerald-400 text-white";
    if (pct >= 55) return "bg-amber-400 text-white";
    if (pct >= 40) return "bg-orange-400 text-white";
    return "bg-red-400 text-white";
  }

  return (
    <EvangelismShell>
      <div className="min-h-full bg-[hsl(var(--bg-secondary))]">
        {/* ── Header ── */}
        <div className="sticky top-0 z-20 bg-[hsl(var(--bg-primary))] border-b border-[hsl(var(--border-primary))] px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/plataforma/evangelism/strategies/${id}`)}
              className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-colors text-slate-500"
            >
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-sm font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <BarChart3 size={16} className="text-[hsl(var(--primary))]" />
                Métricas — {strategyName || "Estrategia"}
              </h1>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
                Dashboard analítico · Tiempo real
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Period selector */}
            <div className="flex items-center bg-slate-100 dark:bg-white/10 rounded-lg p-0.5 gap-0.5">
              {PERIODS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value as Period)}
                  className={`px-3 py-1 text-[11px] font-semibold rounded-md transition-all ${
                    period === p.value
                      ? "bg-white dark:bg-white/20 text-slate-800 dark:text-slate-100 shadow-sm"
                      : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <button
              onClick={() => loadAll(true)}
              disabled={refreshing}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-colors text-slate-500 disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {/* ── Body ── */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 size={28} className="animate-spin text-[hsl(var(--primary))]" />
          </div>
        ) : (
          <div className="px-6 py-6 space-y-8 max-w-screen-2xl mx-auto">

            {/* ═══ KPI Cards ═══ */}
            {kpis && (
              <section>
                <SectionHeader
                  title="Indicadores clave"
                  sub={`Período: ${PERIODS.find((p) => p.value === period)?.label} · vs período anterior`}
                />
                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                  <KpiCard
                    title="Personas activas"
                    value={kpis.active_members.value}
                    delta={kpis.active_members.delta}
                    icon={Users}
                  />
                  <KpiCard
                    title="Asistencia promedio"
                    value={kpis.attendance_pct.value}
                    delta={kpis.attendance_pct.delta}
                    icon={CheckCircle2}
                    format="percent"
                  />
                  <KpiCard
                    title="Sesiones realizadas"
                    value={kpis.sessions.done}
                    sub={`de ${kpis.sessions.total} planeadas · ${kpis.sessions.completion_pct}%`}
                    icon={BarChart3}
                  />
                  <KpiCard
                    title="Retención"
                    value={kpis.retention_pct.value}
                    icon={TrendingUp}
                    format="percent"
                  />
                  <KpiCard
                    title="Nuevos ingresos"
                    value={kpis.new_joiners.value}
                    delta={kpis.new_joiners.delta}
                    icon={Users}
                  />
                  <KpiCard
                    title="Grupos activos"
                    value={kpis.active_groups.value}
                    sub={`${kpis.active_groups.with_sessions} con sesiones`}
                    icon={Zap}
                  />
                </div>
              </section>
            )}

            {/* ═══ Trend + Funnel (2 columns) ═══ */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

              {/* Tendencia de asistencia */}
              <section className="xl:col-span-2 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
                <SectionHeader
                  title="Tendencia de asistencia"
                  sub="Porcentaje de asistencia por período"
                />
                {!trend || trend.buckets.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-sm">Sin datos de sesiones en este período</div>
                ) : (
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={trend.buckets} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                      <XAxis
                        dataKey="label"
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: "#94a3b8" }}
                        axisLine={false}
                        tickLine={false}
                        domain={[0, 100]}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--bg-primary))",
                          border: "1px solid hsl(var(--border-primary))",
                          borderRadius: "8px",
                          fontSize: "11px",
                        }}
                        formatter={(val: number, name: string) => [`${val ?? "—"}%`, name]}
                      />
                      {/* Global average */}
                      <Line
                        type="monotone"
                        dataKey="avg_pct"
                        name="Promedio"
                        stroke="#6366f1"
                        strokeWidth={2.5}
                        dot={false}
                        connectNulls
                      />
                      {/* Per-group lines */}
                      {trendLines.map((line) => (
                        <Line
                          key={line.dataKey}
                          type="monotone"
                          dataKey={line.dataKey}
                          name={line.name}
                          stroke={line.color}
                          strokeWidth={1.5}
                          dot={false}
                          strokeDasharray="4 2"
                          connectNulls
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                )}

                {/* Legend */}
                {trendLines.length > 0 && (
                  <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-[hsl(var(--border-primary))]">
                    <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                      <span className="w-4 h-[2px] bg-[hsl(var(--primary))] inline-block rounded" />
                      Promedio global
                    </span>
                    {trendLines.map((l) => (
                      <span key={l.dataKey} className="flex items-center gap-1.5 text-[10px] text-slate-500">
                        <span
                          className="w-4 h-[1.5px] inline-block rounded"
                          style={{ background: l.color }}
                        />
                        {l.name}
                      </span>
                    ))}
                  </div>
                )}
              </section>

              {/* Embudo de conversión */}
              <section className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
                <SectionHeader
                  title="Embudo de roles"
                  sub={`${funnel?.total_active ?? 0} personas en total`}
                />
                {!funnel || funnel.stages.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-sm">Sin participantes</div>
                ) : (
                  <div className="space-y-2">
                    {funnel.stages.map((stage, i) => {
                      const colors = [
                        "bg-slate-400",
                        "bg-blue-400",
                        "bg-[hsl(var(--primary))]",
                        "bg-sky-500",
                        "bg-slate-600",
                      ];
                      return (
                        <div key={stage.key}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                              {stage.label}
                            </span>
                            <span className="text-[11px] font-black text-slate-800 dark:text-slate-100 tabular-nums">
                              {stage.count}
                              <span className="font-normal text-slate-400 ml-1">
                                ({stage.pct_of_top}%)
                              </span>
                            </span>
                          </div>
                          <div className="h-2 bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${colors[i] ?? "bg-[hsl(var(--primary))]"}`}
                              style={{ width: `${Math.max(stage.pct_of_top, 2)}%` }}
                            />
                          </div>
                          {stage.avg_days_before !== null && stage.avg_days_before > 0 && (
                            <p className="text-[10px] text-slate-400 mt-0.5">
                              ⟵ promedio {stage.avg_days_before} días antes de ascender
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            </div>

            {/* ═══ Groups table + Heatmap ═══ */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

              {/* Tabla de grupos */}
              <section className="xl:col-span-2 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5 overflow-hidden">
                <SectionHeader
                  title="Grupos"
                  sub="Métricas por grupo ordenadas por asistencia"
                />
                {!groupsDetail || groupsDetail.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-sm">Sin grupos</div>
                ) : (
                  <div className="overflow-x-auto -mx-1">
                    <table className="w-full text-[11px]">
                      <thead>
                        <tr className="border-b border-[hsl(var(--border-primary))]">
                          {["Grupo", "Líder", "Personas", "Asistencia", "Δ Período", "Nuevos", "Últimas sesiones"].map((h) => (
                            <th
                              key={h}
                              className="text-left py-2 px-2 font-semibold text-slate-400 uppercase tracking-wider text-[10px]"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[hsl(var(--border-primary))]">
                        {groupsDetail.map((g) => (
                          <tr key={g.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <td className="py-2.5 px-2 font-semibold text-slate-800 dark:text-slate-100">
                              {g.name}
                              {g.code && (
                                <span className="ml-1 text-[10px] text-slate-400">{g.code}</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2 text-slate-500">{g.leader_name}</td>
                            <td className="py-2.5 px-2 tabular-nums text-slate-700 dark:text-slate-300">
                              {g.members}
                              <span className="text-slate-400">/{g.capacity}</span>
                            </td>
                            <td className="py-2.5 px-2">
                              <div className="flex items-center gap-2">
                                <div className="w-16 h-1.5 bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      g.attendance_pct >= 80
                                        ? "bg-emerald-500"
                                        : g.attendance_pct >= 60
                                        ? "bg-amber-400"
                                        : "bg-red-400"
                                    }`}
                                    style={{ width: `${g.attendance_pct}%` }}
                                  />
                                </div>
                                <span className="tabular-nums font-bold text-slate-800 dark:text-slate-100">
                                  {g.attendance_pct}%
                                </span>
                              </div>
                            </td>
                            <td className="py-2.5 px-2 tabular-nums">
                              <span
                                className={`flex items-center gap-0.5 font-semibold ${
                                  g.attendance_delta > 0
                                    ? "text-emerald-600 dark:text-emerald-400"
                                    : g.attendance_delta < 0
                                    ? "text-red-500"
                                    : "text-slate-400"
                                }`}
                              >
                                {g.attendance_delta > 0 ? (
                                  <TrendingUp size={10} />
                                ) : g.attendance_delta < 0 ? (
                                  <TrendingDown size={10} />
                                ) : null}
                                {g.attendance_delta > 0 ? "+" : ""}
                                {g.attendance_delta}pp
                              </span>
                            </td>
                            <td className="py-2.5 px-2 tabular-nums">
                              {g.new_joiners > 0 ? (
                                <span className="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 px-1.5 py-0.5 rounded text-[10px] font-bold">
                                  +{g.new_joiners}
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                            <td className="py-2.5 px-2">
                              <Sparkline data={g.sparkline} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* Mapa de calor por día */}
              <section className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
                <SectionHeader
                  title="Asistencia por día"
                  sub="Rendimiento promedio según día de la semana"
                />
                {!heatmap || heatmap.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-sm">Sin datos</div>
                ) : (
                  <div className="space-y-2">
                    {heatmap.map((cell) => (
                      <div key={cell.weekday} className="flex items-center gap-3">
                        <span className="text-[11px] font-semibold text-slate-500 w-16 shrink-0 truncate">
                          {cell.label}
                        </span>
                        <div className="flex-1 h-7 bg-slate-100 dark:bg-white/5 rounded-lg overflow-hidden">
                          {cell.pct !== null ? (
                            <div
                              className={`h-full flex items-center justify-end pr-2 rounded-lg text-[10px] font-bold transition-all ${heatColor(cell.pct)}`}
                              style={{ width: `${Math.max(cell.pct, 8)}%` }}
                            >
                              {cell.pct}%
                            </div>
                          ) : (
                            <div className="h-full flex items-center pl-3 text-[10px] text-slate-400">
                              sin sesiones
                            </div>
                          )}
                        </div>
                        {cell.sessions > 0 && (
                          <span className="text-[10px] text-slate-400 w-12 text-right shrink-0">
                            {cell.sessions} ses.
                          </span>
                        )}
                      </div>
                    ))}

                    {/* Color legend */}
                    <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[hsl(var(--border-primary))]">
                      <span className="text-[10px] text-slate-400">Baja</span>
                      <div className="flex gap-0.5 flex-1">
                        {["bg-red-400", "bg-orange-400", "bg-amber-400", "bg-emerald-400", "bg-emerald-500"].map((c, i) => (
                          <div key={i} className={`h-2 flex-1 rounded-sm ${c}`} />
                        ))}
                      </div>
                      <span className="text-[10px] text-slate-400">Alta</span>
                    </div>
                  </div>
                )}
              </section>
            </div>

            {/* ═══ Alerts + Velocity ═══ */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

              {/* Alertas tempranas */}
              <section className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
                <SectionHeader
                  title="Alertas tempranas"
                  sub={`${alerts?.length ?? 0} alertas activas`}
                />
                {!alerts || alerts.length === 0 ? (
                  <div className="text-center py-10">
                    <CheckCircle2 size={32} className="mx-auto text-emerald-400 mb-2" />
                    <p className="text-sm text-slate-400">Todo en orden — sin alertas activas</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {alerts.map((alert, i) => {
                      const cfg = alertConfig[alert.severity] ?? alertConfig.medium;
                      const AlertIcon = cfg.icon;
                      return (
                        <div
                          key={i}
                          className={`flex gap-3 p-3 rounded-lg border text-[11px] ${cfg.bg}`}
                        >
                          <AlertIcon size={14} className={`shrink-0 mt-0.5 ${cfg.color}`} />
                          <div>
                            <p className="font-semibold text-slate-700 dark:text-slate-200">
                              {alert.group_name || alert.persona_name}
                            </p>
                            <p className="text-slate-500 dark:text-slate-400">{alert.message}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Velocidad ministerial */}
              <section className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
                <SectionHeader
                  title="Velocidad ministerial"
                  sub="Días promedio que una persona permanece en cada rol antes de ascender"
                />
                {!velocity || velocity.length === 0 ? (
                  <div className="text-center py-10 text-slate-400 text-sm">
                    Sin historial de cambios de rol registrado
                  </div>
                ) : (
                  <div className="space-y-3">
                    {velocity.map((stage) => (
                      <div key={stage.role}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                            {stage.label}
                          </span>
                          <span className="text-[11px] text-slate-500 tabular-nums">
                            <span className="font-black text-slate-800 dark:text-slate-100">
                              {stage.avg_days}
                            </span>{" "}
                            días · {stage.transitions} transiciones
                          </span>
                        </div>
                        <div className="h-2.5 bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[hsl(var(--primary))] transition-all"
                            style={{ width: `${Math.max(stage.pct_of_max, 3)}%` }}
                          />
                        </div>
                      </div>
                    ))}

                    <div className="mt-4 pt-3 border-t border-[hsl(var(--border-primary))]">
                      <p className="text-[10px] text-slate-400">
                        Barras más cortas = ascenso más rápido = mayor dinamismo ministerial
                      </p>
                    </div>
                  </div>
                )}
              </section>
            </div>

          </div>
        )}
      </div>
    </EvangelismShell>
  );
}

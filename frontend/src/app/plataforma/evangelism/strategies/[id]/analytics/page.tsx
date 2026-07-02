"use client";

import EvangelismShell from "@/components/evangelism/EvangelismShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  AlertTriangle, ArrowLeft, BarChart3, CheckCircle2, Loader2,
  RefreshCw, TrendingUp, Users, MapPin, Target,
  Activity, Zap, Star, Baby, Heart, Shield,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import type { BreadcrumbOption } from "@/components/evangelism/EvangelismShell";
import { useCallback, useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, LineChart, Line, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";

// ── Types ──────────────────────────────────────────────────────────────

interface FullAnalytics {
  resumen: {
    estrategia_id: string;
    periodo_semanas: number;
    fecha_desde: string;
    fecha_hasta: string;
    total_grupos: number;
    grupos_activos: number;
    total_sesiones_periodo: number;
    total_participantes: number;
    personas_unicas_analizadas: number;
    tasa_asistencia_global: number;
    total_primera_vez: number;
    total_alertas_enfriamiento: number;
    ofrenda_total: number;
    ics_global: number;
  };
  tendencia_semanal: Array<{
    semana: string;
    presentes: number;
    ausentes: number;
    primera_vez: number;
    sesiones: number;
    ofrenda: number;
    tasa_asistencia: number;
  }>;
  dim1_territorial: {
    idc: number;
    semaforo: string;
    grupos_activos: number;
    zonas_identificadas: number;
    por_zona: Array<{ zona: string; grupos: number }>;
  };
  dim2_capacidad: {
    saturados: number;
    saludables: number;
    bajos: number;
    grupos: Array<{ nombre: string; tof_porcentaje: number; participantes_activos: number; capacidad: number; estado: string }>;
  };
  dim3_atraccion: {
    total_nuevos_periodo: number;
    tan_global_porcentaje: number;
    por_grupo: Array<{ nombre: string; nuevos_visitantes: number; tan_porcentaje: number; irt_promedio: number; irt_semaforo: string }>;
  };
  dim4_conversion_crm: {
    total_casos_crm: number;
    total_resueltos: number;
    icn_global: number;
    por_grupo: Array<{ nombre: string; casos_crm_total: number; casos_resueltos_exito: number; icn_porcentaje: number; clasificacion: string }>;
  };
  dim5_fidelidad: {
    ica_global_porcentaje: number;
    total_personas_analizadas: number;
    total_alertas_enfriamiento: number;
    alertas_enfriamiento: Array<{ nombre: string; grupo: string; ausencias_consecutivas: number }>;
    top_asistentes: Array<{ nombre: string; ica_porcentaje: number; sesiones_asistidas: number; grupo: string }>;
  };
  dim6_eficiencia: {
    ics_global_porcentaje: number;
    sesiones_proyectadas_total: number;
    sesiones_realizadas_total: number;
    ofrenda_total_periodo: number;
    por_grupo: Array<{ nombre: string; ics_porcentaje: number; sesiones_realizadas: number; sesiones_proyectadas: number; ofrenda_total: number; estado_operativo: string }>;
  };
  dim7_multiplicacion: {
    grupos_iniciales: number;
    grupos_multiplicados_periodo: number;
    tmg_porcentaje: number;
    tpm_meses_promedio: number | null;
    estado_reproduccion: string;
  };
  dim8_liderazgo: {
    total_lideres_asignados: number;
    lideres_inactivos: number;
    tds_porcentaje: number;
    promovidos_periodo: number;
    irl_porcentaje: number;
    alertas_burnout: Array<{ nombre: string; grupo: string; estado_vital: string }>;
  };
  dim9_campanas: {
    total_captados_campana: number;
    retenidos_3_sesiones: number;
    irc_porcentaje: number;
    semaforo: string;
  };
  dim10_demografia: {
    total_personas: number;
    bautizados: number;
    pct_bautizados: number;
    idg: number;
    equilibrio_porcentaje: number;
    estado_equilibrio: string;
    distribucion_etaria: Record<string, number>;
    distribucion_spiritual_status: Record<string, number>;
    distribucion_church_role: Record<string, number>;
  };
}

// ── Helpers ────────────────────────────────────────────────────────────

const SEMAFORO_COLOR: Record<string, string> = {
  ALTO: "text-emerald-600", MEDIO: "text-amber-500", CRITICO: "text-[hsl(var(--destructive))]",
  SATURADO: "text-[hsl(var(--destructive))]", SALUDABLE: "text-emerald-600", BAJO: "text-amber-500",
  OPTIMO: "text-emerald-600", INCONSTANTE: "text-amber-500", ABANDONO: "text-[hsl(var(--destructive))]",
  EXCELENTE: "text-emerald-600", REGULAR: "text-amber-500", ALERTA_DESERCION: "text-[hsl(var(--destructive))]", INEFICIENTE: "text-[hsl(var(--destructive))]",
  EXPONENCIAL: "text-emerald-600", ESTANCADO: "text-[hsl(var(--destructive))]",
  EQUILIBRADO: "text-emerald-600", MODERADO: "text-amber-500", HOMOGENEO: "text-[hsl(var(--destructive))]",
};

const SEMAFORO_BG: Record<string, string> = {
  ALTO: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  SALUDABLE: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  OPTIMO: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  EXCELENTE: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  EXPONENCIAL: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  EQUILIBRADO: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
  MEDIO: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  INCONSTANTE: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  REGULAR: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  MODERADO: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  BAJO: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  CRITICO: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  SATURADO: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  ABANDONO: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  ALERTA_DESERCION: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  INEFICIENTE: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  ESTANCADO: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  HOMOGENEO: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
};

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#f97316"];

const sem = (s: string) => SEMAFORO_COLOR[s] || "text-[hsl(var(--text-primary))]";
const semBg = (s: string) => SEMAFORO_BG[s] || "bg-[hsl(var(--bg-secondary))] border-[hsl(var(--border-primary))]";

function KpiCard({ label, value, sub, semaforo, icon: Icon }: {
  label: string; value: string | number; sub?: string; semaforo?: string; icon: React.ElementType;
}) {
  return (
    <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-4 flex flex-col gap-1">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className="text-[hsl(var(--text-secondary))]" />
        <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">{label}</p>
      </div>
      <p className={`text-2xl font-black ${semaforo ? sem(semaforo) : "text-[hsl(var(--text-primary))]"}`}>{value}</p>
      {sub && <p className="text-[11px] text-[hsl(var(--text-secondary))]">{sub}</p>}
      {semaforo && (
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border w-fit mt-1 ${semBg(semaforo)}`}>
          {semaforo.replace(/_/g, " ")}
        </span>
      )}
    </div>
  );
}

function SectionHeader({ icon: Icon, title, sub }: { icon: React.ElementType; title: string; sub: string }) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))]/10 flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={16} className="text-[hsl(var(--primary))]" />
      </div>
      <div>
        <h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">{title}</h2>
        <p className="text-[11px] text-[hsl(var(--text-secondary))]">{sub}</p>
      </div>
    </div>
  );
}

function ProgressBar({ value, max = 100, color = "bg-[hsl(var(--primary))]" }: { value: number; max?: number; color?: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="h-1.5 w-full bg-[hsl(var(--bg-muted))] rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

const WEEKS_OPTIONS = [4, 8, 12, 24, 52];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const renderPieLabel = ({ name, percent }: any) => `${name} ${(((percent as number) ?? 0) * 100).toFixed(0)}%`;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const renderPiePct = ({ percent }: any) => `${(((percent as number) ?? 0) * 100).toFixed(0)}%`;

// ── Main Page ──────────────────────────────────────────────────────────

export default function StrategyAnalyticsPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const { token } = useAuth();

  const [data, setData] = useState<FullAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [weeks, setWeeks] = useState(12);
  const [heatmap, setHeatmap] = useState<Array<{ weekday: number; label: string; sessions: number; present: number; total: number; pct: number | null }>>([]);
  const [velocity, setVelocity] = useState<Array<{ role: string; label: string; avg_days: number; transitions: number; order: number; pct_of_max: number }>>([]);

  const breadcrumbs: BreadcrumbOption[] = [
    { label: "Evangelismo", href: "/plataforma/evangelism" },
    { label: "Estrategias", href: `/plataforma/evangelism/strategies/${id}` },
    { label: "Analytics" },
  ];

  const fetchData = useCallback(async () => {
    if (!id) { setLoading(false); return; }
    setLoading(true);
    try {
      const res = await apiFetch<FullAnalytics>(
        `/evangelism/analytics/strategy/${id}/full?weeks=${weeks}`,
        { token }
      );
      if (res) setData(res);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [id, token, weeks]);

  const fetchHeatmapVelocity = useCallback(async () => {
    if (!id) return;
    try {
      const periodMap: Record<number, string> = { 4: "90d", 8: "90d", 12: "90d", 24: "180d", 52: "365d" };
      const [hm, vc] = await Promise.all([
        apiFetch<{ cells: Array<{ weekday: number; label: string; sessions: number; present: number; total: number; pct: number | null }> }>(
          `/evangelism/analytics/strategy/${id}/heatmap?period=${periodMap[weeks] || '90d'}`,
          { token }
        ).catch(() => null),
        apiFetch<{ stages: typeof velocity }>(
          `/evangelism/analytics/strategy/${id}/velocity`,
          { token }
        ).catch(() => null),
      ]);
      if (hm?.cells) setHeatmap(hm.cells);
      if (vc?.stages) setVelocity(vc.stages);
    } catch {
      // silent
    }
  }, [id, token, weeks]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchHeatmapVelocity(); }, [fetchHeatmapVelocity]);

  if (loading) return (
    <EvangelismShell breadcrumbs={breadcrumbs}>
      <div className="flex items-center justify-center h-64">
        <Loader2 size={28} className="animate-spin text-[hsl(var(--primary))]" />
      </div>
    </EvangelismShell>
  );

  if (!data) return (
    <EvangelismShell breadcrumbs={breadcrumbs}>
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertTriangle size={28} className="text-amber-500" />
        <p className="text-sm text-[hsl(var(--text-secondary))]">No se pudieron cargar las métricas</p>
        <button onClick={fetchData} className="text-xs text-[hsl(var(--primary))] font-semibold">Reintentar</button>
      </div>
    </EvangelismShell>
  );

  const { resumen, tendencia_semanal, dim1_territorial, dim2_capacidad, dim3_atraccion,
    dim4_conversion_crm, dim5_fidelidad, dim6_eficiencia, dim7_multiplicacion,
    dim8_liderazgo, dim9_campanas, dim10_demografia } = data;

  const pieEtaria = Object.entries(dim10_demografia.distribucion_etaria)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const pieSpiritual = Object.entries(dim10_demografia.distribucion_spiritual_status)
    .filter(([k]) => k !== "Sin dato")
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const radarData = dim2_capacidad.grupos.map(g => ({
    grupo: g.nombre,
    "Ocupación": g.tof_porcentaje,
    "Asistencia": dim3_atraccion.por_grupo.find(x => x.nombre === g.nombre)?.tan_porcentaje ?? 0,
    "Cumplimiento": dim6_eficiencia.por_grupo.find(x => x.nombre === g.nombre)?.ics_porcentaje ?? 0,
  }));

  return (
    <EvangelismShell breadcrumbs={breadcrumbs}>
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-8">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()}
              className="p-2 rounded-lg hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] transition-colors">
              <ArrowLeft size={16} />
            </button>
            <div>
              <h1 className="text-lg font-black text-[hsl(var(--text-primary))] flex items-center gap-2">
                <BarChart3 size={18} className="text-[hsl(var(--primary))]" />
                Dashboard Analítico
              </h1>
              <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                {resumen.fecha_desde} → {resumen.fecha_hasta} · {resumen.total_grupos} grupos · {resumen.total_participantes} participantes
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 bg-[hsl(var(--bg-muted))] rounded-lg p-1">
              {WEEKS_OPTIONS.map(w => (
                <button key={w} onClick={() => setWeeks(w)}
                  className={`px-3 py-1 rounded-md text-[11px] font-bold transition-all ${weeks === w
                    ? "bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] shadow-sm"
                    : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"}`}>
                  {w}s
                </button>
              ))}
            </div>
            <button onClick={fetchData}
              className="p-2 rounded-lg bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--border-primary))] text-[hsl(var(--text-secondary))] transition-colors">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {/* ── RESUMEN EJECUTIVO ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <KpiCard icon={Users} label="Participantes" value={resumen.total_participantes} sub={`${resumen.personas_unicas_analizadas} personas únicas`} />
          <KpiCard icon={Activity} label="Asistencia global" value={`${resumen.tasa_asistencia_global}%`}
            semaforo={resumen.tasa_asistencia_global >= 70 ? "SALUDABLE" : resumen.tasa_asistencia_global >= 50 ? "REGULAR" : "CRITICO"} />
          <KpiCard icon={Star} label="Primera vez" value={resumen.total_primera_vez} sub="visitantes nuevos" />
          <KpiCard icon={CheckCircle2} label="Cumplimiento" value={`${resumen.ics_global}%`}
            semaforo={resumen.ics_global >= 90 ? "OPTIMO" : resumen.ics_global >= 70 ? "INCONSTANTE" : "ABANDONO"} />
          <KpiCard icon={AlertTriangle} label="Alertas frío" value={resumen.total_alertas_enfriamiento}
            semaforo={resumen.total_alertas_enfriamiento === 0 ? "SALUDABLE" : resumen.total_alertas_enfriamiento <= 3 ? "REGULAR" : "CRITICO"} />
          <KpiCard icon={Zap} label="Sesiones" value={resumen.total_sesiones_periodo} sub="en el período" />
          <KpiCard icon={Heart} label="Ofrendas" value={`$${resumen.ofrenda_total.toLocaleString()}`} />
        </div>

        {/* ── DIM 1: TERRITORIAL ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={MapPin} title="1. Dimensión Territorial" sub="Densidad de cobertura por zona geográfica (IDC)" />
          <div className="grid md:grid-cols-3 gap-4">
            <div className={`rounded-lg border p-4 text-center ${semBg(dim1_territorial.semaforo)}`}>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">IDC Global</p>
              <p className={`text-4xl font-black ${sem(dim1_territorial.semaforo)}`}>{dim1_territorial.idc}</p>
              <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">grupos / zona</p>
              <span className={`text-[10px] font-bold ${sem(dim1_territorial.semaforo)}`}>{dim1_territorial.semaforo}</span>
            </div>
            <div className="md:col-span-2">
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">Grupos por zona</p>
              {dim1_territorial.por_zona.length === 0 && (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin datos de ubicación en los grupos</p>
              )}
              <div className="space-y-2">
                {dim1_territorial.por_zona.map(z => (
                  <div key={z.zona}>
                    <div className="flex justify-between text-[11px] mb-0.5">
                      <span className="text-[hsl(var(--text-primary))] font-medium truncate">{z.zona}</span>
                      <span className="text-[hsl(var(--text-secondary))] font-bold ml-2">{z.grupos} grupos</span>
                    </div>
                    <ProgressBar value={z.grupos} max={Math.max(...dim1_territorial.por_zona.map(x => x.grupos), 1)} />
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-3 italic">
                Para activar el mapa GIS agrega latitud/longitud a los grupos.
              </p>
            </div>
          </div>
        </div>

        {/* ── DIM 2: CAPACIDAD ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Users} title="2. Capacidad y Población (TOF)" sub="Tasa de Ocupación Física por grupo" />
          <div className="grid md:grid-cols-3 gap-3 mb-4">
            {[
              { label: "Saturados (>85%)", count: dim2_capacidad.saturados, color: "text-[hsl(var(--destructive))]", bg: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800" },
              { label: "Saludables (60–85%)", count: dim2_capacidad.saludables, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800" },
              { label: "Bajos (<60%)", count: dim2_capacidad.bajos, color: "text-amber-500", bg: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800" },
            ].map(s => (
              <div key={s.label} className={`rounded-lg border p-3 text-center ${s.bg}`}>
                <p className={`text-3xl font-black ${s.color}`}>{s.count}</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          {dim2_capacidad.grupos.length === 0 ? (
            <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-6">Sin grupos con datos de capacidad</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(120, dim2_capacidad.grupos.length * 36)}>
              <BarChart data={dim2_capacidad.grupos} layout="vertical" margin={{ left: 8, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border-primary))" />
                <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="nombre" tick={{ fontSize: 11 }} width={60} />
                <Tooltip formatter={(v) => [`${v}%`, "TOF"]} />
                <Bar dataKey="tof_porcentaje" name="Ocupación %" radius={[0, 4, 4, 0]}>
                  {dim2_capacidad.grupos.map((g, i) => (
                    <Cell key={i} fill={g.estado === "SATURADO" ? "#ef4444" : g.estado === "SALUDABLE" ? "#22c55e" : "#f59e0b"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* ── DIM 3: ATRACCIÓN ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Star} title="3. Atracción de Nuevos (TAN + IRT)"
            sub="Tasa de atracción e Índice de Recurrencia Temprana" />
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">
                TAN global: <span className="text-[hsl(var(--primary))]">{dim3_atraccion.tan_global_porcentaje}%</span>
                {" "}· Total nuevos: <span className="text-[hsl(var(--primary))]">{dim3_atraccion.total_nuevos_periodo}</span>
              </p>
              {dim3_atraccion.por_grupo.length === 0 && (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin grupos con datos de asistencia</p>
              )}
              <div className="space-y-3">
                {dim3_atraccion.por_grupo.map(g => (
                  <div key={g.nombre} className="p-3 bg-[hsl(var(--bg-secondary))] rounded-lg">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[12px] font-bold text-[hsl(var(--text-primary))]">{g.nombre}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${semBg(g.irt_semaforo)}`}>
                        IRT {g.irt_promedio}
                      </span>
                    </div>
                    <div className="flex gap-4 text-[11px] text-[hsl(var(--text-secondary))]">
                      <span><strong className="text-[hsl(var(--text-primary))]">{g.nuevos_visitantes}</strong> nuevos</span>
                      <span>TAN <strong className="text-[hsl(var(--text-primary))]">{g.tan_porcentaje}%</strong></span>
                    </div>
                    <div className="mt-2">
                      <ProgressBar value={g.tan_porcentaje} color={g.tan_porcentaje > 20 ? "bg-emerald-500" : g.tan_porcentaje > 10 ? "bg-amber-400" : "bg-[hsl(var(--destructive))]"} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">Tendencia de primera vez</p>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={tendencia_semanal} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border-primary))" />
                  <XAxis dataKey="semana" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="primera_vez" name="Primera vez" stroke="#22c55e" fill="#22c55e20" strokeWidth={2} />
                  <Area type="monotone" dataKey="presentes" name="Presentes" stroke="#6366f1" fill="#6366f120" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ── DIM 4: CONVERSIÓN CRM ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Target} title="4. Conversión al CRM (ICN)"
            sub="Índice de Conversión de Nuevos — embudo desde visita hasta caso resuelto" />
          <div className="grid md:grid-cols-4 gap-3 mb-4">
            {[
              { label: "Casos totales", value: dim4_conversion_crm.total_casos_crm, color: "" },
              { label: "Resueltos exitosos", value: dim4_conversion_crm.total_resueltos, color: "text-emerald-600" },
              { label: "ICN global", value: `${dim4_conversion_crm.icn_global}%`, color: dim4_conversion_crm.icn_global >= 70 ? "text-emerald-600" : "text-amber-500" },
              { label: "Casos abiertos", value: dim4_conversion_crm.total_casos_crm - dim4_conversion_crm.total_resueltos, color: "text-[hsl(var(--primary))]" },
            ].map(s => (
              <div key={s.label} className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 text-center">
                <p className={`text-2xl font-black ${s.color || "text-[hsl(var(--text-primary))]"}`}>{s.value}</p>
                <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          {dim4_conversion_crm.por_grupo.length === 0 && (
            <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-4">Sin grupos con casos CRM registrados</p>
          )}
          <div className="space-y-2">
            {dim4_conversion_crm.por_grupo.map(g => (
              <div key={g.nombre} className="flex items-center gap-3 p-3 bg-[hsl(var(--bg-secondary))] rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[12px] font-bold text-[hsl(var(--text-primary))]">{g.nombre}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${semBg(_semClasif(g.clasificacion))}`}>
                      {g.clasificacion.replace(/_/g, " ")}
                    </span>
                  </div>
                  <ProgressBar value={g.icn_porcentaje} color="bg-[hsl(var(--primary))]" />
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-black text-[hsl(var(--text-primary))]">{g.icn_porcentaje}%</p>
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">{g.casos_resueltos_exito}/{g.casos_crm_total}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── DIM 5: FIDELIDAD ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Activity} title="5. Consistencia y Fidelidad (ICA)"
            sub="Índice de Consistencia de Asistencia + alertas de enfriamiento espiritual" />
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <div className="flex items-center gap-4 mb-4 p-3 bg-[hsl(var(--bg-secondary))] rounded-lg">
                <div className="text-center">
                  <p className="text-3xl font-black text-[hsl(var(--primary))]">{dim5_fidelidad.ica_global_porcentaje}%</p>
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">ICA global</p>
                </div>
                <div className="flex-1">
                  <ProgressBar value={dim5_fidelidad.ica_global_porcentaje}
                    color={dim5_fidelidad.ica_global_porcentaje >= 70 ? "bg-emerald-500" : "bg-amber-400"} />
                  <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-1">{dim5_fidelidad.total_personas_analizadas} personas analizadas</p>
                </div>
              </div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                Alertas de enfriamiento ({dim5_fidelidad.total_alertas_enfriamiento})
              </p>
              {dim5_fidelidad.alertas_enfriamiento.length === 0 ? (
                <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                  <CheckCircle2 size={14} className="text-emerald-600" />
                  <p className="text-[11px] text-emerald-700 dark:text-emerald-400 font-medium">Sin alertas activas</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {dim5_fidelidad.alertas_enfriamiento.slice(0, 8).map((a) => (
                    <div key={`${a.nombre}-${a.grupo}`} className="flex items-center justify-between p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <div>
                        <p className="text-[11px] font-bold text-[hsl(var(--text-primary))]">{a.nombre}</p>
                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{a.grupo}</p>
                      </div>
                      <span className="text-[10px] font-black text-[hsl(var(--destructive))] bg-red-100 dark:bg-red-900/40 px-2 py-0.5 rounded-full">
                        {a.ausencias_consecutivas}× FALTO
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">Top asistentes</p>
              {dim5_fidelidad.top_asistentes.length === 0 ? (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin datos suficientes aún</p>
              ) : (
                <div className="space-y-1.5">
                  {dim5_fidelidad.top_asistentes.map((a) => (
                    <div key={`${a.nombre}-${a.grupo}`} className="p-2 bg-[hsl(var(--bg-secondary))] rounded-lg">
                      <div className="flex justify-between items-center mb-1">
                        <div>
                          <p className="text-[11px] font-bold text-[hsl(var(--text-primary))]">{a.nombre}</p>
                          <p className="text-[10px] text-[hsl(var(--text-secondary))]">{a.grupo}</p>
                        </div>
                        <span className="text-[11px] font-black text-emerald-600">{a.ica_porcentaje}%</span>
                      </div>
                      <ProgressBar value={a.ica_porcentaje} color="bg-emerald-500" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── DIM 6: EFICIENCIA OPERATIVA ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={CheckCircle2} title="6. Eficiencia Operativa (ICS)"
            sub="Índice de Cumplimiento de Sesiones + ofrendas" />
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
                {[
                  { label: "Proyectadas", value: dim6_eficiencia.sesiones_proyectadas_total, color: "text-[hsl(var(--text-primary))]" },
                  { label: "Realizadas", value: dim6_eficiencia.sesiones_realizadas_total, color: "text-emerald-600" },
                  { label: "ICS global", value: `${dim6_eficiencia.ics_global_porcentaje}%`, color: dim6_eficiencia.ics_global_porcentaje >= 90 ? "text-emerald-600" : "text-amber-500" },
                ].map(s => (
                  <div key={s.label} className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 text-center">
                    <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))]">{s.label}</p>
                  </div>
                ))}
              </div>
              {dim6_eficiencia.por_grupo.length === 0 && (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin datos de sesiones por grupo</p>
              )}
              <div className="space-y-2">
                {dim6_eficiencia.por_grupo.map(g => (
                  <div key={g.nombre} className="p-3 bg-[hsl(var(--bg-secondary))] rounded-lg">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[12px] font-bold text-[hsl(var(--text-primary))]">{g.nombre}</span>
                      <span className={`text-[10px] font-bold ${sem(g.estado_operativo)}`}>{g.estado_operativo}</span>
                    </div>
                    <div className="flex gap-4 text-[11px] text-[hsl(var(--text-secondary))] mb-1.5">
                      <span>{g.sesiones_realizadas}/{g.sesiones_proyectadas} sesiones</span>
                      {g.ofrenda_total > 0 && <span className="text-emerald-600 font-bold">${g.ofrenda_total.toLocaleString()}</span>}
                    </div>
                    <ProgressBar value={g.ics_porcentaje} color={g.ics_porcentaje >= 90 ? "bg-emerald-500" : g.ics_porcentaje >= 70 ? "bg-amber-400" : "bg-[hsl(var(--destructive))]"} />
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">Tendencia semanal de asistencia</p>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={tendencia_semanal} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border-primary))" />
                  <XAxis dataKey="semana" tick={{ fontSize: 10 }} tickFormatter={v => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="presentes" name="Presentes" stroke="#6366f1" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="ausentes" name="Ausentes" stroke="#ef4444" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="tasa_asistencia" name="Tasa %" stroke="#22c55e" strokeWidth={2} strokeDasharray="4 2" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ── HEATMAP DE ASISTENCIA POR DÍA ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Activity} title="Heatmap de Asistencia por Día de la Semana"
            sub="¿Qué días concentran más asistencia? Color según % de asistencia promedio" />
          {heatmap.length === 0 ? (
            <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-4">
              Sin datos suficientes para calcular heatmap en el período actual
            </p>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-7 gap-1.5">
                {heatmap.map((d) => {
                  const ratio = d.pct !== null ? Math.max(0, Math.min(1, d.pct / 100)) : 0;
                  const intensity = ratio; // 0..1
                  return (
                    <div key={d.weekday} className="flex flex-col gap-1">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center">
                        {d.label.slice(0, 3)}
                      </p>
                      <div
                        className="aspect-square rounded-md flex items-center justify-center text-white font-black text-sm transition-all hover:scale-105 cursor-default border border-[hsl(var(--border-primary))]"
                        style={{
                          backgroundColor: d.sessions === 0
                            ? 'hsl(var(--bg-muted))'
                            : `rgba(99, 102, 241, ${0.15 + intensity * 0.85})`,
                          color: intensity > 0.55 || d.sessions === 0 ? 'white' : 'hsl(var(--text-primary))',
                        }}
                        title={`${d.label}: ${d.sessions} sesiones, ${d.pct !== null ? `${d.pct.toFixed(1)}% asistencia` : 'sin datos'}`}
                      >
                        {d.sessions > 0 ? `${Math.round(d.pct ?? 0)}%` : '—'}
                      </div>
                      <p className="text-[9px] text-[hsl(var(--text-secondary))] text-center font-mono">
                        {d.sessions} ses.
                      </p>
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center justify-between gap-2 pt-2 border-t border-[hsl(var(--border-primary))]">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    Leyenda:
                  </span>
                  <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                    <span className="size-3 rounded" style={{ background: 'hsl(var(--bg-muted))' }} /> Sin sesiones
                  </span>
                  <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                    <span className="size-3 rounded" style={{ background: 'rgba(99, 102, 241, 0.2)' }} /> Bajo
                  </span>
                  <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                    <span className="size-3 rounded" style={{ background: 'rgba(99, 102, 241, 0.55)' }} /> Medio
                  </span>
                  <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                    <span className="size-3 rounded" style={{ background: 'rgba(99, 102, 241, 0.95)' }} /> Alto
                  </span>
                </div>
                <p className="text-[10px] text-[hsl(var(--text-secondary))] italic">
                  Período: últimas {weeks} semanas
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ── VELOCIDAD DE TRANSICIÓN DE ROLES ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Zap} title="Velocidad de Transición entre Roles"
            sub="Días promedio antes de que una persona avance al siguiente rol en el embudo ministerial" />
          {velocity.length === 0 ? (
            <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-4">
              Sin transiciones de rol registradas aún
            </p>
          ) : (
            <div className="overflow-x-auto pb-2">
              <div className="flex items-center gap-2 min-w-fit">
                {velocity.map((s, i) => {
                  const maxDays = Math.max(...velocity.map(v => v.avg_days), 1);
                  const barWidth = (s.avg_days / maxDays) * 100;
                  const toneColor = s.avg_days < 30
                    ? 'bg-emerald-500'
                    : s.avg_days < 90
                    ? 'bg-amber-500'
                    : 'bg-red-500';
                  return (
                    <div key={`${s.role}-${i}`} className="flex items-center gap-2 shrink-0">
                      <div className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 min-w-[140px] flex flex-col gap-2 hover:shadow-md transition-shadow">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                          Etapa {i + 1}
                        </p>
                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate" title={s.label}>
                          {s.label}
                        </p>
                        <div className="flex items-baseline gap-1">
                          <p className="text-2xl font-black text-[hsl(var(--primary))]">
                            {Math.round(s.avg_days)}
                          </p>
                          <p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))]">días</p>
                        </div>
                        <div className="space-y-1">
                          <div className="h-1.5 w-full bg-[hsl(var(--bg-muted))] rounded-full overflow-hidden">
                            <div className={`h-full rounded-full transition-all ${toneColor}`} style={{ width: `${barWidth}%` }} />
                          </div>
                          <p className="text-[9px] text-[hsl(var(--text-secondary))] font-mono">
                            {s.transitions} transición{s.transitions !== 1 ? 'es' : ''}
                          </p>
                        </div>
                      </div>
                      {i < velocity.length - 1 && (
                        <div className="text-[hsl(var(--text-secondary))] shrink-0 px-1" aria-hidden="true">
                          →
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-[10px] text-[hsl(var(--text-secondary))] italic mt-3 text-center">
                El conteo se reinicia al cambiar de rol. La barra crece con días promedio.
              </p>
            </div>
          )}
        </div>

        {/* ── DIM 7 + 8: MULTIPLICACIÓN Y LIDERAZGO ── */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
            <SectionHeader icon={TrendingUp} title="7. Multiplicación (TMG / TPM)"
              sub="Tasa de Multiplicación de Grupos y tiempo promedio" />
            <div className={`rounded-lg border p-4 text-center mb-4 ${semBg(dim7_multiplicacion.estado_reproduccion)}`}>
              <p className={`text-4xl font-black ${sem(dim7_multiplicacion.estado_reproduccion)}`}>
                {dim7_multiplicacion.tmg_porcentaje}%
              </p>
              <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">TMG — Tasa de multiplicación</p>
              <p className={`text-[10px] font-bold mt-1 ${sem(dim7_multiplicacion.estado_reproduccion)}`}>
                {dim7_multiplicacion.estado_reproduccion}
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 text-center">
                <p className="text-xl font-black text-[hsl(var(--text-primary))]">{dim7_multiplicacion.grupos_multiplicados_periodo}</p>
                <p className="text-[10px] text-[hsl(var(--text-secondary))]">Multiplicaciones</p>
              </div>
              <div className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 text-center">
                <p className="text-xl font-black text-[hsl(var(--text-primary))]">
                  {dim7_multiplicacion.tpm_meses_promedio ?? "—"}
                </p>
                <p className="text-[10px] text-[hsl(var(--text-secondary))]">meses TPM</p>
              </div>
            </div>
            {dim7_multiplicacion.grupos_multiplicados_periodo === 0 && (
              <p className="text-[11px] text-[hsl(var(--text-secondary))] italic mt-3 text-center">
                Sin multiplicaciones registradas en el período. La estructura está lista.
              </p>
            )}
          </div>

          <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
            <SectionHeader icon={Shield} title="8. Liderazgo (IRL / TDS)"
              sub="Reclutamiento de líderes y deserción de servidores" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              {[
                { label: "Líderes asignados", value: dim8_liderazgo.total_lideres_asignados, color: "text-[hsl(var(--primary))]" },
                { label: "TDS (Deserción)", value: `${dim8_liderazgo.tds_porcentaje}%`, color: dim8_liderazgo.tds_porcentaje > 20 ? "text-[hsl(var(--destructive))]" : "text-emerald-600" },
                { label: "Promovidos", value: dim8_liderazgo.promovidos_periodo, color: "text-emerald-600" },
                { label: "IRL", value: `${dim8_liderazgo.irl_porcentaje}%`, color: "text-[hsl(var(--text-primary))]" },
              ].map(s => (
                <div key={s.label} className="bg-[hsl(var(--bg-secondary))] rounded-lg p-3 text-center">
                  <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">{s.label}</p>
                </div>
              ))}
            </div>
            {dim8_liderazgo.alertas_burnout.length > 0 ? (
              <div className="space-y-1.5">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--destructive))] mb-1">Alertas burnout</p>
                {dim8_liderazgo.alertas_burnout.map((a) => (
                  <div key={`${a.nombre}-${a.grupo}`} className="flex justify-between items-center p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <div>
                      <p className="text-[11px] font-bold text-[hsl(var(--text-primary))]">{a.nombre}</p>
                      <p className="text-[10px] text-[hsl(var(--text-secondary))]">{a.grupo}</p>
                    </div>
                    <span className="text-[10px] text-[hsl(var(--destructive))] font-bold">{a.estado_vital}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                <CheckCircle2 size={14} className="text-emerald-600" />
                <p className="text-[11px] text-emerald-700 dark:text-emerald-400 font-medium">Liderazgo sin alertas</p>
              </div>
            )}
          </div>
        </div>

        {/* ── DIM 9: CAMPAÑAS ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Zap} title="9. Retención de Campañas (IRC)"
            sub="Personas capturadas por esta estrategia que se convirtieron en asistentes regulares" />
          <div className="grid md:grid-cols-3 gap-4">
            <div className={`rounded-lg border p-4 text-center col-span-1 ${semBg(dim9_campanas.semaforo)}`}>
              <p className={`text-4xl font-black ${sem(dim9_campanas.semaforo)}`}>{dim9_campanas.irc_porcentaje}%</p>
              <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">IRC — Índice de Retención</p>
              <p className={`text-[10px] font-bold mt-1 ${sem(dim9_campanas.semaforo)}`}>{dim9_campanas.semaforo}</p>
            </div>
            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              <div className="bg-[hsl(var(--bg-secondary))] rounded-lg p-4 text-center">
                <p className="text-3xl font-black text-[hsl(var(--primary))]">{dim9_campanas.total_captados_campana}</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))]">captados por campaña</p>
              </div>
              <div className="bg-[hsl(var(--bg-secondary))] rounded-lg p-4 text-center">
                <p className="text-3xl font-black text-emerald-600">{dim9_campanas.retenidos_3_sesiones}</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))]">retenidos (≥3 sesiones)</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── DIM 10: DEMOGRAFÍA ── */}
        <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
          <SectionHeader icon={Baby} title="10. Diversidad Generacional (IDG)"
            sub="Entropía de Shannon adaptada — equilibrio intergeneracional" />
          <div className="grid md:grid-cols-3 gap-6">
            <div>
              <div className={`rounded-lg border p-4 text-center mb-3 ${semBg(dim10_demografia.estado_equilibrio)}`}>
                <p className={`text-3xl font-black ${sem(dim10_demografia.estado_equilibrio)}`}>{dim10_demografia.idg}</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">IDG (máx 1.61)</p>
                <p className="text-[11px] font-bold mt-1">{dim10_demografia.equilibrio_porcentaje}% equilibrio</p>
                <span className={`text-[10px] font-bold ${sem(dim10_demografia.estado_equilibrio)}`}>{dim10_demografia.estado_equilibrio}</span>
              </div>
              <div className="p-3 bg-[hsl(var(--bg-secondary))] rounded-lg text-center">
                <p className="text-2xl font-black text-[hsl(var(--primary))]">{dim10_demografia.pct_bautizados}%</p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))]">bautizados ({dim10_demografia.bautizados}/{dim10_demografia.total_personas})</p>
              </div>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">Distribución por edad</p>
              {pieEtaria.length === 0 ? (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-8">Sin datos de edad registrados</p>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie data={pieEtaria} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={renderPieLabel} labelLine={false} style={{ fontSize: 10 }}>
                      {pieEtaria.map((e, i) => <Cell key={e.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">Estado espiritual</p>
              {pieSpiritual.length === 0 ? (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic text-center py-8">Sin datos de estado espiritual</p>
              ) : (
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={pieSpiritual} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label={renderPiePct} labelLine={false} style={{ fontSize: 10 }}>
                      {pieSpiritual.map((e, i) => <Cell key={e.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="space-y-1 mt-2">
                {pieSpiritual.map((e, i) => (
                  <div key={e.name} className="flex items-center gap-2 text-[11px]">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-[hsl(var(--text-secondary))] truncate">{e.name}</span>
                    <span className="ml-auto font-bold text-[hsl(var(--text-primary))]">{e.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── RADAR COMPARATIVO ── */}
        {radarData.length > 0 && (
          <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-5">
            <SectionHeader icon={BarChart3} title="Comparativa por Grupo"
              sub="Ocupación · Atracción · Cumplimiento operativo" />
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="grupo" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
                <Radar name="Ocupación" dataKey="Ocupación" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
                <Radar name="Atracción" dataKey="Asistencia" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
                <Radar name="Cumplimiento" dataKey="Cumplimiento" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

      </div>
    </EvangelismShell>
  );
}

function _semClasif(c: string) {
  if (c === "IMAN_FUERTE") return "SALUDABLE";
  if (c === "COLADOR") return "CRITICO";
  if (c === "INCUBADORA") return "MEDIO";
  return "MEDIO";
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { Activity, AlertTriangle, BarChart3, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import RightPanel from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type {
  PMOPortfolioMatrixResponse,
  ProjectDevelopmentApproach,
  ProjectPortfolioQuadrant,
} from "@/types/projects";

interface ProjectPMOPortfolioDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

type ApproachFilter = "all" | ProjectDevelopmentApproach;
type QuadrantFilter = "all" | ProjectPortfolioQuadrant;

const QUADRANTS: Array<{
  id: ProjectPortfolioQuadrant;
  title: string;
  condition: string;
  diagnosis: string;
  actions: string[];
  borderClass: string;
}> = [
  {
    id: "q1_optimal",
    title: "Zona Óptima",
    condition: "CPI ≥ 1.0 · SPI ≥ 1.0",
    diagnosis: "Buen desempeño de costo y cronograma.",
    actions: ["Mantener el ritmo.", "Documentar lecciones de productividad.", "Revisar si las reservas pueden optimizarse."],
    borderClass: "border-[hsl(var(--success)/0.35)]",
  },
  {
    id: "q2_cost_acceleration",
    title: "Comprando Tiempo",
    condition: "CPI < 1.0 · SPI ≥ 1.0",
    diagnosis: "Avance a tiempo o adelantado con sobrecosto.",
    actions: ["Auditar la estructura de costos.", "Reducir turnos extraordinarios prescindibles.", "Proteger la calidad de los entregables."],
    borderClass: "border-[hsl(var(--warning)/0.35)]",
  },
  {
    id: "q3_underutilized_capacity",
    title: "Ahorro Ficticio por Retraso",
    condition: "CPI ≥ 1.0 · SPI < 1.0",
    diagnosis: "El costo favorable coincide con retraso del trabajo planeado.",
    actions: ["Desbloquear dependencias.", "Inyectar recursos en la ruta crítica.", "No tratar el menor gasto como ahorro definitivo."],
    borderClass: "border-[hsl(var(--warning)/0.35)]",
  },
  {
    id: "q4_critical_emergency",
    title: "Zona Crítica / Emergencia",
    condition: "CPI < 1.0 · SPI < 1.0",
    diagnosis: "El proyecto avanza lento y consume más de lo previsto.",
    actions: ["Intervenir de inmediato desde la PMO.", "Revisar formalmente la línea base.", "Evaluar reducción de alcance o contratos."],
    borderClass: "border-[hsl(var(--destructive)/0.35)]",
  },
];

const APPROACH_LABELS: Record<ProjectDevelopmentApproach, string> = {
  predictive: "Predictivo",
  agile: "Ágil",
  hybrid: "Híbrido",
};

const PMO_TYPE_LABELS: Record<"supportive" | "controlling" | "directive", string> = {
  supportive: "De apoyo",
  controlling: "De control",
  directive: "Directiva",
};

const QUADRANT_LABELS = Object.fromEntries(QUADRANTS.map(quadrant => [quadrant.id, quadrant.title])) as Record<ProjectPortfolioQuadrant, string>;

function money(value: number): string {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(value);
}

export function ProjectPMOPortfolioDrawer({ isOpen, onClose }: ProjectPMOPortfolioDrawerProps) {
  const { token } = useAuth();
  const [data, setData] = useState<PMOPortfolioMatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approachFilter, setApproachFilter] = useState<ApproachFilter>("all");
  const [quadrantFilter, setQuadrantFilter] = useState<QuadrantFilter>("all");

  const loadPortfolio = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<PMOPortfolioMatrixResponse>("/projects/pmo-portfolio-matrix", { token });
      setData(response);
    } catch (cause: unknown) {
      const message = cause instanceof Error ? cause.message : "No se pudo cargar el portafolio PMO.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isOpen) void loadPortfolio();
  }, [isOpen, loadPortfolio]);

  const filteredProjects = useMemo(() => (data?.projects_matrix ?? []).filter(project =>
    (approachFilter === "all" || project.development_approach === approachFilter)
    && (quadrantFilter === "all" || project.quadrant === quadrantFilter)
  ), [approachFilter, data, quadrantFilter]);

  if (!isOpen) return null;

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title="Portafolio PMO Ministerial"
      subtitle="Diagnóstico multi-proyecto CPI vs SPI · PMI Vol. 1 y 5"
      width="w-full sm:max-w-5xl xl:max-w-7xl"
      contentClassName="bg-[hsl(var(--surface-1))]"
    >
      <div className="space-y-5 p-4 sm:p-6" data-testid="pmo-portfolio-drawer">
        {loading && !data && <div role="status" aria-label="Cargando portafolio" className="grid gap-3 sm:grid-cols-3"><div className="h-24 animate-pulse rounded-xl bg-[hsl(var(--surface-2))]" /><div className="h-24 animate-pulse rounded-xl bg-[hsl(var(--surface-2))]" /><div className="h-24 animate-pulse rounded-xl bg-[hsl(var(--surface-2))]" /></div>}
        {error && !data && <div role="alert" className="flex items-center gap-2 rounded-xl border border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.08)] p-4 text-sm text-[hsl(var(--destructive))]"><AlertTriangle size={18} />{error}<button type="button" onClick={() => void loadPortfolio()} className="ml-auto rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-[hsl(var(--text-primary))]">Reintentar</button></div>}
        {data && <>
          <section aria-label="Indicadores consolidados del portafolio">
            <div className="mb-3 flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-sm font-bold text-[hsl(var(--text-primary))]"><BarChart3 size={16} />Resumen consolidado</h2><button type="button" onClick={() => void loadPortfolio()} disabled={loading} className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"><RefreshCw size={13} className={clsx(loading && "animate-spin")} />Actualizar</button></div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Proyectos activos" value={String(data.portfolio_totals.total_projects)} />
              <Metric label="BAC del portafolio" value={money(data.portfolio_totals.total_bac)} />
              <Metric label="Valor ganado (EV)" value={money(data.portfolio_totals.total_ev)} />
              <Metric label="Costo real (AC)" value={money(data.portfolio_totals.total_ac)} />
              <Metric label="CPI consolidado" value={data.portfolio_totals.portfolio_cpi.toFixed(2)} />
              <Metric label="SPI consolidado" value={data.portfolio_totals.portfolio_spi.toFixed(2)} />
              <Metric label="CSI consolidado" value={data.portfolio_totals.portfolio_csi.toFixed(2)} />
            </div>
          </section>

          <section aria-label="Matriz diagnóstica de cuatro cuadrantes">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-[hsl(var(--text-primary))]"><Activity size={16} />Matriz diagnóstica CPI vs SPI</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {QUADRANTS.map(quadrant => <article key={quadrant.id} className={clsx("space-y-2 rounded-xl border bg-[hsl(var(--surface-1))] p-4", quadrant.borderClass)} data-testid={`portfolio-${quadrant.id}`}>
                <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{quadrant.title}</h3><span className="rounded-full bg-[hsl(var(--surface-2))] px-2 py-1 text-xs font-bold tabular-nums">{data.quadrants_distribution[quadrant.id]}</span></div>
                <p className="font-mono text-xs text-[hsl(var(--text-secondary))]">{quadrant.condition}</p>
                <p className="text-xs text-[hsl(var(--text-secondary))]">{quadrant.diagnosis}</p>
                <ul className="list-inside list-disc space-y-1 text-xs text-[hsl(var(--text-primary))]">{quadrant.actions.map(action => <li key={action}>{action}</li>)}</ul>
              </article>)}
            </div>
          </section>

          <section aria-label="Proyectos del portafolio" className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">Detalle por proyecto</h2><p className="text-xs text-[hsl(var(--text-secondary))]">Enfoque de desarrollo, tipología PMO y desempeño EVM.</p></div>
              <div className="flex flex-wrap gap-2">
                <label className="text-xs text-[hsl(var(--text-secondary))]">Cuadrante<select aria-label="Filtrar por cuadrante" value={quadrantFilter} onChange={event => setQuadrantFilter(event.target.value as QuadrantFilter)} className="ml-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-[hsl(var(--text-primary))]"><option value="all">Todos</option>{QUADRANTS.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
                <label className="text-xs text-[hsl(var(--text-secondary))]">Enfoque<select aria-label="Filtrar por enfoque" value={approachFilter} onChange={event => setApproachFilter(event.target.value as ApproachFilter)} className="ml-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-[hsl(var(--text-primary))]"><option value="all">Todos</option><option value="predictive">Predictivo</option><option value="agile">Ágil</option><option value="hybrid">Híbrido</option></select></label>
              </div>
            </div>
            <div className="overflow-x-auto rounded-xl border border-[hsl(var(--border))]">
              <table className="w-full min-w-[920px] border-collapse text-left text-xs">
                <thead className="bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]"><tr>{["Proyecto", "Estado", "Enfoque", "Tipología PMO", "CPI", "SPI", "CSI", "Avance", "Acta", "Cuadrante"].map(label => <th key={label} className="px-3 py-2.5 font-semibold">{label}</th>)}</tr></thead>
                <tbody className="divide-y divide-[hsl(var(--border))]">{filteredProjects.map(project => <tr key={project.project_id} className="text-[hsl(var(--text-primary))]"><td className="px-3 py-2.5 font-semibold">{project.title}<span className="mt-0.5 block text-[10px] font-normal text-[hsl(var(--text-secondary))]">BAC {money(project.bac)} · EV {money(project.ev)} · AC {money(project.ac)}</span></td><td className="px-3 py-2.5">{project.status}</td><td className="px-3 py-2.5">{APPROACH_LABELS[project.development_approach]}</td><td className="px-3 py-2.5">{PMO_TYPE_LABELS[project.pmo_type]}</td><td className="px-3 py-2.5 tabular-nums">{project.cpi.toFixed(2)}</td><td className="px-3 py-2.5 tabular-nums">{project.spi.toFixed(2)}</td><td className="px-3 py-2.5 tabular-nums">{project.csi.toFixed(2)}</td><td className="px-3 py-2.5">{project.progress_pct.toFixed(1)}%</td><td className="px-3 py-2.5">{project.charter_status === "authorized" ? "Autorizada" : "Borrador"}</td><td className="px-3 py-2.5">{QUADRANT_LABELS[project.quadrant]}</td></tr>)}</tbody>
              </table>
              {filteredProjects.length === 0 && <p className="p-6 text-center text-sm text-[hsl(var(--text-secondary))]">No hay proyectos para esos filtros.</p>}
            </div>
          </section>
        </>}
        {!loading && !error && !data && <div className="rounded-xl border border-dashed border-[hsl(var(--border))] p-8 text-center text-sm text-[hsl(var(--text-secondary))]">No hay datos de portafolio disponibles.</div>}
      </div>
    </RightPanel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3"><p className="text-xs text-[hsl(var(--text-secondary))]">{label}</p><p className="mt-1 text-lg font-bold tabular-nums text-[hsl(var(--text-primary))]">{value}</p></div>;
}

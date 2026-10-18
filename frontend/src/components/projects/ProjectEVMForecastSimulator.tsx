"use client";

import { useMemo, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, Info, TrendingUp } from "lucide-react";
import clsx from "clsx";
import type { ProjectEVMMetrics } from "@/types/projects";

type EVMForecastInput = Pick<ProjectEVMMetrics, "bac" | "ev" | "ac" | "cpi" | "spi" | "progress_percentage">;

export interface EVMForecastScenario {
  futureCpi: number;
  contingency: number;
  scheduleCompressionPct: number;
}

export interface EVMForecastResults {
  eacAtypical: number | null;
  eacTypical: number | null;
  eacCombined: number | null;
  tcpiBac: number | null;
  tcpiEac: number | null;
  whatIfEac: number | null;
  whatIfVac: number | null;
  whatIfTcpi: number | null;
  effectiveFutureCpi: number | null;
  cpiImprovementPct: number | null;
  stabilityStatus: "early" | "plausible" | "unlikely" | "indeterminate";
  meetsRevisedBudget: boolean | null;
  revisedBac: number;
}

function safeDivide(numerator: number, denominator: number): number | null {
  return Number.isFinite(numerator) && Number.isFinite(denominator) && denominator > 0
    ? numerator / denominator
    : null;
}

export function calculateEVMForecast(
  evm: EVMForecastInput,
  scenario: EVMForecastScenario,
): EVMForecastResults {
  const { bac, ev, ac, cpi, spi, progress_percentage: progress } = evm;
  const remainingBudgetedWork = bac - ev;
  const eacAtypical = Number.isFinite(remainingBudgetedWork + ac) ? ac + remainingBudgetedWork : null;
  const eacTypical = safeDivide(bac, cpi);
  const eacCombined = safeDivide(remainingBudgetedWork, cpi * spi);
  const tcpiBac = safeDivide(remainingBudgetedWork, bac - ac);
  const tcpiEac = eacTypical === null ? null : safeDivide(remainingBudgetedWork, eacTypical - ac);
  const revisedBac = bac + Math.max(0, scenario.contingency);
  const costPremium = 1 + Math.max(0, scenario.scheduleCompressionPct) / 100;
  const futureCpi = Math.max(0, scenario.futureCpi);
  const whatIfEac = safeDivide(remainingBudgetedWork * costPremium, futureCpi);
  const projectedTotalCost = whatIfEac === null ? null : ac + whatIfEac;
  const whatIfVac = projectedTotalCost === null ? null : revisedBac - projectedTotalCost;
  const whatIfTcpi = safeDivide(revisedBac - ev, revisedBac - ac);
  const effectiveFutureCpi = futureCpi / costPremium;
  const cpiImprovementPct = cpi > 0 ? ((futureCpi / cpi) - 1) * 100 : null;
  const stabilityEstablished = progress >= 15;

  return {
    eacAtypical,
    eacTypical,
    eacCombined: eacCombined === null ? null : ac + eacCombined,
    tcpiBac,
    tcpiEac,
    whatIfEac: projectedTotalCost,
    whatIfVac,
    whatIfTcpi,
    effectiveFutureCpi,
    cpiImprovementPct,
    stabilityStatus: !stabilityEstablished
      ? "early"
      : cpiImprovementPct === null
        ? "indeterminate"
        : cpiImprovementPct > 10
          ? "unlikely"
          : "plausible",
    meetsRevisedBudget: whatIfTcpi === null || effectiveFutureCpi <= 0
      ? null
      : effectiveFutureCpi >= whatIfTcpi,
    revisedBac,
  };
}

function money(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "No disponible";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value);
}

function index(value: number | null): string {
  return value === null || !Number.isFinite(value) ? "—" : value.toFixed(2);
}

export function ProjectEVMForecastSimulator({ evm }: { evm: EVMForecastInput }) {
  const currentCpi = Number.isFinite(evm.cpi) ? Math.max(0, evm.cpi) : 0;
  const maxFutureCpi = Math.max(2, Math.ceil(currentCpi * 2 * 100) / 100);
  const [futureCpiOverride, setFutureCpiOverride] = useState<number | null>(null);
  const [contingencyPct, setContingencyPct] = useState(0);
  const [scheduleCompressionPct, setScheduleCompressionPct] = useState(0);
  const futureCpi = futureCpiOverride ?? Math.min(maxFutureCpi, Math.max(0.1, currentCpi));
  const scenario = useMemo(() => ({
    futureCpi,
    contingency: Math.max(0, evm.bac) * contingencyPct / 100,
    scheduleCompressionPct,
  }), [contingencyPct, evm.bac, futureCpi, scheduleCompressionPct]);
  const result = useMemo(() => calculateEVMForecast(evm, scenario), [evm, scenario]);

  const stabilityCopy = {
    early: "Aún no hay estabilidad estadística: el avance es menor al 15%.",
    plausible: "La mejora de CPI está dentro del margen histórico del 10%.",
    unlikely: "Tras el 15% de avance, una mejora superior al 10% del CPI actual es estadísticamente poco probable.",
    indeterminate: "No se puede evaluar la estabilidad del CPI actual; revisa que exista una base de costo válida.",
  }[result.stabilityStatus];

  return (
    <section className="space-y-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 sm:p-5" aria-label="Simulador de pronóstico EVM" data-testid="evm-forecast-simulator">
      <header className="flex items-start gap-2">
        <TrendingUp size={17} className="mt-0.5 shrink-0 text-[hsl(var(--primary))]" aria-hidden="true" />
        <div>
          <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">Simulador de Pronóstico EVM</h3>
          <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">Tres modelos PMI de EAC y escenarios de recuperación directiva, sin alterar la línea base guardada.</p>
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        <ForecastMetric title="EAC 1 · Variación atípica" formula="AC + (BAC − EV)" value={money(result.eacAtypical)} description="Hecho aislado; el trabajo restante sigue el presupuesto original." />
        <ForecastMetric title="EAC 2 · Variación típica" formula="BAC ÷ CPI" value={money(result.eacTypical)} description="La eficiencia de costo actual continúa hasta el cierre." />
        <ForecastMetric title="EAC 3 · Costo × cronograma" formula="AC + (BAC − EV) ÷ (CPI × SPI)" value={money(result.eacCombined)} description="Incluye el efecto conjunto de costo y retraso." />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ForecastMetric title="TCPI sobre BAC" formula="(BAC − EV) ÷ (BAC − AC)" value={index(result.tcpiBac)} description="Eficiencia necesaria para cumplir el presupuesto original." compact />
        <ForecastMetric title="TCPI sobre EAC" formula="(BAC − EV) ÷ (EAC típico − AC)" value={index(result.tcpiEac)} description="Eficiencia necesaria para cumplir el EAC típico proyectado." compact />
      </div>

      <div className="space-y-4 border-t border-[hsl(var(--border))] pt-4">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-[hsl(var(--primary))]" aria-hidden="true" />
          <div>
            <h4 className="text-sm font-bold text-[hsl(var(--text-primary))]">What-If de recuperación: crashing, fast-tracking o re-baseline</h4>
            <p className="text-xs text-[hsl(var(--text-secondary))]">Ajusta los supuestos para recalcular la proyección en tiempo real.</p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <RangeControl
            label="CPI futuro esperado"
            id="evm-future-cpi"
            min={0.1}
            max={maxFutureCpi}
            step={0.01}
            value={futureCpi}
            display={futureCpi.toFixed(2)}
            onChange={value => setFutureCpiOverride(value)}
          />
          <RangeControl
            label="Inyección delta BAC"
            id="evm-contingency"
            min={0}
            max={20}
            step={1}
            value={contingencyPct}
            display={`${contingencyPct}% · ${money(scenario.contingency)}`}
            onChange={setContingencyPct}
          />
          <RangeControl
            label="Compresión de cronograma"
            id="evm-schedule-compression"
            min={0}
            max={30}
            step={1}
            value={scheduleCompressionPct}
            display={`${scheduleCompressionPct}%`}
            onChange={setScheduleCompressionPct}
          />
        </div>
        <p className="flex items-start gap-1.5 text-[11px] text-[hsl(var(--text-secondary))]">
          <Info size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
          La compresión modela una prima de costo del mismo porcentaje sobre el trabajo restante. La contingencia incrementa el BAC objetivo; los cambios son solo de simulación.
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-live="polite">
          <ForecastMetric title="EAC del escenario" value={money(result.whatIfEac)} description={`CPI futuro ${futureCpi.toFixed(2)} con prima de compresión ${scheduleCompressionPct}%.`} compact />
          <ForecastMetric title="VAC sobre BAC revisado" value={money(result.whatIfVac)} description={`BAC simulado: ${money(result.revisedBac)}.`} compact />
          <ForecastMetric title="TCPI del escenario" value={index(result.whatIfTcpi)} description="Eficiencia requerida sobre el BAC simulado." compact />
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Viabilidad presupuestal</p>
            <p className={clsx("mt-1 text-sm font-bold", result.meetsRevisedBudget === null ? "text-[hsl(var(--text-secondary))]" : result.meetsRevisedBudget ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]")}>
              {result.meetsRevisedBudget === null ? "No determinable" : result.meetsRevisedBudget ? "Compatible con el BAC simulado" : "Requiere re-baseline o más recuperación"}
            </p>
            <p className="mt-1 text-[11px] text-[hsl(var(--text-secondary))]">CPI efectivo del escenario: {index(result.effectiveFutureCpi)}.</p>
          </div>
        </div>

        <div className={clsx(
          "flex items-start gap-2 rounded-lg border p-3 text-xs",
          result.stabilityStatus === "unlikely"
            ? "border-[hsl(var(--warning)/0.4)] bg-[hsl(var(--warning)/0.08)] text-[hsl(var(--warning))]"
            : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
        )} role="status" data-testid="cpi-stability-status">
          {result.stabilityStatus === "unlikely"
            ? <AlertTriangle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
            : result.stabilityStatus === "plausible"
              ? <CheckCircle2 size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
              : <Info size={15} className="mt-0.5 shrink-0" aria-hidden="true" />}
          <span>{stabilityCopy}{result.cpiImprovementPct !== null && ` Mejora asumida: ${result.cpiImprovementPct.toFixed(1)}%.`}</span>
        </div>
      </div>
    </section>
  );
}

function ForecastMetric({
  title,
  formula,
  value,
  description,
  compact = false,
}: {
  title: string;
  formula?: string;
  value: string;
  description: string;
  compact?: boolean;
}) {
  return (
    <article className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
      <h5 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{title}</h5>
      {formula && <p className="mt-1 font-mono text-[10px] text-[hsl(var(--text-secondary))]">{formula}</p>}
      <p className={clsx("mt-1 font-bold tabular-nums text-[hsl(var(--text-primary))]", compact ? "text-base" : "text-lg")}>
        {value}
      </p>
      <p className="mt-1 text-[11px] leading-relaxed text-[hsl(var(--text-secondary))]">{description}</p>
    </article>
  );
}

function RangeControl({
  label,
  id,
  min,
  max,
  step,
  value,
  display,
  onChange,
}: {
  label: string;
  id: string;
  min: number;
  max: number;
  step: number;
  value: number;
  display: string;
  onChange: (value: number) => void;
}) {
  return (
    <label htmlFor={id} className="space-y-2 rounded-lg border border-[hsl(var(--border))] p-3">
      <span className="flex items-center justify-between gap-2 text-xs font-semibold text-[hsl(var(--text-primary))]">
        {label}<output className="tabular-nums text-[hsl(var(--primary))]">{display}</output>
      </span>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={event => onChange(Number(event.target.value))} className="w-full accent-[hsl(var(--primary))]" />
    </label>
  );
}

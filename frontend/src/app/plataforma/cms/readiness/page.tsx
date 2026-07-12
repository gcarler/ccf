"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  Loader2,
  RefreshCcw,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { SITE_KEY } from "@/lib/site-config";
import {
  CmsReadinessCapability,
  CmsReadinessIssue,
  CmsReadinessMetric,
  CmsReadinessResponse,
  getCmsReadiness,
} from "@/lib/cms/v2";

const ISSUE_STYLE: Record<CmsReadinessIssue["severity"], { icon: typeof AlertCircle; className: string; label: string }> = {
  error: {
    icon: AlertCircle,
    className: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300",
    label: "Crítico",
  },
  warning: {
    icon: AlertTriangle,
    className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300",
    label: "Atención",
  },
  info: {
    icon: ShieldCheck,
    className: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300",
    label: "Info",
  },
};

const CAPABILITY_STYLE: Record<CmsReadinessCapability["status"], string> = {
  ready: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300",
  partial: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300",
  attention: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300",
};

function scoreLabel(score: number) {
  if (score >= 85) return "Listo";
  if (score >= 65) return "Mejorable";
  return "Crítico";
}

function formatDate(value?: string) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return date.toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CmsReadinessPage() {
  const { token } = useAuth();
  const [data, setData] = useState<CmsReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await getCmsReadiness(SITE_KEY, token);
      setData(response);
    } catch {
      toast.error("No se pudo cargar el readiness del CMS");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load().catch(() => toast.error("Error al cargar readiness"));
  }, [load]);

  const issueSummary = useMemo(() => {
    const issues = data?.issues ?? [];
    return {
      errors: issues.filter((issue) => issue.severity === "error").length,
      warnings: issues.filter((issue) => issue.severity === "warning").length,
    };
  }, [data]);

  return (
    <div className="flex h-full flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[hsl(var(--border))] px-4 dark:border-white/5">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Gauge size={16} className="shrink-0 text-[hsl(var(--primary))]" />
          <h1 className="truncate text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
            Readiness CMS
          </h1>
          <span className="rounded-full bg-[hsl(var(--surface-2))] px-2 py-0.5 text-[10px] font-semibold text-[hsl(var(--text-secondary))] dark:bg-white/5">
            {data ? scoreLabel(data.score) : "Calculando"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => load().catch(() => toast.error("Error al cargar readiness"))}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] disabled:opacity-40 dark:border-white/10"
          title="Refrescar"
        >
          <RefreshCcw size={12} className={loading ? "animate-spin" : ""} />
          Refrescar
        </button>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4">
        {loading && !data && (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-[hsl(var(--text-secondary))]">
            <Loader2 size={16} className="animate-spin" />
            Calculando salud del CMS...
          </div>
        )}

        {!loading && !data && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
            No hay datos de readiness disponibles.
          </div>
        )}

        {data && (
          <div className="mx-auto max-w-7xl space-y-4">
            <section className="grid gap-3 lg:grid-cols-[280px_1fr]">
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/[0.03]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      Score operativo
                    </p>
                    <p className="mt-2 text-5xl font-semibold tracking-normal text-[hsl(var(--text-primary))]">
                      {data.score}
                    </p>
                  </div>
                  <ShieldCheck
                    size={22}
                    className={clsx(
                      data.score >= 85 && "text-emerald-500",
                      data.score < 85 && data.score >= 65 && "text-amber-500",
                      data.score < 65 && "text-rose-500",
                    )}
                  />
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10">
                  <div
                    className={clsx(
                      "h-full rounded-full",
                      data.score >= 85 && "bg-emerald-500",
                      data.score < 85 && data.score >= 65 && "bg-amber-500",
                      data.score < 65 && "bg-rose-500",
                    )}
                    style={{ width: `${data.score}%` }}
                  />
                </div>
                <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
                  Último cálculo: {formatDate(data.generated_at)}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                {data.metrics.slice(0, 10).map((metric) => (
                  <MetricTile key={metric.key} metric={metric} />
                ))}
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/[0.03]">
                <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] px-4 py-3 dark:border-white/10">
                  <div>
                    <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Brechas de producción</h2>
                    <p className="text-xs text-[hsl(var(--text-secondary))]">
                      {issueSummary.errors} críticas, {issueSummary.warnings} advertencias
                    </p>
                  </div>
                </div>
                <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/10">
                  {data.issues.length === 0 ? (
                    <div className="flex items-center gap-2 px-4 py-8 text-sm text-emerald-600 dark:text-emerald-300">
                      <CheckCircle2 size={16} />
                      No hay brechas activas en el CMS.
                    </div>
                  ) : (
                    data.issues.map((issue) => <IssueRow key={issue.code} issue={issue} />)
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/[0.03]">
                <div className="border-b border-[hsl(var(--border))] px-4 py-3 dark:border-white/10">
                  <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Capacidades CMS</h2>
                  <p className="text-xs text-[hsl(var(--text-secondary))]">Funcionalidad esperada para páginas públicas.</p>
                </div>
                <div className="space-y-2 p-3">
                  {data.capabilities.map((capability) => (
                    <CapabilityRow key={capability.key} capability={capability} />
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

function MetricTile({ metric }: { metric: CmsReadinessMetric }) {
  const content = (
    <div className="h-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 transition-colors hover:border-[hsl(var(--primary))] dark:border-white/10 dark:bg-white/[0.03]">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{metric.label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-normal text-[hsl(var(--text-primary))]">{metric.value}</p>
    </div>
  );
  if (!metric.href) return content;
  return <Link href={metric.href}>{content}</Link>;
}

function IssueRow({ issue }: { issue: CmsReadinessIssue }) {
  const style = ISSUE_STYLE[issue.severity];
  const Icon = style.icon;
  const body = (
    <div className="flex gap-3 px-4 py-3 transition-colors hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/[0.04]">
      <div className={clsx("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border", style.className)}>
        <Icon size={14} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">{issue.title}</h3>
          <span className={clsx("rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide", style.className)}>
            {style.label} · {issue.count}
          </span>
        </div>
        <p className="mt-1 text-xs leading-5 text-[hsl(var(--text-secondary))]">{issue.detail}</p>
      </div>
    </div>
  );
  if (!issue.href) return body;
  return <Link href={issue.href}>{body}</Link>;
}

function CapabilityRow({ capability }: { capability: CmsReadinessCapability }) {
  const body = (
    <div className="rounded-lg border border-[hsl(var(--border))] p-3 transition-colors hover:border-[hsl(var(--primary))] dark:border-white/10">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">{capability.label}</h3>
        <span className={clsx("rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide", CAPABILITY_STYLE[capability.status])}>
          {capability.status === "ready" ? "Ready" : capability.status === "partial" ? "Parcial" : "Atención"}
        </span>
      </div>
      <p className="mt-1 text-xs leading-5 text-[hsl(var(--text-secondary))]">{capability.detail}</p>
    </div>
  );
  if (!capability.href) return body;
  return <Link href={capability.href}>{body}</Link>;
}

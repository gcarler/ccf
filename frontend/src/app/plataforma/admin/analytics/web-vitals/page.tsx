"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, Gauge } from "lucide-react";
import AdminShell from "@/components/admin/AdminShell";
import AdminHero from "@/components/admin/AdminHero";
import { useConfig } from "@/context/ConfigContext";
import { apiFetch } from "@/lib/http";

type VitalRecord = {
  id: string;
  name: "TTFB" | "LCP" | "FCP";
  value: number;
  path: string;
  page: string;
  timestamp: number;
};

type Summary = Record<string, { count: number; p50: number | null; p75: number | null; latest: number | null }>;

export default function WebVitalsAnalyticsPage() {
  const { isFeatureEnabled, loading: configLoading } = useConfig();
  const [records, setRecords] = useState<VitalRecord[]>([]);
  const [summary, setSummary] = useState<Summary>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isFeatureEnabled("web_vitals_dashboard")) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    const load = async (signal?: AbortSignal) => {
      try {
        const data = await apiFetch<{ records?: VitalRecord[]; summary?: Summary }>("/analytics/web-vitals", {
          query: { limit: "500" },
          cache: "no-store",
          signal,
        });
        setRecords(Array.isArray(data.records) ? data.records : []);
        setSummary((data.summary || {}) as Summary);
      } catch (error) {
        console.error("web vitals fetch failed", error);
      } finally {
        setLoading(false);
      }
    };
    load(controller.signal);
    return () => controller.abort();
  }, [isFeatureEnabled]);

  const recent = useMemo(() => records.slice().reverse().slice(0, 20), [records]);

  return (
    <AdminShell breadcrumbs={[{ label: "Analitica", icon: BarChart3 }, { label: "Web Vitals", icon: Gauge }]}>
      <AdminHero
        eyebrow="Performance"
        title="Web Vitals en tiempo real"
        description="Monitoreo interno de TTFB, FCP y LCP para validar impacto de SSR y optimizaciones por ruta."
        tags={["TTFB", "FCP", "LCP"]}
        watchers={["Frontend", "Platform", "Observability"]}
      />

      <div className="space-y-3 pb-4">
        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <VitalCard metric="TTFB" unit="ms" summary={summary.TTFB} />
          <VitalCard metric="FCP" unit="ms" summary={summary.FCP} />
          <VitalCard metric="LCP" unit="ms" summary={summary.LCP} />
        </section>

        <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 shadow-sm">
          <header className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Eventos recientes</h2>
            <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">{records.length} muestras</span>
          </header>

          {configLoading ? (
            <p className="py-8 text-sm text-[hsl(var(--muted-foreground))]">Cargando feature flags...</p>
          ) : !isFeatureEnabled("web_vitals_dashboard") ? (
            <p className="py-8 text-sm text-[hsl(var(--muted-foreground))]">Este módulo está desactivado por feature flag.</p>
          ) : loading ? (
            <p className="py-8 text-sm text-[hsl(var(--muted-foreground))]">Cargando telemetria...</p>
          ) : recent.length === 0 ? (
            <p className="py-8 text-sm text-[hsl(var(--muted-foreground))]">Aun no hay muestras registradas.</p>
          ) : (
            <div className="max-h-[520px] overflow-y-auto overflow-x-auto">
              <table className="w-full text-left text-sm min-w-[520px]">
                <thead className="sticky top-0 bg-[hsl(var(--surface-1))]">
                  <tr className="text-2xs uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                    <th className="py-2">Metrica</th>
                    <th className="py-2">Valor</th>
                    <th className="py-2">Ruta</th>
                    <th className="py-2">Pagina</th>
                    <th className="py-2">Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((item) => (
                    <tr key={`${item.id}-${item.timestamp}`} className="border-t border-[hsl(var(--border))]">
                      <td className="py-2 font-bold text-[hsl(var(--foreground))]">{item.name}</td>
                      <td className="py-2 text-[hsl(var(--muted-foreground))]">{Math.round(item.value)} ms</td>
                      <td className="py-2 text-[hsl(var(--muted-foreground))]">{item.path}</td>
                      <td className="max-w-[240px] truncate py-2 text-[hsl(var(--muted-foreground))]">{item.page}</td>
                      <td className="py-2 text-[hsl(var(--muted-foreground))]">{new Date(item.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </AdminShell>
  );
}

function VitalCard({ metric, unit, summary }: { metric: string; unit: string; summary?: Summary[string] }) {
  return (
    <article className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{metric}</p>
        <Activity size={14} className="text-[hsl(var(--primary))]" />
      </div>
      <dl className="space-y-1">
        <div className="flex items-center justify-between text-sm">
          <dt className="text-[hsl(var(--muted-foreground))]">p50</dt>
          <dd className="font-bold text-[hsl(var(--foreground))]">{summary?.p50 ?? "-"} {summary?.p50 != null ? unit : ""}</dd>
        </div>
        <div className="flex items-center justify-between text-sm">
          <dt className="text-[hsl(var(--muted-foreground))]">p75</dt>
          <dd className="font-bold text-[hsl(var(--foreground))]">{summary?.p75 ?? "-"} {summary?.p75 != null ? unit : ""}</dd>
        </div>
        <div className="flex items-center justify-between text-sm">
          <dt className="text-[hsl(var(--muted-foreground))]">ultimo</dt>
          <dd className="font-bold text-[hsl(var(--foreground))]">{summary?.latest ?? "-"} {summary?.latest != null ? unit : ""}</dd>
        </div>
      </dl>
    </article>
  );
}

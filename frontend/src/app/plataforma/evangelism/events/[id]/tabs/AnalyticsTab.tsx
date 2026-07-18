"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import type { EventAnalyticsData } from "@/app/plataforma/evangelism/types";

interface AnalyticsTabProps {
  eventId: string;
  token: string | null;
}

export default function AnalyticsTab({ eventId, token }: AnalyticsTabProps) {
  const [analytics, setAnalytics] = useState<EventAnalyticsData | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [failed, setFailed] = useState(false);

  const loadAnalytics = async (signal: AbortSignal) => {
    if (!token) return;
    setLoadingAnalytics(true);
    setFailed(false);
    try {
      const data = await apiFetch<EventAnalyticsData>(`/evangelism/events/${eventId}/analytics`, { token, silent: true, signal });
      if (signal.aborted) return;
      setAnalytics(data);
    } catch {
      if (!signal.aborted) {
        setAnalytics(null);
        setFailed(true);
      }
    } finally {
      if (!signal.aborted) setLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    const abort = new AbortController();
    loadAnalytics(abort.signal);
    return () => abort.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, token]);

  if (loadingAnalytics) {
    return (
      <div className="space-y-3">
        <div className="text-center py-1.5 text-[hsl(var(--text-secondary))] font-medium">Cargando analítica...</div>
      </div>
    );
  }

  if (failed) {
    return (
      <div className="space-y-3">
        <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 text-center">
          <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">No se pudo cargar la analítica</p>
          <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">La vista puede seguir usándose mientras se corrige el origen de datos.</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg p-3 text-center">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Promedio Histórico</p>
          <h3 className="text-xl font-bold text-[hsl(var(--text-primary))]">{analytics.kpis.historical_avg}</h3>
          <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">Personas por sesión</p>
        </div>
        <div className="bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg p-3 text-center">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Tendencia de Crecimiento</p>
          <h3 className={`text-xl font-bold ${analytics.kpis.trend_percentage > 0 ? 'text-emerald-500' : analytics.kpis.trend_percentage < 0 ? 'text-[hsl(var(--destructive))]' : 'text-[hsl(var(--text-secondary))]'}`}>
            {analytics.kpis.trend_percentage > 0 ? '+' : ''}{analytics.kpis.trend_percentage}%
          </h3>
          <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-1">Respecto al mes anterior</p>
        </div>
        <div className="bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg p-3 text-center">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Mes Pico (Récord)</p>
          <h3 className="text-xl font-bold text-[hsl(var(--primary))]">{analytics.kpis.peak_month.avg}</h3>
          <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">{analytics.kpis.peak_month.month}</p>
        </div>
      </div>

      {/* Gráfico de Barras CSS */}
      <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-md p-4 shadow-sm">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Asistencia Promedio por Mes</h3>

        {analytics.monthly_data.length === 0 ? (
          <div className="text-center py-2 text-[hsl(var(--text-secondary))] text-sm">No hay datos suficientes para graficar.</div>
        ) : (
          <div className="flex items-end gap-2 h-48 mt-4 w-full overflow-x-auto pb-4 scrollbar-thin">
            {analytics.monthly_data.map((d) => {
              const maxAvg = analytics.kpis.peak_month.avg || 1;
              const heightPct = Math.max(5, Math.round((d.avg_attendance / maxAvg) * 100));

              return (
                <div key={d.month} className="flex-1 min-w-[40px] max-w-[80px] flex flex-col items-center justify-end group">
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-[hsl(var(--bg-primary))] text-white text-[10px] font-bold px-2 py-1 rounded-md mb-2 whitespace-nowrap">
                    {d.avg_attendance} asis.
                  </div>
                  <div
                    className="w-full bg-blue-100 dark:bg-blue-900/40 hover:bg-[hsl(var(--primary))] dark:hover:bg-[hsl(var(--primary))] rounded-t-lg transition-all duration-500"
                    style={{ height: `${heightPct}%` }}
                  ></div>
                  <div className="mt-2 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] rotate-[-45deg] origin-top-left translate-y-2 translate-x-2">
                    {d.month}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

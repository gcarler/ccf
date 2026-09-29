"use client";

import { useCallback, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { AlertTriangle, BarChart3, BookOpenCheck, HeartPulse, Users, UsersRound } from 'lucide-react';
import { toast } from 'sonner';
import { DSCard, DSMetric, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { CohortHealthResponse, InstitutionalAcademySummary, OfferingGradesDetail, PeriodOffering } from '@/types/academy';

type GradeBand = { label: string; count: number; color: string };

const ALERT_TONE: Record<string, string> = {
  critical: 'border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))]',
  high: 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.08)] text-[hsl(var(--warning))]',
  medium: 'border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))]',
  low: 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]',
};

function formatPercent(value: number | undefined) {
  return value == null || !Number.isFinite(value) ? '—' : `${Math.round(value)}%`;
}

function displayAlertValue(value: string | undefined) {
  return value ? value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Señal de bienestar';
}

export default function AcademyAnalyticsPage() {
  const { token, isAuthenticated } = useAuth();
  const [offerings, setOfferings] = useState<PeriodOffering[]>([]);
  const [selectedSede, setSelectedSede] = useState('all');
  const [selectedOffering, setSelectedOffering] = useState('');
  const [summary, setSummary] = useState<InstitutionalAcademySummary | null>(null);
  const [cohort, setCohort] = useState<CohortHealthResponse | null>(null);
  const [gradeDetail, setGradeDetail] = useState<OfferingGradesDetail | null>(null);
  const [offeringsLoading, setOfferingsLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  useEffect(() => {
    if (!token || !isAuthenticated) return;
    const controller = new AbortController();
    async function loadOfferings() {
      try {
        const result = await apiFetch<PeriodOffering[]>('/academy/admin/offerings', {
          token,
          cache: 'no-store',
          signal: controller.signal,
        });
        const records = Array.isArray(result) ? result : [];
        setOfferings(records);
        setSelectedOffering((current) => current && records.some((item) => item.id === current) ? current : records[0]?.id ?? '');
        const siteIds = Array.from(new Set(records.flatMap((item) => item.sede_id ? [item.sede_id] : [])));
        if (siteIds.length === 1) setSelectedSede(siteIds[0]);
      } catch (error) {
        if (!controller.signal.aborted) {
          console.error(error);
          toast.error('No pudimos cargar las comisiones disponibles para analítica.');
          setOfferings([]);
        }
      } finally {
        if (!controller.signal.aborted) setOfferingsLoading(false);
      }
    }
    void loadOfferings();
    return () => controller.abort();
  }, [token, isAuthenticated]);

  const visibleOfferings = useMemo(
    () => selectedSede === 'all' ? offerings : offerings.filter((item) => item.sede_id === selectedSede),
    [offerings, selectedSede],
  );
  const activeOffering = visibleOfferings.find((item) => item.id === selectedOffering) ?? visibleOfferings[0] ?? null;
  const siteOptions = useMemo(() => {
    const ids = Array.from(new Set(offerings.flatMap((item) => item.sede_id ? [item.sede_id] : [])));
    return ids.map((id) => ({ id, label: `Sede ${id.slice(0, 8)}` }));
  }, [offerings]);

  const loadAnalytics = useCallback(async () => {
    if (!token || !isAuthenticated) return;
    setAnalyticsLoading(true);
    const summaryQuery = selectedSede !== 'all' ? { sede_id: selectedSede } : undefined;
    const summaryRequest = apiFetch<InstitutionalAcademySummary>('/academy/analytics/institutional-summary', {
      token,
      cache: 'no-store',
      query: summaryQuery,
    });
    try {
      const data = await summaryRequest;
      setSummary(data);
    } catch (error) {
      console.error(error);
      setSummary(null);
      toast.error('No pudimos cargar los indicadores institucionales.');
    }

    if (!activeOffering) {
      setCohort(null);
      setGradeDetail(null);
      setAnalyticsLoading(false);
      return;
    }
    try {
      const [health, grades] = await Promise.all([
        apiFetch<CohortHealthResponse>(`/academy/analytics/cohort-health/${activeOffering.id}`, { token, cache: 'no-store' }),
        apiFetch<OfferingGradesDetail>(`/academy/admin/offerings/${activeOffering.id}/grades`, { token, cache: 'no-store' }),
      ]);
      setCohort(health);
      setGradeDetail(grades);
    } catch (error) {
      console.error(error);
      setCohort(null);
      setGradeDetail(null);
      toast.error('No pudimos cargar la salud académica de la comisión seleccionada.');
    } finally {
      setAnalyticsLoading(false);
    }
  }, [activeOffering, isAuthenticated, selectedSede, token]);

  useEffect(() => { void loadAnalytics(); }, [loadAnalytics]);

  const gradeBands = useMemo<GradeBand[]>(() => {
    const records = gradeDetail?.records ?? [];
    const grades = records.flatMap((record) => record.calculated_final_grade == null ? [] : [record.calculated_final_grade]);
    return [
      { label: '0–59', count: grades.filter((grade) => grade < 60).length, color: 'bg-[hsl(var(--destructive))]' },
      { label: '60–69', count: grades.filter((grade) => grade >= 60 && grade < 70).length, color: 'bg-[hsl(var(--warning))]' },
      { label: '70–89', count: grades.filter((grade) => grade >= 70 && grade < 90).length, color: 'bg-[hsl(var(--primary))]' },
      { label: '90–100', count: grades.filter((grade) => grade >= 90).length, color: 'bg-[hsl(var(--success))]' },
    ];
  }, [gradeDetail]);
  const gradeTotal = gradeBands.reduce((total, band) => total + band.count, 0);

  if (!isAuthenticated) return null;

  return (
    <main className="space-y-6 p-4 text-[hsl(var(--text-primary))] md:p-6">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--primary))]">Gestión institucional</p>
          <h1 className="mt-1 text-2xl font-bold">Analítica académica</h1>
          <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Indicadores institucionales y señales tempranas de salud de cohorte.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-xs font-medium text-[hsl(var(--text-secondary))]">
            <span>Sede</span>
            <select value={selectedSede} onChange={(event) => {
              const nextSede = event.target.value;
              setSelectedSede(nextSede);
              const nextOffering = nextSede === 'all' ? offerings[0] : offerings.find((item) => item.sede_id === nextSede);
              setSelectedOffering(nextOffering?.id ?? '');
            }} className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))]">
              <option value="all">Todas las sedes disponibles</option>
              {siteOptions.map((site) => <option key={site.id} value={site.id}>{site.label}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-xs font-medium text-[hsl(var(--text-secondary))]">
            <span>Cohorte / comisión</span>
            <select value={activeOffering?.id ?? ''} onChange={(event) => setSelectedOffering(event.target.value)} disabled={offeringsLoading || visibleOfferings.length === 0} className="w-full max-w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))] disabled:opacity-60">
              {visibleOfferings.length === 0 ? <option value="">Sin comisiones disponibles</option> : visibleOfferings.map((offering) => <option key={offering.id} value={offering.id}>{offering.subject_name ?? 'Materia'} · {offering.group_name} · {offering.period_code ?? 'Periodo'}</option>)}
            </select>
          </label>
        </div>
      </header>

      {offeringsLoading || analyticsLoading ? (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Cargando analítica">
          {Array.from({ length: 5 }, (_, index) => <DSSkeleton key={index} className="h-28 rounded-xl" />)}
        </section>
      ) : (
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Indicadores institucionales">
          <DSMetric label="Estudiantes" value={String(summary?.total_students ?? '—')} trend="Matriculados" icon={Users} tone="blue" />
          <DSMetric label="Retención proyectada" value={formatPercent(summary?.retention_projected_rate)} trend="Proyección institucional" icon={BookOpenCheck} tone="emerald" />
          <DSMetric label="Aprobación socrática" value={formatPercent(summary?.socratic_pass_rate)} trend="Defensas aprobadas" icon={BarChart3} tone="blue" />
          <DSMetric label="Bienestar promedio" value={formatPercent(summary?.wellness_health_index)} trend="Índice de salud" icon={HeartPulse} tone="amber" />
          <DSMetric label="Grupos activos" value={String(summary?.active_study_groups ?? '—')} trend="Grupos de estudio" icon={UsersRound} tone="emerald" />
        </section>
      )}

      {analyticsLoading ? (
        <div className="grid gap-4 xl:grid-cols-2"><DSSkeleton className="h-72 rounded-xl" /><DSSkeleton className="h-72 rounded-xl" /></div>
      ) : !activeOffering ? (
        <EmptyState title="Sin cohortes disponibles" description="No hay comisiones visibles para esta cuenta o sede. Cuando exista una comisión, aparecerá aquí su diagnóstico." icon={BarChart3} />
      ) : cohort ? (
        <section className="grid gap-4 xl:grid-cols-2">
          <DSCard className="min-w-0 overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4" tone="light">
            <header className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Salud de cohorte</p>
                <h2 className="mt-1 text-lg font-semibold">{cohort.subject_name}</h2>
                <p className="text-sm text-[hsl(var(--text-secondary))]">{cohort.period_code} · {activeOffering.group_name}</p>
              </div>
              <span className={clsx('rounded-full border px-3 py-1 text-xs font-semibold', cohort.health_status === 'at_risk' ? ALERT_TONE.critical : cohort.health_status === 'needs_attention' ? ALERT_TONE.high : ALERT_TONE.medium)}>
                {cohort.health_status === 'at_risk' ? 'En riesgo' : cohort.health_status === 'needs_attention' ? 'Requiere atención' : 'Salud estable'}
              </span>
            </header>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3"><p className="text-xs text-[hsl(var(--text-secondary))]">Promedio general</p><p className="mt-1 text-xl font-bold">{cohort.average_grade.toFixed(1)}</p></div>
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3"><p className="text-xs text-[hsl(var(--text-secondary))]">Tasa de aprobación</p><p className="mt-1 text-xl font-bold">{formatPercent(cohort.completion_rate)}</p></div>
            </div>
            <div className="mt-5">
              <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">Distribución de calificaciones</h3><span className="text-xs text-[hsl(var(--text-secondary))]">{gradeTotal} notas registradas</span></div>
              {gradeTotal > 0 ? (
                <div className="mt-3 space-y-3">
                  {gradeBands.map((band) => (
                    <div key={band.label} className="grid grid-cols-[3.5rem_1fr_2rem] items-center gap-2 text-xs">
                      <span className="text-[hsl(var(--text-secondary))]">{band.label}</span>
                      <div className="h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-3))]"><div className={clsx('h-full rounded-full transition-[width]', band.color)} style={{ width: `${(band.count / gradeTotal) * 100}%` }} /></div>
                      <span className="text-right font-semibold">{band.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-sm text-[hsl(var(--text-secondary))]">Aún no hay calificaciones finales para distribuir.</div>
              )}
            </div>
          </DSCard>

          <DSCard className="min-w-0 overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4" tone="light">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Señales de aprendizaje y bienestar</p>
              <h2 className="mt-1 text-lg font-semibold">Puntos que requieren atención</h2>
            </div>
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold">Nodos con mayor dificultad</h3>
              {cohort.lowest_mastery_nodes.length > 0 ? (
                <ul className="space-y-2">
                  {cohort.lowest_mastery_nodes.map((node) => (
                    <li key={node.node_id} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
                      <div className="flex items-start justify-between gap-3"><p className="text-sm font-medium">{node.title}</p><span className="shrink-0 text-xs font-semibold text-[hsl(var(--warning))]">{Math.round(node.average_mastery * 100)}% dominio</span></div>
                      <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{node.evaluated_students_count} evaluaciones{node.code ? ` · ${node.code}` : ''}</p>
                    </li>
                  ))}
                </ul>
              ) : <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-sm text-[hsl(var(--text-secondary))]">Sin nodos evaluados para esta comisión.</p>}
            </div>
            <div className="mt-5">
              <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">Alertas de bienestar pendientes</h3><span className="rounded-full bg-[hsl(var(--surface-2))] px-2 py-1 text-xs">{cohort.active_alerts_count}</span></div>
              {cohort.active_alerts.length > 0 ? (
                <ul className="mt-2 space-y-2">
                  {cohort.active_alerts.map((alert) => (
                    <li key={alert.id} className={clsx('flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-xs', ALERT_TONE[alert.severity ?? ''] ?? ALERT_TONE.low)}>
                      <span className="flex items-center gap-2 font-semibold"><AlertTriangle className="size-4" /> {displayAlertValue(alert.signal_type)} · {displayAlertValue(alert.severity)}</span>
                      <span>{alert.detected_at ? new Date(alert.detected_at).toLocaleDateString('es') : 'Fecha no disponible'}</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="mt-2 rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-sm text-[hsl(var(--text-secondary))]">No hay alertas pendientes para esta comisión.</p>}
            </div>
            {cohort.recommendations.length > 0 && <p className="mt-4 flex items-start gap-2 rounded-lg border border-[hsl(var(--primary)/0.25)] bg-[hsl(var(--primary)/0.06)] p-3 text-sm"><HeartPulse className="mt-0.5 size-4 shrink-0 text-[hsl(var(--primary))]" /> {cohort.recommendations[0]}</p>}
          </DSCard>
        </section>
      ) : (
        <EmptyState title="Salud de cohorte no disponible" description="No se pudieron obtener datos para la comisión seleccionada. Cambia la selección o vuelve a intentarlo más tarde." icon={AlertTriangle} />
      )}
    </main>
  );
}

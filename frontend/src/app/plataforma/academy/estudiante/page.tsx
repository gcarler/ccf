"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Award,
  BellRing,
  BookOpenCheck,
  Brain,
  CalendarClock,
  CheckCircle2,
  GraduationCap,
  Map as MapIcon,
  Target,
  TrendingUp,
} from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import WellnessAlertDrawer from '@/components/academy/WellnessAlertDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type {
  AcademicTranscriptSummary,
  KnowledgeGraph,
  StudentNodeProgress,
  WellnessAlert,
} from '@/types/academy';

const quickLinks = [
  { label: 'Tutor Socrático', description: 'Piensa cada tema con ayuda del tutor', href: '/plataforma/academy/tutor', icon: Brain },
  { label: 'Mi Portafolio', description: 'Consulta tus logros y credenciales', href: '/plataforma/academy/portafolio', icon: Award },
  { label: 'Mapa de Aprendizaje', description: 'Explora conceptos y competencias', href: '/plataforma/academy/mapa', icon: MapIcon },
  { label: 'Historial Académico', description: 'Revisa tus cursos y actividad', href: '/plataforma/academy', icon: BookOpenCheck },
] as const;

function latestOfferingId(record: AcademicTranscriptSummary): string | null {
  const entries = record.subjects
    .filter((subject) => Boolean(subject.offering_id))
    .sort((left, right) => right.period_code.localeCompare(left.period_code));
  return entries[0]?.offering_id ?? null;
}

function isActiveSubject(status: string, passed: boolean): boolean {
  if (passed) return false;
  return ['enrolled', 'active', 'in_progress', 'in progress', 'pending'].includes(status.toLowerCase());
}

function getSeverity(alert: WellnessAlert): 'critical' | 'high' | 'medium' | 'low' {
  const severity = alert.severity?.toLowerCase();
  if (severity === 'critical' || severity === 'high' || severity === 'medium' || severity === 'low') return severity;
  const match = alert.message.match(/\b(critical|high|medium|low)\b/i);
  const parsed = match?.[1]?.toLowerCase();
  return parsed === 'critical' || parsed === 'high' || parsed === 'medium' || parsed === 'low' ? parsed : 'medium';
}

function severityLabel(severity: 'critical' | 'high' | 'medium' | 'low'): string {
  return { critical: 'Crítica', high: 'Alta', medium: 'Media', low: 'Baja' }[severity];
}

function severityClass(severity: 'critical' | 'high' | 'medium' | 'low'): string {
  if (severity === 'critical') return 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]';
  if (severity === 'high') return 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]';
  if (severity === 'medium') return 'border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]';
  return 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground,var(--text-secondary)))]';
}

export default function StudentAcademyDashboardPage() {
  const router = useRouter();
  const { token, isAuthenticated } = useAuth();
  const [record, setRecord] = useState<AcademicTranscriptSummary | null>(null);
  const [alerts, setAlerts] = useState<WellnessAlert[]>([]);
  const [nodes, setNodes] = useState<KnowledgeGraph['nodes']>([]);
  const [progress, setProgress] = useState<StudentNodeProgress[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<WellnessAlert | null>(null);
  const [loadingAcademic, setLoadingAcademic] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(true);
  const [academicError, setAcademicError] = useState<string | null>(null);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (signal: AbortSignal) => {
    if (!token) {
      setLoadingAcademic(false);
      setLoadingAlerts(false);
      setLoadingProgress(false);
      return;
    }

    setLoadingAcademic(true);
    setLoadingAlerts(true);
    setLoadingProgress(true);
    setAcademicError(null);
    setAlertsError(null);
    setProgressError(null);

    const alertsRequest = apiFetch<WellnessAlert[]>('/academy/wellness/my-alerts', {
      token,
      cache: 'no-store',
      signal,
    }).then((data) => {
      setAlerts(Array.isArray(data) ? data : []);
    }).catch((error: unknown) => {
      if (!signal.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar tus alertas de bienestar');
        setAlertsError(message);
        toast.error(message);
      }
    }).finally(() => {
      if (!signal.aborted) setLoadingAlerts(false);
    });

    try {
      const academicRecord = await apiFetch<AcademicTranscriptSummary>('/academy/me/academic-record', {
        token,
        cache: 'no-store',
        signal,
      });
      if (signal.aborted) return;
      setRecord(academicRecord);
      setLoadingAcademic(false);

      const offeringId = latestOfferingId(academicRecord);
      if (!offeringId) {
        setNodes([]);
        setProgress([]);
        setLoadingProgress(false);
      } else {
        try {
          const [graph, studentProgress] = await Promise.all([
            apiFetch<KnowledgeGraph>(`/academy/knowledge/${offeringId}/graph`, { token, cache: 'no-store', signal }),
            apiFetch<StudentNodeProgress[]>(`/academy/knowledge/${offeringId}/student-progress`, { token, cache: 'no-store', signal }),
          ]);
          if (!signal.aborted) {
            setNodes(graph.nodes ?? []);
            setProgress(Array.isArray(studentProgress) ? studentProgress : []);
          }
        } catch (error: unknown) {
          if (!signal.aborted) {
            const message = extractErrorMessage(error, 'No pudimos cargar tu progreso de aprendizaje');
            setProgressError(message);
            toast.error(message);
          }
        } finally {
          if (!signal.aborted) setLoadingProgress(false);
        }
      }
    } catch (error: unknown) {
      if (!signal.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar tu resumen académico');
        setAcademicError(message);
        toast.error(message);
        setLoadingAcademic(false);
        setLoadingProgress(false);
      }
    }

    await alertsRequest;
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoadingAcademic(false);
      setLoadingAlerts(false);
      setLoadingProgress(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadDashboard(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadDashboard, token]);

  const weakestNodes = useMemo(() => {
    const masteryByNode = new Map(progress.map((entry) => [entry.node_id, entry]));
    return nodes
      .map((node) => ({ node, mastery: masteryByNode.get(node.id)?.mastery_score ?? 0 }))
      .sort((left, right) => left.mastery - right.mastery)
      .slice(0, 5);
  }, [nodes, progress]);

  const activeAlerts = alerts.filter((alert) => alert.is_resolved !== true);
  const activeSubjects = record?.subjects.filter((subject) => isActiveSubject(subject.status, subject.passed)).length ?? 0;
  const requiredCredits = record?.total_credits_required;
  const graduationProgress = requiredCredits && requiredCredits > 0 && record
    ? Math.min(100, Math.round((record.total_credits_earned / requiredCredits) * 100))
    : null;

  return (
    <div className="min-h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-3">
          <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><GraduationCap className="size-6" /></div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Campus OS Cognitivo</p>
            <h1 className="mt-1 text-xl font-bold sm:text-2xl">Mi Dashboard</h1>
            <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Tu resumen académico, bienestar y próximos pasos de aprendizaje.</p>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-5 px-4 py-5 sm:px-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="academic-summary-title">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">A</p>
              <h2 id="academic-summary-title" className="mt-1 text-lg font-bold">Resumen académico</h2>
            </div>
            <TrendingUp className="size-5 text-[hsl(var(--primary))]" aria-hidden="true" />
          </div>
          {loadingAcademic ? (
            <div className="space-y-3"><DSSkeleton className="h-16 rounded-xl" /><DSSkeleton className="h-20 rounded-xl" /></div>
          ) : academicError ? (
            <p className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{academicError}</p>
          ) : record ? (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Metric label="Promedio general" value={record.weighted_gpa.toFixed(2)} icon={Target} />
                <Metric label="Créditos aprobados" value={record.total_credits_earned} icon={CheckCircle2} />
                <Metric label="Materias activas" value={activeSubjects} icon={BookOpenCheck} />
              </div>
              <div className="mt-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold">Progreso hacia graduación</span>
                  <span className="text-sm font-bold text-[hsl(var(--primary))]">{graduationProgress === null ? '—' : `${graduationProgress}%`}</span>
                </div>
                <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-[hsl(var(--surface-3))]" role="progressbar" aria-label="Progreso hacia graduación" aria-valuemin={0} aria-valuemax={100} aria-valuenow={graduationProgress ?? 0}>
                  <div className="h-full rounded-full bg-[hsl(var(--primary))] transition-all" style={{ width: `${graduationProgress ?? 0}%` }} />
                </div>
                <p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">
                  {graduationProgress === null
                    ? 'La meta total de créditos aún no está disponible en tu historial académico.'
                    : `${record.total_credits_earned} de ${requiredCredits} créditos del programa.`}
                </p>
              </div>
            </>
          ) : (
            <EmptyState title="Resumen académico no disponible" description="No encontramos datos académicos para mostrar." icon={GraduationCap} />
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="wellness-alerts-title">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">B</p>
              <h2 id="wellness-alerts-title" className="mt-1 text-lg font-bold">Alertas de bienestar</h2>
            </div>
            <BellRing className="size-5 text-[hsl(var(--primary))]" aria-hidden="true" />
          </div>
          {loadingAlerts ? (
            <div className="space-y-3"><DSSkeleton className="h-16 rounded-xl" /><DSSkeleton className="h-16 rounded-xl" /></div>
          ) : alertsError ? (
            <p className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{alertsError}</p>
          ) : activeAlerts.length === 0 ? (
            <EmptyState title="Todo marcha bien 🎉" description="No tienes alertas activas de bienestar en este momento." icon={CheckCircle2} />
          ) : (
            <ul className="space-y-3">
              {activeAlerts.map((alert) => {
                const severity = getSeverity(alert);
                return (
                  <li key={alert.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-2 text-sm font-medium">{alert.message}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-[hsl(var(--text-secondary))]"><CalendarClock className="size-3.5" />{new Date(alert.sent_at).toLocaleDateString('es')}</p>
                    </div>
                    <span className={clsx('rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase', severityClass(severity))}>{severityLabel(severity)}</span>
                    <DSButton variant="secondary" onClick={() => setSelectedAlert(alert)} className="inline-flex items-center gap-1.5">Ver detalle <ArrowRight className="size-3.5" /></DSButton>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="learning-progress-title">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">C</p>
              <h2 id="learning-progress-title" className="mt-1 text-lg font-bold">Progreso de aprendizaje</h2>
              <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">Conceptos que puedes reforzar en tu comisión más reciente.</p>
            </div>
            <Brain className="size-5 text-[hsl(var(--primary))]" aria-hidden="true" />
          </div>
          {loadingProgress ? (
            <div className="space-y-3"><DSSkeleton className="h-12 rounded-xl" /><DSSkeleton className="h-12 rounded-xl" /></div>
          ) : progressError ? (
            <p className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{progressError}</p>
          ) : weakestNodes.length === 0 ? (
            <EmptyState title="Aún no hay progreso disponible" description="Cuando tengas nodos evaluados en una comisión, aparecerán aquí tus oportunidades de aprendizaje." icon={Brain} />
          ) : (
            <div className="space-y-2">
              {weakestNodes.map(({ node, mastery }, index) => {
                const percentage = Math.round(Math.min(1, Math.max(0, mastery)) * 100);
                return (
                  <div key={node.id} className="flex items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
                    <span className="grid size-7 shrink-0 place-items-center rounded-full bg-[hsl(var(--primary)/0.12)] text-xs font-bold text-[hsl(var(--primary))]">{index + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-3">
                        <p className="truncate text-sm font-semibold">{node.title}</p>
                        <span className="shrink-0 text-xs font-semibold text-[hsl(var(--text-secondary))]">{percentage}%</span>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[hsl(var(--surface-3))]">
                        <div className="h-full rounded-full bg-[hsl(var(--primary))]" style={{ width: `${percentage}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
              <DSButton variant="secondary" onClick={() => router.push('/plataforma/academy/mapa')} className="mt-2 inline-flex items-center gap-2">Ir al Mapa completo <ArrowRight className="size-4" /></DSButton>
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="quick-access-title">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">D</p>
              <h2 id="quick-access-title" className="mt-1 text-lg font-bold">Accesos rápidos</h2>
            </div>
            <Target className="size-5 text-[hsl(var(--primary))]" aria-hidden="true" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {quickLinks.map(({ label, description, href, icon: Icon }) => (
              <button
                key={href}
                type="button"
                onClick={() => router.push(href)}
                className="group flex min-w-0 items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-left transition-colors hover:border-[hsl(var(--primary)/0.4)] hover:bg-[hsl(var(--surface-1))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
              >
                <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]"><Icon className="size-5" /></span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">{label}</span>
                  <span className="mt-0.5 block text-xs text-[hsl(var(--text-secondary))]">{description}</span>
                </span>
                <ArrowRight className="size-4 shrink-0 text-[hsl(var(--text-secondary))] transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
        </section>
      </main>

      <WellnessAlertDrawer open={Boolean(selectedAlert)} onClose={() => setSelectedAlert(null)} alert={selectedAlert} />
    </div>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: string | number; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="min-w-0 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
      <Icon className="size-4 text-[hsl(var(--primary))]" aria-hidden="true" />
      <p className="mt-2 truncate text-xs text-[hsl(var(--text-secondary))]">{label}</p>
      <p className="mt-0.5 text-lg font-bold">{value}</p>
    </div>
  );
}

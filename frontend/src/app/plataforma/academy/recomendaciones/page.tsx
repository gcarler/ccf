"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, BookOpenCheck, Brain, CalendarDays, Compass, Lightbulb, RefreshCw, Sparkles, UsersRound } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { AcademyRecommendation } from '@/types/academy';

function typeIcon(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes('study') || normalized.includes('group')) return UsersRound;
  if (normalized.includes('tutor') || normalized.includes('socratic') || normalized.includes('knowledge')) return Brain;
  if (normalized.includes('course') || normalized.includes('lesson')) return BookOpenCheck;
  if (normalized.includes('resource') || normalized.includes('material')) return Compass;
  return Sparkles;
}

function typeLabel(type: string): string {
  const labels: Record<string, string> = {
    study_group: 'Grupo de estudio',
    socratic_tutor: 'Tutor socrático',
    tutor: 'Tutoría',
    course: 'Curso',
    resource: 'Recurso',
    learning_path: 'Ruta de aprendizaje',
    mentor: 'Mentoría',
  };
  return labels[type.toLowerCase()] ?? type.replaceAll('_', ' ');
}

function formatScore(score: number): string {
  const normalizedScore = score >= 0 && score <= 1 ? score * 100 : score;
  return `${Math.round(normalizedScore)}%`;
}

function formatDate(value?: string): string {
  if (!value) return 'Reciente';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Reciente' : date.toLocaleDateString('es');
}

export default function StudentRecommendationsPage() {
  const { token, isAuthenticated } = useAuth();
  const [recommendations, setRecommendations] = useState<AcademyRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const loadRecommendations = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AcademyRecommendation[]>('/academy/recommendations/my', { token, cache: 'no-store', signal });
      if (!signal?.aborted) setRecommendations(Array.isArray(data) ? data : []);
    } catch (requestError: unknown) {
      if (!signal?.aborted) {
        const message = extractErrorMessage(requestError, 'No pudimos cargar tus recomendaciones');
        setError(message);
        toast.error(message);
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadRecommendations(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadRecommendations, token]);

  const handleGenerate = async () => {
    if (!token || generating) return;
    setGenerating(true);
    try {
      await apiFetch('/academy/recommendations/generate', { method: 'POST', token });
      toast.success('Recomendaciones actualizadas');
      await loadRecommendations();
    } catch (requestError: unknown) {
      toast.error(extractErrorMessage(requestError, 'No pudimos generar recomendaciones'));
    } finally {
      setGenerating(false);
    }
  };

  const handleView = async (recommendation: AcademyRecommendation) => {
    if (!token || viewingId) return;
    setViewingId(recommendation.id);
    try {
      await apiFetch(`/academy/recommendations/${recommendation.id}/viewed`, { method: 'POST', token });
      setExpandedIds((current) => {
        const next = new Set(current);
        if (next.has(recommendation.id)) next.delete(recommendation.id);
        else next.add(recommendation.id);
        return next;
      });
    } catch (requestError: unknown) {
      toast.error(extractErrorMessage(requestError, 'No pudimos abrir esta recomendación'));
    } finally {
      setViewingId(null);
    }
  };

  return (
    <div className="min-h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><Lightbulb className="size-6" /></span>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Campus OS Cognitivo</p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">Recomendaciones para ti</h1>
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Sugerencias para avanzar en tu aprendizaje y conectar con la comunidad.</p>
            </div>
          </div>
          <DSButton onClick={() => void handleGenerate()} loading={generating} className="inline-flex items-center gap-2"><RefreshCw className={clsx('size-4', generating && 'animate-spin')} /> Generar</DSButton>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6">
        <section aria-label="Mis recomendaciones">
          {loading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"><DSSkeleton className="h-56 rounded-xl" /><DSSkeleton className="h-56 rounded-xl" /><DSSkeleton className="h-56 rounded-xl" /></div>
          ) : error ? (
            <p role="alert" className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--surface-1))] p-4 text-sm text-[hsl(var(--destructive))]">{error}</p>
          ) : recommendations.length === 0 ? (
            <EmptyState title="Aún no tienes recomendaciones" description="Genera nuevas sugerencias personalizadas según tu trayectoria académica." icon={Lightbulb} onAction={() => void handleGenerate()} actionLabel="Generar recomendaciones" />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {recommendations.map((recommendation) => {
                const Icon = typeIcon(recommendation.recommendation_type);
                const expanded = expandedIds.has(recommendation.id);
                return (
                  <article key={recommendation.id} className="flex min-w-0 flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm">
                    <div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-[hsl(var(--primary)/0.25)] bg-[hsl(var(--primary)/0.08)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]"><Icon className="size-3.5" />{typeLabel(recommendation.recommendation_type)}</span>
                        <span className="shrink-0 rounded-full bg-[hsl(var(--surface-2))] px-2.5 py-1 text-xs font-bold">{formatScore(recommendation.score)}</span>
                      </div>
                      <h2 className="mt-3 break-words text-base font-bold">{recommendation.title}</h2>
                      <p className={clsx('mt-2 text-sm text-[hsl(var(--text-secondary))]', !expanded && 'line-clamp-3')}>{recommendation.reason}</p>
                      {expanded && recommendation.description && <p className="mt-2 break-words text-sm leading-relaxed">{recommendation.description}</p>}
                      <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))]"><CalendarDays className="size-3.5" />{formatDate(recommendation.created_at)}</p>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                      <DSButton variant="secondary" onClick={() => void handleView(recommendation)} loading={viewingId === recommendation.id} className="inline-flex items-center gap-2">{expanded ? 'Ocultar' : 'Ver'} <ArrowUpRight className="size-4" /></DSButton>
                      {expanded && recommendation.target_url && <a href={recommendation.target_url} className="inline-flex items-center gap-1 text-sm font-semibold text-[hsl(var(--primary))] hover:underline">Ir a sugerencia <ArrowUpRight className="size-3.5" /></a>}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

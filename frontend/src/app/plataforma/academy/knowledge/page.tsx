"use client";

import React, { useCallback, useEffect, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock,
  Layers,
  Network,
  Plus,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import NodeEvaluateDrawer from '@/components/academy/NodeEvaluateDrawer';
import NodeCreateDrawer from '@/components/academy/NodeCreateDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type {
  KnowledgeGraph,
  KnowledgeNode,
  LearningPath,
  StudentAcademicCommission,
  StudentNodeProgress,
} from '@/types/academy';

type StudentAcademicRecordPayload =
  | StudentAcademicCommission[]
  | { commissions?: unknown; offerings?: unknown; subjects?: unknown };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeCommissions(payload: StudentAcademicRecordPayload): StudentAcademicCommission[] {
  const candidates = Array.isArray(payload)
    ? payload
    : payload.commissions ?? payload.offerings ?? payload.subjects ?? [];
  if (!Array.isArray(candidates)) return [];

  return candidates.flatMap((candidate): StudentAcademicCommission[] => {
    if (!isRecord(candidate)) return [];
    const offeringId =
      typeof candidate.offering_id === 'string'
        ? candidate.offering_id
        : typeof candidate.id === 'string'
        ? candidate.id
        : null;
    const subjectName =
      typeof candidate.subject_name === 'string'
        ? candidate.subject_name
        : typeof candidate.name === 'string'
        ? candidate.name
        : null;
    if (!offeringId || !subjectName) return [];
    return [
      {
        offering_id: offeringId,
        subject_name: subjectName,
        subject_code: typeof candidate.subject_code === 'string' ? candidate.subject_code : null,
        period_code: typeof candidate.period_code === 'string' ? candidate.period_code : null,
        group_name: typeof candidate.group_name === 'string' ? candidate.group_name : null,
        credits: typeof candidate.credits === 'number' ? candidate.credits : undefined,
        status: typeof candidate.status === 'string' ? candidate.status : null,
      },
    ];
  });
}

export default function KnowledgeGraphPage() {
  const { token, isAuthenticated, user } = useAuth();
  const [commissions, setCommissions] = useState<StudentAcademicCommission[]>([]);
  const [selectedOffering, setSelectedOffering] = useState<StudentAcademicCommission | null>(null);

  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [progressList, setProgressList] = useState<StudentNodeProgress[]>([]);
  const [learningPath, setLearningPath] = useState<LearningPath | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [evaluatingNode, setEvaluatingNode] = useState<KnowledgeNode | null>(null);
  const [evaluatingProgress, setEvaluatingProgress] = useState<StudentNodeProgress | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const isEditor = Boolean(
    user?.role === 'admin' ||
    user?.role === 'superadmin' ||
    (user as { permissions?: string[] })?.permissions?.includes('academy:edit') ||
    (user as { permissions?: string[] })?.permissions?.includes('academy:manage')
  );

  const loadCommissions = useCallback(async (signal?: AbortSignal) => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await apiFetch<StudentAcademicRecordPayload>('/academy/student/academic-record', {
        token,
        cache: 'no-store',
        signal,
      });
      const list = normalizeCommissions(payload);
      setCommissions(list);
      if (list.length > 0 && !selectedOffering) {
        setSelectedOffering(list[0]);
      }
    } catch (err: unknown) {
      if (!signal?.aborted) {
        const msg = extractErrorMessage(err, 'No se pudo cargar el historial de materias');
        setError(msg);
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [selectedOffering, token]);

  const loadGraphData = useCallback(async (offeringId: string) => {
    if (!token) return;
    setLoadingGraph(true);
    try {
      const [gData, pData, lData] = await Promise.all([
        apiFetch<KnowledgeGraph>(`/academy/knowledge/${offeringId}/graph`, { token }),
        apiFetch<StudentNodeProgress[]>(`/academy/knowledge/${offeringId}/student-progress`, { token }),
        apiFetch<LearningPath>(`/academy/knowledge/${offeringId}/learning-path`, { token }),
      ]);
      setGraph(gData);
      setProgressList(pData);
      setLearningPath(lData);
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err, 'No pudimos cargar el grafo cognitivo'));
    } finally {
      setLoadingGraph(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const controller = new AbortController();
    void loadCommissions(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadCommissions]);

  useEffect(() => {
    if (selectedOffering?.offering_id) {
      void loadGraphData(selectedOffering.offering_id);
    }
  }, [loadGraphData, selectedOffering?.offering_id]);

  const handleEvaluate = (node: KnowledgeNode) => {
    const p = progressList.find((item) => item.node_id === node.id) || null;
    setEvaluatingNode(node);
    setEvaluatingProgress(p);
  };

  const getProgressForNode = (nodeId: string): StudentNodeProgress | null => {
    return progressList.find((p) => p.node_id === nodeId) || null;
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
              <Network className="size-6" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">
                Campus OS Cognitivo · Hito 2
              </p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">Grafo de Conocimiento y Prerequisitos</h1>
              <p className="mt-1 max-w-2xl text-sm text-[hsl(var(--text-secondary))]">
                Navega la estructura conceptual de tu materia y sigue la ruta óptima de aprendizaje.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isEditor && selectedOffering && (
              <DSButton onClick={() => setIsCreateOpen(true)} className="inline-flex items-center gap-2">
                <Plus className="size-4" /> Nuevo Nodo
              </DSButton>
            )}
            <DSButton
              variant="secondary"
              onClick={() => {
                if (selectedOffering) void loadGraphData(selectedOffering.offering_id);
              }}
              disabled={loadingGraph}
              className="inline-flex items-center gap-2"
            >
              <RefreshCw className={clsx('size-4', loadingGraph && 'animate-spin')} /> Actualizar
            </DSButton>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <div className="mx-auto w-full max-w-6xl space-y-6">
          {/* Selector de materias / comisiones */}
          {commissions.length > 1 && (
            <div className="flex flex-wrap items-center gap-2 border-b border-[hsl(var(--border))] pb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Materia activa:
              </span>
              {commissions.map((comm) => (
                <button
                  key={comm.offering_id}
                  type="button"
                  onClick={() => setSelectedOffering(comm)}
                  className={clsx(
                    'rounded-lg px-3 py-1.5 text-xs font-semibold transition',
                    selectedOffering?.offering_id === comm.offering_id
                      ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm'
                      : 'border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))]'
                  )}
                >
                  {comm.subject_name}
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <DSSkeleton className="h-64 rounded-xl" />
              <DSSkeleton className="h-64 rounded-xl" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--surface-2))] p-5 text-sm text-[hsl(var(--destructive))]">
              {error}
            </div>
          ) : !selectedOffering ? (
            <EmptyState
              title="No hay materias activas"
              description="Inscríbete en una materia para explorar su grafo conceptual y ruta de aprendizaje."
              icon={BookOpen}
            />
          ) : (
            <>
              {/* Resumen del Learning Path */}
              {learningPath && learningPath.path.length > 0 && (
                <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-5 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-4">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">
                        Ruta de Aprendizaje Óptima
                      </span>
                      <h2 className="mt-0.5 text-lg font-bold">
                        Dominio Global: {Math.round(learningPath.current_average_mastery * 100)}%
                      </h2>
                    </div>
                    {learningPath.suggested_next_node && (
                      <div className="inline-flex items-center gap-2 rounded-xl bg-[hsl(var(--primary)/0.1)] px-3 py-2 text-xs font-semibold text-[hsl(var(--primary))]">
                        <Sparkles className="size-4" />
                        Siguiente paso recomendado: {learningPath.suggested_next_node.title}
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-2 overflow-x-auto py-1">
                    {learningPath.path.map((step, idx) => (
                      <div key={step.node_id} className="flex items-center gap-2">
                        <div
                          className={clsx(
                            'flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-semibold',
                            step.status === 'mastered'
                              ? 'border-[hsl(var(--primary)/0.4)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                              : step.status === 'ready_to_learn'
                              ? 'border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] shadow-sm'
                              : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))]'
                          )}
                        >
                          <span className="grid size-5 place-items-center rounded-full bg-[hsl(var(--surface-2))] text-[10px]">
                            {idx + 1}
                          </span>
                          <span>{step.title}</span>
                          {step.status === 'mastered' && <CheckCircle2 className="size-3.5" />}
                        </div>
                        {idx < learningPath.path.length - 1 && (
                          <ArrowRight className="size-3.5 text-[hsl(var(--text-secondary))]" />
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Listado de Nodos del Grafo */}
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="size-5 text-[hsl(var(--primary))]" />
                    <h2 className="text-base font-semibold">Nodos de Conocimiento ({graph?.nodes.length ?? 0})</h2>
                  </div>
                  <span className="text-xs text-[hsl(var(--text-secondary))]">
                    Aristas / Prerrequisitos: {graph?.edges.length ?? 0}
                  </span>
                </div>

                {loadingGraph ? (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                      <DSSkeleton key={i} className="h-44 rounded-xl" />
                    ))}
                  </div>
                ) : !graph || graph.nodes.length === 0 ? (
                  <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-8 text-center text-sm text-[hsl(var(--text-secondary))]">
                    Aún no se han definido nodos de conocimiento para esta asignatura.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {graph.nodes.map((node) => {
                      const p = getProgressForNode(node.id);
                      const masteryPercent = p ? Math.round(p.mastery_score * 100) : 0;
                      return (
                        <article
                          key={node.id}
                          className="flex flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <span className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                                {node.node_type}
                              </span>
                              <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                                Peso: {node.weight}
                              </span>
                            </div>
                            <h3 className="mt-2 text-base font-semibold">{node.title}</h3>
                            {node.description && (
                              <p className="mt-1 line-clamp-2 text-xs text-[hsl(var(--text-secondary))]">
                                {node.description}
                              </p>
                            )}
                          </div>

                          <div className="mt-5 space-y-3">
                            <div>
                              <div className="mb-1 flex items-center justify-between text-xs">
                                <span className="text-[hsl(var(--text-secondary))]">Dominio:</span>
                                <span className="font-semibold text-[hsl(var(--text-primary))]">
                                  {masteryPercent}%
                                </span>
                              </div>
                              <div className="h-2 w-full overflow-hidden rounded-full bg-[hsl(var(--surface-2))]">
                                <div
                                  className="h-full bg-[hsl(var(--primary))] transition-all"
                                  style={{ width: `${masteryPercent}%` }}
                                />
                              </div>
                            </div>

                            <div className="flex items-center justify-between border-t border-[hsl(var(--border))] pt-3">
                              <span className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]">
                                <Clock className="size-3" /> {p?.attempts ?? 0} intentos
                              </span>
                              <DSButton
                                onClick={() => handleEvaluate(node)}
                                className="h-8 px-2.5 text-xs inline-flex items-center gap-1.5"
                              >
                                <Brain className="size-3.5" /> Evaluar
                              </DSButton>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </main>

      <NodeEvaluateDrawer
        open={Boolean(evaluatingNode)}
        onClose={() => setEvaluatingNode(null)}
        node={evaluatingNode}
        progress={evaluatingProgress}
        token={token}
        onSuccess={() => {
          if (selectedOffering) void loadGraphData(selectedOffering.offering_id);
        }}
      />

      <NodeCreateDrawer
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        offeringId={selectedOffering?.offering_id ?? null}
        token={token}
        onSuccess={() => {
          if (selectedOffering) void loadGraphData(selectedOffering.offering_id);
        }}
      />
    </div>
  );
}

"use client";

import React, { useCallback, useEffect, useState } from 'react';
import {
  BookOpen,
  Brain,
  Clock,
  Layers,
  Network,
  Plus,
  RefreshCw,
  Route,
} from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import dynamic from 'next/dynamic';

// Drawers cargados bajo demanda: reducen el JS del bundle inicial.
const NodeCreateDrawer = dynamic(() => import('@/components/academy/NodeCreateDrawer'), { ssr: false });
const LearningPathDrawer = dynamic(() => import('@/components/academy/LearningPathDrawer'), { ssr: false });
const SocraticChatDrawer = dynamic(() => import('@/components/academy/SocraticChatDrawer'), { ssr: false });
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
  const [loadingPath, setLoadingPath] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [evaluatingNode, setEvaluatingNode] = useState<KnowledgeNode | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isLearningPathOpen, setIsLearningPathOpen] = useState(false);

  const isEditor = Boolean(
    user?.role === 'admin' ||
    user?.role === 'superadmin' ||
    (user as { permissions?: string[] })?.permissions?.includes('academy:edit') ||
    (user as { permissions?: string[] })?.permissions?.includes('academy:manage')
  );

  const loadCommissions = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Use the canonical self-service transcript endpoint currently exposed by the backend.
      const payload = await apiFetch<StudentAcademicRecordPayload>('/academy/me/academic-record', {
        token,
        cache: 'no-store',
        signal,
      });
      const list = normalizeCommissions(payload);
      setCommissions(list);
      setSelectedOffering((current) => list.find((item) => item.offering_id === current?.offering_id) ?? list[0] ?? null);
    } catch (err: unknown) {
      if (!signal?.aborted) {
        const msg = extractErrorMessage(err, 'No se pudo cargar el historial de materias');
        setError(msg);
        toast.error(msg);
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [token]);

  const loadGraphData = useCallback(async (offeringId: string) => {
    if (!token) return;
    setLoadingGraph(true);
    setGraph(null);
    setProgressList([]);
    try {
      const [gData, pData] = await Promise.all([
        apiFetch<KnowledgeGraph>(`/academy/knowledge/${offeringId}/graph`, { token }),
        apiFetch<StudentNodeProgress[]>(`/academy/knowledge/${offeringId}/student-progress`, { token }),
      ]);
      setGraph(gData);
      setProgressList(pData);
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err, 'No pudimos cargar el grafo cognitivo'));
    } finally {
      setLoadingGraph(false);
    }
  }, [token]);

  const loadLearningPath = useCallback(async () => {
    if (!token || !selectedOffering) return;
    setLoadingPath(true);
    try {
      const path = await apiFetch<LearningPath>(
        `/academy/knowledge/${selectedOffering.offering_id}/learning-path`,
        { token, cache: 'no-store' },
      );
      setLearningPath(path);
      setIsLearningPathOpen(true);
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err, 'No pudimos calcular el camino óptimo'));
    } finally {
      setLoadingPath(false);
    }
  }, [selectedOffering, token]);

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
    setEvaluatingNode(node);
  };

  const evaluateNodeAnswer = useCallback(async (responseText: string) => {
    if (!token || !evaluatingNode) return;
    await apiFetch(`/academy/knowledge/nodes/${evaluatingNode.id}/evaluate`, {
      method: 'POST',
      token,
      body: { response_text: responseText },
    });
    toast.success('Dominio del nodo actualizado');
    if (selectedOffering) await loadGraphData(selectedOffering.offering_id);
  }, [evaluatingNode, loadGraphData, selectedOffering, token]);

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
            <DSButton
              variant="secondary"
              onClick={() => void loadLearningPath()}
              disabled={!selectedOffering || loadingPath}
              className="inline-flex items-center gap-2"
            >
              <Route className={clsx('size-4', loadingPath && 'animate-pulse')} />
              {loadingPath ? 'Calculando camino…' : 'Ver Camino Óptimo'}
            </DSButton>
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
              title="No hay comisiones disponibles"
              description="Cuando tengas una comisión activa, aquí podrás explorar su grafo conceptual y ruta de aprendizaje."
              icon={BookOpen}
            />
          ) : (
            <>
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
                  <EmptyState
                    title="Aún no hay nodos de conocimiento"
                    description="Todavía no se han definido conceptos o competencias para esta comisión."
                    icon={Layers}
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {graph.nodes.map((node) => {
                      const p = getProgressForNode(node.id);
                      const masteryScore = p?.mastery_score ?? 0;
                      const masteryPercent = Math.round(Math.min(1, Math.max(0, masteryScore)) * 100);
                      const masteryStatus = masteryScore >= 0.7
                        ? { label: 'Dominado', icon: '✅', className: 'text-[hsl(var(--primary))]' }
                        : masteryScore >= 0.3
                          ? { label: 'En progreso', icon: '⚠️', className: 'text-[hsl(var(--text-secondary))]' }
                          : { label: 'Pendiente', icon: '🔴', className: 'text-[hsl(var(--destructive))]' };
                      return (
                        <article
                          key={node.id}
                          className="flex flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm"
                        >
                          <div>
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="rounded-md bg-[hsl(var(--surface-2))] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                                {node.node_type}
                              </span>
                              <span className={clsx('inline-flex items-center gap-1 text-[11px] font-semibold', masteryStatus.className)}>
                                <span aria-hidden="true">{masteryStatus.icon}</span>{masteryStatus.label}
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
                                <Clock className="size-3" /> {p?.attempts ?? 0} intentos · Peso {node.weight}
                              </span>
                              <DSButton
                                onClick={() => handleEvaluate(node)}
                                className="h-8 px-2.5 text-xs inline-flex items-center gap-1.5"
                              >
                                <Brain className="size-3.5" /> Evaluar Dominio
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

      <SocraticChatDrawer
        open={Boolean(evaluatingNode)}
        onClose={() => setEvaluatingNode(null)}
        offering={selectedOffering}
        token={token}
        contextOverride={evaluatingNode ? `${selectedOffering?.subject_name ?? 'Comisión'} · ${evaluatingNode.title}` : undefined}
        evaluationMode
        onQuestionSubmitted={evaluateNodeAnswer}
      />

      <LearningPathDrawer
        open={isLearningPathOpen}
        onClose={() => setIsLearningPathOpen(false)}
        learningPath={learningPath}
        offeringName={selectedOffering?.subject_name}
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

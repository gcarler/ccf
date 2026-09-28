"use client";

import React, { useMemo } from 'react';
import { ArrowDown, CheckCircle2, Circle, LockKeyhole, Route } from 'lucide-react';
import clsx from 'clsx';
import { DSButton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import { RightPanel } from '@/components/ui/RightPanel';
import type { LearningPath } from '@/types/academy';

interface LearningPathDrawerProps {
  open: boolean;
  onClose: () => void;
  learningPath: LearningPath | null;
  offeringName?: string;
}

export default function LearningPathDrawer({ open, onClose, learningPath, offeringName }: LearningPathDrawerProps) {
  const orderedNodes = useMemo(
    () => [...(learningPath?.path ?? [])].sort((left, right) => left.order_index - right.order_index),
    [learningPath],
  );

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><Route className="size-4 text-[hsl(var(--primary))]" /> Camino Óptimo de Aprendizaje</span>}
      subtitle={offeringName || 'Nodos ordenados por prerequisitos y dominio'}
      width="w-full sm:max-w-xl"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        {learningPath ? (
          <>
            <div className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Dominio promedio actual</p>
              <p className="mt-1 text-2xl font-bold text-[hsl(var(--primary))]">{Math.round(learningPath.current_average_mastery * 100)}%</p>
            </div>
            {orderedNodes.length > 0 ? (
              <ol className="flex-1 space-y-3 overflow-y-auto p-4">
                {orderedNodes.map((node, index) => {
                const mastered = node.status === 'mastered' || node.mastery_score >= 0.7;
                const blocked = node.status === 'needs_prerequisites';
                return (
                  <li key={node.node_id} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className={clsx(
                        'grid size-8 shrink-0 place-items-center rounded-full border',
                        mastered
                          ? 'border-[hsl(var(--primary)/0.4)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]'
                          : blocked
                            ? 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                            : 'border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))]',
                      )}>
                        {mastered ? <CheckCircle2 className="size-4" /> : blocked ? <LockKeyhole className="size-4" /> : <Circle className="size-4" />}
                      </span>
                      {index < orderedNodes.length - 1 && <ArrowDown className="my-1 size-4 text-[hsl(var(--text-secondary))]" aria-hidden="true" />}
                    </div>
                    <div className="min-w-0 flex-1 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Paso {index + 1} · {node.node_type}</span>
                        <span className="text-xs font-semibold text-[hsl(var(--primary))]">{Math.round(node.mastery_score * 100)}% dominio</span>
                      </div>
                      <h3 className="mt-1 break-words text-sm font-semibold">{node.title}</h3>
                      <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                        {mastered ? 'Dominado' : blocked ? 'Completa primero sus prerequisitos' : 'Listo para estudiar'}
                      </p>
                    </div>
                  </li>
                );
                })}
              </ol>
            ) : (
              <div className="flex flex-1 items-center justify-center p-6">
                <EmptyState title="Camino sin pasos" description="No hay nodos definidos para construir una ruta de aprendizaje." icon={Route} />
              </div>
            )}
            {learningPath.suggested_next_node && (
              <div className="border-t border-[hsl(var(--border))] p-4 text-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Siguiente paso sugerido</p>
                <p className="mt-1 font-semibold">{learningPath.suggested_next_node.title}</p>
              </div>
            )}
            <div className="flex justify-end border-t border-[hsl(var(--border))] p-4">
              <DSButton variant="secondary" onClick={onClose}>Cerrar</DSButton>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center p-6">
            <EmptyState title="Camino no disponible" description="Selecciona una comisión y solicita el camino óptimo de aprendizaje." icon={Route} />
          </div>
        )}
      </div>
    </RightPanel>
  );
}

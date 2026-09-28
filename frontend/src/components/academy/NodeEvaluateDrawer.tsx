"use client";

import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { Award, Brain, CheckCircle2, Loader2, Send, Sparkles } from 'lucide-react';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { KnowledgeNode, StudentNodeProgress } from '@/types/academy';

interface NodeEvaluateDrawerProps {
  open: boolean;
  onClose: () => void;
  node: KnowledgeNode | null;
  progress: StudentNodeProgress | null;
  token: string | null;
  onSuccess?: () => void;
}

interface NodeEvaluateResponse {
  node_id: string;
  student_id: string;
  mastery_score: number;
  attempts: number;
  feedback: string;
  last_evaluated_at: string;
}

export default function NodeEvaluateDrawer({
  open,
  onClose,
  node,
  progress,
  token,
  onSuccess,
}: NodeEvaluateDrawerProps) {
  const [responseHtml, setResponseHtml] = useState('');
  const [masteryInput, setMasteryInput] = useState<number | ''>('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<NodeEvaluateResponse | null>(null);

  useEffect(() => {
    if (open) {
      setResponseHtml('');
      setMasteryInput('');
      setResult(null);
    }
  }, [open, node?.id]);

  const handleSubmit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!node || !token || submitting) return;

    setSubmitting(true);
    try {
      const body: Record<string, unknown> = {};
      if (responseHtml.trim()) {
        body.response_text = responseHtml.trim();
      }
      if (typeof masteryInput === 'number') {
        body.mastery_score = masteryInput / 100;
      }

      const res = await apiFetch<NodeEvaluateResponse>(
        `/academy/knowledge/nodes/${node.id}/evaluate`,
        { method: 'POST', token, body },
      );
      setResult(res);
      toast.success('Evaluación de dominio registrada');
      onSuccess?.();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos registrar tu evaluación'));
    } finally {
      setSubmitting(false);
    }
  }, [masteryInput, node, onSuccess, responseHtml, submitting, token]);

  const currentMasteryPercent = progress ? Math.round(progress.mastery_score * 100) : 0;

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Brain className="size-4 text-[hsl(var(--primary))]" />
          Evaluación de Dominio
        </span>
      }
      subtitle={node?.title || 'Nodo de conocimiento'}
      width="w-full sm:max-w-xl"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
          {node ? (
            <>
              <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex rounded-full bg-[hsl(var(--primary)/0.12)] px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">
                    {node.node_type}
                  </span>
                  <span className="text-xs text-[hsl(var(--text-secondary))]">
                    Peso: {node.weight}
                  </span>
                </div>
                <h3 className="mt-2 text-base font-semibold">{node.title}</h3>
                {node.description && (
                  <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">
                    {node.description}
                  </p>
                )}
                <div className="mt-4 flex items-center justify-between border-t border-[hsl(var(--border))] pt-3 text-xs">
                  <span className="text-[hsl(var(--text-secondary))]">Dominio actual:</span>
                  <span className="font-semibold text-[hsl(var(--text-primary))]">
                    {currentMasteryPercent}% ({progress?.attempts ?? 0} intentos)
                  </span>
                </div>
              </section>

              {result ? (
                <section className="rounded-xl border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.05)] p-5 text-center">
                  <div className="mx-auto grid size-12 place-items-center rounded-full bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
                    <CheckCircle2 className="size-6" />
                  </div>
                  <h4 className="mt-2 text-lg font-bold">
                    Dominio: {Math.round(result.mastery_score * 100)}%
                  </h4>
                  <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">
                    {result.feedback}
                  </p>
                  <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">
                    Intentos acumulados: {result.attempts}
                  </p>
                  <DSButton
                    variant="secondary"
                    className="mt-4"
                    onClick={() => {
                      setResult(null);
                      setResponseHtml('');
                    }}
                  >
                    Evaluar nuevamente
                  </DSButton>
                </section>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <label
                      htmlFor="node-argumentation"
                      className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
                    >
                      Fundamentación o Respuesta Conceptual
                    </label>
                    <textarea
                      id="node-argumentation"
                      rows={5}
                      value={responseHtml}
                      onChange={(e) => setResponseHtml(e.target.value)}
                      placeholder="Explica en tus propias palabras los principios y aplicaciones prácticas de este concepto..."
                      className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
                      disabled={submitting}
                    />
                  </div>

                  <div className="space-y-2">
                    <label
                      htmlFor="node-mastery-slider"
                      className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
                    >
                      Autoevaluación Cuantitativa (Opcional, 0 - 100%)
                    </label>
                    <input
                      id="node-mastery-slider"
                      type="number"
                      min={0}
                      max={100}
                      value={masteryInput}
                      onChange={(e) => setMasteryInput(e.target.value ? Number(e.target.value) : '')}
                      placeholder="Ej. 85"
                      className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
                      disabled={submitting}
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <DSButton variant="secondary" type="button" onClick={onClose} disabled={submitting}>
                      Cancelar
                    </DSButton>
                    <DSButton
                      type="submit"
                      disabled={submitting || (!responseHtml.trim() && masteryInput === '')}
                      className="inline-flex items-center gap-2"
                    >
                      {submitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                      Registrar Evaluación
                    </DSButton>
                  </div>
                </form>
              )}
            </>
          ) : (
            <DSSkeleton className="h-40 w-full rounded-xl" />
          )}
        </div>
      </div>
    </RightPanel>
  );
}

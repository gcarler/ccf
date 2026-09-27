"use client";

import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Award, Clock3, Loader2, Send, ShieldCheck } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { DefenseAnswer, DefenseScore, DefenseSession, StudentAcademicCommission } from '@/types/academy';

interface SocraticDefenseDrawerProps {
  open: boolean;
  onClose: () => void;
  offering: StudentAcademicCommission | null;
  token: string | null;
}

function formatTime(seconds: number) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
  const remainder = (seconds % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
}

export default function SocraticDefenseDrawer({ open, onClose, offering, token }: SocraticDefenseDrawerProps) {
  const [session, setSession] = useState<DefenseSession | null>(null);
  const [score, setScore] = useState<DefenseScore | null>(null);
  const [answer, setAnswer] = useState('');
  const [remaining, setRemaining] = useState(300);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [closing, setClosing] = useState(false);
  const [lastAnswer, setLastAnswer] = useState<DefenseAnswer | null>(null);
  const closeRequestRef = useRef(false);

  useEffect(() => {
    if (!open || !offering || !token) return;
    const controller = new AbortController();
    setLoading(true);
    setSession(null);
    setScore(null);
    setAnswer('');
    setLastAnswer(null);
    setRemaining(300);
    closeRequestRef.current = false;

    apiFetch<DefenseSession>(`/academy/defense/${offering.offering_id}/start`, {
      method: 'POST',
      token,
      body: {},
      signal: controller.signal,
    }).then((data) => {
      setSession(data);
      setRemaining(Math.max(0, data.time_remaining_seconds ?? data.duration_seconds ?? 300));
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) toast.error(extractErrorMessage(error, 'No pudimos iniciar la defensa'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });

    return () => controller.abort();
  }, [open, offering, token]);

  const closeDefense = useCallback(async () => {
    if (!session || !token || closeRequestRef.current || score) return;
    closeRequestRef.current = true;
    setClosing(true);
    try {
      const result = await apiFetch<DefenseScore>(`/academy/defense/${session.id}/close`, { method: 'POST', token });
      setScore(result);
      setSession((current) => current ? { ...current, status: result.status, score: result.score, ended_at: result.ended_at } : current);
    } catch (error: unknown) {
      closeRequestRef.current = false;
      toast.error(extractErrorMessage(error, 'No pudimos cerrar la defensa'));
    } finally {
      setClosing(false);
    }
  }, [score, session, token]);

  const handleDrawerClose = useCallback(async () => {
    if (session?.status === 'active' && !score) await closeDefense();
    onClose();
  }, [closeDefense, onClose, score, session?.status]);

  useEffect(() => {
    if (!open || !session || score || session.status !== 'active') return undefined;
    if (remaining <= 0) {
      void closeDefense();
      return undefined;
    }
    const interval = window.setInterval(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(interval);
  }, [closeDefense, open, remaining, score, session]);

  const handleAnswer = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || !token || !answer.trim() || sending || session.status !== 'active') return;
    setSending(true);
    try {
      const result = await apiFetch<DefenseAnswer>(`/academy/defense/${session.id}/answer`, {
        method: 'POST', token, body: { answer: answer.trim() },
      });
      setLastAnswer(result);
      setAnswer('');
      setSession((current) => current ? {
        ...current,
        status: result.status,
        current_question_index: result.current_question_index,
        current_question: result.next_question ?? null,
        score: result.score ?? current.score,
      } : current);
      if (result.is_completed) await closeDefense();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos guardar tu respuesta'));
    } finally {
      setSending(false);
    }
  }, [answer, closeDefense, sending, session, token]);

  return (
    <RightPanel
      open={open}
      onClose={() => { void handleDrawerClose(); }}
      title={<span className="flex items-center gap-2"><ShieldCheck className="size-4 text-[hsl(var(--primary))]" /> Defensa interactiva</span>}
      subtitle={offering ? `${offering.subject_name}${offering.group_name ? ` · ${offering.group_name}` : ''}` : 'Defiende tu comprensión del tema'}
      width="w-full sm:max-w-2xl"
      contentClassName="min-h-0"
    >
      <div className="flex h-full min-h-0 flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        {loading ? (
          <div className="space-y-4 p-4" aria-label="Iniciando defensa"><DSSkeleton className="h-8 w-36 rounded-lg" /><DSSkeleton className="h-28 w-full rounded-xl" /><DSSkeleton className="h-24 w-full rounded-xl" /></div>
        ) : score ? (
          <section className="flex flex-1 flex-col items-center justify-center gap-4 overflow-y-auto p-6 text-center" aria-live="polite">
            <div className="grid size-16 place-items-center rounded-full bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><Award className="size-8" /></div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Defensa finalizada</p>
              <h2 className="mt-1 text-3xl font-bold">{score.score.toFixed(1)}<span className="text-base font-medium text-[hsl(var(--text-secondary))"> / 100</span></h2>
            </div>
            <p className="max-w-lg whitespace-pre-wrap text-sm leading-relaxed text-[hsl(var(--text-secondary))]">{score.feedback}</p>
            <DSButton variant="secondary" onClick={onClose}>Cerrar</DSButton>
          </section>
        ) : session ? (
          <>
            <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] px-4 py-3">
              <span className="text-sm text-[hsl(var(--text-secondary))]">Pregunta {Math.min(session.current_question_index + 1, session.total_questions)} de {session.total_questions}</span>
              <span className={clsx('inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-sm font-semibold', remaining <= 60 ? 'border-[hsl(var(--destructive))] text-[hsl(var(--destructive))]' : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]')} aria-live="polite" aria-label={`Tiempo restante ${formatTime(remaining)}`}>
                <Clock3 className="size-4" /> {formatTime(remaining)}
              </span>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-4">
              {session.current_question ? (
                <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-5">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Pregunta socrática</p>
                  <h2 className="whitespace-pre-wrap text-lg font-semibold leading-relaxed">{session.current_question}</h2>
                </section>
              ) : (
                <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-5 text-sm text-[hsl(var(--text-secondary))]">
                  No hay más preguntas pendientes. Finaliza la defensa para ver tu resultado.
                </section>
              )}
              {lastAnswer?.feedback && <p className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-sm text-[hsl(var(--text-secondary))]">{lastAnswer.feedback}</p>}
            </div>
            <form onSubmit={handleAnswer} className="space-y-3 border-t border-[hsl(var(--border))] p-4">
              <label htmlFor="defense-answer" className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tu respuesta</label>
              <textarea
                id="defense-answer"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                rows={4}
                maxLength={4000}
                placeholder="Explica tu razonamiento…"
                className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
                disabled={sending || closing || session.status !== 'active' || remaining <= 0 || !session.current_question}
              />
              <div className="flex flex-wrap justify-end gap-2">
                {session.status === 'active' && <DSButton type="button" variant="secondary" onClick={() => void closeDefense()} disabled={sending || closing} loading={closing}>Terminar defensa</DSButton>}
                <DSButton type="submit" className="inline-flex items-center gap-2" disabled={sending || closing || !answer.trim() || !session.current_question || remaining <= 0} loading={sending}>
                  {sending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />} Enviar respuesta
                </DSButton>
              </div>
            </form>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center text-sm text-[hsl(var(--text-secondary))]">
            <ShieldCheck className="size-8 text-[hsl(var(--primary))]" />
            <p>No fue posible iniciar la defensa. Cierra y vuelve a intentarlo.</p>
          </div>
        )}
      </div>
    </RightPanel>
  );
}

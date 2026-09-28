"use client";

import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Brain, Loader2, MessageCircle, Send } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { SocraticQueryResponse, StudentAcademicCommission } from '@/types/academy';

interface SocraticChatDrawerProps {
  open: boolean;
  onClose: () => void;
  offering: StudentAcademicCommission | null;
  token: string | null;
  contextOverride?: string;
  evaluationMode?: boolean;
  onQuestionSubmitted?: (studentText: string) => Promise<void>;
}

export default function SocraticChatDrawer({
  open,
  onClose,
  offering,
  token,
  contextOverride,
  evaluationMode = false,
  onQuestionSubmitted,
}: SocraticChatDrawerProps) {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<SocraticQueryResponse[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQuestion('');
      setMessages([]);
      setLoading(true);
      const timeout = window.setTimeout(() => setLoading(false), 180);
      return () => window.clearTimeout(timeout);
    }
    return undefined;
  }, [open, offering?.offering_id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !offering || !token || sending) return;

    setSending(true);
    try {
      const response = await apiFetch<SocraticQueryResponse>(
        `/academy/socratic/${offering.offering_id}/query`,
        { method: 'POST', token, body: { question: trimmedQuestion, context: contextOverride ?? offering.subject_name } },
      );
      setMessages((current) => [...current, response]);
      setQuestion('');
      if (onQuestionSubmitted) {
        try {
          await onQuestionSubmitted(trimmedQuestion);
        } catch (evaluationError: unknown) {
          toast.error(extractErrorMessage(evaluationError, 'No pudimos actualizar tu dominio en este nodo'));
        }
      }
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos enviar tu pregunta al tutor'));
    } finally {
      setSending(false);
    }
  }, [contextOverride, offering, onQuestionSubmitted, question, sending, token]);

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><Brain className="size-4 text-[hsl(var(--primary))]" /> {evaluationMode ? 'Evaluación Socrática de Dominio' : 'Tutor Socrático'}</span>}
      subtitle={contextOverride || (offering ? `${offering.subject_name}${offering.period_code ? ` · ${offering.period_code}` : ''}` : 'Acompañamiento para pensar y aprender')}
      width="w-full sm:max-w-2xl"
      contentClassName="min-h-0"
    >
      <div className="flex h-full min-h-0 flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="border-b border-[hsl(var(--border))] px-4 py-3 text-sm text-[hsl(var(--text-secondary))]">
          {evaluationMode
            ? 'Explica con tus palabras el concepto. Tu respuesta actualizará el dominio y el tutor te ayudará a profundizar.'
            : 'El tutor te guiará con preguntas para que construyas tu propia respuesta.'}
        </div>
        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite" aria-label="Conversación con el tutor">
          {loading ? (
            <div className="space-y-3" aria-label="Preparando conversación">
              <DSSkeleton className="h-20 w-4/5 rounded-xl" />
              <DSSkeleton className="ml-auto h-14 w-3/5 rounded-xl" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full min-h-48 flex-col items-center justify-center gap-3 text-center text-[hsl(var(--text-secondary))]">
              <div className="grid size-12 place-items-center rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))]">
                <MessageCircle className="size-6" />
              </div>
              <div>
                <p className="font-semibold text-[hsl(var(--text-primary))]">¿Qué tema quieres comprender?</p>
                <p className="mt-1 max-w-sm text-sm">Escribe una pregunta y exploraremos juntos distintas formas de razonarla.</p>
              </div>
            </div>
          ) : messages.map((message) => (
            <article key={message.session_id} className="space-y-2">
              <div className="ml-auto max-w-[90%] whitespace-pre-wrap break-words rounded-2xl rounded-br-sm bg-[hsl(var(--primary))] px-4 py-3 text-sm text-[hsl(var(--primary-foreground))]">
                {message.question}
              </div>
              <div className={clsx('max-w-[95%] whitespace-pre-wrap break-words rounded-2xl rounded-bl-sm border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-4 py-3 text-sm')}>
                <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-[hsl(var(--primary))]"><Brain className="size-3.5" /> Tutor</p>
                {message.socratic_response}
              </div>
            </article>
          ))}
          {sending && <div className="flex items-center gap-2 text-sm text-[hsl(var(--text-secondary))]" role="status"><Loader2 className="size-4 animate-spin" /> El tutor está pensando…</div>}
        </div>
        <form onSubmit={handleSubmit} className="flex shrink-0 items-end gap-2 border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3">
          <label className="sr-only" htmlFor="socratic-question">Escribe tu pregunta</label>
          <textarea
            id="socratic-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            rows={2}
            maxLength={2000}
            placeholder={evaluationMode ? 'Explica el concepto y cómo lo aplicarías…' : 'Escribe tu pregunta…'}
            className="min-h-11 flex-1 resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
            disabled={sending || !offering}
          />
          <DSButton type="submit" className="inline-flex h-11 items-center gap-2" disabled={sending || !question.trim() || !offering || !token} aria-label="Enviar pregunta">
            {sending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            <span className="hidden sm:inline">Enviar</span>
          </DSButton>
        </form>
      </div>
    </RightPanel>
  );
}

"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { Award, BookOpen, Brain, RefreshCw, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import SocraticChatDrawer from '@/components/academy/SocraticChatDrawer';
import SocraticDefenseDrawer from '@/components/academy/SocraticDefenseDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { StudentAcademicCommission } from '@/types/academy';

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
    const offeringId = typeof candidate.offering_id === 'string'
      ? candidate.offering_id
      : typeof candidate.id === 'string' ? candidate.id : null;
    const subjectName = typeof candidate.subject_name === 'string'
      ? candidate.subject_name
      : typeof candidate.name === 'string' ? candidate.name : null;
    if (!offeringId || !subjectName) return [];
    return [{
      offering_id: offeringId,
      subject_name: subjectName,
      subject_code: typeof candidate.subject_code === 'string' ? candidate.subject_code : null,
      period_code: typeof candidate.period_code === 'string' ? candidate.period_code : null,
      group_name: typeof candidate.group_name === 'string' ? candidate.group_name : null,
      credits: typeof candidate.credits === 'number' ? candidate.credits : undefined,
      status: typeof candidate.status === 'string' ? candidate.status : null,
    }];
  });
}

export default function SocraticTutorPage() {
  const { token, isAuthenticated } = useAuth();
  const [commissions, setCommissions] = useState<StudentAcademicCommission[]>([]);
  const [selectedCommission, setSelectedCommission] = useState<StudentAcademicCommission | null>(null);
  const [activeDrawer, setActiveDrawer] = useState<'chat' | 'defense' | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAcademicRecord = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = await apiFetch<StudentAcademicRecordPayload>('/academy/me/academic-record', {
        token,
        cache: 'no-store',
        signal,
      });
      setCommissions(normalizeCommissions(payload));
    } catch (requestError: unknown) {
      if (signal?.aborted) return;
      const message = extractErrorMessage(requestError, 'No pudimos cargar tu historial académico');
      setError(message);
      toast.error(message);
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    const controller = new AbortController();
    void loadAcademicRecord(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadAcademicRecord]);

  const openDrawer = (commission: StudentAcademicCommission, drawer: 'chat' | 'defense') => {
    setSelectedCommission(commission);
    setActiveDrawer(drawer);
  };

  const closeDrawer = () => setActiveDrawer(null);

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><Brain className="size-6" /></div>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Academia · aprendizaje activo</p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">Tutor Socrático y Defensas</h1>
              <p className="mt-1 max-w-2xl text-sm text-[hsl(var(--text-secondary))]">Explora tus materias con preguntas guía y practica la defensa de tus ideas.</p>
            </div>
          </div>
          <DSButton variant="secondary" onClick={() => void loadAcademicRecord()} disabled={loading} className="inline-flex items-center gap-2">
            <RefreshCw className={clsx('size-4', loading && 'animate-spin')} /> Actualizar
          </DSButton>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <section className="mx-auto w-full max-w-6xl" aria-labelledby="academic-commissions-heading">
          <div className="mb-4 flex items-center gap-2">
            <BookOpen className="size-5 text-[hsl(var(--primary))]" />
            <h2 id="academic-commissions-heading" className="text-base font-semibold">Mi historial académico</h2>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="Cargando comisiones">
              {[1, 2, 3].map((item) => <DSSkeleton key={item} className="h-48 rounded-xl" />)}
            </div>
          ) : error ? (
            <div className="rounded-xl border border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--surface-2))] p-5">
              <p className="text-sm text-[hsl(var(--destructive))]">{error}</p>
              <DSButton variant="secondary" onClick={() => void loadAcademicRecord()} className="mt-3">Reintentar</DSButton>
            </div>
          ) : commissions.length === 0 ? (
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-8">
              <EmptyState
                title="Aún no tienes comisiones disponibles"
                description="Cuando tengas materias inscritas, aparecerán aquí para que puedas estudiar con el tutor y practicar una defensa."
                icon={BookOpen}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {commissions.map((commission) => (
                <article key={commission.offering_id} className="flex min-w-0 flex-col rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))]"><BookOpen className="size-5" /></span>
                    <div className="min-w-0 flex-1">
                      <h3 className="break-words font-semibold">{commission.subject_name}</h3>
                      <p className="mt-1 break-words text-xs text-[hsl(var(--text-secondary))]">
                        {[commission.subject_code, commission.period_code, commission.group_name].filter(Boolean).join(' · ') || 'Comisión académica'}
                      </p>
                    </div>
                  </div>
                  {typeof commission.credits === 'number' && <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">{commission.credits} créditos</p>}
                  <div className="mt-auto flex flex-wrap gap-2 pt-5">
                    <DSButton onClick={() => openDrawer(commission, 'chat')} className="inline-flex items-center gap-2"><Sparkles className="size-4" /> Estudiar</DSButton>
                    <DSButton variant="secondary" onClick={() => openDrawer(commission, 'defense')} className="inline-flex items-center gap-2"><Award className="size-4" /> Defender trabajo</DSButton>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      <SocraticChatDrawer
        open={activeDrawer === 'chat'}
        onClose={closeDrawer}
        offering={selectedCommission}
        token={token}
      />
      <SocraticDefenseDrawer
        open={activeDrawer === 'defense'}
        onClose={closeDrawer}
        offering={selectedCommission}
        token={token}
      />
    </div>
  );
}

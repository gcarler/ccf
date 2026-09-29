"use client";

import React, { useEffect, useState } from 'react';
import { Award, CheckCircle2, Copy, Fingerprint, ShieldCheck, XCircle } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { AchievementCredentialVerification, StudentAchievement } from '@/types/academy';

interface AchievementVerifyDrawerProps {
  open: boolean;
  onClose: () => void;
  award: StudentAchievement | null;
  token: string | null;
}

export default function AchievementVerifyDrawer({ open, onClose, award, token }: AchievementVerifyDrawerProps) {
  const [verification, setVerification] = useState<AchievementCredentialVerification | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !award) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setVerification(null);

    apiFetch<AchievementCredentialVerification>(
      `/academy/achievements/${award.student_id}/credential/${award.achievement_id}/verify`,
      { token, cache: 'no-store', signal: controller.signal },
    ).then((result) => {
      setVerification(result);
    }).catch((requestError: unknown) => {
      if (!controller.signal.aborted) {
        const message = extractErrorMessage(requestError, 'No pudimos verificar esta credencial');
        setError(message);
        toast.error(message);
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });

    return () => controller.abort();
  }, [award, open, token]);

  const copyHash = async () => {
    if (!verification?.credential_hash) return;
    try {
      await navigator.clipboard.writeText(verification.credential_hash);
      toast.success('Hash de credencial copiado');
    } catch {
      toast.error('No se pudo copiar el hash');
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><ShieldCheck className="size-4 text-[hsl(var(--primary))]" /> Verificación de credencial</span>}
      subtitle={award?.achievement?.title ?? 'Credencial de logro'}
      width="w-full sm:max-w-xl"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {loading ? (
            <div className="space-y-3" aria-label="Verificando credencial">
              <DSSkeleton className="h-28 rounded-xl" />
              <DSSkeleton className="h-20 rounded-xl" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--surface-2))] p-4 text-sm text-[hsl(var(--destructive))]">{error}</div>
          ) : verification ? (
            <>
              <section className={clsx(
                'rounded-2xl border p-5 text-center',
                verification.is_valid
                  ? 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))]'
                  : 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)]',
              )}>
                <div className={clsx(
                  'mx-auto grid size-14 place-items-center rounded-full',
                  verification.is_valid
                    ? 'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]'
                    : 'bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))]',
                )}>
                  {verification.is_valid ? <CheckCircle2 className="size-8" /> : <XCircle className="size-8" />}
                </div>
                <h2 className="mt-3 text-lg font-bold">{verification.is_valid ? 'Credencial verificada' : 'Verificación no válida'}</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">
                  {verification.is_valid ? 'La credencial corresponde a un logro emitido por la plataforma.' : 'No fue posible validar la integridad de esta credencial.'}
                </p>
              </section>

              <section className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                <Detail label="Estudiante" value={verification.student_name} />
                <Detail label="Logro" value={verification.achievement_title} />
                <Detail label="Puntos" value={String(verification.points)} />
                <Detail label="Fecha de obtención" value={new Date(verification.earned_at).toLocaleString('es')} />
              </section>

              <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"><Fingerprint className="size-4" /> Huella SHA-256</span>
                  <button type="button" onClick={() => void copyHash()} className="inline-flex items-center gap-1 text-xs font-semibold text-[hsl(var(--primary))] hover:underline">
                    <Copy className="size-3.5" /> Copiar
                  </button>
                </div>
                <p className="mt-2 break-all rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 font-mono text-xs">{verification.credential_hash}</p>
              </section>
            </>
          ) : (
            <EmptyState title="Credencial no disponible" description="Selecciona un logro obtenido para verificar su credencial." icon={Award} />
          )}
        </div>
        <div className="flex justify-end border-t border-[hsl(var(--border))] p-4">
          <DSButton variant="secondary" onClick={onClose}>Cerrar</DSButton>
        </div>
      </div>
    </RightPanel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[hsl(var(--border))] pb-2 last:border-0 last:pb-0">
      <span className="text-xs text-[hsl(var(--text-secondary))]">{label}</span>
      <span className="break-words text-right text-sm font-medium">{value}</span>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from 'react';
import { CheckCircle2, Copy, ShieldCheck, XCircle } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { CredentialVerification, PortfolioEntry } from '@/types/academy';

interface PortfolioVerifyDrawerProps {
  open: boolean;
  onClose: () => void;
  entry: PortfolioEntry | null;
  token: string | null;
}

export default function PortfolioVerifyDrawer({
  open,
  onClose,
  entry,
  token,
}: PortfolioVerifyDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CredentialVerification | null>(null);

  useEffect(() => {
    if (!open || !entry) return;

    setLoading(true);
    setResult(null);

    const controller = new AbortController();
    apiFetch<CredentialVerification>(`/academy/portfolio/entries/${entry.id}/verify`, {
      token: token || undefined,
      signal: controller.signal,
    })
      .then((data) => {
        setResult(data);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          toast.error(extractErrorMessage(error, 'No pudimos verificar la autenticidad'));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [entry, open, token]);

  const copyHash = async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash);
      toast.success('Hash SHA-256 copiado al portapapeles');
    } catch {
      toast.error('No se pudo copiar el hash al portapapeles');
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-[hsl(var(--primary))]" />
          Verificación Criptográfica
        </span>
      }
      subtitle="Auditoría de integridad inmutable basada en SHA-256"
      width="w-full sm:max-w-lg"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
          {loading ? (
            <div className="space-y-4" aria-label="Verificando credencial">
              <DSSkeleton className="h-28 w-full rounded-xl" />
              <DSSkeleton className="h-40 w-full rounded-xl" />
            </div>
          ) : result && entry ? (
            <>
              <section
                className={clsx(
                  'rounded-2xl border p-5 text-center',
                  result.is_valid
                    ? 'border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.05)]'
                    : 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)]',
                )}
              >
                <div
                  className={clsx(
                    'mx-auto grid size-14 place-items-center rounded-full',
                    result.is_valid
                      ? 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]'
                      : 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]',
                  )}
                >
                  {result.is_valid ? <CheckCircle2 className="size-8" /> : <XCircle className="size-8" />}
                </div>
                <h3 className="mt-3 text-lg font-bold">
                  {result.is_valid ? 'Credencial Auténtica y Verificada' : 'Inconsistencia Detectada'}
                </h3>
                <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
                  {result.is_valid
                    ? 'La firma criptográfica SHA-256 coincide exactamente con el registro original inmutable emitido por la institución.'
                    : 'El contenido o la fecha de emisión no concuerdan con el hash almacenado.'}
                </p>
              </section>

              <section className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4 text-xs">
                <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2.5">
                  <span className="text-[hsl(var(--text-secondary))]">Título de evidencia:</span>
                  <span className="font-semibold text-[hsl(var(--text-primary))]">{entry.title}</span>
                </div>
                <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2.5">
                  <span className="text-[hsl(var(--text-secondary))]">Tipo de logro:</span>
                  <span className="uppercase font-semibold text-[hsl(var(--primary))]">{entry.entry_type}</span>
                </div>
                {typeof entry.score === 'number' && (
                  <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2.5">
                    <span className="text-[hsl(var(--text-secondary))]">Calificación acreditada:</span>
                    <span className="font-bold text-[hsl(var(--text-primary))]">{entry.score.toFixed(1)} / 100</span>
                  </div>
                )}
                <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2.5">
                  <span className="text-[hsl(var(--text-secondary))]">Fecha oficial de emisión:</span>
                  <span className="font-mono text-[hsl(var(--text-primary))]">
                    {new Date(entry.issued_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[hsl(var(--text-secondary))]">ID de Estudiante:</span>
                  <span className="font-mono text-[hsl(var(--text-primary))]">{entry.student_id.slice(0, 18)}…</span>
                </div>
              </section>

              <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    Hash Criptográfico SHA-256
                  </span>
                  {result.credential_hash && (
                    <button
                      type="button"
                      onClick={() => void copyHash(result.credential_hash ?? '')}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-[hsl(var(--primary))] hover:underline"
                    >
                      <Copy className="size-3.5" /> Copiar
                    </button>
                  )}
                </div>
                <p className="mt-2 break-all rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5 font-mono text-xs text-[hsl(var(--text-primary))]">
                  {result.credential_hash || result.calculated_hash}
                </p>
              </section>
            </>
          ) : (
            <div className="p-8 text-center text-sm text-[hsl(var(--text-secondary))]">
              No hay evidencia seleccionada para verificación.
            </div>
          )}

          <div className="flex justify-end pt-4">
            <DSButton variant="secondary" onClick={onClose}>
              Cerrar
            </DSButton>
          </div>
        </div>
      </div>
    </RightPanel>
  );
}

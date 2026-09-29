"use client";

import React, { useCallback, useEffect, useState } from 'react';
import {
  Briefcase,
  ExternalLink,
  Eye,
  EyeOff,
  Filter,
  Globe,
  Lock,
  Plus,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import PortfolioEntryDrawer from '@/components/academy/PortfolioEntryDrawer';
import PortfolioVerifyDrawer from '@/components/academy/PortfolioVerifyDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { PortfolioEntry } from '@/types/academy';

export default function VerifiablePortfolioPage() {
  const { token, isAuthenticated } = useAuth();
  const [entries, setEntries] = useState<PortfolioEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEntryDrawerOpen, setIsEntryDrawerOpen] = useState(false);
  const [verifyingEntry, setVerifyingEntry] = useState<PortfolioEntry | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<'all' | 'project' | 'defense' | 'certification' | 'grade'>('all');

  const loadPortfolio = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<PortfolioEntry[]>('/academy/portfolio/my', {
        token,
        cache: 'no-store',
        signal,
      });
      setEntries(data);
    } catch (err: unknown) {
      if (!signal?.aborted) {
        const msg = extractErrorMessage(err, 'No pudimos cargar tu portafolio');
        setError(msg);
        toast.error(msg);
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const controller = new AbortController();
    void loadPortfolio(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadPortfolio]);

  const handleTogglePublish = async (entry: PortfolioEntry) => {
    if (!token || togglingId) return;
    setTogglingId(entry.id);
    try {
      const res = await apiFetch<{ id: string; is_public: boolean; message: string }>(
        `/academy/portfolio/entries/${entry.id}/publish`,
        { method: 'POST', token }
      );
      setEntries((current) =>
        current.map((item) => (item.id === entry.id ? { ...item, is_public: res.is_public } : item))
      );
      toast.success(res.message);
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err, 'No pudimos cambiar la visibilidad'));
    } finally {
      setTogglingId(null);
    }
  };

  const publicCount = entries.filter((e) => e.is_public).length;
  const verifiedCount = entries.filter((e) => Boolean(e.credential_hash)).length;
  const visibleEntries = typeFilter === 'all'
    ? entries
    : entries.filter((entry) => entry.entry_type === typeFilter);
  const entryTypes = [
    { value: 'all', label: 'Todos' },
    { value: 'project', label: 'Proyectos' },
    { value: 'defense', label: 'Defensas' },
    { value: 'certification', label: 'Certificaciones' },
    { value: 'grade', label: 'Calificaciones' },
  ] as const;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
              <Briefcase className="size-6" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">
                Acreditación Profesional · Campus OS
              </p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">Portafolio Verificable</h1>
              <p className="mt-1 max-w-2xl text-sm text-[hsl(var(--text-secondary))]">
                Evidencias de aprendizaje y certificaciones respaldadas por firmas criptográficas inmutables.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <DSButton onClick={() => setIsEntryDrawerOpen(true)} className="inline-flex items-center gap-2">
              <Plus className="size-4" /> Nueva Evidencia
            </DSButton>
            <DSButton
              variant="secondary"
              onClick={() => void loadPortfolio()}
              disabled={loading}
              className="inline-flex items-center gap-2"
            >
              <RefreshCw className={clsx('size-4', loading && 'animate-spin')} /> Actualizar
            </DSButton>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <div className="mx-auto w-full max-w-6xl space-y-6">
          {/* Métricas del portafolio */}
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Evidencias Registradas
              </span>
              <p className="mt-1 text-2xl font-bold">{entries.length}</p>
            </div>
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Firmas Criptográficas SHA-256
              </span>
              <p className="mt-1 flex items-center gap-2 text-2xl font-bold text-[hsl(var(--primary))]">
                {verifiedCount} <ShieldCheck className="size-5" />
              </p>
            </div>
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Evidencias Públicas
              </span>
              <p className="mt-1 flex items-center gap-2 text-2xl font-bold">
                {publicCount} <Globe className="size-5 text-[hsl(var(--text-secondary))]" />
              </p>
            </div>
          </section>

          {/* Listado de evidencias */}
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-semibold">Mis Evidencias y Logros</h2>
              <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtrar portafolio por tipo">
                <Filter className="size-4 text-[hsl(var(--text-secondary))]" aria-hidden="true" />
                {entryTypes.map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    aria-pressed={typeFilter === type.value}
                    onClick={() => setTypeFilter(type.value)}
                    className={clsx(
                      'rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors',
                      typeFilter === type.value
                        ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                        : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))]',
                    )}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {[1, 2].map((i) => (
                  <DSSkeleton key={i} className="h-56 rounded-xl" />
                ))}
              </div>
            ) : error ? (
              <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--surface-2))] p-5 text-sm text-[hsl(var(--destructive))]">
                {error}
              </div>
            ) : entries.length === 0 ? (
              <EmptyState
                title="Tu portafolio está vacío"
                description="Al defender trabajos o registrar proyectos finales, aparecerán aquí con su firma criptográfica de autenticidad."
                icon={Briefcase}
              />
            ) : visibleEntries.length === 0 ? (
              <EmptyState
                title="No hay evidencias de este tipo"
                description="Prueba otro filtro para consultar el resto de tu portafolio."
                icon={Filter}
              />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {visibleEntries.map((entry) => (
                  <article
                    key={entry.id}
                    className="flex flex-col justify-between rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm transition hover:border-[hsl(var(--primary)/0.4)]"
                  >
                    <div>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="rounded-md bg-[hsl(var(--surface-2))] px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                          {entry.entry_type}
                        </span>
                        <div className="flex items-center gap-2">
                          {entry.is_public ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.08)] px-2.5 py-0.5 text-[11px] font-semibold text-[hsl(var(--primary))]">
                              <Globe className="size-3" /> Público
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-0.5 text-[11px] font-semibold text-[hsl(var(--text-secondary))]">
                              <Lock className="size-3" /> Privado
                            </span>
                          )}
                          {typeof entry.score === 'number' && (
                            <span className="rounded-lg bg-[hsl(var(--surface-2))] px-2 py-0.5 font-mono text-xs font-bold">
                              {entry.score.toFixed(1)} / 100
                            </span>
                          )}
                        </div>
                      </div>

                      <h3 className="mt-3 text-lg font-bold">{entry.title}</h3>
                      {entry.description && (
                        <p className="mt-1 line-clamp-3 text-sm text-[hsl(var(--text-secondary))]">
                          {entry.description}
                        </p>
                      )}

                      {entry.evidence_url && (
                        <a
                          href={entry.evidence_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-[hsl(var(--primary))] hover:underline"
                        >
                          <ExternalLink className="size-3.5" /> Ver artefacto adjunto
                        </a>
                      )}
                    </div>

                    <div className="mt-5 space-y-3 border-t border-[hsl(var(--border))] pt-3 text-xs text-[hsl(var(--text-secondary))]">
                      <div className="flex items-center justify-between">
                        <span>Emitido: {new Date(entry.issued_at).toLocaleDateString()}</span>
                        {entry.credential_hash && (
                          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-[hsl(var(--primary))]">
                            <ShieldCheck className="size-3.5" /> SHA-256 verificado
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                        <DSButton
                          type="button"
                          onClick={() => handleTogglePublish(entry)}
                          disabled={togglingId === entry.id}
                          variant="secondary"
                          loading={togglingId === entry.id}
                          className="inline-flex items-center gap-1.5 normal-case tracking-normal"
                        >
                          {entry.is_public ? (
                            <>
                              <EyeOff className="size-3.5" /> Despublicar
                            </>
                          ) : (
                            <>
                              <Eye className="size-3.5" /> Publicar
                            </>
                          )}
                        </DSButton>

                        <DSButton
                          variant="secondary"
                          onClick={() => setVerifyingEntry(entry)}
                          className="h-8 px-2.5 text-xs inline-flex items-center gap-1.5"
                        >
                          <ShieldCheck className="size-3.5 text-[hsl(var(--primary))]" /> Verificar Hash
                        </DSButton>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>

      <PortfolioEntryDrawer
        open={isEntryDrawerOpen}
        onClose={() => setIsEntryDrawerOpen(false)}
        token={token}
        onSuccess={() => void loadPortfolio()}
      />

      <PortfolioVerifyDrawer
        open={Boolean(verifyingEntry)}
        onClose={() => setVerifyingEntry(null)}
        entry={verifyingEntry}
        token={token}
      />
    </div>
  );
}

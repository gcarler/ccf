"use client";

import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { Briefcase, Loader2, ShieldCheck } from 'lucide-react';
import { DSButton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';

interface PortfolioEntryDrawerProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  onSuccess?: () => void;
}

export default function PortfolioEntryDrawer({
  open,
  onClose,
  token,
  onSuccess,
}: PortfolioEntryDrawerProps) {
  const [title, setTitle] = useState('');
  const [entryType, setEntryType] = useState<'project' | 'defense' | 'certification' | 'grade'>('project');
  const [description, setDescription] = useState('');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [score, setScore] = useState<number | ''>('');
  const [isPublic, setIsPublic] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle('');
      setEntryType('project');
      setDescription('');
      setEvidenceUrl('');
      setScore('');
      setIsPublic(false);
    }
  }, [open]);

  const handleSubmit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || !title.trim() || submitting) return;

    setSubmitting(true);
    try {
      await apiFetch('/academy/portfolio/entries', {
        method: 'POST',
        token,
        body: {
          title: title.trim(),
          entry_type: entryType,
          description: description.trim() || null,
          evidence_url: evidenceUrl.trim() || null,
          score: typeof score === 'number' ? score : null,
          is_public: isPublic,
        },
      });
      toast.success('Entrada añadida al portafolio');
      onSuccess?.();
      onClose();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos registrar la entrada'));
    } finally {
      setSubmitting(false);
    }
  }, [description, entryType, evidenceUrl, isPublic, onClose, onSuccess, score, submitting, title, token]);

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Briefcase className="size-4 text-[hsl(var(--primary))]" />
          Nueva Evidencia de Portafolio
        </span>
      }
      subtitle="Registra un proyecto, certificación o logro con verificación criptográfica"
      width="w-full sm:max-w-lg"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <form onSubmit={handleSubmit} className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          <div className="space-y-1.5">
            <label
              htmlFor="entry-title"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Título de la Evidencia *
            </label>
            <input
              id="entry-title"
              type="text"
              required
              maxLength={255}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej. Proyecto Final: Arquitectura Limpia"
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="entry-type"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Tipo de Entrada
            </label>
            <select
              id="entry-type"
              value={entryType}
              onChange={(e) => setEntryType(e.target.value as 'project' | 'defense' | 'certification' | 'grade')}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            >
              <option value="project">Proyecto / Ensayo Académico</option>
              <option value="certification">Certificación / Distinción</option>
              <option value="defense">Defensa Oral / Socrática</option>
              <option value="grade">Acta de Calificación Aprobatoria</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="entry-evidence-url"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Enlace de Evidencia (Opcional)
            </label>
            <input
              id="entry-evidence-url"
              type="url"
              maxLength={500}
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://repositorio.ejemplo.org/evidencia.pdf"
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="entry-score"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Calificación Cuantitativa (0 - 100, Opcional)
            </label>
            <input
              id="entry-score"
              type="number"
              min={0}
              max={100}
              step="0.1"
              value={score}
              onChange={(e) => setScore(e.target.value ? Number(e.target.value) : '')}
              placeholder="Ej. 95.0"
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="entry-desc"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Descripción del Logro
            </label>
            <textarea
              id="entry-desc"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe los objetivos alcanzados, metodologías aplicadas y competencias demostradas..."
              className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3.5">
            <input
              id="entry-is-public"
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
              disabled={submitting}
            />
            <label htmlFor="entry-is-public" className="cursor-pointer text-xs text-[hsl(var(--text-primary))]">
              <span className="font-semibold">Hacer visible en mi portafolio público</span>
              <p className="text-[hsl(var(--text-secondary))]">
                Permitirá a terceros y empleadores verificar la autenticidad con el hash criptográfico.
              </p>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <DSButton variant="secondary" type="button" onClick={onClose} disabled={submitting}>
              Cancelar
            </DSButton>
            <DSButton type="submit" disabled={submitting || !title.trim()} className="inline-flex items-center gap-2">
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
              Guardar y Emitir Hash
            </DSButton>
          </div>
        </form>
      </div>
    </RightPanel>
  );
}

"use client";

import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Share2 } from 'lucide-react';
import { DSButton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';

interface NodeCreateDrawerProps {
  open: boolean;
  onClose: () => void;
  offeringId: string | null;
  token: string | null;
  onSuccess?: () => void;
}

export default function NodeCreateDrawer({
  open,
  onClose,
  offeringId,
  token,
  onSuccess,
}: NodeCreateDrawerProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [nodeType, setNodeType] = useState<'concept' | 'skill' | 'competency'>('concept');
  const [weight, setWeight] = useState<number>(1.0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle('');
      setDescription('');
      setNodeType('concept');
      setWeight(1.0);
    }
  }, [open]);

  const handleSubmit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!offeringId || !token || !title.trim() || submitting) return;

    setSubmitting(true);
    try {
      await apiFetch(`/academy/knowledge/${offeringId}/nodes`, {
        method: 'POST',
        token,
        body: {
          title: title.trim(),
          description: description.trim() || null,
          node_type: nodeType,
          weight,
        },
      });
      toast.success('Nodo cognitivo creado con éxito');
      onSuccess?.();
      onClose();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, 'No pudimos crear el nodo'));
    } finally {
      setSubmitting(false);
    }
  }, [description, nodeType, offeringId, onClose, onSuccess, submitting, title, token, weight]);

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Share2 className="size-4 text-[hsl(var(--primary))]" />
          Nuevo Nodo de Conocimiento
        </span>
      }
      subtitle="Define un concepto, habilidad o competencia evaluable"
      width="w-full sm:max-w-md"
    >
      <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <form onSubmit={handleSubmit} className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          <div className="space-y-1.5">
            <label
              htmlFor="node-title"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Título *
            </label>
            <input
              id="node-title"
              type="text"
              required
              maxLength={255}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej. Análisis de Redes Neuronales"
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="node-type-select"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Tipo de Nodo
            </label>
            <select
              id="node-type-select"
              value={nodeType}
              onChange={(e) => setNodeType(e.target.value as 'concept' | 'skill' | 'competency')}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            >
              <option value="concept">Concepto (Teórico / Abstracto)</option>
              <option value="skill">Habilidad (Práctica / Procedimental)</option>
              <option value="competency">Competencia (Integradora / Profesional)</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="node-weight"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Ponderación (Peso relativo)
            </label>
            <input
              id="node-weight"
              type="number"
              step="0.1"
              min="0.1"
              max="10.0"
              value={weight}
              onChange={(e) => setWeight(parseFloat(e.target.value) || 1.0)}
              className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="node-desc"
              className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]"
            >
              Descripción
            </label>
            <textarea
              id="node-desc"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detalla qué implica dominar este nodo y qué evidencias son necesarias..."
              className="w-full resize-y rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:border-[hsl(var(--primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
              disabled={submitting}
            />
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <DSButton variant="secondary" type="button" onClick={onClose} disabled={submitting}>
              Cancelar
            </DSButton>
            <DSButton type="submit" disabled={submitting || !title.trim()} className="inline-flex items-center gap-2">
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
              Crear Nodo
            </DSButton>
          </div>
        </form>
      </div>
    </RightPanel>
  );
}

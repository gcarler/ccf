'use client';

import React from 'react';
import { ChevronLeft, ChevronRight, Send } from 'lucide-react';

interface SectionPagerProps {
  currentIndex: number;
  totalSections: number;
  /** True si hay validaciones pendientes que impiden avanzar. */
  blocked: boolean;
  /** Mensaje de bloqueo (preguntas obligatorias vacías). */
  blockedMessage?: string | null;
  isSubmitting: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onSubmit: () => void;
}

/**
 * Paginador por secciones del respondente público (paridad Google Forms).
 * El último paso envía; los intermedios navegan con validación de bloqueo.
 */
export default function SectionPager({
  currentIndex,
  totalSections,
  blocked,
  blockedMessage,
  isSubmitting,
  onPrevious,
  onNext,
  onSubmit,
}: SectionPagerProps) {
  const isLast = currentIndex >= totalSections - 1;
  const isFirst = currentIndex === 0;

  return (
    <div className="mt-6">
      {blocked && blockedMessage ? (
        <p role="alert" className="mb-3 text-sm font-medium text-[hsl(var(--destructive))]">
          {blockedMessage}
        </p>
      ) : null}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={onPrevious}
          disabled={isFirst || isSubmitting}
          className="inline-flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] px-4 py-2 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Anterior
        </button>

        {isLast ? (
          <button
            type="button"
            onClick={onSubmit}
            disabled={blocked || isSubmitting}
            className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-5 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? (
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-[hsl(var(--primary-foreground))] border-t-transparent"
                aria-hidden="true"
              />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
            {isSubmitting ? 'Enviando…' : 'Enviar respuestas'}
          </button>
        ) : (
          <button
            type="button"
            onClick={onNext}
            disabled={blocked || isSubmitting}
            className="inline-flex items-center gap-1 rounded-lg bg-[hsl(var(--primary))] px-5 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Siguiente
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

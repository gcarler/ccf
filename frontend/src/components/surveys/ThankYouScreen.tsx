'use client';

import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface ThankYouScreenProps {
  /** Mensaje de confirmación configurado en la encuesta. */
  message: string;
  /** URL de redirección opcional (botón continuar). */
  redirectUrl: string | null;
  /** Si la encuesta permite múltiples envíos, ofrece responder de nuevo. */
  canRespondAgain: boolean;
  onRespondAgain: () => void;
}

/**
 * Pantalla final del respondente público (paridad Google Forms).
 * Muestra ``mensaje_confirmacion`` y habilita un nuevo envío si procede.
 */
export default function ThankYouScreen({
  message,
  redirectUrl,
  canRespondAgain,
  onRespondAgain,
}: ThankYouScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-10 text-center shadow-sm">
      <CheckCircle2 className="h-14 w-14 text-[hsl(var(--primary))]" aria-hidden="true" />
      <h2 className="text-xl font-semibold text-[hsl(var(--text-primary))]">
        {message || '¡Tu respuesta ha sido registrada exitosamente!'}
      </h2>
      {redirectUrl ? (
        <a
          href={redirectUrl}
          className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-5 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90"
        >
          Continuar
        </a>
      ) : null}
      {canRespondAgain ? (
        <button
          type="button"
          onClick={onRespondAgain}
          className="rounded-lg border border-[hsl(var(--border))] px-4 py-2 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))]"
        >
          Responder de nuevo
        </button>
      ) : null}
    </div>
  );
}

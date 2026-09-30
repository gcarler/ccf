'use client';

import React from 'react';

interface ProgressBarProps {
  /** Porcentaje de llenado 0-100. */
  value: number;
  /** Etiqueta opcional junto al porcentaje. */
  label?: string;
}

/**
 * Barra de progreso del respondente público.
 * 100% tokens semánticos del Design System (sin colores hardcodeados).
 */
export default function ProgressBar({ value, label }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="w-full">
      <div className="flex items-center justify-between pb-1">
        <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">
          {label ?? 'Progreso'}
        </span>
        <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">{clamped}%</span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-[hsl(var(--surface-3))]"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? 'Progreso de la encuesta'}
      >
        <div
          className="h-full rounded-full bg-[hsl(var(--primary))] transition-all duration-300"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import { AlertTriangle, CalendarX, X, Clock, MapPin } from 'lucide-react';
import clsx from 'clsx';

export interface RoomConflictInfo {
  conflict: boolean;
  conflict_event_id?: string;
  conflict_event_title?: string;
  conflict_start?: string;
  conflict_end?: string;
  room_id?: string;
  message?: string;
}

export interface RoomConflictAlertProps {
  conflict: RoomConflictInfo | null;
  onDismiss?: () => void;
  onSelectAlternative?: () => void;
  className?: string;
}

function formatConflictTime(isoString?: string): string {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export default function RoomConflictAlert({
  conflict,
  onDismiss,
  onSelectAlternative,
  className,
}: RoomConflictAlertProps) {
  if (!conflict || !conflict.conflict) {
    return null;
  }

  const startFormatted = formatConflictTime(conflict.conflict_start);
  const endFormatted = formatConflictTime(conflict.conflict_end);

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={clsx(
        'relative rounded-xl border p-4 transition-all duration-200',
        'bg-[hsl(var(--destructive)/0.08)] border-[hsl(var(--destructive)/0.3)]',
        'shadow-sm',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="size-9 rounded-lg bg-[hsl(var(--destructive)/0.15)] flex items-center justify-center shrink-0 text-[hsl(var(--destructive))]">
          <CalendarX size={18} aria-hidden="true" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-[hsl(var(--destructive))]">
              Conflicto de reserva física
            </h4>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]">
              <AlertTriangle size={12} aria-hidden="true" />
              Ocupado
            </span>
          </div>

          <p className="mt-1 text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
            {conflict.message ||
              'El salón o espacio seleccionado ya se encuentra reservado en el horario propuesto.'}
          </p>

          {(conflict.conflict_event_title || startFormatted) && (
            <div className="mt-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 flex flex-col gap-2">
              {conflict.conflict_event_title && (
                <div className="flex items-center gap-2 text-xs font-medium text-[hsl(var(--text-primary))]">
                  <MapPin size={13} className="text-[hsl(var(--text-secondary))] shrink-0" aria-hidden="true" />
                  <span className="truncate">
                    Evento en conflicto:{' '}
                    <strong className="font-semibold text-[hsl(var(--text-primary))]">
                      {conflict.conflict_event_title}
                    </strong>
                  </span>
                </div>
              )}

              {startFormatted && (
                <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
                  <Clock size={13} className="text-[hsl(var(--text-secondary))] shrink-0" aria-hidden="true" />
                  <span>
                    {startFormatted} {endFormatted ? `— ${endFormatted}` : ''}
                  </span>
                </div>
              )}
            </div>
          )}

          <div className="mt-3 flex items-center gap-2">
            {onSelectAlternative && (
              <button
                type="button"
                onClick={onSelectAlternative}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                  'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]',
                  'hover:opacity-90 active:scale-[0.98]'
                )}
              >
                Cambiar espacio o fecha
              </button>
            )}

            {onDismiss && (
              <button
                type="button"
                onClick={onDismiss}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                  'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]',
                  'hover:text-[hsl(var(--text-primary))] border border-[hsl(var(--border))]'
                )}
              >
                Entendido
              </button>
            )}
          </div>
        </div>

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Cerrar alerta de conflicto"
            className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors cursor-pointer"
          >
            <X size={16} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

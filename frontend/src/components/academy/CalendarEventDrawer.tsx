"use client";

import { CalendarDays, Clock3, GraduationCap, Tag } from 'lucide-react';
import { RightPanel } from '@/components/ui/RightPanel';
import type { AcademyCalendarEvent } from '@/types/academy';

interface CalendarEventDrawerProps {
  open: boolean;
  onClose: () => void;
  event: AcademyCalendarEvent | null;
}

const EVENT_LABELS: Record<string, string> = {
  evaluation: 'Evaluación',
  assignment: 'Entrega',
  socratic_defense: 'Defensa socrática',
  study_group: 'Grupo de estudio',
  milestone: 'Hito académico',
};

function formatDate(value: string, options: Intl.DateTimeFormatOptions) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha por confirmar' : new Intl.DateTimeFormat('es', options).format(date);
}

export default function CalendarEventDrawer({ open, onClose, event }: CalendarEventDrawerProps) {
  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><CalendarDays className="size-4 text-[hsl(var(--primary))]" /> Detalle del evento</span>}
      subtitle={event ? EVENT_LABELS[event.event_type] ?? 'Evento académico' : 'Información del calendario'}
      width="w-full sm:max-w-lg"
    >
      {event ? (
        <div className="space-y-5 bg-[hsl(var(--surface-1))] p-5 text-[hsl(var(--text-primary))]">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-1 text-xs font-medium text-[hsl(var(--primary))]">
              <Tag className="size-3.5" /> {EVENT_LABELS[event.event_type] ?? event.event_type.replaceAll('_', ' ')}
            </span>
            <h2 className="mt-3 text-xl font-semibold">{event.title}</h2>
          </div>

          <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold"><Clock3 className="size-4 text-[hsl(var(--primary))]" /> Fecha y hora</h3>
            <p className="mt-2 text-sm">{formatDate(event.start_date, { dateStyle: 'full', timeStyle: 'short' })}</p>
            <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">Hasta {formatDate(event.end_date, { dateStyle: 'medium', timeStyle: 'short' })}</p>
          </section>

          {event.description ? (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{event.description}</p>
            </section>
          ) : null}

          {event.offering_id ? (
            <p className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]"><GraduationCap className="size-4" /> Comisión académica asociada</p>
          ) : null}
        </div>
      ) : (
        <div className="p-5 text-sm text-[hsl(var(--text-secondary))]">Selecciona un evento para consultar sus detalles.</div>
      )}
    </RightPanel>
  );
}

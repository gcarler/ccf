"use client";

import React from 'react';
import { BellRing, CalendarClock, HeartHandshake } from 'lucide-react';
import clsx from 'clsx';
import { DSButton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { toast } from 'sonner';
import type { WellnessAlert } from '@/types/academy';

type Severity = 'critical' | 'high' | 'medium' | 'low';

interface WellnessAlertDrawerProps {
  open: boolean;
  onClose: () => void;
  alert: WellnessAlert | null;
}

function resolveSeverity(alert: WellnessAlert): Severity {
  const knownSeverity = alert.severity?.toLowerCase();
  if (knownSeverity === 'critical' || knownSeverity === 'high' || knownSeverity === 'medium' || knownSeverity === 'low') {
    return knownSeverity;
  }
  const match = alert.message.match(/\b(critical|high|medium|low)\b/i);
  return (match?.[1]?.toLowerCase() as Severity | undefined) ?? 'medium';
}

function resolveType(alert: WellnessAlert): string {
  if (alert.signal_type) return alert.signal_type.replaceAll('_', ' ');
  const separator = alert.message.indexOf(':');
  return separator >= 0 ? 'Alerta preventiva' : 'Señal de bienestar';
}

function severityLabel(severity: Severity): string {
  return {
    critical: 'Crítica',
    high: 'Alta',
    medium: 'Media',
    low: 'Baja',
  }[severity];
}

function severityClasses(severity: Severity): string {
  if (severity === 'critical') return 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]';
  if (severity === 'high') return 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]';
  if (severity === 'medium') return 'border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]';
  return 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground,var(--text-secondary)))]';
}

export default function WellnessAlertDrawer({ open, onClose, alert }: WellnessAlertDrawerProps) {
  const severity = alert ? resolveSeverity(alert) : 'low';

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={<span className="flex items-center gap-2"><BellRing className="size-4 text-[hsl(var(--primary))]" /> Detalle de bienestar</span>}
      subtitle="Información de acompañamiento académico"
      width="w-full sm:max-w-lg"
    >
      {alert ? (
        <div className="flex h-full flex-col bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
          <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className={clsx('inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', severityClasses(severity))}>
                {severityLabel(severity)}
              </span>
              <span className="rounded-md bg-[hsl(var(--surface-2))] px-2.5 py-1 text-xs font-medium capitalize text-[hsl(var(--text-secondary))]">
                {resolveType(alert)}
              </span>
            </div>

            <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
              <h2 className="text-sm font-semibold">Mensaje</h2>
              <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[hsl(var(--text-secondary))]">{alert.message}</p>
            </section>

            <div className="flex items-center gap-2 rounded-xl border border-[hsl(var(--border))] p-4 text-sm">
              <CalendarClock className="size-4 shrink-0 text-[hsl(var(--primary))]" />
              <div>
                <p className="text-xs text-[hsl(var(--text-secondary))]">Fecha de la alerta</p>
                <p className="font-medium">{new Date(alert.detected_at ?? alert.sent_at).toLocaleString('es')}</p>
              </div>
            </div>

            <p className="text-xs text-[hsl(var(--text-secondary))]">Si necesitas apoyo, puedes solicitar que tu tutor se ponga en contacto contigo.</p>
          </div>
          <div className="flex justify-end border-t border-[hsl(var(--border))] p-4">
            <DSButton
              onClick={() => toast.success('Solicitud enviada')}
              className="inline-flex items-center gap-2"
            >
              <HeartHandshake className="size-4" /> Contactar tutor
            </DSButton>
          </div>
        </div>
      ) : (
        <div className="p-6 text-sm text-[hsl(var(--text-secondary))]">Selecciona una alerta para ver su detalle.</div>
      )}
    </RightPanel>
  );
}

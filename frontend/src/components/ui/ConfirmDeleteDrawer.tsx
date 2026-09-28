"use client";

import React, { useState } from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';
import { RightPanel } from '@/components/ui/RightPanel';
import { DSButton } from '@/design';

export interface ConfirmDeleteDrawerProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title?: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
}

export default function ConfirmDeleteDrawer({
  open,
  onClose,
  onConfirm,
  title = '¿Confirmar eliminación?',
  description,
  confirmLabel = 'Eliminar',
  cancelLabel = 'Cancelar',
  loading: externalLoading = false,
}: ConfirmDeleteDrawerProps) {
  const [internalLoading, setInternalLoading] = useState(false);
  const isLoading = externalLoading || internalLoading;

  const handleConfirm = async () => {
    try {
      setInternalLoading(true);
      await onConfirm();
      onClose();
    } catch {
      // Dejar abierto para reintentar o cancelar
    } finally {
      setInternalLoading(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2 text-[hsl(var(--destructive))]">
          <Trash2 className="size-4 shrink-0" />
          <span>{title}</span>
        </span>
      }
      width="w-full sm:max-w-md"
    >
      <div className="flex h-full flex-col justify-between p-5 bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]">
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl border border-[hsl(var(--destructive)/0.25)] bg-[hsl(var(--destructive)/0.06)] p-4 text-[hsl(var(--text-primary))]">
            <AlertTriangle className="size-5 shrink-0 text-[hsl(var(--destructive))] mt-0.5" />
            <p className="text-sm leading-relaxed">{description}</p>
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            Esta acción se registrará con fines de auditoría. Si no estás seguro, puedes cancelar sin afectar tus datos.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))]">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:bg-[hsl(var(--destructive)/0.9)] active:scale-95 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="size-3.5" />
            <span>{isLoading ? 'Eliminando…' : confirmLabel}</span>
          </button>
        </div>
      </div>
    </RightPanel>
  );
}

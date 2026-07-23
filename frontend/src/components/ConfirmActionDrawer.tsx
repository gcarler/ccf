'use client';

import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

export type ConfirmActionState = {
  title: string;
  description: string;
  confirmLabel?: string;
  destructive?: boolean;
  onConfirm: () => void | Promise<void>;
} | null;

type Props = {
  action: ConfirmActionState;
  onClose: () => void;
};

export default function ConfirmActionDrawer({ action, onClose }: Props) {
  return (
    <WorkspaceDrawer
      isOpen={Boolean(action)}
      onClose={onClose}
      title={action?.title || 'Confirmar accion'}
      actions={(
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={async () => {
              if (!action) return;
              try {
                await action.onConfirm();
                onClose();
              } catch {
                // Keep the drawer open so the user can retry or cancel.
              }
            }}
            className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-white transition-colors ${
              action?.destructive
                ? 'bg-[hsl(var(--danger))] hover:bg-[hsl(var(--danger))]'
                : 'bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]'
            }`}
          >
            <CheckCircle2 size={14} />
            {action?.confirmLabel || 'Confirmar'}
          </button>
        </div>
      )}
    >
      <div className="flex items-start gap-3 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/30 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <p className="text-sm leading-6">{action?.description}</p>
      </div>
    </WorkspaceDrawer>
  );
}

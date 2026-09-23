'use client';

import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
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
  const open = Boolean(action);
  return (
    <WorkspaceDrawer
      isOpen={open}
      onClose={onClose}
      title={action?.title || 'Confirmar accion'}
      actions={(
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
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
            className={clsx(
              'inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-colors',
              action?.destructive
                ? 'bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:opacity-90'
                : 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90'
            )}
          >
            <CheckCircle2 size={14} />
            {action?.confirmLabel || 'Confirmar'}
          </button>
        </div>
      )}
    >
      <div className="flex items-start gap-3 rounded-md border border-[hsl(var(--warning)/30%)] bg-[hsl(var(--warning)/10%)] p-3 text-[hsl(var(--warning))]">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <p className="text-sm leading-6">{action?.description}</p>
      </div>
    </WorkspaceDrawer>
  );
}

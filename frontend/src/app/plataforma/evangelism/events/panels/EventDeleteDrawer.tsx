'use client';

import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Trash2 } from 'lucide-react';

interface EventDeleteDrawerProps {
  deletingId: string | null;
  deletingLoadingId: string | null;
  onDelete: (id: string) => void;
  onClose: () => void;
}

export default function EventDeleteDrawer({
  deletingId,
  deletingLoadingId,
  onDelete,
  onClose,
}: EventDeleteDrawerProps) {
  return (
 <ErrorBoundary moduleName="Eventos - Eliminar" compact>
 <WorkspaceDrawer
 isOpen={!!deletingId}
 onClose={() => onClose()}
 title="¿Eliminar evento?"
 subtitle="Atención: acción destructiva irreversible"
 actions={
 <>
 <button disabled={deletingLoadingId === deletingId} onClick={() => onClose()} className="px-4 py-2 text-xs font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </button>
 <button onClick={() => deletingId && onDelete(deletingId)} disabled={deletingLoadingId === deletingId} className="px-3 py-2 bg-[hsl(var(--destructive))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--destructive))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
 <Trash2 size={14} /> Eliminar
 </button>
 </>
 }
 >
 <div className="flex flex-col items-center text-center p-4 bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger)/0.1)] rounded-md border border-danger-muted dark:border-danger">
 <div className="size-8 bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger)/0.4)] text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))] rounded-full flex items-center justify-center mb-4">
 <Trash2 size={24} />
 </div>
 <p className="text-sm text-danger dark:text-danger font-bold mb-2">Se eliminará todo el historial del evento</p>
 <p className="text-xs text-[hsl(var(--destructive))] dark:text-danger">Esta acción también borrará los registros de asistencia asociados. No podrás recuperar esta información.</p>
 </div>
 </WorkspaceDrawer>
 </ErrorBoundary>
  );
}

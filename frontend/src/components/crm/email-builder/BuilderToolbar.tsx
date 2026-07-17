/** BuilderToolbar — toolbar superior. */
'use client';
import { Undo2, Redo2, Eye, Save, ArrowLeft } from 'lucide-react';
import type { UseEmailBuilderReturn } from './useEmailBuilder';

interface Props { builder: UseEmailBuilderReturn; templateName: string; onNameChange: (n: string) => void; onPreview: () => void; onSave: () => void; onBack: () => void; saving?: boolean; }

export default function BuilderToolbar({ builder, templateName, onNameChange, onPreview, onSave, onBack, saving }: Props) {
  const { canUndo, canRedo, undo, redo } = builder;
  return (
    <div className="flex items-center justify-between h-12 px-4 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors" aria-label="Volver"><ArrowLeft size={14} /></button>
        <input value={templateName} onChange={e => onNameChange(e.target.value)} className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white bg-transparent border-none focus:outline-none w-48" placeholder="Nombre de la plantilla" />
      </div>
      <div className="flex items-center gap-1">
        <button onClick={undo} disabled={!canUndo} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] disabled:opacity-30" aria-label="Deshacer"><Undo2 size={14} /></button>
        <button onClick={redo} disabled={!canRedo} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] disabled:opacity-30" aria-label="Rehacer"><Redo2 size={14} /></button>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={onPreview} className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"><Eye size={13} />Preview</button>
        <button onClick={onSave} disabled={saving} className="flex items-center gap-1.5 h-8 px-4 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-medium hover:opacity-90 disabled:opacity-50"><Save size={13} />{saving ? 'Guardando...' : 'Guardar'}</button>
      </div>
    </div>
  );
}

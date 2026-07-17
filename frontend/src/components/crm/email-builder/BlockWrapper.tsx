/** BlockWrapper — wrapper con drag handle + acciones. */
'use client';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import clsx from 'clsx';
import { GripVertical, Trash2, Copy } from 'lucide-react';
import type { EmailBlock } from './blockTypes';

interface Props { block: EmailBlock; isSelected: boolean; onSelect: () => void; onRemove: () => void; onDuplicate: () => void; children: React.ReactNode; }

export default function BlockWrapper({ block, isSelected, onSelect, onRemove, onDuplicate, children }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: block.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} className={clsx('group relative rounded-lg transition-all', isSelected ? 'ring-2 ring-[hsl(var(--primary))] ring-offset-1 ring-offset-[hsl(var(--bg-primary))]' : 'hover:ring-1 hover:ring-[hsl(var(--border))]', isDragging && 'opacity-50 z-50')} onClick={(e) => { e.stopPropagation(); onSelect(); }}>
      <div className={clsx('absolute -left-8 top-1/2 -translate-y-1/2 flex flex-col items-center gap-0.5 transition-opacity', isSelected || isDragging ? 'opacity-100' : 'opacity-0 group-hover:opacity-100')}>
        <button className="size-6 flex items-center justify-center rounded text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] cursor-grab active:cursor-grabbing" {...attributes} {...listeners} aria-label="Arrastrar"><GripVertical size={12} /></button>
      </div>
      <div className={clsx('absolute -top-3 right-2 flex items-center gap-1 transition-opacity z-10', isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100')}>
        <button onClick={(e) => { e.stopPropagation(); onDuplicate(); }} className="size-6 flex items-center justify-center rounded bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]" title="Duplicar" aria-label="Duplicar"><Copy size={11} /></button>
        <button onClick={(e) => { e.stopPropagation(); onRemove(); }} className="size-6 flex items-center justify-center rounded bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-rose-500" title="Eliminar" aria-label="Eliminar"><Trash2 size={11} /></button>
      </div>
      <div className="relative">{children}</div>
    </div>
  );
}

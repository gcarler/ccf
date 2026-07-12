/** BlockPalette — panel de bloques arrastrables. */
'use client';
import { useDraggable } from '@dnd-kit/core';
import { Type, AlignLeft, MousePointerClick, Image, Minus, Space, BookOpen, Columns } from 'lucide-react';
import { BLOCK_DEFINITIONS, type BlockTypeDefinition } from './blockTypes';

const ICON_MAP: Record<string, React.ElementType> = { Type, AlignLeft, MousePointerClick, Image, Minus, Space, BookOpen, Columns };

function DraggableBlock({ def }: { def: BlockTypeDefinition }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `palette-${def.type}`, data: { type: 'palette-item', blockType: def.type } });
  const Icon = ICON_MAP[def.icon] || Type;
  return (
    <div ref={setNodeRef} {...listeners} {...attributes} className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 cursor-grab active:cursor-grabbing hover:border-[hsl(var(--primary)/0.5)] hover:shadow-md transition-all select-none" style={{ opacity: isDragging ? 0.5 : 1 }}>
      <div className="size-8 rounded-md bg-[hsl(var(--primary)/0.1)] flex items-center justify-center shrink-0"><Icon size={14} className="text-[hsl(var(--primary))]" /></div>
      <div className="min-w-0"><p className="text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white truncate">{def.label}</p><p className="text-[10px] text-[hsl(var(--text-secondary))] capitalize">{def.category === 'content' ? 'Contenido' : 'Layout'}</p></div>
    </div>
  );
}

export default function BlockPalette() {
  const content = BLOCK_DEFINITIONS.filter(b => b.category === 'content');
  const layout = BLOCK_DEFINITIONS.filter(b => b.category === 'layout');
  return (
    <div className="space-y-4">
      <div><h3 className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 px-1">Contenido</h3><div className="space-y-1.5">{content.map(d => <DraggableBlock key={d.type} def={d} />)}</div></div>
      <div><h3 className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 px-1">Layout</h3><div className="space-y-1.5">{layout.map(d => <DraggableBlock key={d.type} def={d} />)}</div></div>
    </div>
  );
}

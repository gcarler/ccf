'use client';
import { Image as ImageIcon } from 'lucide-react';
import type { EmailBlock, ImageProps } from '../blockTypes';
export default function ImageBlock({ block }: { block: EmailBlock }) {
  const p = block.props as ImageProps;
  if (!p.src) return <div className="p-4"><div className="flex flex-col items-center justify-center py-12 bg-[hsl(var(--surface-1))] dark:bg-white/5 border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-xl"><ImageIcon size={32} className="text-[hsl(var(--text-secondary))] mb-2" /><p className="text-xs text-[hsl(var(--text-secondary))]">Selecciona una imagen</p></div></div>;
  return <div className="p-4"><img src={p.src} alt={p.alt || ''} className="block mx-auto" style={{ width: p.width || '100%' }} /></div>;
}

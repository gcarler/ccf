'use client';
import type { EmailBlock, DividerProps } from '../blockTypes';
export default function DividerBlock({ block }: { block: EmailBlock }) {
  const p = block.props as DividerProps;
  return <div className="px-4 py-2"><hr style={{ borderColor: p.color || '#e5e7eb', borderWidth: p.thickness ?? 1, borderStyle: p.style || 'solid', width: p.width || '100%', margin: '0 auto' }} /></div>;
}

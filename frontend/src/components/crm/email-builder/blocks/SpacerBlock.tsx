'use client';
import type { EmailBlock, SpacerProps } from '../blockTypes';
export default function SpacerBlock({ block }: { block: EmailBlock }) {
  const p = block.props as SpacerProps;
  const h = p.height || 24;
  return <div className="relative"><div style={{ height: `${h}px` }} /><div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"><span className="text-[9px] text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-white/10 px-2 py-0.5 rounded-full">{h}px</span></div></div>;
}

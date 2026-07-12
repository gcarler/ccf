'use client';
import type { EmailBlock, ColumnsProps } from '../blockTypes';
export default function ColumnsBlock({ block }: { block: EmailBlock }) {
  const p = block.props as ColumnsProps;
  const c = p.count || 2;
  return <div className="p-4"><div className="flex gap-3">{Array.from({ length: c }).map((_, i) => <div key={i} className="flex-1 min-h-[60px] rounded-lg border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 p-3 flex items-center justify-center"><span className="text-[10px] text-[hsl(var(--text-secondary))] opacity-50">Columna {i + 1}</span></div>)}</div></div>;
}

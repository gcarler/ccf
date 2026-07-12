'use client';
import type { EmailBlock, ButtonProps } from '../blockTypes';
export default function ButtonBlock({ block }: { block: EmailBlock }) {
  const p = block.props as ButtonProps;
  return <div className="p-4" style={{ textAlign: (p.align as any) || 'center' }}><a href={p.url || '#'} className="inline-block px-6 py-3 text-sm font-semibold no-underline" style={{ backgroundColor: p.bgColor || '#018ABD', color: p.textColor || '#ffffff', borderRadius: p.borderRadius ?? 10 }} onClick={e => e.preventDefault()}>{p.label || 'Haz clic'}</a></div>;
}

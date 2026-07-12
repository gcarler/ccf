'use client';
import type { EmailBlock, HeaderProps } from '../blockTypes';
export default function HeaderBlock({ block }: { block: EmailBlock }) {
  const p = block.props as HeaderProps;
  return <div className="p-6 text-center" style={{ backgroundColor: p.bgColor || undefined, textAlign: (p.textAlign as any) || 'center' }}><h2 className="text-2xl font-bold mb-1" style={{ color: p.titleColor || '#001B48' }}>{p.title || 'Titulo'}</h2>{p.subtitle && <p className="text-sm opacity-70">{p.subtitle}</p>}</div>;
}

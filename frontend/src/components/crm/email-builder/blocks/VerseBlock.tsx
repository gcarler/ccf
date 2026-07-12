'use client';
import type { EmailBlock, VerseProps } from '../blockTypes';
export default function VerseBlock({ block }: { block: EmailBlock }) {
  const p = block.props as VerseProps;
  return <div className="p-4"><div className="rounded-xl p-5 text-center" style={{ backgroundColor: '#f0f5fa', textAlign: (p.textAlign as any) || 'center' }}><p className="text-base italic leading-relaxed mb-2" style={{ color: '#004581' }}>&ldquo;{p.text || 'Versiculo aqui'}&rdquo;</p>{p.reference && <p className="text-xs font-bold uppercase tracking-widest" style={{ color: '#001B48' }}>&mdash; {p.reference}</p>}</div></div>;
}

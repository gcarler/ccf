/** PropertiesPanel — editor de propiedades del bloque seleccionado. */
'use client';
import type { EmailBlock } from './blockTypes';
import { AlignLeft, AlignCenter, AlignRight, Type } from 'lucide-react';

interface Props { block: EmailBlock | undefined; onUpdate: (props: Record<string, unknown>) => void; }

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <div className="space-y-1"><label className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">{label}</label>{children}</div>; }
function Input({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) { return <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]" />; }
function Color({ value, onChange }: { value: string; onChange: (v: string) => void }) { return <div className="flex items-center gap-2"><input type="color" value={value || '#000000'} onChange={e => onChange(e.target.value)} className="size-7 rounded border border-[hsl(var(--border))] cursor-pointer" /><input type="text" value={value} onChange={e => onChange(e.target.value)} className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white font-mono focus:outline-none" /></div>; }
function Align({ value, onChange }: { value: string; onChange: (v: string) => void }) { const opts = [{ v: 'left', I: AlignLeft, l: 'Alinear a la izquierda' }, { v: 'center', I: AlignCenter, l: 'Centrar' }, { v: 'right', I: AlignRight, l: 'Alinear a la derecha' }]; return <div className="flex gap-1">{opts.map(({ v, I, l }) => <button key={v} onClick={() => onChange(v)} aria-label={l} className={`size-7 flex items-center justify-center rounded border transition-colors ${value === v ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'}`}><I size={12} /></button>)}</div>; }

function HeaderFields({ block, onUpdate }: { block: EmailBlock; onUpdate: (p: Record<string, unknown>) => void }) {
  return <><Field label="Titulo"><Input value={String(block.props.title || '')} onChange={v => onUpdate({ title: v })} /></Field><Field label="Subtitulo"><Input value={String(block.props.subtitle || '')} onChange={v => onUpdate({ subtitle: v })} placeholder="Opcional" /></Field><Field label="Alineacion"><Align value={String(block.props.textAlign || 'center')} onChange={v => onUpdate({ textAlign: v })} /></Field><Field label="Color titulo"><Color value={String(block.props.titleColor || '')} onChange={v => onUpdate({ titleColor: v })} /></Field><Field label="Color fondo"><Color value={String(block.props.bgColor || '')} onChange={v => onUpdate({ bgColor: v })} /></Field></>;
}

function ButtonFields({ block, onUpdate }: { block: EmailBlock; onUpdate: (p: Record<string, unknown>) => void }) {
  return <><Field label="Texto"><Input value={String(block.props.label || '')} onChange={v => onUpdate({ label: v })} /></Field><Field label="URL"><Input value={String(block.props.url || '')} onChange={v => onUpdate({ url: v })} placeholder="https://..." /></Field><Field label="Alineacion"><Align value={String(block.props.align || 'center')} onChange={v => onUpdate({ align: v })} /></Field><Field label="Color fondo"><Color value={String(block.props.bgColor || '')} onChange={v => onUpdate({ bgColor: v })} /></Field><Field label="Color texto"><Color value={String(block.props.textColor || '#ffffff')} onChange={v => onUpdate({ textColor: v })} /></Field></>;
}

function ImageFields({ block, onUpdate }: { block: EmailBlock; onUpdate: (p: Record<string, unknown>) => void }) {
  return <><Field label="URL imagen"><Input value={String(block.props.src || '')} onChange={v => onUpdate({ src: v })} placeholder="https://..." /></Field><Field label="Alt text"><Input value={String(block.props.alt || '')} onChange={v => onUpdate({ alt: v })} /></Field><Field label="Ancho"><Input value={String(block.props.width || '100%')} onChange={v => onUpdate({ width: v })} /></Field></>;
}

function VerseFields({ block, onUpdate }: { block: EmailBlock; onUpdate: (p: Record<string, unknown>) => void }) {
  return <><Field label="Texto"><textarea value={String(block.props.text || '')} onChange={e => onUpdate({ text: e.target.value })} rows={3} className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none resize-none" /></Field><Field label="Referencia"><Input value={String(block.props.reference || '')} onChange={v => onUpdate({ reference: v })} /></Field><Field label="Alineacion"><Align value={String(block.props.textAlign || 'center')} onChange={v => onUpdate({ textAlign: v })} /></Field></>;
}

function DividerFields({ block, onUpdate }: { block: EmailBlock; onUpdate: (p: Record<string, unknown>) => void }) {
  return <><Field label="Color"><Color value={String(block.props.color || '#e5e7eb')} onChange={v => onUpdate({ color: v })} /></Field><Field label="Grosor"><input type="range" min={1} max={10} value={Number(block.props.thickness ?? 1)} onChange={e => onUpdate({ thickness: Number(e.target.value) })} className="w-full accent-[hsl(var(--primary))]" /></Field></>;
}

export default function PropertiesPanel({ block, onUpdate }: Props) {
  if (!block) return <div className="flex flex-col items-center justify-center h-full text-center px-4"><Type size={24} className="text-[hsl(var(--text-secondary))] mb-2 opacity-40" /><p className="text-xs text-[hsl(var(--text-secondary))]">Selecciona un bloque para editar</p></div>;
  const labels: Record<string, string> = { header: 'Encabezado', text: 'Texto', button: 'Boton CTA', image: 'Imagen', divider: 'Divisor', spacer: 'Espacio', verse: 'Versiculo', columns: 'Columnas' };
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2"><div className="size-6 rounded bg-[hsl(var(--primary)/0.1)] flex items-center justify-center"><Type size={12} className="text-[hsl(var(--primary))]" /></div><span className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">{labels[block.type] || block.type}</span></div>
      <div className="space-y-3">
        {block.type === 'header' && <HeaderFields block={block} onUpdate={onUpdate} />}
        {block.type === 'text' && <p className="text-[10px] text-[hsl(var(--text-secondary))] italic">Haz clic en el bloque para editar el texto</p>}
        {block.type === 'button' && <ButtonFields block={block} onUpdate={onUpdate} />}
        {block.type === 'image' && <ImageFields block={block} onUpdate={onUpdate} />}
        {block.type === 'divider' && <DividerFields block={block} onUpdate={onUpdate} />}
        {block.type === 'spacer' && <Field label="Altura"><input type="range" min={4} max={200} value={Number(block.props.height || 24)} onChange={e => onUpdate({ height: Number(e.target.value) })} className="w-full accent-[hsl(var(--primary))]" /><span className="text-[10px] text-[hsl(var(--text-secondary))]">{String(block.props.height || 24)}px</span></Field>}
        {block.type === 'verse' && <VerseFields block={block} onUpdate={onUpdate} />}
        {block.type === 'columns' && <Field label="Columnas"><div className="flex gap-1">{[1, 2, 3].map(n => <button key={n} onClick={() => onUpdate({ count: n })} className={`flex-1 h-8 rounded-lg text-xs font-medium border transition-colors ${Number(block.props.count || 2) === n ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'}`}>{n}</button>)}</div></Field>}
      </div>
    </div>
  );
}

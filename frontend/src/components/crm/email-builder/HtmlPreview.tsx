/** HtmlPreview — preview del email en iframe. */
'use client';
import { useState } from 'react';
import { Copy, Check, Monitor, Smartphone, X } from 'lucide-react';

interface Props { html: string; onClose: () => void; }

export default function HtmlPreview({ html, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  const [vp, setVp] = useState<'desktop' | 'mobile'>('desktop');
  const copyHtml = async () => { await navigator.clipboard.writeText(html); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-50" onClick={onClose} />
      <div className="fixed inset-x-4 top-[5vh] bottom-[5vh] md:inset-x-16 lg:inset-x-32 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] z-50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-[hsl(var(--border))] dark:border-white/10">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">Preview del email</h3>
            <div className="flex items-center gap-1 bg-[hsl(var(--surface-2))] dark:bg-white/10 rounded-lg p-0.5">
              <button onClick={() => setVp('desktop')} className={`size-7 flex items-center justify-center rounded-md ${vp === 'desktop' ? 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))]'}`} aria-label="Vista escritorio"><Monitor size={13} /></button>
              <button onClick={() => setVp('mobile')} className={`size-7 flex items-center justify-center rounded-md ${vp === 'mobile' ? 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))]'}`} aria-label="Vista móvil"><Smartphone size={13} /></button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={copyHtml} className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]">{copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}{copied ? 'Copiado' : 'Copiar HTML'}</button>
            <button onClick={onClose} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]" aria-label="Cerrar"><X size={14} /></button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-6 flex justify-center bg-gray-100 dark:bg-black/20">
          <div className="bg-white shadow-xl rounded-lg overflow-hidden transition-all duration-300" style={{ width: vp === 'mobile' ? '375px' : '600px', maxWidth: '100%' }}>
            <iframe srcDoc={html} title="Preview" className="w-full border-0" style={{ minHeight: '600px' }} sandbox="allow-same-origin" />
          </div>
        </div>
      </div>
    </>
  );
}

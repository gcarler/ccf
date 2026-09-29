/** HtmlPreview — preview del email en iframe. */
'use client';
import { useState } from 'react';
import { Copy, Check, Monitor, Smartphone } from 'lucide-react';
import SidePanel from '@/components/ui/SidePanel';

interface Props { html: string; onClose: () => void; }

export default function HtmlPreview({ html, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  const [vp, setVp] = useState<'desktop' | 'mobile'>('desktop');
  const copyHtml = async () => {
    await navigator.clipboard.writeText(html);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <SidePanel
      isOpen={true}
      onClose={onClose}
      title="Preview del email"
      subtitle="Visualiza la plantilla generada para escritorio y móvil"
      width="w-full max-w-3xl"
    >
      <div className="flex flex-col h-full gap-4 mt-1">
        <div className="flex items-center justify-between pb-3 border-b border-[hsl(var(--border))]">
          <div className="flex items-center gap-1 bg-[hsl(var(--surface-2))] rounded-lg p-0.5">
            <button
              onClick={() => setVp('desktop')}
              className={`size-7 flex items-center justify-center rounded-md transition-colors ${vp === 'desktop' ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-xs font-semibold' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'}`}
              aria-label="Vista escritorio"
            >
              <Monitor size={13} />
            </button>
            <button
              onClick={() => setVp('mobile')}
              className={`size-7 flex items-center justify-center rounded-md transition-colors ${vp === 'mobile' ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-xs font-semibold' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'}`}
              aria-label="Vista móvil"
            >
              <Smartphone size={13} />
            </button>
          </div>
          <button
            onClick={copyHtml}
            className="flex items-center gap-1.5 h-8 px-3 rounded-lg border border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
          >
            {copied ? <Check size={12} className="text-[hsl(var(--success))]" /> : <Copy size={12} />}
            {copied ? 'Copiado' : 'Copiar HTML'}
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4 flex justify-center bg-[hsl(var(--surface-2))] rounded-xl border border-[hsl(var(--border))]">
          <div
            className="bg-[hsl(var(--surface-1))] shadow-lg rounded-lg overflow-hidden transition-all duration-300 border border-[hsl(var(--border))]"
            style={{ width: vp === 'mobile' ? '375px' : '100%', maxWidth: '640px' }}
          >
            <iframe
              srcDoc={html}
              title="Preview"
              className="w-full border-0"
              style={{ minHeight: '600px' }}
              sandbox="allow-same-origin"
            />
          </div>
        </div>
      </div>
    </SidePanel>
  );
}

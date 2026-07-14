/** Builder page — editor visual drag & drop para plantillas email. */
'use client';
import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { PlantillaMensaje } from '@/types/crm';
import type { EmailBlock } from '@/components/crm/email-builder/blockTypes';
import { useEmailBuilder } from '@/components/crm/email-builder/useEmailBuilder';
import BlockPalette from '@/components/crm/email-builder/BlockPalette';
import EmailCanvas from '@/components/crm/email-builder/EmailCanvas';
import PropertiesPanel from '@/components/crm/email-builder/PropertiesPanel';
import BuilderToolbar from '@/components/crm/email-builder/BuilderToolbar';
import HtmlPreview from '@/components/crm/email-builder/HtmlPreview';

export default function EmailBuilderPage() {
  const { token } = useAuth();
  const router = useRouter();
  const params = useParams();
  const plantillaId = params?.id as string | undefined;
  const [templateName, setTemplateName] = useState('Nueva plantilla');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const builder = useEmailBuilder([]);
  const { setBlocks, getBlocksJson, selectedBlock, selectedId, updateBlockProps } = builder;

  useEffect(() => {
    if (!plantillaId || !token) { setLoading(false); return; }
    apiFetch<PlantillaMensaje>(`/crm/resources/plantillas/${plantillaId}`, { token })
      .then(data => { if (data) { setTemplateName(data.titulo); try { const parsed = JSON.parse(data.contenido_html || '[]'); if (Array.isArray(parsed) && parsed.length > 0) setBlocks(parsed); } catch {} } })
      .finally(() => setLoading(false));
  }, [plantillaId, setBlocks, token]);

  const handleSave = useCallback(async () => {
    if (!token || !plantillaId) return;
    setSaving(true);
    try {
      await apiFetch(`/crm/resources/plantillas/${plantillaId}`, { token, method: 'PATCH', body: { titulo: templateName, contenido_html: JSON.stringify(getBlocksJson()) }, headers: { 'Content-Type': 'application/json' } });
      toast.success('Plantilla guardada');
    } catch { toast.error('Error al guardar'); } finally { setSaving(false); }
  }, [getBlocksJson, plantillaId, templateName, token]);

  const handlePreview = useCallback(() => {
    const blocks = getBlocksJson();
    const body = blocks.map(b => renderBlockToHtml(b)).join('\n');
    setPreviewHtml(`<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head><body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 20px;"><tr><td align="center"><table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">${body}</table></td></tr></table></body></html>`);
    setShowPreview(true);
  }, [getBlocksJson]);

  if (loading) return <div className="flex items-center justify-center h-screen"><p className="text-sm text-[hsl(var(--text-secondary))]">Cargando editor...</p></div>;

  return (
    <div className="flex flex-col h-screen">
      <BuilderToolbar builder={builder} templateName={templateName} onNameChange={setTemplateName} onPreview={handlePreview} onSave={handleSave} onBack={() => router.push('/plataforma/crm/resources')} saving={saving} />
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[260px] border-r border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] overflow-y-auto p-4">
          <h2 className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white mb-3">Bloques</h2>
          <BlockPalette />
        </div>
        <EmailCanvas builder={builder} />
        <div className="w-[300px] border-l border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] overflow-y-auto p-4">
          <h2 className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white mb-3">Propiedades</h2>
          <PropertiesPanel block={selectedBlock} onUpdate={(props) => { if (selectedId) updateBlockProps(selectedId, props); }} />
        </div>
      </div>
      {showPreview && <HtmlPreview html={previewHtml} onClose={() => setShowPreview(false)} />}
    </div>
  );
}

function renderBlockToHtml(block: EmailBlock): string {
  const p = block.props;
  const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  switch (block.type) {
    case 'header': return `<tr><td style="padding:24px;text-align:${p.textAlign || 'center'};"><h2 style="margin:0;font-size:24px;font-weight:bold;color:${p.titleColor || '#001B48'};">${esc(String(p.title || ''))}</h2>${p.subtitle ? `<p style="margin:4px 0 0;font-size:14px;opacity:0.7;">${esc(String(p.subtitle))}</p>` : ''}</td></tr>`;
    case 'text': return `<tr><td style="padding:16px 24px;text-align:${p.textAlign || 'left'};font-size:15px;line-height:1.7;color:#374151;">${String(p.content || '')}</td></tr>`;
    case 'button': return `<tr><td style="padding:16px 24px;text-align:${p.align || 'center'};"><a href="${esc(String(p.url || '#'))}" style="display:inline-block;padding:12px 32px;background:${p.bgColor || '#018ABD'};color:${p.textColor || '#fff'};font-size:14px;font-weight:600;text-decoration:none;border-radius:${p.borderRadius ?? 10}px;">${esc(String(p.label || ''))}</a></td></tr>`;
    case 'image': return p.src ? `<tr><td style="padding:16px 24px;"><img src="${esc(String(p.src))}" alt="${esc(String(p.alt || ''))}" style="width:${p.width || '100%'};display:block;" /></td></tr>` : '';
    case 'divider': return `<tr><td style="padding:8px 24px;"><hr style="border:none;border-top:${p.thickness || 1}px ${p.style || 'solid'} ${p.color || '#e5e7eb'};width:${p.width || '100%'};" /></td></tr>`;
    case 'spacer': return `<tr><td style="height:${p.height || 24}px;"></td></tr>`;
    case 'verse': return `<tr><td style="padding:16px 24px;"><div style="background:#f0f5fa;border-radius:12px;padding:20px;text-align:${p.textAlign || 'center'};"><p style="margin:0;font-size:16px;font-style:italic;color:#004581;line-height:1.7;">&ldquo;${esc(String(p.text || ''))}&rdquo;</p>${p.reference ? `<p style="margin:8px 0 0;font-size:12px;font-weight:bold;color:#001B48;letter-spacing:2px;text-transform:uppercase;">&mdash; ${esc(String(p.reference))}</p>` : ''}</div></td></tr>`;
    case 'columns': return `<tr><td style="padding:16px 24px;"><table width="100%" cellpadding="0" cellspacing="0"><tr>${Array.from({ length: Number(p.count || 2) }).map(() => `<td style="width:${100 / Number(p.count || 2)}%;padding:0 4px;vertical-align:top;border:1px dashed #e5e7eb;"></td>`).join('')}</tr></table></td></tr>`;
    default: return '';
  }
}

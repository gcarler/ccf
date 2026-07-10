"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
    Archive,
    Layout,
    Image as ImageIcon,
    Save,
    RotateCcw,
    Download,
    Maximize2,
    Info,
    Link2,
    Plus
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

function formatBytes(bytes?: number): string {
    if (!bytes) return '0 KB';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface MediaItemData {
  id: string;
  url: string;
  filename: string;
  created_at?: string;
  alt_text?: string;
  section?: string;
  tags?: string[];
  mime_type?: string;
  mimetype?: string;
  file_size?: number;
  size?: number;
  status?: string;
}

export default function CmsMediaDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();

    const [item, setItem] = useState<MediaItemData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [tagsText, setTagsText] = useState('');

    useEffect(() => {
        if (!token || !id) return;
        const loadItem = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<MediaItemData>(`/cms/media/${id}`, { token }).catch(() => null);
                const normalized = data ? {
                    ...data,
                    alt_text: data.alt_text || data.filename || '',
                    section: data.section || 'general',
                    tags: Array.isArray(data.tags) ? data.tags : [],
                    mime_type: data.mime_type || data.mimetype || '',
                    file_size: data.file_size || data.size || 0,
                    status: data.status || 'active',
                } : null;                setItem(normalized);
                setTagsText(normalized?.tags?.join(', ') || '');
            } catch (err) {
                toast.error('Error al cargar detalle del recurso');
            } finally {
                setLoading(false);
            }
        };
        loadItem();
    }, [id, token]);

    const saveMetadata = async () => {
        if (!token || !item) return;
        setSaving(true);
        try {
            const tags = tagsText.split(',').map((tag) => tag.trim()).filter(Boolean);
            const updated = await apiFetch<MediaItemData>(`/cms/media/${id}`, {
                method: 'PATCH',
                token,
                body: {
                    alt_text: item.alt_text,
                    section: item.section || 'general',
                    tags,
                    filename: item.filename,
                },
            });
            setItem({ ...updated, tags });
            setTagsText(tags.join(', '));
            toast.success('Metadata del recurso guardada');
        } catch (err) {
            toast.error('Error al guardar metadata');
        } finally {
            setSaving(false);
        }
    };

    const copyUrl = async () => {
        if (!item?.url) return;
        await navigator.clipboard.writeText(item.url);
        toast.success('URL copiada');
    };

    const toggleArchiveItem = async () => {
        if (!token || !item) return;
        try {
            if (item.status === 'archived') {
                const updated = await apiFetch<MediaItemData>(`/cms/media/${id}`, { method: 'PATCH', token, body: { status: 'active' } });
                setItem({ ...item, ...updated, status: 'active' });
                toast.success('Recurso restaurado');
            } else {
                await apiFetch(`/cms/media/${id}`, { method: 'DELETE', token });
                setItem({ ...item, status: 'archived' });
                toast.success('Recurso archivado');
            }
        } catch (err) {
            toast.error('Error al actualizar estado del recurso');
        }
    };

    if (loading) return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Recuperando Recurso Multimedia...</div>;
    if (!item) return <div className="p-4 text-center font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Recurso multimedia no encontrado.</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', icon: Layout, href: '/plataforma/cms' },
                    { label: 'Media', icon: ImageIcon, href: '/plataforma/cms/media' },
                    { label: item.filename, icon: Info },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button onClick={toggleArchiveItem} className={`p-2 rounded-md transition-all ${item.status === 'archived' ? 'text-emerald-600 hover:bg-emerald-500/10' : 'text-amber-600 hover:bg-amber-500/10'}`}>
                            {item.status === 'archived' ? <RotateCcw size={20} /> : <Archive size={20} />}
                        </button>
                        <button onClick={saveMetadata} disabled={saving} className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2 disabled:opacity-50">
                            <Save size={14} /> {saving ? 'Guardando...' : 'Guardar Cambios'}
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-3">
                    <div className="space-y-3">
                        <div className="aspect-video rounded-lg bg-[hsl(var(--bg-muted))] overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 shadow-2xl relative group">
                            {item.mime_type?.startsWith('image/') ? (
                                <OptimizedImage
                                    src={item.url}
                                    alt={item.alt_text || item.filename || 'Media'}
                                    fill
                                    sizes="(max-width: 768px) 100vw, 50vw"
                                    className="w-full h-full object-contain"
                                />
                            ) : item.mime_type?.startsWith('video/') ? (
                                <video controls className="w-full h-full bg-black">
                                    <source src={item.url} type={item.mime_type} />
                                </video>
                            ) : item.mime_type?.startsWith('audio/') ? (
                                <div className="flex h-full items-center justify-center p-4">
                                    <audio controls src={item.url} className="w-full" />
                                </div>
                            ) : (
                                <div className="flex h-full items-center justify-center text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    Sin vista previa
                                </div>
                            )}
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <button className="p-4 bg-white/20 backdrop-blur-xl rounded-full text-white hover:scale-110 transition-transform">
                                    <Maximize2 size={24} />
                                </button>
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button onClick={() => item?.url && window.open(item.url, '_blank')} className="flex-1 py-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2 hover:bg-[hsl(var(--surface-1))] transition-all">
                                <Download size={14} /> Descargar Original
                            </button>
                            <button onClick={copyUrl} className="flex-1 py-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2 hover:bg-[hsl(var(--surface-1))] transition-all">
                                <Link2 size={14} /> Copiar URL
                            </button>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <section className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">TÃ­tulo del Recurso</label>
                                <input 
                                    value={item.alt_text || ''}
                                    onChange={(e) => setItem({ ...item, alt_text: e.target.value })}
                                    className="w-full bg-transparent border-b border-[hsl(var(--border))] dark:border-white/10 py-2 text-xl font-semibold outline-none focus:border-blue-500 transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Seccion CMS</label>
                                <input
                                    value={item.section || 'general'}
                                    onChange={(e) => setItem({ ...item, section: e.target.value })}
                                    className="w-full bg-transparent border-b border-[hsl(var(--border))] dark:border-white/10 py-2 text-sm font-bold outline-none focus:border-blue-500 transition-all"
                                />
                            </div>
                        </section>

                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">InformaciÃ³n TÃ©cnica</h3>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nombre de Archivo</p>
                                    <p className="text-xs font-bold truncate">{item.filename}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tipo de MIME</p>
                                    <p className="text-xs font-bold">{item.mime_type || 'sin tipo'}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">TamaÃ±o</p>
                                    <p className="text-xs font-bold">{formatBytes(item.file_size)}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Subido</p>
                                    <p className="text-xs font-bold">{item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}</p>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Etiquetas y OrganizaciÃ³n</h3>
                            <div className="space-y-4">
                                <input
                                    value={tagsText}
                                    onChange={(e) => setTagsText(e.target.value)}
                                    placeholder="hero, comunidad, campana"
                                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-4 py-3 text-sm font-bold outline-none focus:border-blue-500"
                                />
                                <div className="flex flex-wrap gap-2">
                                    {tagsText.split(',').map((tag: string) => tag.trim()).filter(Boolean).map((tag: string) => (
                                        <DSBadge key={tag} tone="blue" label={`#${tag}`} />
                                    ))}
                                    <button className="size-6 rounded-lg border border-dashed border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:border-blue-500 hover:text-[hsl(var(--primary))] transition-all">
                                        <Plus size={12} />
                                    </button>
                                </div>
                            </div>
                        </DSCard>
                    </div>
                </div>
            </main>
        </div>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Layout, 
    Image as ImageIcon, 
    Save, 
    ArrowLeft,
    Trash2,
    Download,
    Maximize2,
    Settings,
    Tag,
    Info,
    History,
    Link2,
    Plus
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

export default function CmsMediaDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [item, setItem] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadItem = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/cms/media/${id}`, { token }).catch(() => null);
                setItem(data || {
                    id,
                    title: 'Hero Banner Campaña 2026',
                    filename: 'banner-faro-2026.webp',
                    url: '/api/static/banner-faro-2026.webp',
                    mimetype: 'image/webp',
                    size: 1024 * 450, // 450KB
                    created_at: '2026-04-10T08:00:00Z',
                    tags: ['marketing', 'faro', 'hero']
                });
            } catch (err) {
                toast.error('Error al cargar detalle del recurso');
            } finally {
                setLoading(false);
            }
        };
        loadItem();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Recuperando Recurso Multimedia...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', icon: Layout, href: '/cms' },
                    { label: 'Media', icon: ImageIcon, href: '/cms/media' },
                    { label: item.filename, icon: Info },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="p-2 text-rose-500 hover:bg-rose-500/10 rounded-xl transition-all">
                            <Trash2 size={20} />
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Save size={14} /> Guardar Cambios
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12">
                    <div className="space-y-8">
                        <div className="aspect-video rounded-[2.5rem] bg-slate-900 overflow-hidden border border-slate-200 dark:border-white/10 shadow-2xl relative group">
                            <img 
                                src={item.url} 
                                alt={item.title}
                                className="w-full h-full object-contain"
                                onError={(e) => {
                                    (e.target as any).src = 'https://placehold.co/800x450/1e293b/64748b?text=Media+Preview';
                                }}
                            />
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <button className="p-4 bg-white/20 backdrop-blur-xl rounded-full text-white hover:scale-110 transition-transform">
                                    <Maximize2 size={24} />
                                </button>
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button className="flex-1 py-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-slate-50 transition-all">
                                <Download size={14} /> Descargar Original
                            </button>
                            <button className="flex-1 py-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-slate-50 transition-all">
                                <Link2 size={14} /> Copiar URL
                            </button>
                        </div>
                    </div>

                    <div className="space-y-8">
                        <section className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Título del Recurso</label>
                                <input 
                                    value={item.title}
                                    onChange={(e) => setItem({ ...item, title: e.target.value })}
                                    className="w-full bg-transparent border-b border-slate-200 dark:border-white/10 py-2 text-2xl font-black outline-none focus:border-blue-500 transition-all"
                                />
                            </div>
                        </section>

                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Información Técnica</h3>
                            <div className="grid grid-cols-2 gap-6">
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Nombre de Archivo</p>
                                    <p className="text-xs font-bold truncate">{item.filename}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Tipo de MIME</p>
                                    <p className="text-xs font-bold">{item.mimetype}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Tamaño</p>
                                    <p className="text-xs font-bold">{(item.size / 1024).toFixed(2)} KB</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Subido</p>
                                    <p className="text-xs font-bold">{new Date(item.created_at).toLocaleDateString()}</p>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Etiquetas y Organización</h3>
                            <div className="space-y-4">
                                <div className="flex flex-wrap gap-2">
                                    {item.tags?.map((tag: string) => (
                                        <DSBadge key={tag} tone="blue" label={`#${tag}`} />
                                    ))}
                                    <button className="size-6 rounded-lg border border-dashed border-slate-300 flex items-center justify-center text-slate-400 hover:border-blue-500 hover:text-blue-500 transition-all">
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

"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import { 
    Image as ImageIcon, 
    Save, 
    Trash2, 
    ChevronLeft, 
    MoreHorizontal, 
    Download, 
    Copy, 
    Shield, 
    Tag, 
    Layout, 
    Bot, 
    Sparkles, 
    Maximize2, 
    Info,
    Activity,
    ExternalLink,
    Zap
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

export default function MediaDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [item, setItem] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('detalles');
    const [isSaving, setIsSaving] = useState(false);
    const [previewScale, setPreviewScale] = useState(1);

    const fetchMedia = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>(`/cms/media`, { token });
            const found = data.find(m => m.id.toString() === id);
            
            if (found) {
                setItem({
                    ...found,
                    dimensions: '1920x1080', // Mock metadata
                    file_size: '2.4 MB',      // Mock metadata
                    created_at: '2026-04-10',
                    last_used: 'Hace 2 horas en /inicio'
                });
            } else {
                addToast('Recurso no encontrado', 'error');
            }
        } catch (err) {
            addToast('Error al cargar multimedia', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, id, addToast]);

    useEffect(() => { fetchMedia(); }, [fetchMedia]);

    const handleSave = async () => {
        if (!item || !token) return;
        setIsSaving(true);
        try {
            await apiFetch(`/cms/media/${id}`, {
                method: 'PATCH',
                token,
                body: { 
                    alt_text: item.alt_text,
                    section: item.section,
                    tags: Array.isArray(item.tags) ? item.tags : item.tags.split(',').map((t: string) => t.trim())
                }
            });
            addToast('Metadatos actualizados', 'success');
        } catch {
            addToast('Error al guardar cambios', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        addToast('URL copiada al portapapeles', 'success');
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: ImageIcon }, { label: 'Media', icon: Layout }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="size-16 relative">
                    <div className="absolute inset-0 border-4 border-blue-500/10 rounded-full" />
                    <div className="absolute inset-0 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
                <p className="text-[10px] font-black text-slate-400 tracking-[0.4em] uppercase">Renderizando Asset...</p>
            </div>
        </CrmShell>
    );

    if (!item) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: ImageIcon }, { label: 'Media', icon: Layout }, { label: 'Error' }]}>
            <div className="p-12 text-center">
                <h1 className="text-2xl font-black italic uppercase">Asset Perdido</h1>
                <p className="text-slate-500 mt-2">No se pudo encontrar el recurso multimedia solicitado.</p>
                <button onClick={() => router.push('/cms/media')} className="mt-6 px-8 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest">Regresar a Biblioteca</button>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Layout },
                { label: 'CMS Engine', icon: Zap },
                { label: 'Media Library', icon: ImageIcon },
                { label: 'Asset Detail', icon: Info }
            ]}
        >
            <div className="flex flex-col h-full bg-[#f8f9fa] dark:bg-[#0a0a0b]">
                
                {/* ─── Header ─── */}
                <div className="px-6 py-4">
                    <button 
                        onClick={() => router.push('/cms/media')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Biblioteca Multimedia
                    </button>

                    <AdminHero 
                        eyebrow={`${item.section.toUpperCase()} · ID: #${id}`}
                        title={item.alt_text || 'Asset sin nombre'}
                        description="Gestiona los metadatos de accesibilidad, etiquetas de organización y uso de este recurso en la plataforma."
                        tags={[...item.tags]}
                        watchers={['Curación Visual', 'IT Dept']}
                        primaryAction={{ 
                            label: 'Copiar URL', 
                            icon: Copy, 
                            onClick: () => copyToClipboard(item.url) 
                        }}
                        secondaryAction={{
                            label: 'Descargar Original',
                            icon: Download,
                            onClick: () => window.open(item.url, '_blank')
                        }}
                    />
                </div>

                {/* ─── Workspace ─── */}
                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
                        
                        {/* ── Left Column: Preview & Visual Ops ── */}
                        <div className="lg:col-span-7 space-y-6">
                            
                            {/* Main Preview Container */}
                            <div className="bg-white dark:bg-white/5 p-4 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm relative overflow-hidden group">
                                <div className="absolute top-8 right-8 z-10 hidden group-hover:flex gap-2">
                                    <button 
                                        onClick={() => setPreviewScale(prev => prev === 1 ? 1.5 : 1)}
                                        className="p-3 bg-white/90 dark:bg-black/80 backdrop-blur-xl rounded-2xl shadow-xl text-slate-600 dark:text-white hover:scale-110 transition-all"
                                    >
                                        <Maximize2 size={18} />
                                    </button>
                                </div>
                                <div className="relative aspect-video rounded-[2.5rem] overflow-hidden bg-slate-100 dark:bg-black/40 border border-slate-50 dark:border-white/5">
                                    <Image 
                                        src={item.url} 
                                        alt={item.alt_text} 
                                        fill 
                                        className="object-contain transition-transform duration-700"
                                        style={{ transform: `scale(${previewScale})` }}
                                        unoptimized
                                    />
                                </div>
                                
                                {/* Info Strip */}
                                <div className="mt-4 px-4 py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-6">
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Dimensiones</p>
                                            <p className="text-xs font-black text-slate-800 dark:text-white uppercase">{item.dimensions}</p>
                                        </div>
                                        <div className="w-px h-6 bg-slate-100 dark:bg-white/10" />
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Peso</p>
                                            <p className="text-xs font-black text-slate-800 dark:text-white uppercase">{item.file_size}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 text-[10px] font-black uppercase tracking-widest rounded-full">WebP Optimized</span>
                                    </div>
                                </div>
                            </div>

                            {/* Usage Analytics */}
                            <div className="p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                    <Activity size={14} className="text-blue-500" /> Presencia en Ecosistema
                                </h3>
                                <div className="space-y-3">
                                    {[
                                        { app: 'Landing Faro', path: '/inicio', type: 'Hero Image' },
                                        { app: 'CMS v2', path: '/nosotros', type: 'Secondary Section' }
                                    ].map((use, i) => (
                                        <div key={i} className="p-4 bg-slate-50 dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5 flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <div className="size-8 rounded-lg bg-blue-600/10 text-blue-500 flex items-center justify-center"><Layout size={16} /></div>
                                                <div>
                                                    <p className="text-sm font-black">{use.app}</p>
                                                    <p className="text-[10px] text-slate-400 font-bold uppercase">{use.path}</p>
                                                </div>
                                            </div>
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest italic">{use.type}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* ── Right Column: Metadata & AI ── */}
                        <div className="lg:col-span-5 space-y-6">
                            
                            {/* Management Card */}
                            <div className="p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-8">
                                <h3 className="text-xl font-black italic uppercase flex items-center gap-3">
                                    <Settings className="text-slate-400" /> Metadatos de Asset
                                </h3>

                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Texto Alternativo (Accesibilidad)</label>
                                        <input 
                                            value={item.alt_text}
                                            onChange={(e) => setItem({ ...item, alt_text: e.target.value })}
                                            className="w-full px-5 py-4 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-bold"
                                            placeholder="Describre la imagen..."
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sección Asignada</label>
                                        <select 
                                            value={item.section}
                                            onChange={(e) => setItem({ ...item, section: e.target.value })}
                                            className="w-full px-5 py-4 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-bold appearance-none"
                                        >
                                            <option value="general">General</option>
                                            <option value="hero">Hero / Masthead</option>
                                            <option value="events">Eventos</option>
                                            <option value="members">Socios / Miembros</option>
                                        </select>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Etiquetas de Organización</label>
                                        <div className="flex flex-wrap gap-2 mb-3">
                                            {item.tags.map((tag: string) => (
                                                <span key={tag} className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-[10px] font-black uppercase tracking-widest rounded-lg flex items-center gap-1">
                                                    <Tag size={10} /> {tag}
                                                </span>
                                            ))}
                                            <button className="px-3 py-1 border border-dashed border-slate-200 text-slate-400 text-[10px] font-black rounded-lg hover:border-blue-400 hover:text-blue-500">+</button>
                                        </div>
                                    </div>
                                </div>

                                <button 
                                    onClick={handleSave}
                                    disabled={isSaving}
                                    className="w-full py-4 bg-slate-900 text-white dark:bg-white dark:text-black rounded-2xl text-[11px] font-black uppercase tracking-widest hover:scale-[1.01] transition-transform flex items-center justify-center gap-3"
                                >
                                    {isSaving ? 'Sincronizando...' : 'Guardar Metadata'}
                                </button>
                            </div>

                            {/* AI Vision Card */}
                            <div className="p-8 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-[3rem] shadow-2xl relative overflow-hidden group">
                                <Bot size={120} className="absolute -bottom-8 -right-8 opacity-10 rotate-12 transition-transform group-hover:scale-110" />
                                <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-blue-200 mb-4 flex items-center gap-2">
                                    <Bot size={14} /> Optimus Vision AI
                                </h3>
                                <p className="text-sm font-medium leading-relaxed italic opacity-90 mb-6">
                                    "Analizando imagen... Se detecta 'Púlpito', 'Gente', 'Luces Cálidas'. Sugerencia de Alt: 'Pastor predicando en auditorio iluminado durante servicio dominical'."
                                </p>
                                <button className="w-full py-3 bg-white/20 hover:bg-white/30 backdrop-blur-md rounded-2xl text-[10px] font-black uppercase tracking-widest border border-white/20 transition-all flex items-center justify-center gap-2">
                                    <Sparkles size={12} /> Aplicar Sugerencia IA
                                </button>
                            </div>

                            <div className="flex items-center justify-center gap-4">
                                <button
                                    onClick={() => addToast('Recurso en uso. No se puede eliminar.', 'warning')}
                                    className="p-4 bg-rose-50 dark:bg-rose-900/10 text-rose-500 rounded-2xl hover:bg-rose-100 transition-colors"
                                >
                                    <Trash2 size={20} />
                                </button>
                                <button className="flex-1 py-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2">
                                    <ExternalLink size={14} /> Abrir en nueva pestaña
                                </button>
                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

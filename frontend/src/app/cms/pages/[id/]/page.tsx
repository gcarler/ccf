"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    FileText, 
    Globe, 
    Shield, 
    Clock, 
    Eye, 
    Settings, 
    ChevronLeft, 
    MoreHorizontal, 
    ExternalLink, 
    History, 
    CheckCircle2, 
    Zap, 
    Search,
    Edit3,
    Activity,
    Bot,
    Sparkles,
    Layout,
    Globe2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { listCmsPages, patchCmsPage, workflowCmsPage } from '@/lib/cms/v2';
import { CmsPage } from '@/types/cms-v2';

export default function CmsPageDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [page, setPage] = useState<CmsPage | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('configuracion');
    const [isSaving, setIsSaving] = useState(false);
    const [siteKey] = useState('faro'); // Default for now

    const fetchPage = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            // The API usually works with slugs in v2, but we might have an ID.
            // For now, let's list all and find by ID to be safe, or try to get by slug if ID is a string.
            const pages = await listCmsPages(siteKey, token);
            const found = pages.find(p => p.id.toString() === id || p.slug === id);
            
            if (found) {
                setPage(found);
            } else {
                throw new Error('Pagina no encontrada');
            }
        } catch (err) {
            addToast('Error al cargar la página', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, id, siteKey, addToast]);

    useEffect(() => { fetchPage(); }, [fetchPage]);

    const handleSave = async () => {
        if (!page || !token) return;
        setIsSaving(true);
        try {
            await patchCmsPage(siteKey, page.slug, {
                title: page.title,
                slug: page.slug,
                seo_json: page.seo_json
            }, token);
            addToast('Cambios guardados correctamente', 'success');
        } catch {
            addToast('Error al guardar cambios', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleWorkflowAction = async (action: any) => {
        if (!page || !token) return;
        try {
            const updated = await workflowCmsPage(siteKey, page.slug, action, 'Cambio de estado desde panel de detalle', token);
            setPage(updated);
            addToast(`Estado actualizado a ${action.replace('_', ' ')}`, 'success');
        } catch {
            addToast('Error al ejecutar acción de flujo', 'error');
        }
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: Globe }, { label: 'Páginas', icon: FileText }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Globe2 size={48} className="text-blue-500 animate-spin-slow opacity-20" />
                <p className="text-[10px] font-black text-slate-400 tracking-[0.4em] uppercase">Rastreando Metadatos...</p>
            </div>
        </CrmShell>
    );

    if (!page) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: Globe }, { label: 'Páginas', icon: FileText }, { label: 'Error' }]}>
            <div className="p-12 text-center">
                <h1 className="text-2xl font-black italic uppercase">Página Inexistente</h1>
                <p className="text-slate-500 mt-2">El recurso solicitado no pudo ser localizado en el servidor CMS.</p>
                <button onClick={() => router.push('/cms/pages')} className="mt-6 px-8 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest">Regresar a Gestión</button>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Globe },
                { label: 'CMS Engine', icon: Zap },
                { label: 'Gestión de Páginas', icon: FileText },
                { label: page.title, icon: Edit3 }
            ]}
        >
            <div className="flex flex-col h-full bg-[#f4f7f5] dark:bg-[#0c0d0c]">
                
                {/* ─── Hero / Header ─── */}
                <div className="px-6 py-4">
                    <button 
                        onClick={() => router.push('/cms/pages')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Gestión de Páginas
                    </button>

                    <AdminHero 
                        eyebrow={`v2 · /${page.slug}`}
                        title={page.title}
                        description={page.seo_json?.description as string || 'Administra el contenido, el SEO y el flujo de publicación de esta página.'}
                        tags={['Landing', page.status?.toUpperCase()]}
                        watchers={['Marketing Team', 'IT Admin']}
                        primaryAction={{ 
                            label: 'Ver Builder', 
                            icon: Layout, 
                            onClick: () => router.push(`/cms/builder?site=${siteKey}&page=${page.slug}`) 
                        }}
                        secondaryAction={{
                            label: 'Ver Pública',
                            icon: ExternalLink,
                            onClick: () => window.open(`/${page.slug}`, '_blank')
                        }}
                    />
                </div>

                {/* ─── Content Area ─── */}
                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto space-y-6">
                        
                        {/* Tabs */}
                        <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/5 mb-6">
                            {[
                                { id: 'configuracion', label: 'Estructura y SEO', icon: Settings },
                                { id: 'historial', label: 'Versiones', icon: History },
                                { id: 'analitica', label: 'Desempeño', icon: Activity },
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={clsx(
                                        "flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-widest transition-all relative",
                                        activeTab === tab.id ? "text-emerald-600" : "text-slate-400 hover:text-slate-600"
                                    )}
                                >
                                    <tab.icon size={14} />
                                    {tab.label}
                                    {activeTab === tab.id && (
                                        <motion.div layoutId="cms-tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600" />
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                            
                            {/* Main Config Column */}
                            <div className="lg:col-span-8 space-y-6">
                                <AnimatePresence mode="wait">
                                    {activeTab === 'configuracion' && (
                                        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                                            
                                            {/* SEO metadata */}
                                            <div className="bg-white dark:bg-white/5 p-8 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-8">
                                                <h3 className="text-xl font-black italic uppercase flex items-center gap-3">
                                                    <Globe2 className="text-blue-500" /> Metadatos SEO
                                                </h3>
                                                
                                                <div className="space-y-6">
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Título de Página</label>
                                                        <input 
                                                            value={page.title}
                                                            onChange={(e) => setPage({ ...page, title: e.target.value })}
                                                            className="w-full px-5 py-4 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-bold"
                                                        />
                                                    </div>

                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Slug (URL)</label>
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-slate-400 text-sm font-bold">faro.ccf/</span>
                                                            <input 
                                                                value={page.slug}
                                                                onChange={(e) => setPage({ ...page, slug: e.target.value })}
                                                                className="flex-1 px-5 py-4 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-bold"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Meta Descripción</label>
                                                        <textarea 
                                                            value={(page.seo_json?.description as string) || ''}
                                                            onChange={(e) => setPage({ ...page, seo_json: { ...page.seo_json, description: e.target.value } })}
                                                            rows={3}
                                                            className="w-full px-5 py-4 rounded-2xl bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-emerald-500/20 text-sm font-bold resize-none"
                                                        />
                                                    </div>
                                                </div>

                                                <button 
                                                    onClick={handleSave}
                                                    disabled={isSaving}
                                                    className="w-full py-4 bg-slate-900 text-white dark:bg-white dark:text-black rounded-2xl text-[11px] font-black uppercase tracking-widest hover:scale-[1.01] transition-transform flex items-center justify-center gap-3"
                                                >
                                                    {isSaving ? <Loader2 className="animate-spin" size={16} /> : <CheckCircle2 size={16} />}
                                                    Sincronizar Cambios
                                                </button>
                                            </div>

                                            {/* Preview Card */}
                                            <div className="p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6">
                                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Previsualización en Buscadores</h3>
                                                <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-3xl border border-slate-100 dark:border-white/5 space-y-1 max-w-xl">
                                                    <p className="text-xs text-slate-500 truncate">https://faro.ccf/{page.slug}</p>
                                                    <p className="text-xl text-[#1a0dab] dark:text-[#8ab4f8] font-medium hover:underline cursor-pointer truncate">{page.title}</p>
                                                    <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">{(page.seo_json?.description as string) || 'Agrega una meta descripción para mejorar el CTR en buscadores...'}</p>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    {activeTab === 'historial' && (
                                        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-4">
                                            <div className="bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 overflow-hidden">
                                                <div className="px-8 py-6 bg-slate-50 dark:bg-black/20 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                                                    <h3 className="text-[11px] font-black uppercase tracking-widest">Historial de Versiones</h3>
                                                    <button className="text-[10px] font-black text-blue-600 hover:underline uppercase tracking-widest">Ver todo</button>
                                                </div>
                                                <div className="divide-y divide-slate-100 dark:divide-white/5">
                                                    {[
                                                        { v: 'v3.2', date: 'Hoy, 10:24 AM', user: 'Admin', note: 'Ajuste de SEO' },
                                                        { v: 'v3.1', date: 'Ayer', user: 'Soporte', note: 'Cambio de imagen de fondo' },
                                                        { v: 'v3.0', date: '12 Abr 2026', user: 'Admin', note: 'Publicación Inicial' },
                                                    ].map(ver => (
                                                        <div key={ver.v} className="p-6 flex items-center gap-6 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer group">
                                                            <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center font-black text-xs text-slate-500 group-hover:text-blue-600 transition-colors">{ver.v}</div>
                                                            <div className="flex-1">
                                                                <p className="text-sm font-black">{ver.note}</p>
                                                                <p className="text-[10px] text-slate-400 font-bold uppercase">{ver.date} · por {ver.user}</p>
                                                            </div>
                                                            <button className="px-4 py-2 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-black uppercase tracking-wide hover:bg-white transition-all">Restaurar</button>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Sidebar Options Column */}
                            <div className="lg:col-span-4 space-y-6">
                                
                                {/* Status & Workflow */}
                                <div className="p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6">
                                    <div>
                                        <div className="flex items-center justify-between mb-6">
                                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Estado Actual</h3>
                                            <span className={clsx(
                                                "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest shrink-0",
                                                page.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                                            )}>
                                                {page.status}
                                            </span>
                                        </div>
                                        
                                        <div className="space-y-2">
                                            {[
                                                { id: 'submit_review', label: 'Pedir Revisión', icon: Eye, color: 'blue' },
                                                { id: 'publish', label: 'Publicar Ahora', icon: Zap, color: 'emerald' },
                                                { id: 'archive', label: 'Archivar', icon: Trash2, color: 'slate' },
                                            ].map(btn => (
                                                <button
                                                    key={btn.id}
                                                    onClick={() => handleWorkflowAction(btn.id)}
                                                    className={clsx(
                                                        "w-full flex items-center gap-3 px-5 py-4 rounded-2xl border transition-all text-left group",
                                                        `hover:bg-${btn.color}-50 dark:hover:bg-${btn.color}-500/10 hover:border-${btn.color}-500/30`
                                                    )}
                                                >
                                                    <btn.icon size={16} className={`text-slate-400 group-hover:text-${btn.color}-500 transition-colors`} />
                                                    <span className="text-[11px] font-black uppercase tracking-widest text-slate-500 group-hover:text-slate-800 dark:group-hover:text-white transition-colors">
                                                        {btn.label}
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="p-8 bg-gradient-to-br from-[#1a1c1e] to-[#0f1113] text-white rounded-[3rem] shadow-2xl relative overflow-hidden">
                                    <Bot size={80} className="absolute -bottom-4 -right-4 opacity-5 rotate-12" />
                                    <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-blue-400 mb-4 flex items-center gap-2">
                                        <Sparkles size={14} /> AI Recommendation
                                    </h3>
                                    <p className="text-xs font-medium leading-relaxed italic opacity-80">
                                        "El slug '/{page.slug}' tiene un buen rendimiento semántico, pero la meta descripción podría incluir la palabra 'comunidad' para mejorar el ranking SEO en el sector."
                                    </p>
                                    <button className="mt-6 w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all">
                                        Aplicar sugerencia
                                    </button>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

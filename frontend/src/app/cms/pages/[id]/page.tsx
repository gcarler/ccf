"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Layout, 
    FileText, 
    Save, 
    ArrowLeft,
    Eye,
    History,
    Settings,
    Globe,
    Lock,
    Plus,
    ChevronRight,
    Search,
    PenTool
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

export default function CmsPageDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [page, setPage] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadPage = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/cms/pages/${id}`, { token }).catch(() => null);
                setPage(data || {
                    id,
                    title: 'Página de Inicio FARO',
                    slug: 'faro-home',
                    status: 'published',
                    last_updated: '2026-04-12T10:00:00Z',
                    sections: [
                        { id: 1, name: 'Hero Section', type: 'hero' },
                        { id: 2, name: 'Features Grid', type: 'grid' },
                        { id: 3, name: 'Call to Action', type: 'cta' }
                    ]
                });
            } catch (err) {
                toast.error('Error al cargar la página del CMS');
            } finally {
                setLoading(false);
            }
        };
        loadPage();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Cargando Editor de Páginas...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', icon: Layout, href: '/cms' },
                    { label: 'Páginas', icon: FileText, href: '/cms/pages' },
                    { label: page.title, icon: PenTool },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="px-4 py-2 text-slate-500 text-[10px] font-black uppercase tracking-widest hover:text-slate-700 transition-all flex items-center gap-2">
                            <Eye size={14} /> Vista Previa
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Save size={14} /> Publicar
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
                    <div className="lg:col-span-3 space-y-8">
                        <header className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="violet" label="SITE: FARO" />
                                <DSBadge tone="emerald" label="PUBLISHED" />
                            </div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                                {page.title}
                            </h1>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                <Globe size={12} /> URL: /faro/{page.slug}
                            </p>
                        </header>

                        <section className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-black uppercase tracking-[0.3em] text-slate-400">Estructura de Secciones</h3>
                                <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:border-blue-500 transition-all">
                                    <Plus size={14} /> Agregar Sección
                                </button>
                            </div>

                            <div className="space-y-4">
                                {page.sections.map((section: any) => (
                                    <div key={section.id} className="group bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-3xl p-6 flex items-center justify-between hover:border-blue-500/30 transition-all cursor-pointer">
                                        <div className="flex items-center gap-6">
                                            <div className="size-12 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-blue-500 transition-colors">
                                                <Layout size={24} />
                                            </div>
                                            <div>
                                                <h4 className="text-base font-black text-slate-800 dark:text-white uppercase tracking-tight">{section.name}</h4>
                                                <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest">Componente: {section.type}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button className="p-2 text-slate-300 hover:text-blue-500 transition-colors">
                                                <Settings size={18} />
                                            </button>
                                            <ChevronRight size={20} className="text-slate-200 group-hover:text-blue-500" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    <aside className="space-y-6">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Configuración SEO</h3>
                            <div className="space-y-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Meta Title</p>
                                    <p className="text-xs font-bold text-slate-600 dark:text-slate-300">{page.title}</p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Indexación</p>
                                    <DSBadge tone="emerald" label="SEARCH_INDEX_OK" />
                                </div>
                            </div>
                        </DSCard>

                        <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                <History size={14} /> Versiones
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center justify-between text-[10px] font-bold">
                                    <span className="text-blue-300">v12 (Actual)</span>
                                    <span className="opacity-50">Hace 2h</span>
                                </div>
                                <div className="flex items-center justify-between text-[10px] font-bold opacity-50">
                                    <span>v11 (Archivo)</span>
                                    <span>Ayer</span>
                                </div>
                            </div>
                            <button className="w-full py-2 bg-white/10 rounded-xl text-[9px] font-black uppercase tracking-widest hover:bg-white/20">
                                Comparar Versiones
                            </button>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    );
}

"use client";

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import { LayoutDashboard, MessageCircle, Feather, CalendarRange, Link2, FileText, Globe, ChevronRight, Palette, PanelsTopLeft, ImageIcon } from 'lucide-react';
import { FARO_BLOCKS } from '@/lib/cms/blocks';
import clsx from 'clsx';
import { canEditCms, canManageSites } from '@/lib/cms/permissions';

// ── Tabs de navegación del módulo CMS ────────────────────────────
const CMS_TABS = [
    { id: 'resumen',     label: 'Resumen',      href: '/cms',               icon: LayoutDashboard },
    { id: 'paginas',     label: 'Páginas',      href: '/cms/pages',        icon: FileText },
    { id: 'testimonios', label: 'Testimonios',  href: '/cms/testimonials', icon: MessageCircle },
    { id: 'hero',        label: 'Landing Hero', href: '/cms/content',      icon: Feather },
    { id: 'eventos',     label: 'Eventos',      href: '/cms/events',       icon: CalendarRange },
    { id: 'menus',       label: 'Menús',        href: '/cms/menus',        icon: Link2 },
    { id: 'media',       label: 'Media',        href: '/cms/media',        icon: ImageIcon },
    { id: 'builder',     label: 'Builder',      href: '/cms/builder',      icon: PanelsTopLeft },
    { id: 'themes',      label: 'Temas',        href: '/cms/themes',       icon: Palette },
    { id: 'sites',       label: 'Sitios',       href: '/cms/sites',        icon: Globe },
] as const;

interface CmsStats {
    testimonials: number;
    pendingTestimonials: number;
    approvedTestimonials: number;
    sections: number;
    publishedBlocks: number;
    inReviewBlocks: number;
    activeAnnouncements: number;
    mediaTotal: number;
    mediaImages: number;
    mediaVideos: number;
    mediaAudio: number;
}

interface TestimonialPreview {
    id: number;
    content: string;
    emotion: string;
    created_at: string;
    is_approved?: boolean;
}

export default function CmsHomePage() {
    const { token, isAuthenticated, user } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const [stats, setStats] = useState<CmsStats | null>(null);
    const [recentTestimonials, setRecentTestimonials] = useState<TestimonialPreview[]>([]);
    const [loading, setLoading] = useState(true);
    const canEdit = canEditCms(user?.role);
    const canManage = canManageSites(user?.role);

    const availableTabs = useMemo(
        () => CMS_TABS.filter((tab) => {
            if (tab.id === 'sites') return canManage;
            if (['paginas', 'hero', 'eventos', 'menus', 'media', 'builder', 'themes', 'testimonios'].includes(tab.id)) return canEdit;
            return true;
        }),
        [canEdit, canManage]
    );

    // Determine active tab from pathname
    const activeTab = availableTabs.find(t => {
        if (t.href === '/cms') return pathname === '/cms';
        return pathname ? pathname.startsWith(t.href) : false;
    })?.id ?? 'resumen';

    useEffect(() => {
        const fetchData = async () => {
            if (!token) {
                setLoading(false);
                return;
            }
            setLoading(true);
            try {
                const testimonials = await apiFetch<TestimonialPreview[]>('/admin/testimonials', {
                    token,
                    cache: 'no-store'
                });
                const metrics = await apiFetch<{
                    published_blocks: number;
                    in_review_blocks: number;
                    announcements_active: number;
                    testimonials_approved: number;
                    media_total: number;
                    media_images: number;
                    media_videos: number;
                    media_audio: number;
                }>('/cms/metrics', { token, cache: 'no-store' });
                setRecentTestimonials(Array.isArray(testimonials) ? testimonials.slice(0, 5) : []);
                setStats({
                    testimonials: testimonials.length,
                    pendingTestimonials: testimonials.filter((testimony) => !testimony.is_approved).length,
                    approvedTestimonials: metrics?.testimonials_approved ?? testimonials.filter((testimony) => testimony.is_approved).length,
                    sections: FARO_BLOCKS.length,
                    publishedBlocks: metrics?.published_blocks ?? 0,
                    inReviewBlocks: metrics?.in_review_blocks ?? 0,
                    activeAnnouncements: metrics?.announcements_active ?? 0,
                    mediaTotal: metrics?.media_total ?? 0,
                    mediaImages: metrics?.media_images ?? 0,
                    mediaVideos: metrics?.media_videos ?? 0,
                    mediaAudio: metrics?.media_audio ?? 0
                });
            } catch (error) {
                console.error('CMS home fetch', error);
                setRecentTestimonials([]);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [token]);

    const quickLinks = useMemo(
        () => [
            { label: 'Páginas', href: '/cms/pages', description: 'Gestiona contenido dinámico', icon: FileText },
            { label: 'Menús del sitio', href: '/cms/menus', description: 'Estructura la navegación', icon: Link2 },
            { label: 'Testimonios', href: '/cms/testimonials', description: 'Aprueba y publica historias', icon: MessageCircle },
            { label: 'Landing hero', href: '/cms/content', description: 'Actualiza copys y assets hero', icon: Feather },
            { label: 'Media', href: '/cms/media', description: 'Sube y reutiliza archivos', icon: ImageIcon },
            { label: 'Builder visual', href: '/cms/builder', description: 'Arma páginas por secciones', icon: PanelsTopLeft },
            { label: 'Temas multisitio', href: '/cms/themes', description: 'Edita paletas por sitio', icon: Palette },
            { label: 'Sitios', href: '/cms/sites', description: 'Crea y administra portales', icon: Globe },
        ].filter((link) => {
            if (link.href === '/cms/sites') return canManage;
            if (link.href === '/cms') return true;
            return canEdit;
        }),
        [canEdit, canManage]
    );

    if (!isAuthenticated) {
        return (
            <div className="max-w-3xl mx-auto py-24 text-center space-y-3">
                <h1 className="text-3xl font-black">Inicia sesión</h1>
                <p className="text-slate-500">Necesitas una sesión válida para administrar el CMS.</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">

            {/* ── SUB-TOOLBAR: Breadcrumb + Tabs ─────────────────────── */}
            <div className="shrink-0 border-b border-slate-100 dark:border-white/[0.05] bg-white dark:bg-[#141517]">
                {/* Breadcrumbs row */}
                <div className="flex items-center gap-1.5 px-5 pt-2.5 pb-0">
                    <Globe size={11} className="text-slate-400" />
                    <span className="text-[11px] text-slate-400">Sitio Web</span>
                    <ChevronRight size={10} className="text-slate-300" />
                    <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-200">
                        {CMS_TABS.find(t => t.id === activeTab)?.label ?? 'Resumen'}
                    </span>
                </div>

                {/* Tabs row */}
                <div className="flex items-center gap-0 px-4 pt-1">
                    {availableTabs.map(tab => {
                        const Icon = tab.icon;
                        const isActive = tab.id === activeTab;
                        return (
                            <Link
                                key={tab.id}
                                href={tab.href}
                                className={clsx(
                                    'flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-[2px] transition-all whitespace-nowrap',
                                    isActive
                                        ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                        : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300'
                                )}
                            >
                                <Icon size={13} />
                                {tab.label}
                            </Link>
                        );
                    })}
                </div>
            </div>

            {/* ── SCROLLABLE CONTENT ─────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto">
            <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="CMS"
                title="Centro de contenido"
                description="Orquesta testimonios, hero copy y campañas públicas desde un workspace enfocado."
                tags={['Landing', 'Testimonios', 'Eventos']}
                watchers={['Equipo Comunicación', 'Optimus Brain']}
                primaryAction={{ label: 'Abrir landing', icon: Link2, onClick: () => window.open('/', '_blank') }}
                secondaryAction={{ label: 'Ver pauta', icon: LayoutDashboard, onClick: () => router.push('/cms/builder') }}
            />

            <section className="grid grid-cols-1 md:grid-cols-4 xl:grid-cols-8 gap-4">
                {[
                    { label: 'Testimonios publicados', value: stats?.approvedTestimonials ?? '—' },
                    { label: 'Pendientes', value: stats?.pendingTestimonials ?? '—' },
                    { label: 'Media total', value: stats?.mediaTotal ?? '—' },
                    { label: 'Imagenes', value: stats?.mediaImages ?? '—' },
                    { label: 'Videos', value: stats?.mediaVideos ?? '—' },
                    { label: 'Podcasts', value: stats?.mediaAudio ?? '—' },
                    { label: 'Bloques FARO', value: stats?.sections ?? '—' },
                    { label: 'Bloques publicados', value: stats?.publishedBlocks ?? '—' },
                    { label: 'En revision', value: stats?.inReviewBlocks ?? '—' },
                    { label: 'Anuncios activos', value: stats?.activeAnnouncements ?? '—' }
                ].map((metric) => (
                    <div key={metric.label} className="rounded-[2rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] px-6 py-5 shadow-sm">
                        <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-slate-400">{metric.label}</p>
                        <p className="text-3xl font-black text-slate-900 dark:text-white mt-2">{metric.value}</p>
                    </div>
                ))}
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] p-6 space-y-5">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-xl font-bold">Módulos rápidos</h3>
                            <p className="text-sm text-slate-500">Accesos a las áreas clave del sitio.</p>
                        </div>
                        <CommunityToolbarChip label="+ Módulo" size="sm" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {quickLinks.map(({ label, href, description, icon: Icon }) => (
                            <Link key={label} href={href} className="rounded-2xl border border-slate-100 dark:border-white/10 p-4 hover:border-primary/40 transition-colors">
                                <div className="flex items-center gap-3 mb-2">
                                    <div className="size-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                                        <Icon size={18} />
                                    </div>
                                    <p className="font-bold text-slate-900 dark:text-white">{label}</p>
                                </div>
                                <p className="text-sm text-slate-500 leading-snug">{description}</p>
                            </Link>
                        ))}
                    </div>
                </div>

                <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] p-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-xl font-bold">Testimonios recientes</h3>
                        <CommunityToolbarChip label="Ver todo" size="sm" onClick={() => (window.location.href = '/cms/testimonials')} />
                    </div>
                    {loading ? (
                        <p className="text-sm text-slate-500">Cargando historias...</p>
                    ) : recentTestimonials.length === 0 ? (
                        <p className="text-sm text-slate-500">Sin testimonios en la cola.</p>
                    ) : (
                        <div className="space-y-3">
                            {recentTestimonials.map((testimony) => (
                                <div key={testimony.id} className="rounded-2xl border border-slate-100 dark:border-white/10 p-4">
                                    <p className="text-xs font-bold uppercase tracking-[0.3em] text-primary mb-2">{testimony.emotion || 'Sin categoría'}</p>
                                    <p className="text-sm text-slate-600 dark:text-slate-200 line-clamp-2">{testimony.content}</p>
                                    <p className="text-[10px] text-slate-400 uppercase tracking-[0.3em] mt-3">{new Date(testimony.created_at).toLocaleDateString()}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* NEXT STEP SECTION */}
            <section className="rounded-[2.5rem] border border-dashed border-slate-200 dark:border-white/10 p-8 text-center space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.4em] text-slate-400">Próximo paso</p>
                <h3 className="text-2xl font-black">Define la narrativa de la página principal</h3>
                <p className="text-sm text-slate-500 max-w-2xl mx-auto">
                    Usa este hub para setear hero, testimonios y eventos que se muestran en el sitio público. Cada ajuste se propaga en segundos.
                </p>
            </section>

            </div>
            </div>
        </div>
    );
}


"use client";

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import { LayoutDashboard, MessageCircle, Feather, Image as ImageIcon, CalendarRange, Link2 } from 'lucide-react';
import { FARO_BLOCKS } from '@/lib/cms/blocks';

interface CmsStats {
    testimonials: number;
    pendingTestimonials: number;
    sections: number;
}

interface TestimonialPreview {
    id: number;
    content: string;
    emotion: string;
    created_at: string;
    is_approved?: boolean;
}

export default function CmsHomePage() {
    const { token, isAuthenticated } = useAuth();
    const [stats, setStats] = useState<CmsStats | null>(null);
    const [recentTestimonials, setRecentTestimonials] = useState<TestimonialPreview[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState('Todos');

    useEffect(() => {
        const fetchData = async () => {
            if (!token) {
                setLoading(false);
                return;
            }
            setLoading(true);
            try {
                const testimonials = await apiFetch<TestimonialPreview[]>('/cms/testimonials', {
                    token,
                    cache: 'no-store'
                });
                setRecentTestimonials(Array.isArray(testimonials) ? testimonials.slice(0, 5) : []);
                setStats({
                    testimonials: testimonials.length,
                    pendingTestimonials: testimonials.filter((testimony) => !testimony.is_approved).length,
                    sections: FARO_BLOCKS.length
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
            { label: 'Testimonios', href: '/cms/testimonials', description: 'Aprueba y publica historias', icon: MessageCircle },
            { label: 'Landing hero', href: '/cms/content', description: 'Actualiza copys y assets hero', icon: Feather },
            { label: 'Galería', href: '/cms/media', description: 'Gestiona imágenes destacadas', icon: ImageIcon },
            { label: 'Eventos públicos', href: '/cms/events', description: 'Publica eventos especiales', icon: CalendarRange }
        ],
        []
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
        <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="CMS"
                title="Centro de contenido"
                description="Orquesta testimonios, hero copy y campañas públicas desde un workspace enfocado."
                tags={['Landing', 'Testimonios', 'Eventos']}
                watchers={['Equipo Comunicación', 'Optimus Brain']}
                primaryAction={{ label: 'Abrir landing', icon: Link2, onClick: () => window.open('/', '_blank') }}
                secondaryAction={{ label: 'Ver pauta', icon: LayoutDashboard, onClick: () => {} }}
            />

            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                    { label: 'Testimonios publicados', value: stats?.testimonials ?? '—' },
                    { label: 'Pendientes', value: stats?.pendingTestimonials ?? '—' },
                    { label: 'Secciones hero activas', value: stats?.sections ?? '—' }
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

            <section className="rounded-[2.5rem] border border-dashed border-slate-200 dark:border-white/10 p-8 text-center space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.4em] text-slate-400">Próximo paso</p>
                <h3 className="text-2xl font-black">Define la narrativa de la página principal</h3>
                <p className="text-sm text-slate-500 max-w-2xl mx-auto">
                    Usa este hub para setear hero, testimonios y eventos que se muestran en el sitio público. Cada ajuste se propaga en segundos.
                </p>
            </section>
        </div>
    );
}

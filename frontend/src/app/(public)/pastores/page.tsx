'use client';

import React, { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronRight, Cross, Sparkles } from 'lucide-react';
import RichText from "@/components/public/RichText";
import { useCmsV2Page } from '@/hooks/useCmsV2Page';

import { sanitizeCmsHtml } from '@/lib/cms/sanitize';

type CmsPastor = {
    id?: string;
    slug: string;
    name: string;
    role?: string;
    image?: string;
    photo_url?: string;
    story?: string;
    bio_short?: string;
    isMain?: boolean;
    is_main_pastor?: boolean;
};

export default function PastoresIndexPage() {
    const heroPage = useCmsV2Page('pastors');
    const heroCms = heroPage?.blocks?.hero;
    const feedCms = heroPage?.blocks?.feed;
    const pastorsPage = useCmsV2Page('pastors');
    const pastorsCms = pastorsPage?.blocks?.pastors;

    const heroContent = heroCms?.content ? JSON.parse(heroCms.content) : null;
    const feedContent = feedCms?.content ? JSON.parse(feedCms.content) : null;
    const pastors = useMemo(() => {
        const list = (pastorsCms as unknown as { pastors?: CmsPastor[] } | null)?.pastors;
        return Array.isArray(list) ? list : [];
    }, [pastorsCms]);
    const heroBadge = feedContent?.hero_badge || "Conoce a nuestro equipo pastoral";
    const heroTitle = heroContent?.title || feedContent?.hero_title || "Liderazgo Pastoral";
    const heroDescription = heroContent?.description || feedContent?.hero_description || "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.";
    const heroBgImage = heroContent?.bg_image || null;
    const loadingLabel = feedContent?.loading_label || "Cargando...";
    const emptyTitle = feedContent?.empty_title || "No hay líderes pastorales registrados aún.";
    const cardCta = feedContent?.card_cta || "Conocer más";
    const principalLabel = feedContent?.principal_label || "Pastor Principal";

    return (
        <main className="pt-24 pb-4">
            {/* ── Hero Section ── */}
            <section className="relative overflow-hidden min-h-[70vh] md:min-h-[85vh] flex flex-col">
                {heroBgImage ? (
                    <>
                        <div
                            className="absolute inset-0 bg-cover"
                            style={{ backgroundImage: `url('${heroBgImage}')`, backgroundPosition: "center 20%", backgroundAttachment: "fixed", filter: "brightness(0.28) saturate(0.5)" }}
                        />
                        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-[hsl(var(--bg-primary))]" />
                    </>
                ) : (
                    <div className="absolute inset-0 pointer-events-none">
                        <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-[hsl(var(--primary))/0.08] to-transparent blur-3xl" />
                        <div className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full bg-gradient-to-tr from-[hsl(var(--secondary))/0.06] to-transparent blur-3xl" />
                    </div>
                )}

                <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 mt-auto text-center relative z-10 pb-12 md:pb-16">
                    <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-white/10 backdrop-blur-sm text-white/70 text-xs font-bold uppercase tracking-widest mb-5 border border-white/20 shadow-lg">
                        <Sparkles size={12} className="animate-pulse" /> {heroBadge}
                    </div>
                    <h1 className={`text-4xl md:text-5xl lg:text-6xl font-black tracking-tight mb-5 leading-[1.05] ${heroBgImage ? "text-white" : "text-[hsl(var(--text-primary))] dark:text-white"}`}>
                        {heroTitle}
                    </h1>
                    {heroBgImage ? (
                        <p className="text-base md:text-lg max-w-2xl mx-auto font-medium leading-relaxed" style={{ color: 'white' }}
                            dangerouslySetInnerHTML={{ __html: sanitizeCmsHtml(heroDescription) }} />
                    ) : (
                        <RichText
                            html={heroDescription}
                            className="text-base md:text-lg max-w-2xl mx-auto font-medium leading-relaxed text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                        />
                    )}
                    <div className="flex items-center justify-center gap-3 mt-8">
                        <div className="h-px w-12 bg-gradient-to-r from-transparent to-white/20" />
                        <Cross size={14} className="text-white/30" />
                        <div className="h-px w-12 bg-gradient-to-l from-transparent to-white/20" />
                    </div>
                </div>
            </section>

            {/* ── Pastors Grid ── */}
            <section className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 pt-[3cm] pb-20 md:pb-28">
                {!pastorsCms ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="w-8 h-8 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
                        <span className="sr-only">{loadingLabel}</span>
                    </div>
                ) : pastors.length === 0 ? (
                    <p className="text-center text-[hsl(var(--text-secondary))] py-20">{emptyTitle}</p>
                ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 md:gap-6">
                    {pastors.map((pastor, idx) => (
                        <div key={pastor.id || pastor.slug} className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[#0f1117] rounded-2xl overflow-hidden border border-[hsl(var(--border))]/70 dark:border-white/[0.06] shadow-lg shadow-black/10/40 dark:shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:shadow-2xl hover:shadow-[hsl(var(--primary))/0.15] dark:hover:shadow-[0_16px_48px_rgba(0,0,0,0.5)] hover:-translate-y-1.5 transition-all duration-500 flex flex-col"
                            style={{ animationDelay: `${idx * 100}ms` }}>

                            {/* Image */}
                            <Link href={`/pastores/${pastor.slug}`} className="relative h-52 w-full bg-[hsl(var(--surface-2))] dark:bg-[#0a0c12] overflow-hidden block">
                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-transparent pointer-events-none z-10" />
                                {pastor.photo_url || pastor.image ? (
                                    <Image
                                        src={pastor.photo_url || pastor.image || ""}
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top transition-transform duration-700 group-hover:scale-110"
                                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                                    />
                                ) : (
                                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05]">
                                        <span className="text-4xl font-bold text-[hsl(var(--primary))/0.3]">{pastor.name.charAt(0)}</span>
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-[#0a0c12]/90 via-black/30 to-transparent" />
                                {pastor.is_main_pastor && (
                                    <div className="absolute top-3 left-3 z-20">
                                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-bold uppercase tracking-wider shadow-lg">
                                            <Sparkles size={8} /> {principalLabel}
                                        </span>
                                    </div>
                                )}
                                <div className="absolute bottom-4 left-5 right-5 z-20">
                                    <h3 className="text-lg font-bold text-white drop-shadow-sm">{pastor.name}</h3>
                                    <p className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] drop-shadow-sm">{pastor.role || 'Pastor'}</p>
                                </div>
                                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-[hsl(var(--primary))/0.15] to-transparent rounded-bl-[100%] pointer-events-none" />
                            </Link>

                            {/* Content */}
                            <div className="p-4 flex-1 flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#0f1117]">
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-3 flex-1 leading-relaxed line-clamp-3">
                                    {pastor.bio_short || pastor.story || ''}
                                </p>

                                {/* CTA */}
                                <Link href={`/pastores/${pastor.slug}`} className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))] dark:border-white/[0.06]">
                                    <span className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] group-hover:tracking-[0.15em] transition-all duration-300">
                                        {cardCta}
                                    </span>
                                    <div className="w-9 h-9 rounded-xl bg-[hsl(var(--primary))/0.08] dark:bg-[hsl(var(--primary))/0.12] flex items-center justify-center group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all duration-300 group-hover:shadow-lg group-hover:shadow-[hsl(var(--primary))/0.3]">
                                        <ChevronRight size={15} className="group-hover:translate-x-0.5 transition-transform duration-300" />
                                    </div>
                                </Link>
                            </div>

                            <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-[hsl(var(--border))]/50 dark:ring-white/[0.04] group-hover:ring-[hsl(var(--primary))/0.3] transition-all duration-500 pointer-events-none" />
                        </div>
                    ))}
                </div>
                )}
            </section>
        </main>
    );
}

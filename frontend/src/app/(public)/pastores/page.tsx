'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronRight, Sparkles } from 'lucide-react';
import RichText from "@/components/public/RichText";
import { useCmsV2Page } from '@/hooks/useCmsV2Page';
import PublicHeroWithSlides from '@/components/public/PublicHeroWithSlides';
import { getPublicPastoralTeam, type PastoralProfile } from '@/lib/cms/v2';
import { SITE_KEY } from '@/lib/site-config';

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
    const page = useCmsV2Page('pastors');
    const heroCms = page?.blocks?.hero;
    const feedCms = page?.blocks?.feed;

    const heroContent = heroCms?.content ? JSON.parse(heroCms.content) : null;
    const feedContent = feedCms?.content ? JSON.parse(feedCms.content) : null;

    // Fetch pastors from the pastoral-team API (source of truth)
    const [apiPastors, setApiPastors] = useState<PastoralProfile[]>([]);
    const [apiLoading, setApiLoading] = useState(true);
    useEffect(() => {
        getPublicPastoralTeam(SITE_KEY)
            .then((data) => setApiPastors(Array.isArray(data) ? data : []))
            .catch(() => setApiPastors([]))
            .finally(() => setApiLoading(false));
    }, []);

    const pastors = useMemo(() => {
        // Use API data as source of truth; fall back to CMS block if API empty
        if (apiPastors.length > 0) {
            return apiPastors.map((p) => ({
                id: p.id,
                slug: p.slug,
                name: p.name,
                role: p.role ?? undefined,
                photo_url: p.photo_url ?? undefined,
                bio_short: p.bio_short ?? undefined,
                is_main_pastor: p.is_main_pastor,
            }));
        }
        // Fallback: read from CMS content block
        const pastorsCms = page?.blocks?.pastors;
        const list = (pastorsCms as unknown as { pastors?: CmsPastor[] } | null)?.pastors;
        return Array.isArray(list) ? list : [];
    }, [apiPastors, page]);
    const heroBadge = typeof feedContent?.hero_badge === "string" ? feedContent.hero_badge : "";
    const heroTitle = typeof heroContent?.title === "string" ? heroContent.title : "";
    const heroDescription = typeof heroContent?.description === "string" ? heroContent.description : "";
    const heroBgImage = heroContent?.bg_image ?? null;
    const loadingLabel = typeof feedContent?.loading_label === "string" ? feedContent.loading_label : "";
    const emptyTitle = typeof feedContent?.empty_title === "string" ? feedContent.empty_title : "";
    const cardCta = typeof feedContent?.card_cta === "string" ? feedContent.card_cta : "";
    const principalLabel = typeof feedContent?.principal_label === "string" ? feedContent.principal_label : "";

    const hasHero = heroTitle || heroDescription || heroBadge;

    return (
        <main className="pt-24 pb-4 overflow-hidden">
            {/* ── Hero Section ── */}
            {hasHero && (
                <PublicHeroWithSlides
                    eyebrow={heroBadge}
                    title={heroTitle}
                    description={heroDescription}
                    slides={heroBgImage ? [{ src: String(heroBgImage), alt: heroTitle || "Hero pastoral" }] : []}
                />
            )}

            {/* ── Pastors Grid ── */}
            <section className="ccf-section ccf-container pt-[3cm]">
                {apiLoading && !pastors.length ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="w-8 h-8 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
                        <span className="sr-only">{loadingLabel}</span>
                    </div>
                ) : pastors.length === 0 ? (
                    emptyTitle && <p className="text-center text-[hsl(var(--text-secondary))] py-20">{emptyTitle}</p>
                ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
                    {pastors.map((pastor, idx) => (
                        <div key={pastor.id || pastor.slug} className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[#0f1117] rounded-2xl overflow-hidden border border-[hsl(var(--border))]/70 dark:border-white/[0.06] shadow-lg shadow-black/10/40 dark:shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:shadow-2xl hover:shadow-[hsl(var(--primary))/0.15] dark:hover:shadow-[0_16px_48px_rgba(0,0,0,0.5)] hover:-translate-y-1.5 transition-all duration-500 flex flex-col"
                            style={{ animationDelay: `${idx * 100}ms` }}>

                            {/* Image */}
                            <Link href={`/pastores/${pastor.slug}`} className="relative h-52 w-full bg-[hsl(var(--surface-2))] dark:bg-[#0a0c12] overflow-hidden block">
                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-transparent pointer-events-none z-10" />
                                {pastor.photo_url || (pastor as CmsPastor).image ? (
                                    <Image
                                        src={pastor.photo_url || (pastor as CmsPastor).image || ""}
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
                                {pastor.is_main_pastor && principalLabel && (
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
                                    {pastor.bio_short || (pastor as CmsPastor).story || ''}
                                </p>

                                {/* CTA */}
                                <Link href={`/pastores/${pastor.slug}`} className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))] dark:border-white/[0.06]">
                                    {cardCta && (
                                        <span className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] group-hover:tracking-[0.15em] transition-all duration-300">
                                            {cardCta}
                                        </span>
                                    )}
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

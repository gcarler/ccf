'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronRight, Sparkles, Instagram, Facebook, Twitter } from 'lucide-react';
import { useCmsV2Page } from '@/hooks/useCmsV2Page';
import PublicHeroWithSlides from '@/components/public/PublicHeroWithSlides';
import { getPublicPastoralTeam, type PastoralProfile } from '@/lib/cms/v2';
import { SITE_KEY } from '@/lib/site-config';
import { safeJsonParse } from '@/lib/safeJson';

function plainText(value: string | undefined): string {
    return (value || '')
        .replace(/<[^>]*>/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function formatSocialUrl(url: string | undefined | null, platform: "instagram" | "facebook" | "twitter"): string | null {
    if (!url || !url.trim()) return null;
    const clean = url.trim();
    if (clean.startsWith("@")) {
        const handle = clean.substring(1);
        if (platform === "instagram") return `https://instagram.com/${handle}`;
        if (platform === "facebook") return `https://facebook.com/${handle}`;
        if (platform === "twitter") return `https://x.com/${handle}`;
    }
    if (!/^https?:\/\//i.test(clean)) {
        return `https://${clean}`;
    }
    return clean;
}

type CmsPastor = {
    id?: string;
    slug: string;
    name: string;
    role?: string;
    image?: string;
    photo_url?: string;
    story?: string;
    bio_short?: string;
    social_instagram?: string;
    social_facebook?: string;
    social_twitter?: string;
    isMain?: boolean;
    is_main_pastor?: boolean;
};

export default function PastoresIndexPage() {
    const page = useCmsV2Page('pastors');
    const heroCms = page?.blocks?.hero;
    const feedCms = page?.blocks?.feed;

    const heroContent = safeJsonParse<Record<string, unknown>>(heroCms?.content, {});
    const feedContent = safeJsonParse<Record<string, unknown>>(feedCms?.content, {});

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
                social_instagram: p.social_instagram ?? undefined,
                social_facebook: p.social_facebook ?? undefined,
                social_twitter: p.social_twitter ?? undefined,
                is_main_pastor: p.is_main_pastor,
            }));
        }
        // Fallback: read from CMS content block
        const pastorsCms = page?.blocks?.pastors;
        const rawList = (pastorsCms as unknown as { pastors?: CmsPastor[]; items?: CmsPastor[]; parsed?: { items?: CmsPastor[]; pastors?: CmsPastor[] } } | null);
        const list = rawList?.items || rawList?.pastors || rawList?.parsed?.items || rawList?.parsed?.pastors || [];
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
            <section className="ccf-section ccf-container">
                {apiLoading && !pastors.length ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="w-8 h-8 rounded-full border-2 border-site-primary border-t-transparent animate-spin" />
                        <span className="sr-only">{loadingLabel}</span>
                    </div>
                ) : pastors.length === 0 ? (
                    emptyTitle && <p className="text-center text-site-on-surface-variant py-20">{emptyTitle}</p>
                ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
                    {pastors.map((pastor, idx) => (
                        <div key={pastor.id || pastor.slug} className="group relative bg-site-surface-container-low rounded-2xl overflow-hidden border border-site-outline-variant/30 shadow-lg shadow-black/5 hover:shadow-2xl hover:shadow-site-primary/10 hover:-translate-y-1.5 transition-all duration-500 flex flex-col"
                            style={{ animationDelay: `${idx * 100}ms` }}>

                            {/* Image */}
                            <Link href={`/pastores/${pastor.slug}`} className="relative h-52 w-full bg-site-surface-container overflow-hidden block">
                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-site-primary/10 to-transparent pointer-events-none z-10" />
                                {pastor.photo_url || (pastor as CmsPastor).image ? (
                                    <Image
                                        src={pastor.photo_url || (pastor as CmsPastor).image || ""}
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top transition-transform duration-700 group-hover:scale-110"
                                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                                    />
                                ) : (
                                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-site-primary/10 to-site-secondary/5">
                                        <span className="text-4xl font-bold text-site-primary/30">{pastor.name.charAt(0)}</span>
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
                                {pastor.is_main_pastor && principalLabel && (
                                    <div className="absolute top-3 left-3 z-20">
                                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-site-primary text-site-on-primary text-2xs font-bold uppercase tracking-wider shadow-lg">
                                            <Sparkles size={8} /> {principalLabel}
                                        </span>
                                    </div>
                                )}
                                <div className="absolute bottom-4 left-5 right-5 z-20">
                                    <h3 className="text-lg font-bold text-white drop-shadow-sm">{pastor.name}</h3>
                                    <p className="text-xs font-bold uppercase tracking-widest text-site-primary drop-shadow-sm">{pastor.role || 'Pastor'}</p>
                                </div>
                                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-site-primary/15 to-transparent rounded-bl-[100%] pointer-events-none" />
                            </Link>

                            {/* Content */}
                            <div className="p-4 flex-1 flex flex-col bg-site-surface-container-low">
                                <p className="text-sm text-site-on-surface mb-3 flex-1 leading-relaxed line-clamp-3">
                                    {plainText(pastor.bio_short || (pastor as CmsPastor).story)}
                                </p>

                                {/* CTA & Social Links */}
                                {(() => {
                                    const igUrl = formatSocialUrl(pastor.social_instagram, "instagram");
                                    const fbUrl = formatSocialUrl(pastor.social_facebook, "facebook");
                                    const twUrl = formatSocialUrl(pastor.social_twitter, "twitter");
                                    const hasSocial = Boolean(igUrl || fbUrl || twUrl);
                                    return (
                                        <div className="flex items-center justify-between pt-3 border-t border-site-outline-variant/20">
                                            <div className="flex items-center gap-1.5">
                                                {igUrl && (
                                                    <a
                                                        href={igUrl}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-sm"
                                                        title="Instagram"
                                                        aria-label={`${pastor.name} en Instagram`}
                                                    >
                                                        <Instagram size={13} />
                                                    </a>
                                                )}
                                                {fbUrl && (
                                                    <a
                                                        href={fbUrl}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-sm"
                                                        title="Facebook"
                                                        aria-label={`${pastor.name} en Facebook`}
                                                    >
                                                        <Facebook size={13} />
                                                    </a>
                                                )}
                                                {twUrl && (
                                                    <a
                                                        href={twUrl}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-sm"
                                                        title="X (Twitter)"
                                                        aria-label={`${pastor.name} en X`}
                                                    >
                                                        <Twitter size={13} />
                                                    </a>
                                                )}
                                                {cardCta && (
                                                    <Link href={`/pastores/${pastor.slug}`} className={`text-xs font-bold uppercase tracking-widest text-site-primary group-hover:tracking-[0.15em] transition-all duration-300 ${hasSocial ? 'ml-1' : ''}`}>
                                                        {cardCta}
                                                    </Link>
                                                )}
                                            </div>
                                            <Link href={`/pastores/${pastor.slug}`} className="w-9 h-9 rounded-xl bg-site-primary/10 flex items-center justify-center group-hover:bg-site-primary group-hover:text-site-on-primary transition-all duration-300 group-hover:shadow-lg group-hover:shadow-site-primary/30">
                                                <ChevronRight size={15} className="group-hover:translate-x-0.5 transition-transform duration-300" />
                                            </Link>
                                        </div>
                                    );
                                })()}
                            </div>

                            <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-site-outline-variant/30 group-hover:ring-site-primary/30 transition-all duration-500 pointer-events-none" />
                        </div>
                    ))}
                </div>
                )}
            </section>
        </main>
    );
}

'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft, Quote, BookOpen, Cross, Sparkles, Instagram, Heart } from 'lucide-react';
import { getPublicPastoralTeam, type PastoralProfile } from '@/lib/cms/v2';
import { SITE_KEY, SITE_NAME } from '@/lib/site-config';
import ShareButtons from '@/components/public/ShareButtons';
import { useCmsV2Page } from '@/hooks/useCmsV2Page';
import { sanitizeCmsHtml } from '@/lib/cms/sanitize';

function getString(props: Record<string, unknown> | undefined, key: string): string {
    const value = props?.[key];
    return typeof value === "string" ? value : "";
}

function getStringArray(props: Record<string, unknown> | undefined, key: string): string[] {
    const value = props?.[key];
    if (!Array.isArray(value)) return [];
    return value.filter((item): item is string => typeof item === "string");
}

function applyTemplate(template: string, vars: Record<string, string>): string {
    return template.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
}

function plainText(value: string | undefined): string {
    return (value || "")
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
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
    bio_full?: string;
    social_instagram?: string;
    social_facebook?: string;
    social_twitter?: string;
    is_main_pastor?: boolean;
};

export default function PastorDetailPage() {
    const params = useParams();
    const router = useRouter();
    const slug = params?.slug as string;

    const pastorsPage = useCmsV2Page('pastors');
    const pastorsCms = pastorsPage?.blocks?.pastors;
    const cms: Record<string, unknown> = {
        badge_label: 'Liderazgo Pastoral',
        role_fallback: 'Pastor',
        quote_subtitle: 'Filosofía de vida',
        tags: ['Pastor', 'Líder', 'Consejero'],
        motto_label: 'Versículo Lema',
        story_title: 'Su Historia',
        story_subtitle: 'Testimonio de vida y ministerio',
        cta_eyebrow: 'Comunidad de Fe',
        cta_description: '¿Deseas conectar con el Pastor {first_name} o saber más sobre su ministerio?',
        cta_primary_label: 'Conocer al equipo',
        cta_secondary_label: 'Nuestras sedes',
        ...(pastorsPage?.blocks?.detail_template as Record<string, unknown> | undefined),
    };
    const [apiPastors, setApiPastors] = useState<PastoralProfile[]>([]);
    const [apiLoading, setApiLoading] = useState(true);

    useEffect(() => {
        getPublicPastoralTeam(SITE_KEY)
            .then((data) => setApiPastors(Array.isArray(data) ? data : []))
            .catch(() => setApiPastors([]))
            .finally(() => setApiLoading(false));
    }, []);

    const pastor = useMemo(() => {
        const apiPastor = apiPastors.find((profile) => profile.slug === slug);
        if (apiPastor) {
            return {
                id: apiPastor.id,
                slug: apiPastor.slug,
                name: apiPastor.name,
                role: apiPastor.role ?? undefined,
                photo_url: apiPastor.photo_url ?? undefined,
                bio_short: apiPastor.bio_short ?? undefined,
                bio_full: apiPastor.bio_full ?? undefined,
                social_instagram: apiPastor.social_instagram ?? undefined,
                social_facebook: apiPastor.social_facebook ?? undefined,
                social_twitter: apiPastor.social_twitter ?? undefined,
                is_main_pastor: apiPastor.is_main_pastor,
            } satisfies CmsPastor;
        }

        const rawList = (pastorsCms as unknown as { pastors?: CmsPastor[]; items?: CmsPastor[]; parsed?: { items?: CmsPastor[]; pastors?: CmsPastor[] } } | null);
        const list = rawList?.items || rawList?.pastors || rawList?.parsed?.items || rawList?.parsed?.pastors || [];
        if (!Array.isArray(list)) return null;
        return list.find(p => p.slug === slug || p.slug?.replace(/-gutierrez|-herrera/g, '') === slug?.replace(/-gutierrez|-herrera/g, '')) || null;
    }, [apiPastors, pastorsCms, slug]);

    if (apiLoading && !pastor) {
        return (
            <div className="min-h-screen bg-site-background flex items-center justify-center pt-[88px]">
                <div className="w-10 h-10 rounded-full border-2 border-site-primary border-t-transparent animate-spin" />
            </div>
        );
    }

    if (!pastor) {
        return (
            <div className="min-h-screen bg-site-background flex items-center justify-center pt-[88px]">
                <div className="text-center space-y-6">
                    <div className="w-20 h-20 rounded-[1.25rem] bg-site-primary/10 flex items-center justify-center mx-auto ring-1 ring-site-primary/20">
                        <Heart size={28} className="text-site-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-site-on-surface">Pastor no encontrado</h1>
                        <p className="text-sm text-site-on-surface-variant mt-1">El enlace que buscas no existe o ha sido movido.</p>
                    </div>
                    <button
                        onClick={() => router.push('/pastores')}
                        className="px-6 py-3 rounded-xl bg-site-primary text-site-on-primary text-sm font-bold uppercase tracking-wider hover:scale-105 transition-all shadow-xl shadow-site-primary/25"
                    >
                        Ver todos los pastores
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-site-background selection:bg-site-primary/20 selection:text-site-primary overflow-hidden">

            {/* ── Fondo Ambiental ── */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
                <div className="absolute -top-60 -right-60 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-site-primary/5 to-transparent blur-[150px]" />
                <div className="absolute -bottom-60 -left-60 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-site-secondary/5 to-transparent blur-[120px]" />
                <div className="absolute top-1/3 left-1/3 w-96 h-96 rounded-full bg-site-primary/5 blur-[100px]" />
            </div>

            <main className="relative z-10 pt-[88px]">

                {/* ── Breadcrumb / Back link ── */}
                <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 pt-6 pb-2 flex items-center justify-between flex-wrap gap-3">
                    <Link
                        href="/pastores"
                        className="inline-flex items-center gap-2 text-sm font-bold text-site-on-surface-variant hover:text-site-primary transition-colors group"
                    >
                        <ArrowLeft size={15} className="group-hover:-translate-x-1 transition-transform" />
                        Todos los pastores
                    </Link>
                    <ShareButtons title={`${pastor.name} — ${pastor.role || 'Pastor'} | ${SITE_NAME}`} />
                </div>

                {/* ════════════════════════════════════════
                   HERO — LAYOUT MODERNO
                   ════════════════════════════════════════ */}
                <section className="relative pt-6 pb-8 md:pt-8 md:pb-12 lg:pt-10 lg:pb-16">
                    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="flex flex-col lg:flex-row gap-10 lg:gap-16 xl:gap-20 items-center lg:items-start">

                            {/* ── Foto ── */}
                            <div className="w-full max-w-[400px] lg:w-5/12 relative shrink-0">
                                <div className="relative aspect-[4/5] rounded-[1.25rem] overflow-hidden shadow-2xl shadow-black/15 ring-1 ring-site-outline-variant/30">
                                    {(pastor.photo_url || pastor.image) ? (
                                        <Image
                                            src={pastor.photo_url || pastor.image || ""}
                                            alt={pastor.name}
                                            fill
                                            className="object-cover object-top"
                                            priority
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-site-primary/10 to-site-secondary/5">
                                            <span className="text-6xl font-bold text-site-primary/30">{pastor.name?.charAt(0) || '?'}</span>
                                        </div>
                                    )}
                                    {/* Gradiente inferior */}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                                    {/* Esquina */}
                                    <div className="absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl from-white/[0.08] to-transparent rounded-bl-[100%]" />
                                </div>
                                {/* Aro decorativo */}
                                <div className="absolute -top-4 -right-4 w-full h-full rounded-[1.5rem] border border-site-primary/10 -z-10 hidden lg:block" />
                                <div className="absolute -bottom-4 -left-4 w-3/4 h-3/4 rounded-[1.5rem] border border-site-primary/5 -z-10 hidden lg:block" />
                            </div>

                            {/* ── Info ── */}
                            <div className="w-full lg:w-7/12 space-y-8">
                                {/* Badge */}
                                <div>
                                    {getString(cms, "badge_label") && (
                                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-site-primary/15 to-site-secondary/10 border border-site-primary/20 text-site-primary text-2xs font-bold uppercase tracking-[0.2em] mb-5 shadow-lg shadow-site-primary/5">
                                            <Sparkles size={11} className="animate-pulse" /> {getString(cms, "badge_label")}
                                        </div>
                                    )}
                                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-site-on-surface tracking-tight leading-[1.05] mb-3">
                                        {pastor.name}
                                    </h1>
                                    <div className="h-1 w-16 rounded-full bg-gradient-to-r from-site-primary to-site-secondary mb-4" />
                                    <p className="text-lg md:text-xl font-bold text-site-primary tracking-wide">
                                        {pastor.role || getString(cms, "role_fallback")}
                                    </p>
                                </div>

                                {/* ── Quote ── */}
                                <div className="relative p-6 md:p-7 bg-site-surface-container-low rounded-[1.25rem] border border-site-outline-variant/30 shadow-lg shadow-black/5">
                                    <Quote className="absolute top-5 left-5 text-site-primary/20" size={40} />
                                    <p className="relative z-10 text-base md:text-lg text-site-on-surface font-medium italic leading-relaxed pt-8 pl-1">
                                        &ldquo;{plainText(pastor.bio_short || pastor.story)}&rdquo;
                                    </p>
                                    <div className="flex items-center gap-3 mt-5 pl-1">
                                        <div className="h-px flex-1 bg-gradient-to-r from-site-primary/30 to-transparent max-w-[80px]" />
                                        {getString(cms, "quote_subtitle") && (
                                            <span className="text-2xs font-bold uppercase tracking-widest text-site-on-surface-variant">{getString(cms, "quote_subtitle")}</span>
                                        )}
                                    </div>
                                </div>

                                {/* ── Stats / Tags ── */}
                                {(() => {
                                    const tagLabels = getStringArray(cms, "tags");
                                    const tagColors = [
                                        'bg-site-primary/10 text-site-primary border-site-primary/20',
                                        'bg-site-secondary-container text-site-on-secondary-container border-site-outline-variant/20',
                                        'bg-site-tertiary-container text-site-on-tertiary-container border-site-outline-variant/20',
                                    ];
                                    if (tagLabels.length === 0) return null;
                                    return (
                                        <div className="flex flex-wrap gap-3">
                                            {tagLabels.map((label, i) => (
                                                <span
                                                    key={i}
                                                    className={`px-3 py-1.5 rounded-lg border text-2xs font-bold uppercase tracking-wider ${tagColors[i % tagColors.length]}`}
                                                >
                                                    {label}
                                                </span>
                                            ))}
                                        </div>
                                    );
                                })()}

                                {/* ── Redes Sociales ── siempre visibles, monocromáticas */}
                                {(() => {
                                    const instagramUrl = formatSocialUrl(pastor.social_instagram, "instagram");
                                    const facebookUrl = formatSocialUrl(pastor.social_facebook, "facebook");
                                    const twitterUrl = formatSocialUrl(pastor.social_twitter, "twitter");
                                    return (
                                        <div className="flex items-center gap-3">
                                            <span className="text-2xs font-bold uppercase tracking-widest text-site-on-surface-variant">Síguelo en</span>
                                            <div className="flex items-center gap-2">
                                                {/* Instagram */}
                                                {instagramUrl ? (
                                                    <a href={instagramUrl} target="_blank" rel="noopener noreferrer"
                                                        className="w-9 h-9 rounded-xl bg-site-surface-container-high border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:scale-110 hover:text-site-primary hover:bg-site-surface-bright transition-all shadow-sm"
                                                        aria-label="Instagram">
                                                        <Instagram size={16} className="shrink-0" />
                                                    </a>
                                                ) : (
                                                    <span className="w-9 h-9 rounded-xl bg-site-surface-container-low border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant/40 opacity-40 cursor-not-allowed" aria-label="Instagram no configurado">
                                                        <Instagram size={16} className="shrink-0" />
                                                    </span>
                                                )}
                                                {/* Facebook */}
                                                {facebookUrl ? (
                                                    <a href={facebookUrl} target="_blank" rel="noopener noreferrer"
                                                        className="w-9 h-9 rounded-xl bg-site-surface-container-high border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:scale-110 hover:text-site-primary hover:bg-site-surface-bright transition-all shadow-sm"
                                                        aria-label="Facebook">
                                                        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" className="shrink-0"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                                                    </a>
                                                ) : (
                                                    <span className="w-9 h-9 rounded-xl bg-site-surface-container-low border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant/40 opacity-40 cursor-not-allowed" aria-label="Facebook no configurado">
                                                        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" className="shrink-0"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                                                    </span>
                                                )}
                                                {/* X */}
                                                {twitterUrl ? (
                                                    <a href={twitterUrl} target="_blank" rel="noopener noreferrer"
                                                        className="w-9 h-9 rounded-xl bg-site-surface-container-high border border-site-outline-variant/30 flex items-center justify-center text-site-on-surface-variant hover:scale-110 hover:text-site-primary hover:bg-site-surface-bright transition-all shadow-sm"
                                                        aria-label="X">
                                                        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" className="shrink-0"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                                                    </a>
                                                ) : (
                                                    <span className="w-9 h-9 rounded-xl bg-site-surface-container-low border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant/40 opacity-40 cursor-not-allowed" aria-label="X no configurado">
                                                        <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" className="shrink-0"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}

                                {/* ── Versículo ── */}
                                <div className="flex items-start gap-4 p-5 rounded-[1rem] bg-site-surface-container-low border border-site-outline-variant/30">
                                    <div className="mt-0.5 w-11 h-11 rounded-xl bg-gradient-to-br from-site-primary/15 to-site-primary/5 flex items-center justify-center shrink-0 shadow-sm">
                                        <BookOpen size={18} className="text-site-primary" />
                                    </div>
                                    <div>
                                        {getString(cms, "motto_label") && (
                                            <p className="text-2xs font-bold uppercase tracking-[0.2em] text-site-on-surface-variant mb-1.5">{getString(cms, "motto_label")}</p>
                                        )}
                                        <p className="text-base md:text-lg text-site-on-surface font-medium leading-relaxed">
                                            {plainText(pastor.bio_short || pastor.story)}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ════════════════════════════════════════
                   HISTORIA — TYPOGRAPHY PREMIUM
                   ════════════════════════════════════════ */}
                <section className="relative py-16 md:py-20 lg:py-24">
                    {/* Fondo sección */}
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-site-surface-container-low/50 to-transparent" />

                    <div className="relative max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="max-w-3xl mx-auto">
                            {/* Título sección */}
                            <div className="flex items-center gap-4 mb-10">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-site-primary/15 to-site-primary/5 flex items-center justify-center shrink-0 shadow-sm">
                                    <Cross size={16} className="text-site-primary" />
                                </div>
                                <div>
                                    {getString(cms, "story_title") && (
                                        <h2 className="text-2xl md:text-3xl font-black text-site-on-surface tracking-tight leading-tight">
                                            {getString(cms, "story_title")}
                                        </h2>
                                    )}
                                    {getString(cms, "story_subtitle") && (
                                        <p className="text-xs font-bold uppercase tracking-widest text-site-on-surface-variant mt-0.5">
                                            {getString(cms, "story_subtitle")}
                                        </p>
                                    )}
                                </div>
                                <div className="flex-1 h-px bg-gradient-to-r from-site-primary/15 to-transparent ml-4" />
                            </div>

                            {/* ── Contenido con tipografía premium ── */}
                            <div
                                className="
                                    text-base md:text-lg leading-relaxed space-y-6
                                    text-site-on-surface
                                    [&_p]:leading-relaxed [&_p]:text-site-on-surface
                                    [&_p:first-child]:font-medium
                                    [&_blockquote]:border-l-[3px] [&_blockquote]:border-l-site-primary
                                    [&_blockquote]:pl-6 [&_blockquote]:py-4 [&_blockquote]:my-8
                                    [&_blockquote]:bg-gradient-to-r [&_blockquote]:from-site-primary/5 [&_blockquote]:to-transparent
                                    [&_blockquote]:rounded-r-xl
                                    [&_blockquote_p]:text-base [&_blockquote_p]:md:text-lg
                                    [&_blockquote_p]:text-site-on-surface
                                    [&_blockquote_p]:font-medium [&_blockquote_p]:leading-relaxed
                                    [&_blockquote_p]:italic
                                    [&_blockquote_p]:before:content-['\201C'] [&_blockquote_p]:before:text-site-primary [&_blockquote_p]:before:text-2xl [&_blockquote_p]:before:mr-1
                                    [&_blockquote_p]:after:content-['\201D'] [&_blockquote_p]:after:text-site-primary
                                    [&_strong]:text-site-on-surface [&_strong]:font-bold
                                    [&_em]:text-site-on-surface
                                "
                            >
                                {/* Renderizar bio_full como HTML seguro */}
                                <div dangerouslySetInnerHTML={{ __html: sanitizeCmsHtml(pastor.bio_full || pastor.bio_short || pastor.story || '') }} />
                            </div>

                            {/* ── Footer decorativo ── */}
                            <div className="mt-16 flex items-center justify-center gap-4">
                                <div className="h-px w-16 bg-gradient-to-r from-transparent to-site-primary/20" />
                                <div className="w-8 h-8 rounded-full bg-site-primary/10 flex items-center justify-center">
                                    <Heart size={12} className="text-site-primary/40" />
                                </div>
                                <div className="h-px w-16 bg-gradient-to-l from-transparent to-site-primary/20" />
                            </div>
                        </div>
                    </div>
                </section>

                {/* ════════════════════════════════════════
                   CTA — CONECTAR
                   ════════════════════════════════════════ */}
                <section className="relative py-16 md:py-20">
                    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="max-w-2xl mx-auto text-center">
                            {getString(cms, "cta_eyebrow") && (
                                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-site-primary/10 border border-site-primary/20 text-site-primary text-2xs font-bold uppercase tracking-[0.2em] mb-5">
                                    <Heart size={11} /> {getString(cms, "cta_eyebrow")}
                                </div>
                            )}
                            {getString(cms, "cta_description") && (
                                <p className="text-lg md:text-xl text-site-on-surface-variant font-medium leading-relaxed mb-8 max-w-lg mx-auto">
                                    {applyTemplate(getString(cms, "cta_description"), { first_name: pastor.name.split(' ')[0] })}
                                </p>
                            )}
                            <div className="flex flex-wrap items-center justify-center gap-3">
                                {getString(cms, "cta_primary_label") && (
                                    <Link
                                        href="/pastores"
                                        className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-site-primary text-site-on-primary text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all shadow-xl shadow-site-primary/25"
                                    >
                                        <ArrowLeft size={14} />
                                        {getString(cms, "cta_primary_label")}
                                    </Link>
                                )}
                                {getString(cms, "cta_secondary_label") && (
                                    <Link
                                        href="/sedes"
                                        className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-site-surface-container-high text-site-on-surface text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all border border-site-outline-variant/30 hover:bg-site-surface-bright"
                                    >
                                        {getString(cms, "cta_secondary_label")}
                                    </Link>
                                )}
                            </div>
                        </div>
                    </div>
                </section>

            </main>
        </div>
    );
}

'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft, Quote, BookOpen, Cross, Sparkles } from 'lucide-react';
import { useContentBlock } from '@/hooks/useContent';
import { PASTORS } from '@/data/pastors';

export default function PastorDetailPage() {
    const params = useParams();
    const router = useRouter();
    const slug = params?.slug as string;

    const { data: feedCms } = useContentBlock("faro_pastores_feed");

    let cmsPastors: any[] = [];
    if (feedCms?.content) {
        try { cmsPastors = JSON.parse(feedCms.content).pastors || []; } catch { /* ignore */ }
    }

    const cmsPastor = cmsPastors.find((p: any) => p.slug === slug);
    const fallback = PASTORS.find(p => p.id === slug);

    const pastor = cmsPastor
        ? {
            id: cmsPastor.slug,
            name: cmsPastor.name,
            title: cmsPastor.role,
            image: cmsPastor.image,
            quote: cmsPastor.quote || fallback?.quote || '',
            verse: cmsPastor.verse || fallback?.verse || '',
            shortStory: cmsPastor.story || fallback?.shortStory || '',
            fullStory: cmsPastor.story || fallback?.fullStory || '',
        }
        : fallback;

    if (!pastor) {
        return (
            <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#0b0d11] flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="w-16 h-16 rounded-2xl bg-[hsl(var(--primary))/0.1] flex items-center justify-center mx-auto">
                        <Cross size={24} className="text-[hsl(var(--primary))]" />
                    </div>
                    <h1 className="text-xl font-bold text-slate-800 dark:text-white">Pastor no encontrado</h1>
                    <button onClick={() => router.push('/pastores')} className="px-5 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-white text-sm font-bold uppercase tracking-wider hover:scale-105 transition-all shadow-lg shadow-[hsl(var(--primary))/0.25]">
                        Volver a la galería
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#0b0d11] selection:bg-[hsl(var(--primary))/0.2] selection:text-[hsl(var(--primary))]">

            <main>
                {/* ── Hero / Profile Section ── */}
                <section className="relative overflow-hidden pt-28 pb-8 md:pt-36 md:pb-12 lg:pt-44 lg:pb-16">
                    {/* Background effects */}
                    <div className="absolute inset-0 pointer-events-none overflow-hidden">
                        <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-[hsl(var(--primary))/0.06] to-transparent blur-[120px]" />
                        <div className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full bg-gradient-to-tr from-[hsl(var(--secondary))/0.04] to-transparent blur-[100px]" />
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[hsl(var(--primary))/0.02] blur-[150px]" />
                    </div>

                    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 relative z-10">
                        <Link
                            href="/pastores"
                            className="inline-flex items-center gap-2 text-sm font-bold text-slate-400 dark:text-slate-500 hover:text-[hsl(var(--primary))] transition-colors mb-8 group"
                        >
                            <ArrowLeft size={15} className="group-hover:-translate-x-1 transition-transform" />
                            Volver al liderazgo
                        </Link>

                        <div className="flex flex-col lg:flex-row gap-8 lg:gap-16 xl:gap-24 items-center lg:items-start">
                            {/* Photo */}
                            <div className="w-full max-w-[360px] lg:w-5/12 relative shrink-0">
                                <div className="relative aspect-[4/5] rounded-2xl overflow-hidden shadow-2xl shadow-black/10 dark:shadow-[0_20px_80px_rgba(0,0,0,0.5)] border border-slate-200/50 dark:border-white/[0.06]">
                                    <Image
                                        src={pastor.image}
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top"
                                        priority
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
                                    {/* Decorative corner */}
                                    <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-white/10 to-transparent rounded-bl-[100%]" />
                                </div>
                                {/* Decorative ring behind photo */}
                                <div className="absolute -top-3 -right-3 w-full h-full rounded-2xl border border-[hsl(var(--primary))/0.1] -z-10 hidden lg:block" />
                            </div>

                            {/* Info */}
                            <div className="w-full lg:w-7/12 space-y-6">
                                <div>
                                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[hsl(var(--primary))/0.08] border border-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] text-[10px] font-bold uppercase tracking-widest mb-4">
                                        <Sparkles size={10} /> Ministerio Pastoral
                                    </div>
                                    <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-slate-900 dark:text-white tracking-tight leading-[1.05] mb-3">
                                        {pastor.name}
                                    </h1>
                                    <p className="text-lg md:text-xl font-bold text-[hsl(var(--primary))] tracking-wide">
                                        {pastor.title}
                                    </p>
                                </div>

                                {/* Quote */}
                                <div className="relative p-5 md:p-6 bg-gradient-to-br from-slate-50 to-slate-100/50 dark:from-white/[0.03] dark:to-white/[0.01] rounded-xl border border-slate-200/50 dark:border-white/[0.05]">
                                    <Quote className="absolute top-4 left-4 text-[hsl(var(--primary))/0.15]" size={36} />
                                    <p className="relative z-10 text-base md:text-lg text-slate-600 dark:text-slate-300 font-medium italic leading-relaxed pt-6 pl-2">
                                        &ldquo;{pastor.quote}&rdquo;
                                    </p>
                                    <div className="h-px w-12 bg-gradient-to-r from-[hsl(var(--primary))/0.3] to-transparent mt-4 ml-2" />
                                </div>

                                {/* Verse */}
                                <div className="flex items-start gap-4 p-4 rounded-xl bg-[hsl(var(--primary))/0.03] dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.03]">
                                    <div className="mt-0.5 w-10 h-10 rounded-lg bg-[hsl(var(--primary))/0.1] flex items-center justify-center shrink-0">
                                        <BookOpen size={18} className="text-[hsl(var(--primary))]" />
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">Versículo Lema</p>
                                        <p className="text-base md:text-lg text-slate-700 dark:text-slate-200 font-medium leading-relaxed">{pastor.verse}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ── Full Story ── */}
                <section className="bg-gradient-to-b from-transparent via-slate-50/50 to-slate-100/50 dark:via-white/[0.01] dark:to-white/[0.02] py-12 md:py-16 lg:py-20 border-t border-slate-200/50 dark:border-white/[0.04]">
                    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="max-w-3xl mx-auto">
                            <div className="flex items-center gap-3 mb-8">
                                <Cross size={16} className="text-[hsl(var(--primary))/0.5]" />
                                <h2 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Su Historia</h2>
                                <div className="flex-1 h-px bg-gradient-to-r from-[hsl(var(--primary))/0.2] to-transparent" />
                            </div>
                            <div
                                className="
                                    faro-rich-text
                                    prose prose-lg dark:prose-invert max-w-none
                                    prose-headings:text-slate-900 dark:prose-headings:text-white
                                    prose-p:text-slate-600 dark:prose-p:text-slate-300 prose-p:leading-relaxed
                                    prose-blockquote:border-l-[hsl(var(--primary))]
                                    prose-blockquote:bg-gradient-to-r prose-blockquote:from-[hsl(var(--primary))/0.05] prose-blockquote:to-transparent
                                    prose-blockquote:py-3 prose-blockquote:px-5 prose-blockquote:rounded-r-xl
                                    prose-blockquote:font-medium prose-blockquote:text-slate-700 dark:prose-blockquote:text-slate-200
                                    prose-blockquote:not-italic
                                "
                                dangerouslySetInnerHTML={{ __html: pastor.fullStory }}
                            />
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}

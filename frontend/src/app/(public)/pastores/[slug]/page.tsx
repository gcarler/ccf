'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowLeft, Quote, BookOpen, Cross, Sparkles, Linkedin, Instagram, Heart } from 'lucide-react';
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
            <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#0b0d11] flex items-center justify-center pt-[88px]">
                <div className="text-center space-y-6">
                    <div className="w-20 h-20 rounded-[1.25rem] bg-[hsl(var(--primary))/0.1] flex items-center justify-center mx-auto ring-1 ring-[hsl(var(--primary))/0.15]">
                        <Heart size={28} className="text-[hsl(var(--primary))]" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Pastor no encontrado</h1>
                        <p className="text-sm text-slate-400 mt-1">El enlace que buscas no existe o ha sido movido.</p>
                    </div>
                    <button
                        onClick={() => router.push('/pastores')}
                        className="px-6 py-3 rounded-xl bg-[hsl(var(--primary))] text-white text-sm font-bold uppercase tracking-wider hover:scale-105 transition-all shadow-xl shadow-[hsl(var(--primary))/0.25]"
                    >
                        Ver todos los pastores
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#07080c] selection:bg-[hsl(var(--primary))/0.2] selection:text-[hsl(var(--primary))] overflow-hidden">

            {/* ── Fondo Ambiental ── */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
                <div className="absolute -top-60 -right-60 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-[hsl(var(--primary))/0.05] to-transparent blur-[150px]" />
                <div className="absolute -bottom-60 -left-60 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-[hsl(var(--secondary))/0.04] to-transparent blur-[120px]" />
                <div className="absolute top-1/3 left-1/3 w-96 h-96 rounded-full bg-[hsl(var(--primary))/0.015] blur-[100px]" />
            </div>

            <main className="relative z-10 pt-[88px]">

                {/* ── Breadcrumb / Back link ── */}
                <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 pt-6 pb-2 flex items-center justify-between">
                    <Link
                        href="/pastores"
                        className="inline-flex items-center gap-2 text-sm font-bold text-slate-400 hover:text-[hsl(var(--primary))] transition-colors group"
                    >
                        <ArrowLeft size={15} className="group-hover:-translate-x-1 transition-transform" />
                        Todos los pastores
                    </Link>
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-600">
                        {pastor.title}
                    </span>
                </div>

                {/* ════════════════════════════════════════
                   HERO — LAYOUT MODERNO
                   ════════════════════════════════════════ */}
                <section className="relative pt-6 pb-8 md:pt-8 md:pb-12 lg:pt-10 lg:pb-16">
                    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="flex flex-col lg:flex-row gap-10 lg:gap-16 xl:gap-20 items-center lg:items-start">

                            {/* ── Foto ── */}
                            <div className="w-full max-w-[400px] lg:w-5/12 relative shrink-0">
                                <div className="relative aspect-[4/5] rounded-[1.25rem] overflow-hidden shadow-2xl shadow-black/15 dark:shadow-[0_30px_80px_rgba(0,0,0,0.6)] ring-1 ring-slate-200/50 dark:ring-white/[0.06]">
                                    <Image
                                        src={pastor.image}
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top"
                                        priority
                                    />
                                    {/* Gradiente inferior */}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                                    {/* Esquina */}
                                    <div className="absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl from-white/[0.08] to-transparent rounded-bl-[100%]" />
                                </div>
                                {/* Aro decorativo */}
                                <div className="absolute -top-4 -right-4 w-full h-full rounded-[1.5rem] border border-[hsl(var(--primary))/0.08] -z-10 hidden lg:block" />
                                <div className="absolute -bottom-4 -left-4 w-3/4 h-3/4 rounded-[1.5rem] border border-[hsl(var(--primary))/0.04] -z-10 hidden lg:block" />
                            </div>

                            {/* ── Info ── */}
                            <div className="w-full lg:w-7/12 space-y-8">
                                {/* Badge */}
                                <div>
                                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05] border border-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] text-[10px] font-bold uppercase tracking-[0.2em] mb-5 shadow-lg shadow-[hsl(var(--primary))/0.03]">
                                        <Sparkles size={11} className="animate-pulse" /> Liderazgo Pastoral
                                    </div>
                                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tight leading-[1.05] mb-3">
                                        {pastor.name}
                                    </h1>
                                    <div className="h-1 w-16 rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--secondary))] mb-4" />
                                    <p className="text-lg md:text-xl font-bold text-[hsl(var(--primary))] tracking-wide">
                                        {pastor.title}
                                    </p>
                                </div>

                                {/* ── Quote ── */}
                                <div className="relative p-6 md:p-7 bg-gradient-to-br from-slate-50 to-white dark:from-white/[0.03] dark:to-white/[0.01] rounded-[1.25rem] border border-slate-200/50 dark:border-white/[0.05] shadow-lg shadow-slate-200/30 dark:shadow-none">
                                    <Quote className="absolute top-5 left-5 text-[hsl(var(--primary))/0.1]" size={40} />
                                    <p className="relative z-10 text-base md:text-lg text-slate-600 dark:text-slate-300 font-medium italic leading-relaxed pt-8 pl-1">
                                        &ldquo;{pastor.quote}&rdquo;
                                    </p>
                                    <div className="flex items-center gap-3 mt-5 pl-1">
                                        <div className="h-px flex-1 bg-gradient-to-r from-[hsl(var(--primary))/0.3] to-transparent max-w-[80px]" />
                                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-300 dark:text-slate-600">Filosofía de vida</span>
                                    </div>
                                </div>

                                {/* ── Stats / Tags ── */}
                                <div className="flex flex-wrap gap-3">
                                    {[
                                        { label: 'Pastor', color: 'from-blue-500/10 to-blue-500/5 text-blue-600 dark:text-blue-400 border-blue-200/50 dark:border-blue-500/10' },
                                        { label: 'Líder', color: 'from-emerald-500/10 to-emerald-500/5 text-emerald-600 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-500/10' },
                                        { label: 'Consejero', color: 'from-amber-500/10 to-amber-500/5 text-amber-600 dark:text-amber-400 border-amber-200/50 dark:border-amber-500/10' },
                                    ].map((tag, i) => (
                                        <span
                                            key={i}
                                            className={`px-3 py-1.5 rounded-lg bg-gradient-to-r ${tag.color} border text-[10px] font-bold uppercase tracking-wider`}
                                        >
                                            {tag.label}
                                        </span>
                                    ))}
                                </div>

                                {/* ── Versículo ── */}
                                <div className="flex items-start gap-4 p-5 rounded-[1rem] bg-[hsl(var(--primary))/0.03] dark:bg-white/[0.015] border border-slate-100 dark:border-white/[0.03]">
                                    <div className="mt-0.5 w-11 h-11 rounded-xl bg-gradient-to-br from-[hsl(var(--primary))/0.15] to-[hsl(var(--primary))/0.05] flex items-center justify-center shrink-0 shadow-sm shadow-[hsl(var(--primary))/0.05]">
                                        <BookOpen size={18} className="text-[hsl(var(--primary))]" />
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 mb-1.5">Versículo Lema</p>
                                        <p className="text-base md:text-lg text-slate-700 dark:text-slate-200 font-medium leading-relaxed">
                                            {pastor.verse}
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
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-50/40 to-slate-100/40 dark:via-white/[0.01] dark:to-white/[0.015]" />

                    <div className="relative max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12">
                        <div className="max-w-3xl mx-auto">
                            {/* Título sección */}
                            <div className="flex items-center gap-4 mb-10">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[hsl(var(--primary))/0.15] to-[hsl(var(--primary))/0.05] flex items-center justify-center shrink-0 shadow-sm">
                                    <Cross size={16} className="text-[hsl(var(--primary))]" />
                                </div>
                                <div>
                                    <h2 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-white tracking-tight leading-tight">
                                        Su Historia
                                    </h2>
                                    <p className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mt-0.5">
                                        Testimonio de vida y ministerio
                                    </p>
                                </div>
                                <div className="flex-1 h-px bg-gradient-to-r from-[hsl(var(--primary))/0.15] to-transparent ml-4" />
                            </div>

                            {/* ── Contenido con tipografía premium ── */}
                            <div
                                className="
                                    text-base md:text-lg leading-[1.85] space-y-6
                                    text-slate-700 dark:text-slate-300
                                    [&_p]:leading-[1.85] [&_p]:text-slate-700 [&_p]:dark:text-slate-300
                                    [&_p:first-child]:text-lg [&_p:first-child]:md:text-xl [&_p:first-child]:font-medium [&_p:first-child]:text-slate-800 [&_p:first-child]:dark:text-white
                                    [&_blockquote]:border-l-[3px] [&_blockquote]:border-l-[hsl(var(--primary))]
                                    [&_blockquote]:pl-6 [&_blockquote]:py-4 [&_blockquote]:my-8
                                    [&_blockquote]:bg-gradient-to-r [&_blockquote]:from-[hsl(var(--primary))/0.04] [&_blockquote]:to-transparent
                                    [&_blockquote]:rounded-r-xl
                                    [&_blockquote_p]:text-lg [&_blockquote_p]:md:text-xl
                                    [&_blockquote_p]:text-slate-600 [&_blockquote_p]:dark:text-slate-200
                                    [&_blockquote_p]:font-medium [&_blockquote_p]:leading-relaxed
                                    [&_blockquote_p]:italic
                                    [&_blockquote_p]:before:content-['\\201C'] [&_blockquote_p]:before:text-[hsl(var(--primary))] [&_blockquote_p]:before:text-2xl [&_blockquote_p]:before:mr-1
                                    [&_blockquote_p]:after:content-['\\201D'] [&_blockquote_p]:after:text-[hsl(var(--primary))]
                                    [&_strong]:text-slate-900 [&_strong]:dark:text-white [&_strong]:font-bold
                                    [&_em]:text-slate-600 [&_em]:dark:text-slate-300
                                "
                            >
                                {/* Renderizar fullStory como HTML seguro */}
                                <div dangerouslySetInnerHTML={{ __html: pastor.fullStory }} />
                            </div>

                            {/* ── Footer decorativo ── */}
                            <div className="mt-16 flex items-center justify-center gap-4">
                                <div className="h-px w-16 bg-gradient-to-r from-transparent to-[hsl(var(--primary))/0.2]" />
                                <div className="w-8 h-8 rounded-full bg-[hsl(var(--primary))/0.05] flex items-center justify-center">
                                    <Heart size={12} className="text-[hsl(var(--primary))/0.4]" />
                                </div>
                                <div className="h-px w-16 bg-gradient-to-l from-transparent to-[hsl(var(--primary))/0.2]" />
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
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[hsl(var(--primary))/0.06] border border-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] text-[10px] font-bold uppercase tracking-[0.2em] mb-5">
                                <Heart size={11} /> Comunidad de Fe
                            </div>
                            <p className="text-lg md:text-xl text-slate-500 dark:text-slate-400 font-medium leading-relaxed mb-8 max-w-lg mx-auto">
                                ¿Deseas conectar con el Pastor {pastor.name.split(' ')[0]} o saber más sobre su ministerio?
                            </p>
                            <div className="flex flex-wrap items-center justify-center gap-3">
                                <Link
                                    href="/pastores"
                                    className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all shadow-xl shadow-[hsl(var(--primary))/0.25]"
                                >
                                    <ArrowLeft size={14} />
                                    Conocer al equipo
                                </Link>
                                <Link
                                    href="/sedes"
                                    className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-slate-100 dark:bg-white/[0.05] text-slate-600 dark:text-slate-300 text-xs font-bold uppercase tracking-wider hover:scale-105 transition-all border border-slate-200 dark:border-white/[0.06]"
                                >
                                    Nuestras sedes
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

            </main>
        </div>
    );
}

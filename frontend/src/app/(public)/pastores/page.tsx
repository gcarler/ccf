'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronRight, Cross, Sparkles, Instagram } from 'lucide-react';
import RichText from "@/components/public/RichText";
import { useContentBlock } from '@/hooks/useContent';
import { PASTORS } from '@/data/pastors';
import ShareButtons from '@/components/public/ShareButtons';

const FbIcon = () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
    </svg>
);
const XIcon = () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.737-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
);

export default function PastoresIndexPage() {
    const { data: heroCms } = useContentBlock("faro_pastores_hero");
    const { data: feedCms } = useContentBlock("faro_pastores_feed");

    let cmsPastors: any[] = [];
    if (feedCms?.content) {
        try { cmsPastors = JSON.parse(feedCms.content).pastors || []; } catch { /* ignore */ }
    }

    const pastors = cmsPastors.length > 0
        ? cmsPastors.map((cp: any) => {
            const fallback = PASTORS.find(p => p.id === cp.slug);
            return {
                id: cp.slug,
                name: cp.name,
                title: cp.role,
                image: cp.image,
                isMain: cp.isMain ?? fallback?.isMain ?? false,
                instagram: cp.instagram || fallback?.instagram,
                facebook: cp.facebook || fallback?.facebook,
                twitter: cp.twitter || fallback?.twitter,
                shortStory: cp.story || fallback?.shortStory || '',
            };
        })
        : PASTORS;

    const heroContent = heroCms?.content ? JSON.parse(heroCms.content) : null;
    const heroTitle = heroContent?.title || "Liderazgo Pastoral";
    const heroDescription = heroContent?.description || "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.";

    return (
        <main className="pt-24 pb-4">
            {/* ── Hero Section ── */}
            <section className="relative overflow-hidden">
                <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-br from-[hsl(var(--primary))/0.08] to-transparent blur-3xl" />
                    <div className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full bg-gradient-to-tr from-[hsl(var(--secondary))/0.06] to-transparent blur-3xl" />
                </div>

                <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 mb-16 md:mb-24 text-center relative z-10 pt-12 md:pt-20 pb-8">
                    <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-gradient-to-r from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.1] backdrop-blur-sm text-[hsl(var(--primary))] text-xs font-bold uppercase tracking-widest mb-5 border border-[hsl(var(--primary))/0.2] shadow-lg shadow-[hsl(var(--primary))/0.05]">
                        <Sparkles size={12} className="animate-pulse" /> Conoce a nuestro equipo pastoral
                    </div>
                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-slate-900 dark:text-white mb-5 leading-[1.05]">
                        {heroTitle}
                    </h1>
                    <RichText
                        html={heroDescription}
                        className="text-base md:text-lg text-slate-500 dark:text-slate-400 max-w-2xl mx-auto font-medium leading-relaxed"
                    />
                    <div className="flex items-center justify-center gap-3 mt-8">
                        <div className="h-px w-12 bg-gradient-to-r from-transparent to-[hsl(var(--primary))/0.3]" />
                        <Cross size={14} className="text-[hsl(var(--primary))/0.4]" />
                        <div className="h-px w-12 bg-gradient-to-l from-transparent to-[hsl(var(--primary))/0.3]" />
                    </div>
                    <div className="mt-6 flex justify-center">
                        <ShareButtons title="Liderazgo Pastoral | Comunidad Cristiana El Faro" />
                    </div>
                </div>
            </section>

            {/* ── Pastors Grid ── */}
            <section className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 pb-20 md:pb-28">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 md:gap-6">
                    {pastors.map((pastor, idx) => (
                        <div key={pastor.id} className="group relative bg-white dark:bg-[#0f1117] rounded-2xl overflow-hidden border border-slate-200/70 dark:border-white/[0.06] shadow-lg shadow-slate-200/40 dark:shadow-[0_8px_32px_rgba(0,0,0,0.3)] hover:shadow-2xl hover:shadow-[hsl(var(--primary))/0.15] dark:hover:shadow-[0_16px_48px_rgba(0,0,0,0.5)] hover:-translate-y-1.5 transition-all duration-500 flex flex-col"
                            style={{ animationDelay: `${idx * 100}ms` }}>

                            {/* Image */}
                            <Link href={`/pastores/${pastor.id}`} className="relative h-52 w-full bg-slate-100 dark:bg-[#0a0c12] overflow-hidden block">
                                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-transparent pointer-events-none z-10" />
                                <Image
                                    src={pastor.image}
                                    alt={pastor.name}
                                    fill
                                    className="object-cover object-top transition-transform duration-700 group-hover:scale-110"
                                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-[#0a0c12]/90 via-black/30 to-transparent" />
                                {pastor.isMain && (
                                    <div className="absolute top-3 left-3 z-20">
                                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-bold uppercase tracking-wider shadow-lg">
                                            <Sparkles size={8} /> Pastor Principal
                                        </span>
                                    </div>
                                )}
                                <div className="absolute bottom-4 left-5 right-5 z-20">
                                    <h3 className="text-lg font-bold text-white drop-shadow-sm">{pastor.name}</h3>
                                    <p className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] drop-shadow-sm">{pastor.title}</p>
                                </div>
                                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-[hsl(var(--primary))/0.15] to-transparent rounded-bl-[100%] pointer-events-none" />
                            </Link>

                            {/* Content */}
                            <div className="p-4 flex-1 flex flex-col bg-white dark:bg-[#0f1117]">
                                <p className="text-sm text-slate-500 dark:text-slate-400 mb-3 flex-1 leading-relaxed line-clamp-3">
                                    {pastor.shortStory}
                                </p>

                                {/* Redes sociales — siempre visibles */}
                                <div className="flex items-center gap-1.5 mb-3">
                                    {pastor.instagram ? (
                                        <a href={pastor.instagram} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                                            className="w-7 h-7 rounded-lg bg-gradient-to-br from-pink-500/10 to-purple-500/10 border border-pink-200/50 dark:border-pink-500/15 flex items-center justify-center text-pink-500 hover:scale-110 transition-all"
                                            aria-label="Instagram">
                                            <Instagram size={13} />
                                        </a>
                                    ) : (
                                        <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-pink-500/5 to-purple-500/5 border border-pink-200/20 dark:border-pink-500/10 flex items-center justify-center text-pink-200 dark:text-pink-900 opacity-40">
                                            <Instagram size={13} />
                                        </span>
                                    )}
                                    {pastor.facebook ? (
                                        <a href={pastor.facebook} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                                            className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-200/50 dark:border-blue-500/15 flex items-center justify-center text-blue-600 hover:scale-110 transition-all"
                                            aria-label="Facebook">
                                            <FbIcon />
                                        </a>
                                    ) : (
                                        <span className="w-7 h-7 rounded-lg bg-blue-500/5 border border-blue-200/20 dark:border-blue-500/10 flex items-center justify-center text-blue-200 dark:text-blue-900 opacity-40">
                                            <FbIcon />
                                        </span>
                                    )}
                                    {pastor.twitter ? (
                                        <a href={pastor.twitter} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                                            className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200/50 dark:border-white/10 flex items-center justify-center text-slate-700 dark:text-white hover:scale-110 transition-all"
                                            aria-label="X">
                                            <XIcon />
                                        </a>
                                    ) : (
                                        <span className="w-7 h-7 rounded-lg bg-slate-100/50 dark:bg-white/[0.02] border border-slate-200/20 dark:border-white/5 flex items-center justify-center text-slate-300 dark:text-slate-700 opacity-40">
                                            <XIcon />
                                        </span>
                                    )}
                                </div>

                                {/* CTA */}
                                <Link href={`/pastores/${pastor.id}`} className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-white/[0.06]">
                                    <span className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--primary))] group-hover:tracking-[0.15em] transition-all duration-300">
                                        Conocer más
                                    </span>
                                    <div className="w-9 h-9 rounded-xl bg-[hsl(var(--primary))/0.08] dark:bg-[hsl(var(--primary))/0.12] flex items-center justify-center group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all duration-300 group-hover:shadow-lg group-hover:shadow-[hsl(var(--primary))/0.3]">
                                        <ChevronRight size={15} className="group-hover:translate-x-0.5 transition-transform duration-300" />
                                    </div>
                                </Link>
                            </div>

                            <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-slate-200/50 dark:ring-white/[0.04] group-hover:ring-[hsl(var(--primary))/0.3] transition-all duration-500 pointer-events-none" />
                        </div>
                    ))}
                </div>
            </section>
        </main>
    );
}

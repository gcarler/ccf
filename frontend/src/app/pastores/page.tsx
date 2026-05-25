'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronRight, Heart } from 'lucide-react';
import { FAROHeader, FAROFooter } from '@/components/public/FAROShared';
import RichText from "@/components/public/RichText";
import { useContentBlock } from '@/hooks/useContent';
import { PASTORS } from '@/data/pastors';

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
                quote: cp.quote || fallback?.quote || '',
                verse: cp.verse || fallback?.verse || '',
                shortStory: cp.story || fallback?.shortStory || '',
                fullStory: cp.story || fallback?.fullStory || '',
            };
        })
        : PASTORS;

    const heroContent = heroCms?.content ? JSON.parse(heroCms.content) : null;
    const heroTitle = heroContent?.title || "Liderazgo Pastoral";
    const heroDescription = heroContent?.description || "Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa.";

    return (
        <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b0d11] selection:bg-blue-500/30 selection:text-blue-900">
            <FAROHeader />

            <main className="pt-24 pb-4">
                <div className="max-w-7xl mx-auto px-3 md:px-6 lg:px-8 xl:px-12 mb-20 text-center relative z-10 py-8">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 text-xs font-semibold uppercase tracking-wide mb-3 border border-blue-200 dark:border-blue-500/20">
                        <Heart size={14} /> Conoce a nuestro equipo
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white mb-3">
                        {heroTitle}
                    </h1>
                    <RichText html={heroDescription} className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto font-medium" />
                </div>

                <div className="max-w-7xl mx-auto px-3 md:px-6 lg:px-8 xl:px-12 pb-16">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        {pastors.map((pastor, idx) => (
                            <Link
                                href={`/pastores/${pastor.id}`}
                                key={pastor.id}
                                className="group relative bg-white dark:bg-[#13161c] rounded-lg overflow-hidden border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-2 transition-all duration-500 flex flex-col"
                                style={{ animationDelay: `${idx * 100}ms` }}
                            >
                                <div className="relative h-48 w-full bg-slate-100 dark:bg-black overflow-hidden">
                                    <Image
                                        src={pastor.image}
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top transition-transform duration-700 group-hover:scale-110"
                                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
                                    <div className="absolute bottom-4 left-5 right-5">
                                        <h3 className="text-lg font-bold text-white">{pastor.name}</h3>
                                        <p className="text-blue-300 font-bold text-sm tracking-wide">{pastor.title}</p>
                                    </div>
                                </div>

                                <div className="p-3 flex-1 flex flex-col">
                                    <p className="text-slate-600 dark:text-slate-400 text-sm mb-3 flex-1 leading-relaxed">
                                        {pastor.shortStory}
                                    </p>

                                    <div className="flex items-center justify-between text-blue-600 dark:text-blue-400 font-bold text-sm group-hover:text-indigo-600 transition-colors">
                                        <span>Leer testimonio</span>
                                        <div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 transition-colors">
                                            <ChevronRight size={16} />
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>
            </main>

            <FAROFooter />
        </div>
    );
}

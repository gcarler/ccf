'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { PASTORS } from '@/data/pastors';
import { ArrowLeft, Quote, BookOpen } from 'lucide-react';
import FaroNavbar from '@/components/public/FaroNavbar';
import FaroFooter from '@/components/public/FaroFooter';

export default function PastorDetailPage() {
    const params = useParams();
    const router = useRouter();
    const slug = params?.slug as string;

    const pastor = PASTORS.find(p => p.id === slug);

    if (!pastor) {
        return (
            <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-4xl font-black text-slate-800 mb-4">Pastor no encontrado</h1>
                    <button onClick={() => router.push('/pastores')} className="text-blue-600 font-bold hover:underline">
                        Volver a la galería
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-white dark:bg-[#0b0d11] selection:bg-blue-500/30 selection:text-blue-900">
            <FaroNavbar />
            
            <main>
                {/* Hero Minimalista */}
                <div className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
                    {/* Fondo decorativo */}
                    <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10">
                        <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-400/10 blur-[100px] rounded-full"></div>
                        <div className="absolute top-40 -left-20 w-72 h-72 bg-indigo-400/10 blur-[80px] rounded-full"></div>
                    </div>

                    <div className="max-w-7xl mx-auto px-6 lg:px-8">
                        <Link href="/pastores" className="inline-flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 font-bold text-sm mb-12 transition-colors">
                            <ArrowLeft size={16} /> Volver al liderazgo
                        </Link>
                        
                        <div className="flex flex-col lg:flex-row gap-16 lg:gap-24 items-center">
                            {/* Imagen Portrait */}
                            <div className="w-full lg:w-5/12 relative">
                                <div className="aspect-[4/5] relative rounded-[3rem] overflow-hidden shadow-2xl shadow-blue-900/10 dark:shadow-none border border-slate-100 dark:border-white/5">
                                    <Image 
                                        src={pastor.image} 
                                        alt={pastor.name}
                                        fill
                                        className="object-cover object-top"
                                        priority
                                    />
                                    {/* Overlay Gradient suave */}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent"></div>
                                </div>
                            </div>

                            {/* Info Principal */}
                            <div className="w-full lg:w-7/12">
                                <h1 className="text-5xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tight mb-4">
                                    {pastor.name}
                                </h1>
                                <p className="text-xl lg:text-3xl text-blue-600 dark:text-blue-400 font-bold tracking-wide mb-10">
                                    {pastor.title}
                                </p>

                                {/* Blockquote Principal */}
                                <div className="relative p-8 bg-slate-50 dark:bg-[#13161c] rounded-3xl border border-slate-100 dark:border-white/5 mb-12">
                                    <Quote className="absolute top-6 left-6 text-blue-200 dark:text-blue-500/20" size={40} />
                                    <p className="relative z-10 text-xl lg:text-2xl text-slate-700 dark:text-slate-300 font-medium italic leading-relaxed pt-6">
                                        &ldquo;{pastor.quote}&rdquo;
                                    </p>
                                </div>

                                {/* Versículo Lema */}
                                <div className="flex items-start gap-4">
                                    <div className="mt-1 w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center shrink-0">
                                        <BookOpen className="text-indigo-600 dark:text-indigo-400" size={20} />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Versículo Lema</h3>
                                        <p className="text-lg text-slate-800 dark:text-slate-200 font-medium">{pastor.verse}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Contenido / Historia */}
                <div className="bg-slate-50 dark:bg-[#0f1117] py-24 border-t border-slate-200 dark:border-white/5">
                    <div className="max-w-3xl mx-auto px-6 lg:px-8">
                        <h2 className="text-3xl font-black text-slate-900 dark:text-white mb-10">Su Historia</h2>
                        
                        <div 
                            className="prose prose-lg dark:prose-invert prose-violet max-w-none
                            prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-p:leading-relaxed
                            prose-blockquote:border-l-blue-500 prose-blockquote:bg-white dark:prose-blockquote:bg-[#151821] prose-blockquote:py-4 prose-blockquote:px-6 prose-blockquote:rounded-r-2xl prose-blockquote:font-medium prose-blockquote:text-slate-800 dark:prose-blockquote:text-slate-200 prose-blockquote:shadow-sm"
                            dangerouslySetInnerHTML={{ __html: pastor.fullStory }}
                        />
                    </div>
                </div>
            </main>

            <FaroFooter />
        </div>
    );
}

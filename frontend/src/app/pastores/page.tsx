'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { PASTORS } from '@/data/pastors';
import { ChevronRight, Heart } from 'lucide-react';
import FaroNavbar from '@/components/public/FaroNavbar';
import FaroFooter from '@/components/public/FaroFooter';

export default function PastoresIndexPage() {
    return (
        <div className="min-h-screen bg-[#f8fafc] dark:bg-[#0b0d11] selection:bg-blue-500/30 selection:text-blue-900">
            <FaroNavbar />
            
            <main className="pt-24 pb-4">
                {/* Hero Section */}
                <div className="max-w-7xl mx-auto px-3 lg:px-4 mb-20 text-center relative z-10 pt-10">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 text-xs font-semibold uppercase tracking-wide mb-3 border border-blue-200 dark:border-blue-500/20">
                        <Heart size={14} /> Conoce a nuestro equipo
                    </div>
                    <h1 className="text-lg md:text-xl font-bold tracking-tight text-slate-900 dark:text-white mb-3">
                        Liderazgo <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Pastoral</span>
                    </h1>
                    <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto font-medium">
                        Hombres y mujeres llamados por Dios para servir, guiar y amar a esta casa. Detrás de cada uno hay una historia de gracia y un testimonio del poder transformador de Jesús.
                    </p>
                </div>

                {/* Grid de Pastores */}
                <div className="max-w-7xl mx-auto px-3 lg:px-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        {PASTORS.map((pastor, idx) => (
                            <Link 
                                href={`/pastores/${pastor.id}`} 
                                key={pastor.id}
                                className="group relative bg-white dark:bg-[#13161c] rounded-lg overflow-hidden border border-slate-200 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-2 transition-all duration-500 flex flex-col"
                                style={{ animationDelay: `${idx * 100}ms` }}
                            >
                                {/* Imagen Wrapper */}
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
                                
                                {/* Info Corta */}
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

            <FaroFooter />
        </div>
    );
}

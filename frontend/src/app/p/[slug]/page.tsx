"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { apiUrl } from '@/lib/api';
import { FileText, Calendar, Clock, User, ChevronLeft } from 'lucide-react';
import Link from 'next/link';

export default function DynamicCmsPage() {
    const { slug } = useParams();
    const [content, setContent] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        const fetchContent = async () => {
            try {
                const res = await fetch(apiUrl(`/content/page_${slug}`));
                if (res.ok) {
                    const data = await res.json();
                    setContent(JSON.parse(data.content));
                } else {
                    setError(true);
                }
            } catch (err) {
                console.error("Error fetching dynamic content", err);
                setError(true);
            } finally {
                setLoading(false);
            }
        };
        fetchContent();
    }, [slug]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-background-dark">
                <Navbar />
                <div className="pt-32 flex justify-center">
                    <div className="animate-spin size-8 border-4 border-primary border-t-transparent rounded-full"></div>
                </div>
            </div>
        );
    }

    if (error || !content) {
        return (
            <div className="min-h-screen bg-slate-50 dark:bg-background-dark">
                <Navbar />
                <div className="pt-32 px-6 max-w-xl mx-auto text-center">
                    <h1 className="text-4xl font-black mb-4">Página no encontrada</h1>
                    <p className="text-slate-500 mb-8">Lo sentimos, la sección que buscas no existe o ha sido movida.</p>
                    <Link href="/" className="px-8 py-4 bg-primary text-white rounded-2xl font-bold uppercase tracking-widest shadow-xl">
                        Volver al Inicio
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-background-dark transition-colors duration-500">
            <Navbar />

            {/* Hero Section */}
            <div className="relative pt-32 pb-20 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none"></div>
                <div className="container mx-auto px-6 max-w-5xl relative z-10">
                    <Link href="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-primary transition-colors mb-8 font-bold text-sm">
                        <ChevronLeft size={16} /> Volver
                    </Link>

                    <div className="flex flex-col md:flex-row gap-12 items-center">
                        <div className="flex-1 space-y-6 text-center md:text-left">
                            <h1 className="text-4xl md:text-6xl font-black text-slate-900 dark:text-white tracking-tight leading-tight">
                                {content.title}
                            </h1>
                            <p className="text-xl text-slate-500 dark:text-slate-400 font-medium leading-relaxed">
                                {content.subtitle}
                            </p>
                        </div>
                        {content.image && (
                            <div className="size-64 md:size-80 rounded-[3rem] overflow-hidden shadow-2xl border-8 border-white dark:border-slate-800 rotate-3 transition-transform hover:rotate-0 duration-700">
                                <img src={content.image} alt={content.title} className="w-full h-full object-cover" />
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Content Body */}
            <main className="container mx-auto px-6 max-w-4xl pb-32">
                <div className="glass-card bg-white dark:bg-slate-900/40 p-10 md:p-16 rounded-[4rem] shadow-2xl border border-white dark:border-white/5 relative bg-white/70 dark:bg-slate-950/40 backdrop-blur-3xl">
                    <div className="prose prose-slate dark:prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-p:leading-[2] whitespace-pre-wrap">
                        {content.content}
                    </div>

                    {content.cta && (
                        <div className="mt-16 pt-12 border-t border-slate-100 dark:border-white/5 text-center">
                            <h3 className="text-2xl font-black mb-6">{content.cta_title || "¿Listo para dar el siguiente paso?"}</h3>
                            <Link href={content.cta_link || "/register"} className="px-10 py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-3xl font-black uppercase tracking-widest shadow-2xl hover:scale-105 active:scale-95 transition-all inline-block">
                                {content.cta_label || "Empezar Ahora"}
                            </Link>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
}

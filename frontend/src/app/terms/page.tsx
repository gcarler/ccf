"use client";

import React, { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import { FileText } from 'lucide-react';
import { apiUrl } from '@/lib/api';

export default function TermsPage() {
    const [content, setContent] = useState<any>(null);

    useEffect(() => {
        const fetchContent = async () => {
            try {
                const res = await fetch(apiUrl('/content/terms_of_service'));
                if (res.ok) {
                    const data = await res.json();
                    setContent(JSON.parse(data.content));
                }
            } catch (e) {
                console.error("Error fetching terms of service", e);
            }
        };
        fetchContent();
    }, []);

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-background-dark bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]">
            <Navbar />
            <div className="pt-32 pb-20 container mx-auto px-6 max-w-4xl relative z-10">
                <div className="glass-card bg-white dark:bg-slate-900 p-12 md:p-16 rounded-[3rem] shadow-2xl border border-slate-100 dark:border-white/5">
                    <div className="w-16 h-16 bg-blue-500/10 text-blue-500 rounded-2xl flex items-center justify-center mb-8">
                        <FileText size={32} />
                    </div>
                    <h1 className="text-4xl md:text-5xl font-black text-slate-900 dark:text-white mb-6 tracking-tight">
                        {content?.title || "Términos de Servicio"}
                    </h1>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-medium mb-12">
                        Última actualización: {content?.last_update || "12 de Marzo, 2026"}
                    </p>

                    <div className="prose prose-slate dark:prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-p:leading-relaxed whitespace-pre-wrap">
                        {content?.content || "Cargando términos..."}
                    </div>
                </div>
            </div>
        </div>
    );
}

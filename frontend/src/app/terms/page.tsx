"use client";

import React from 'react';
import Navbar from '@/components/Navbar';
import { FileText } from 'lucide-react';
import { useContentBlock } from '@/hooks/useContent';
import CmsPageOverride from '@/components/public/cms/CmsPageOverride';

export default function TermsPage() {
    const { data: content } = useContentBlock('terms_of_service');

    return (
        <CmsPageOverride slug="terms">
        <div className="min-h-screen bg-slate-50 dark:bg-background-dark bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]">
            <Navbar />
            <div className="pt-32 pb-4 container mx-auto px-3 max-w-4xl relative z-10">
                <div className="glass-card bg-[hsl(var(--bg-primary))] dark:bg-slate-900 p-4 rounded-lg shadow-2xl border border-slate-100 dark:border-white/5">
                    <div className="w-16 h-8 bg-blue-500/10 text-[hsl(var(--primary))] rounded-lg flex items-center justify-center mb-3">
                        <FileText size={32} />
                    </div>
                    <h1 className="text-lg font-bold text-slate-900 dark:text-white mb-3 tracking-tight">
                        {content?.title || "Términos de Servicio"}
                    </h1>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-medium mb-3">
                        Última actualización: {content?.last_update || "12 de Marzo, 2026"}
                    </p>

                    <div className="prose prose-slate dark:prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-p:leading-relaxed whitespace-pre-wrap">
                        {content?.content || "Cargando términos..."}
                    </div>
                </div>
            </div>
        </div>
        </CmsPageOverride>
    );
}


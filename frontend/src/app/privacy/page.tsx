"use client";

import React from 'react';
import Navbar from '@/components/Navbar';
import { ShieldAlert } from 'lucide-react';
import { useContentBlock } from '@/hooks/useContent';

export default function PrivacyPage() {
    const { data: content } = useContentBlock('privacy_policy');

    const rawContent = content?.content || "Cargando contenido...";

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-background-dark bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]">
            <Navbar />
            <div className="pt-32 pb-20 container mx-auto px-6 max-w-4xl relative z-10">
                <div className="glass-card bg-white dark:bg-slate-900 p-4 rounded-lg shadow-2xl border border-slate-100 dark:border-white/5">
                    <div className="w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-lg flex items-center justify-center mb-3">
                        <ShieldAlert size={32} />
                    </div>
                    <h1 className="text-lg font-bold text-slate-900 dark:text-white mb-3 tracking-tight">
                        {content?.title || "Política de Privacidad"}
                    </h1>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-medium mb-3">
                        {content?.subtitle || "Comprometidos con la seguridad de tus datos."}
                    </p>

                    <div className="prose prose-slate dark:prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:text-slate-600 dark:prose-p:text-slate-400 prose-p:leading-relaxed whitespace-pre-wrap">
                        {rawContent}
                    </div>
                </div>
            </div>
        </div>
    );
}


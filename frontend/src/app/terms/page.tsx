"use client";

import React from 'react';
import { FileText } from 'lucide-react';
import { useCmsV2Page } from '@/hooks/useCmsV2Page';
import { safeJsonParse } from '@/lib/safeJson';
import RichText from '@/components/public/RichText';

export default function TermsPage() {
    const cmsPage = useCmsV2Page('terms');
    const cmsContent = cmsPage?.blocks?.hero;
    const content = safeJsonParse<Record<string, unknown>>(cmsContent?.content, {});

    const str = (key: string, fallback = "") =>
        typeof content[key] === "string" && (content[key] as string).trim() ? (content[key] as string) : fallback;

    const title = str("title", "Términos de Servicio");
    const subtitle = str("subtitle", "Última actualización: 12 de Marzo, 2026");
    const body = str("body", "Los términos de servicio de la plataforma se encuentran en construcción. Para dudas, contacta al equipo pastoral.");

    return (
        <div className="min-h-screen bg-[hsl(var(--surface-1))] dark:bg-background-dark">
            <div className="pt-32 pb-4 container mx-auto px-3 max-w-4xl relative z-10">
                <div className="glass-card bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] p-4 rounded-lg shadow-2xl border border-[hsl(var(--border))] dark:border-white/5">
                    <div className="w-16 h-8 bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] rounded-lg flex items-center justify-center mb-3">
                        <FileText size={32} />
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mb-3 tracking-tight">
                        {title}
                    </h1>
                    <p className="text-lg text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium mb-3">
                        {subtitle}
                    </p>
                    <div className="prose prose-slate dark:prose-invert prose-lg max-w-none prose-headings:font-black prose-headings:text-[hsl(var(--text-primary))] dark:prose-headings:text-white prose-p:text-[hsl(var(--text-secondary))] dark:prose-p:text-[hsl(var(--text-secondary))] prose-p:leading-relaxed">
                        <RichText html={body} />
                    </div>
                </div>
            </div>
        </div>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import { HeadphonesIcon, LifeBuoy, Mail } from 'lucide-react';
import { apiUrl } from '@/lib/api';

const ICON_MAP: Record<string, any> = {
    tech: HeadphonesIcon,
    academic: LifeBuoy,
    pastoral: Mail
};

export default function SupportPage() {
    const [content, setContent] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchContent = async () => {
            try {
                const res = await fetch(apiUrl('/content/support_page'));
                if (res.ok) {
                    const data = await res.json();
                    setContent(JSON.parse(data.content));
                }
            } catch (e) {
                console.error("Error fetching support content", e);
            } finally {
                setLoading(false);
            }
        };
        fetchContent();
    }, []);

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-background-dark bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] transition-colors">
            <Navbar />
            <div className="pt-32 pb-20 container mx-auto px-6 max-w-5xl relative z-10">

                <div className="text-center mb-16">
                    <h1 className="text-4xl md:text-6xl font-black text-slate-900 dark:text-white mb-6 tracking-tight">
                        {content?.title || "Centro de Ayuda"}
                    </h1>
                    <p className="text-xl text-slate-500 dark:text-slate-400 font-medium max-w-2xl mx-auto">
                        {content?.description || "Estamos aquí para asistirte en cada paso de tu formación."}
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {(content?.categories || [
                        { title: "Soporte Técnico", desc: "Cargando...", type: "tech" },
                        { title: "Academia", desc: "Cargando...", type: "academic" },
                        { title: "Pastoral", desc: "Cargando...", type: "pastoral" }
                    ]).map((cat: any, i: number) => {
                        const Icon = ICON_MAP[cat.type] || Mail;
                        return (
                            <div key={i} className="glass dark:bg-slate-900/40 p-10 text-center hover:shadow-2xl transition-all border border-slate-200 dark:border-white/5 rounded-[2.5rem]">
                                <div className="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mx-auto mb-6">
                                    <Icon size={32} />
                                </div>
                                <h3 className="text-xl font-black text-slate-900 dark:text-white mb-3">{cat.title}</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm mb-6 leading-relaxed">{cat.desc}</p>
                                <button className="px-6 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-bold text-xs uppercase tracking-widest w-full hover:scale-[1.02] active:scale-[0.98] transition-all">Contactar</button>
                            </div>
                        );
                    })}
                </div>

            </div>
        </div>
    );
}

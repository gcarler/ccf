"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Facebook,
    Instagram,
    Youtube,
    MessageCircle,
    Radio,
    ExternalLink,
    Save,
    CheckCircle2
} from 'lucide-react';

export default function SocialMediaSettings() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    const socials = [
        { id: 'facebook', icon: Facebook, label: 'Facebook', sub: 'Enlace de Perfil', placeholder: 'https://facebook.com/iglesia', value: 'https://facebook.com/bethel_oficial' },
        { id: 'instagram', icon: Instagram, label: 'Instagram', sub: 'Enlace de Perfil', placeholder: 'https://instagram.com/iglesia', value: '' },
        { id: 'youtube', icon: Youtube, label: 'YouTube', sub: 'Enlace de Perfil', placeholder: 'https://youtube.com/c/iglesia', value: '' },
        { id: 'whatsapp', icon: MessageCircle, label: 'WhatsApp', sub: 'Enlace Directo', placeholder: 'https://wa.me/numero', value: '' },
    ];

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={18} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Redes Sociales</h1>
                    <div className="size-10"></div>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-48 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Intro */}
                <div className="space-y-1">
                    <h2 className="text-2xl font-black text-white tracking-tight uppercase tracking-tight">Perfiles Oficiales</h2>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-loose">Configura los enlaces de las plataformas digitales de la iglesia.</p>
                </div>

                {/* Social Cards */}
                <section className="space-y-6">
                    {socials.map((social) => (
                        <div key={social.id} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-6 shadow-2xl group hover:border-primary/30 transition-all">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-6">
                                    <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg border border-white/5">
                                        <social.icon size={28} />
                                    </div>
                                    <div>
                                        <p className="text-base font-black text-white tracking-tight uppercase tracking-tight">{social.label}</p>
                                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">{social.sub}</p>
                                    </div>
                                </div>
                                <button className="px-4 py-2 rounded-xl bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest hover:bg-primary hover:text-white transition-all border border-primary/20">
                                    Probar Enlace
                                </button>
                            </div>
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder={social.placeholder}
                                    defaultValue={social.value}
                                    className="w-full bg-slate-950/40 border border-white/5 rounded-2xl p-5 text-sm font-medium text-slate-300 focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-slate-800"
                                />
                            </div>
                        </div>
                    ))}
                </section>

                {/* Streaming Section */}
                <section className="space-y-6">
                    <h3 className="text-xl font-black text-white tracking-tight uppercase tracking-tight ml-1">Transmisión Externa</h3>
                    <div className="bg-primary/5 border border-primary/20 rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-10">
                            <Radio size={120} className="text-primary rotate-12" />
                        </div>
                        <div className="flex items-start gap-8 relative z-10">
                            <div className="size-16 rounded-[1.5rem] bg-primary text-white flex items-center justify-center shadow-2xl shadow-primary/40 border border-primary-400/20 shrink-0">
                                <Radio size={32} className="animate-pulse" />
                            </div>
                            <div className="flex-1 space-y-6">
                                <div>
                                    <p className="text-lg font-black text-white tracking-tight">RTMP / Web Player</p>
                                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1 leading-relaxed">Introduce el link directo de tu servidor de streaming personalizado.</p>
                                </div>
                                <input
                                    type="text"
                                    placeholder="rtmp://streaming.iglesia.com/live"
                                    className="w-full bg-slate-900 border border-primary/30 rounded-2xl p-5 text-sm font-medium text-slate-200 focus:ring-2 focus:ring-primary outline-none shadow-xl"
                                />
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Sticky Actions */}
            <div className="fixed bottom-0 left-0 right-0 p-8 bg-slate-950/80 backdrop-blur-xl border-t border-white/5 z-50">
                <div className="max-w-4xl mx-auto">
                    <button className="w-full h-18 bg-primary hover:bg-primary-600 text-white font-black rounded-3xl shadow-2xl shadow-primary/30 hover:scale-[1.02] active:scale-[0.98] transition-all text-[11px] uppercase tracking-[0.2em] border border-primary-400/20 flex items-center justify-center gap-3">
                        <Save size={20} />
                        Guardar Cambios
                    </button>
                </div>
            </div>
        </div>
    );
}

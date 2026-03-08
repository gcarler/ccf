"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    ImagePlus,
    Calendar,
    Bold,
    Italic,
    List,
    Link2,
    BellRing,
    Eye,
    Send,
    X
} from 'lucide-react';

export default function CreateAnnouncement() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [pushEnabled, setPushEnabled] = useState(true);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                            <ArrowLeft size={18} />
                        </button>
                        <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Nuevo Anuncio</h1>
                    </div>
                    <button className="text-[10px] font-black text-primary hover:text-white transition-colors uppercase tracking-widest">
                        Limpiar
                    </button>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-40 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Intro */}
                <div className="space-y-1">
                    <h2 className="text-2xl font-black text-white tracking-tight uppercase tracking-tight">Crear Comunicado</h2>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Completa los detalles para notificar a la congregación.</p>
                </div>

                {/* Featured Image */}
                <section className="space-y-4">
                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Imagen Destacada</label>
                    <div className="relative group cursor-pointer">
                        <div className="w-full h-52 rounded-[2.5rem] border-2 border-dashed border-primary/20 bg-primary/5 flex flex-col items-center justify-center gap-4 hover:border-primary hover:bg-primary/10 transition-all shadow-2xl">
                            <div className="size-16 rounded-[1.5rem] bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg border border-white/5">
                                <ImagePlus size={32} />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-black text-white tracking-tight">Toca para cargar imagen</p>
                                <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest mt-1">JPG, PNG o WEBP (Máx. 5MB)</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Fields */}
                <section className="space-y-8">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Título del Anuncio</label>
                        <input
                            type="text"
                            placeholder="Ej: Gran Vigilia de Oración"
                            className="w-full bg-slate-900/40 border border-white/5 rounded-2xl p-5 text-sm font-black text-white focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-slate-700 shadow-xl"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Fecha de Publicación</label>
                        <div className="relative">
                            <input
                                type="date"
                                className="w-full bg-slate-900/40 border border-white/5 rounded-2xl p-5 text-sm font-black text-white focus:ring-2 focus:ring-primary/40 outline-none transition-all pr-14 shadow-xl [color-scheme:dark]"
                            />
                            <Calendar className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={20} />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Contenido del Mensaje</label>
                        <div className="rounded-[2rem] border border-white/5 bg-slate-900/40 shadow-2xl overflow-hidden backdrop-blur-xl">
                            <div className="flex items-center gap-2 p-3 border-b border-white/5 bg-white/5">
                                <button className="p-2 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white transition-all"><Bold size={18} /></button>
                                <button className="p-2 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white transition-all"><Italic size={18} /></button>
                                <button className="p-2 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white transition-all"><List size={18} /></button>
                                <div className="w-px h-6 bg-white/5 mx-2"></div>
                                <button className="p-2 rounded-xl hover:bg-white/10 text-slate-400 hover:text-white transition-all"><Link2 size={18} /></button>
                            </div>
                            <textarea
                                rows={8}
                                placeholder="Escribe el cuerpo del anuncio aquí..."
                                className="w-full bg-transparent border-none focus:ring-0 p-6 text-sm font-medium text-slate-300 placeholder:text-slate-700 resize-none leading-relaxed"
                            ></textarea>
                        </div>
                    </div>

                    {/* Settings Toggle */}
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex items-center justify-between shadow-2xl border-primary/10">
                        <div className="flex items-center gap-4">
                            <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 shadow-lg shadow-primary/5">
                                <BellRing size={22} />
                            </div>
                            <div>
                                <p className="text-sm font-black text-white uppercase tracking-tight">Notificación Push</p>
                                <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest mt-0.5">Alertar a todos los usuarios</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setPushEnabled(!pushEnabled)}
                            className={`relative w-14 h-7 rounded-full transition-all duration-300 ${pushEnabled ? 'bg-primary shadow-[0_0_10px_#4242f0]' : 'bg-slate-800'}`}
                        >
                            <div className={`absolute top-1 left-1 size-5 bg-white rounded-full transition-all duration-300 ${pushEnabled ? 'translate-x-7' : 'translate-x-0'}`}></div>
                        </button>
                    </div>
                </section>
            </main>

            {/* Bottom Actions */}
            <div className="fixed bottom-0 left-0 right-0 p-8 bg-slate-950/80 backdrop-blur-xl border-t border-white/5 z-50">
                <div className="flex gap-4 max-w-4xl mx-auto">
                    <button className="flex-1 h-16 rounded-2xl border border-white/10 bg-white/5 text-[10px] font-black text-white uppercase tracking-[0.2em] hover:bg-white/10 transition-all flex items-center justify-center gap-3">
                        <Eye size={18} className="text-primary" />
                        Vista Previa
                    </button>
                    <button className="flex-[1.5] h-16 rounded-2xl bg-primary text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-2xl shadow-primary/30 hover:bg-primary-600 active:scale-[0.98] transition-all flex items-center justify-center gap-3 border border-primary-400/20">
                        <Send size={18} />
                        Publicar
                    </button>
                </div>
            </div>
        </div>
    );
}

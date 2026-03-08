"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    ImagePlus,
    BookOpen,
    ListPlus,
    Save,
    Send,
    ChevronDown,
    Plus
} from 'lucide-react';


export default function CreateCourse() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Crear Nuevo Curso</h1>
                    <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:bg-primary/10 px-6 py-3 rounded-xl transition-all border border-transparent hover:border-primary/20">
                        Guardar
                    </button>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-40 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Thumbnail Section */}
                <section className="space-y-4">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 ml-1">Imagen de Portada</h3>
                    <div className="relative group cursor-pointer">
                        <div className="w-full aspect-video rounded-[2.5rem] border-2 border-dashed border-primary/20 bg-primary/5 flex flex-col items-center justify-center gap-4 hover:border-primary hover:bg-primary/10 transition-all group-active:scale-[0.98] shadow-2xl">
                            <div className="size-16 rounded-[1.5rem] bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg">
                                <ImagePlus size={32} />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-black text-white tracking-tight">Cargar Miniatura</p>
                                <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest mt-1">Recomendado: 1280x720px</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Form Section */}
                <section className="space-y-8">
                    <h3 className="text-xl font-black text-white tracking-tight uppercase tracking-tight ml-1">Información General</h3>

                    <div className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Título del Curso</label>
                            <input
                                type="text"
                                placeholder="Ej. Fundamentos de la Fe"
                                className="w-full bg-slate-900/40 border border-white/5 rounded-2xl p-5 text-sm font-black text-white focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-slate-700"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Descripción</label>
                            <textarea
                                rows={4}
                                placeholder="Describe los objetivos y el propósito de este curso para la congregación..."
                                className="w-full bg-slate-900/40 border border-white/5 rounded-[2rem] p-6 text-sm font-medium text-slate-300 focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-slate-700 resize-none leading-relaxed"
                            ></textarea>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Categoría</label>
                            <div className="relative">
                                <select className="w-full bg-slate-900/40 border border-white/5 rounded-2xl p-5 text-sm font-black text-white focus:ring-2 focus:ring-primary/40 outline-none appearance-none transition-all cursor-pointer">
                                    <option value="">Seleccionar categoría</option>
                                    <option value="biblia">Estudios Bíblicos</option>
                                    <option value="liderazgo">Liderazgo Cristiano</option>
                                    <option value="vida">Vida Victoriosa</option>
                                    <option value="jovenes">Ministerio Juvenil</option>
                                </select>
                                <ChevronDown className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={20} />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Lessons Section */}
                <section className="space-y-6">
                    <div className="flex items-center justify-between px-1">
                        <h3 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Añadir Lecciones</h3>
                        <span className="text-[10px] font-black text-primary bg-primary/10 px-4 py-1 rounded-full uppercase tracking-widest border border-primary/20">0 Lecciones</span>
                    </div>

                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-10 flex flex-col items-center text-center shadow-2xl group border-dashed border-2 hover:border-primary/40 transition-all">
                        <div className="size-20 rounded-[2rem] bg-primary/5 flex items-center justify-center mb-6 group-hover:bg-primary/10 transition-all shadow-lg border border-white/5">
                            <BookOpen size={32} className="text-primary" />
                        </div>
                        <p className="text-sm font-black text-slate-500 uppercase tracking-tight mb-8">Aún no has añadido contenido a este curso.</p>
                        <button className="flex items-center gap-3 bg-primary hover:bg-primary-600 text-white px-8 py-5 rounded-[1.5rem] font-black shadow-2xl shadow-primary/30 hover:scale-105 active:scale-95 transition-all text-[10px] uppercase tracking-[0.2em] border border-primary-400/20">
                            <Plus size={18} />
                            Añadir Primera Lección
                        </button>
                    </div>
                </section>
            </main>

            {/* Sticky Actions */}
            <div className="fixed bottom-0 left-0 right-0 p-8 bg-slate-950/80 backdrop-blur-xl border-t border-white/5 z-50">
                <div className="flex gap-4 max-w-4xl mx-auto">
                    <button className="flex-1 h-16 rounded-2xl border border-primary/30 text-[10px] font-black text-primary uppercase tracking-[0.2em] hover:bg-primary/5 transition-all active:scale-95">
                        Borrador
                    </button>
                    <button className="flex-[2] h-16 rounded-2xl bg-primary text-white text-[10px] font-black uppercase tracking-[0.2em] shadow-2xl shadow-primary/20 hover:bg-primary-600 active:scale-[0.98] transition-all border border-primary-400/20">
                        Publicar Curso
                    </button>
                </div>
            </div>
        </div>
    );
}

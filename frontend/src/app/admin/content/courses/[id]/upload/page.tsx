"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Video,
    FileText,
    Mic,
    CloudUpload,
    CheckCircle2,
    Plus,
    HelpCircle,
    Loader2
} from 'lucide-react';

export default function UploadMaterials() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [uploadProgress, setUploadProgress] = useState(75);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Cargar Materiales</h1>
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <HelpCircle size={20} />
                    </button>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-40 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Lesson Header */}
                <section className="space-y-4">
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary bg-primary/10 px-4 py-1.5 rounded-full border border-primary/20 shadow-lg shadow-primary/5">Gestión de Contenido</span>
                    <h2 className="text-2xl font-black text-white tracking-tight uppercase tracking-tight">Lección: Fundamentos de la Fe Cristiana</h2>
                    <p className="text-sm font-medium text-slate-500 leading-relaxed">Seleccione los archivos multimedia para esta sesión de discipulado.</p>
                </section>

                {/* Video Upload Card */}
                <section className="bg-slate-900/40 backdrop-blur-xl border border-white/10 rounded-[2.5rem] p-8 space-y-8 shadow-2xl relative overflow-hidden group">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-6">
                            <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg">
                                <Video size={28} />
                            </div>
                            <div>
                                <p className="text-base font-black text-white tracking-tight uppercase tracking-tight">Video de la Lección</p>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">MP4 • Máx. 500MB</p>
                            </div>
                        </div>
                        <CloudUpload size={24} className="text-primary animate-pulse" />
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <div className="space-y-1">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Subiendo...</span>
                                <span className="text-xs font-black text-white">fundamentos_v1.mp4</span>
                            </div>
                            <span className="text-sm font-black text-primary">{uploadProgress}%</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-slate-950 border border-white/5 p-0.5">
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-primary-400 to-primary shadow-[0_0_8px_#259df4] transition-all duration-500"
                                style={{ width: `${uploadProgress}%` }}
                            ></div>
                        </div>
                        <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest flex items-center gap-2">
                            324MB de 432MB • Quedan 2 min
                        </p>
                    </div>
                </section>

                {/* PDF Upload Card */}
                <section className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-6 shadow-2xl group hover:border-emerald-500/30 transition-all">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-6">
                            <div className="size-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 group-hover:bg-emerald-500 group-hover:text-white transition-all shadow-lg">
                                <FileText size={28} />
                            </div>
                            <div>
                                <p className="text-base font-black text-white tracking-tight uppercase tracking-tight">Guía del Alumno (PDF)</p>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">PDF • Máx. 25MB</p>
                            </div>
                        </div>
                        <button className="size-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-slate-500 hover:text-white transition-all">
                            <Plus size={20} />
                        </button>
                    </div>
                    <div className="flex items-center justify-center border-2 border-dashed border-white/5 rounded-[2rem] py-10 cursor-pointer hover:border-emerald-500/40 hover:bg-emerald-500/5 transition-all group/box">
                        <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] group-hover/box:text-emerald-500 transition-colors">Toca para seleccionar archivo PDF</p>
                    </div>
                </section>

                {/* Audio Upload Card */}
                <section className="bg-slate-900/40 backdrop-blur-xl border border-white/10 rounded-[2.5rem] p-8 space-y-6 shadow-2xl">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-6">
                            <div className="size-14 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500 shadow-lg">
                                <Mic size={28} />
                            </div>
                            <div>
                                <p className="text-base font-black text-white tracking-tight uppercase tracking-tight">Audio (MP3)</p>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">MP3 • Máx. 100MB</p>
                            </div>
                        </div>
                        <CheckCircle2 size={24} className="text-emerald-500" />
                    </div>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest">
                            <span className="text-emerald-500">Carga completada</span>
                            <span className="text-emerald-500">100%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-emerald-500/20">
                            <div className="h-full rounded-full bg-emerald-500 w-full shadow-[0_0_8px_rgba(16,185,129,0.4)]"></div>
                        </div>
                        <p className="text-[9px] font-semibold text-slate-600 italic">podcast_leccion_01.mp3 • 45.2 MB</p>
                    </div>
                </section>

                {/* Action Section */}
                <section className="space-y-6 pt-4">
                    <button className="w-full h-18 bg-primary hover:bg-primary-600 text-white font-black rounded-[1.5rem] shadow-2xl shadow-primary/30 hover:scale-[1.02] active:scale-[0.98] transition-all text-sm uppercase tracking-[0.2em] border border-primary-400/20">
                        Finalizar y Publicar
                    </button>
                    <p className="text-center text-[10px] font-black text-slate-700 uppercase tracking-widest leading-loose max-w-xs mx-auto">
                        Los materiales estarán disponibles para todos los miembros registrados una vez finalizado.
                    </p>
                </section>
            </main>
        </div>
    );
}

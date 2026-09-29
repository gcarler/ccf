"use client";

import React from 'react';
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
    HelpCircle
} from 'lucide-react';

export default function UploadMaterials() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const uploadProgress = 75;

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--background))] font-display">
            {/* Header Area */}
            <div className="bg-[hsl(var(--surface-1))]/80 backdrop-blur-xl border-b border-[hsl(var(--border))] sticky top-0 z-50">
                <div className="px-4 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-bold text-[hsl(var(--foreground))] tracking-tight uppercase tracking-tight">Cargar Materiales</h1>
                    <button className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all">
                        <HelpCircle size={20} />
                    </button>
                </div>
            </div>

            <main className="flex-1 px-4 py-1.5 pb-4 space-y-3 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Lesson Header */}
                <section className="space-y-4">
                    <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] px-4 py-1.5 rounded-full border border-[hsl(var(--primary)/0.2)] shadow-lg shadow-[hsl(var(--primary)/0.05)]">Gestión de Contenido</span>
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))] tracking-tight uppercase tracking-tight">Lección: Fundamentos de la Fe Cristiana</h2>
                    <p className="text-sm font-medium text-[hsl(var(--muted-foreground))] leading-relaxed">Seleccione los archivos multimedia para esta sesión de discipulado.</p>
                </section>

                {/* Video Upload Card */}
                <section className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-4 space-y-3 shadow-2xl relative overflow-hidden group">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-[hsl(var(--primary-foreground))] transition-all shadow-lg">
                                <Video size={28} />
                            </div>
                            <div>
                                <p className="text-base font-bold text-[hsl(var(--foreground))] tracking-tight uppercase tracking-tight">Video de la Lección</p>
                                <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">MP4 • Máx. 500MB</p>
                            </div>
                        </div>
                        <CloudUpload size={24} className="text-[hsl(var(--primary))] animate-pulse" />
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <div className="space-y-1">
                                <span className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide block">Subiendo...</span>
                                <span className="text-xs font-semibold text-[hsl(var(--foreground))]">fundamentos_v1.mp4</span>
                            </div>
                            <span className="text-sm font-semibold text-[hsl(var(--primary))]">{uploadProgress}%</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] p-0.5">
                            <div
                                className="h-full rounded-full bg-[hsl(var(--primary))] shadow-sm shadow-[hsl(var(--primary)/0.5)] transition-all duration-500"
                                style={{ width: `${uploadProgress}%` }}
                            ></div>
                        </div>
                        <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide flex items-center gap-2">
                            324MB de 432MB • Quedan 2 min
                        </p>
                    </div>
                </section>

                {/* PDF Upload Card */}
                <section className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-4 space-y-3 shadow-2xl group hover:border-[hsl(var(--success)/0.3)] transition-all">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="size-7 rounded-lg bg-[hsl(var(--success)/0.1)] flex items-center justify-center text-[hsl(var(--success))] group-hover:bg-[hsl(var(--success))] group-hover:text-[hsl(var(--primary-foreground))] transition-all shadow-lg">
                                <FileText size={28} />
                            </div>
                            <div>
                                <p className="text-base font-bold text-[hsl(var(--foreground))] tracking-tight uppercase tracking-tight">Guía del Alumno (PDF)</p>
                                <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">PDF • Máx. 25MB</p>
                            </div>
                        </div>
                        <button className="size-10 rounded-full bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3,var(--surface-2)))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all">
                            <Plus size={20} />
                        </button>
                    </div>
                    <div className="flex items-center justify-center border-2 border-dashed border-[hsl(var(--border))] rounded-lg py-1.5 cursor-pointer hover:border-[hsl(var(--success)/0.4)] hover:bg-[hsl(var(--success)/0.05)] transition-all group/box">
                        <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide group-hover/box:text-[hsl(var(--success))] transition-colors">Toca para seleccionar archivo PDF</p>
                    </div>
                </section>

                {/* Audio Upload Card */}
                <section className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-4 space-y-3 shadow-2xl">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="size-7 rounded-lg bg-[hsl(var(--warning)/0.1)] flex items-center justify-center text-[hsl(var(--warning))] shadow-lg">
                                <Mic size={28} />
                            </div>
                            <div>
                                <p className="text-base font-bold text-[hsl(var(--foreground))] tracking-tight uppercase tracking-tight">Audio (MP3)</p>
                                <p className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">MP3 • Máx. 100MB</p>
                            </div>
                        </div>
                        <CheckCircle2 size={24} className="text-[hsl(var(--success))]" />
                    </div>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center text-2xs font-semibold uppercase tracking-wide">
                            <span className="text-[hsl(var(--success))]">Carga completada</span>
                            <span className="text-[hsl(var(--success))]">100%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-[hsl(var(--success)/0.2)]">
                            <div className="h-full rounded-full bg-[hsl(var(--success))] w-full shadow-[0_0_8px_hsl(var(--success)/0.4)]"></div>
                        </div>
                        <p className="text-2xs font-semibold text-[hsl(var(--muted-foreground))] italic">podcast_leccion_01.mp3 • 45.2 MB</p>
                    </div>
                </section>

                {/* Action Section */}
                <section className="space-y-3 pt-4">
                    <button className="w-full h-8 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.9)] text-[hsl(var(--primary-foreground))] font-black rounded-lg shadow-xl shadow-[hsl(var(--primary)/0.3)] hover:scale-[1.02] active:scale-[0.98] transition-all text-sm uppercase tracking-wide border border-[hsl(var(--primary)/0.2)]">
                        Finalizar y Publicar
                    </button>
                    <p className="text-center font-semibold text-[hsl(var(--foreground))] uppercase tracking-wide leading-loose max-w-xs mx-auto">
                        Los materiales estarán disponibles para todos los personas registrados una vez finalizado.
                    </p>
                </section>
            </main>
        </div>
    );
}

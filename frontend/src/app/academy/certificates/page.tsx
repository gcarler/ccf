"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Search, Award, BookOpen, Users, School, Share2, Download } from 'lucide-react';


export default function StudentCertificates() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds - Celebratory Gradient */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-yellow-500/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
                <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Navigation */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <button onClick={() => router.back()} className="flex items-center justify-center size-10 rounded-full bg-primary/10 hover:bg-primary/20 transition-colors cursor-pointer text-primary">
                            <ArrowLeft size={20} />
                        </button>
                        <h1 className="text-white text-lg font-bold tracking-tight">Mis Certificados</h1>
                        <button className="flex items-center justify-center size-10 rounded-full hover:bg-white/10 transition-colors text-slate-400">
                            <Search size={20} />
                        </button>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto pb-24 relative z-10 hide-scrollbar">
                    {/* Featured Carousel Section */}
                    <section className="mt-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
                        <h2 className="px-6 text-white text-xl font-bold mb-6 flex items-center gap-3">
                            <Award className="text-yellow-500" size={24} />

                            Diplomas Destacados
                        </h2>

                        <div className="flex overflow-x-auto hide-scrollbar gap-5 px-6 snap-x pb-6">
                            {/* Featured Card 1 */}
                            <div className="min-w-[280px] snap-center group">
                                <div className="aspect-[1.6/1] rounded-[2rem] relative overflow-hidden border border-white/10 shadow-2xl shadow-yellow-500/20 bg-gradient-to-br from-slate-800 to-slate-950 group-hover:border-yellow-500/30 transition-all">
                                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-yellow-500/10 via-transparent to-transparent opacity-80 mix-blend-screen"></div>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center transform group-hover:scale-105 transition-transform duration-700">
                                        <Award className="text-yellow-500 mb-3" size={48} />

                                        <p className="text-[9px] uppercase tracking-[0.2em] text-yellow-500 font-bold">Certificado de Honor</p>
                                        <h3 className="text-base font-bold mt-2 text-white">Liderazgo Avanzado</h3>
                                        <div className="w-12 h-px bg-yellow-500/50 my-3"></div>
                                        <p className="text-[10px] text-slate-400 italic">Otorgado por excelencia académica</p>
                                    </div>
                                    <div className="absolute bottom-4 right-4">
                                        <div className="size-8 rounded-full bg-yellow-500/20 backdrop-blur-md flex items-center justify-center border border-yellow-500/30">
                                            <Award className="text-yellow-500" size={16} />

                                        </div>
                                    </div>
                                </div>
                                <p className="mt-4 text-sm font-bold px-2 text-slate-300 transform group-hover:text-yellow-500 transition-colors">Diplomado en Liderazgo</p>
                            </div>

                            {/* Featured Card 2 */}
                            <div className="min-w-[280px] snap-center group">
                                <div className="aspect-[1.6/1] rounded-[2rem] relative overflow-hidden border border-primary/20 shadow-2xl shadow-primary/20 bg-gradient-to-br from-primary/20 to-slate-950 group-hover:border-primary/50 transition-all">
                                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-transparent to-transparent opacity-80 mix-blend-screen"></div>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center transform group-hover:scale-105 transition-transform duration-700">
                                        <BookOpen className="text-primary-300 mb-3" size={48} />
                                        <p className="text-[9px] uppercase tracking-[0.2em] text-primary-400 font-bold">Grado Académico</p>
                                        <h3 className="text-base font-bold mt-2 text-white">Teología Sistemática</h3>
                                        <div className="w-12 h-px bg-primary/50 my-3"></div>
                                        <p className="text-[10px] text-slate-400 italic">Mención en Hermenéutica</p>
                                    </div>
                                </div>
                                <p className="mt-4 text-sm font-bold px-2 text-slate-300 transform group-hover:text-primary-400 transition-colors">Teología Sistemática</p>
                            </div>

                            {/* Featured Card 3 */}
                            <div className="min-w-[280px] snap-center group">
                                <div className="aspect-[1.6/1] rounded-[2rem] relative overflow-hidden border border-emerald-500/20 shadow-2xl shadow-emerald-500/20 bg-gradient-to-br from-emerald-500/20 to-slate-950 group-hover:border-emerald-500/50 transition-all">
                                    <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-500/20 via-transparent to-transparent opacity-80 mix-blend-screen"></div>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center transform group-hover:scale-105 transition-transform duration-700">
                                        <Users className="text-emerald-400 mb-3" size={48} />
                                        <p className="text-[9px] uppercase tracking-[0.2em] text-emerald-400 font-bold">Especialización</p>
                                        <h3 className="text-base font-bold mt-2 text-white">Ministerio Juvenil</h3>
                                        <div className="w-12 h-px bg-emerald-500/50 my-3"></div>
                                        <p className="text-[10px] text-slate-400 italic">Generación de Relevo</p>
                                    </div>
                                </div>
                                <p className="mt-4 text-sm font-bold px-2 text-slate-300 transform group-hover:text-emerald-400 transition-colors">Ministerio Juvenil</p>
                            </div>
                        </div>
                    </section>

                    {/* All Certificates List */}
                    <section className="mt-8 px-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                        <h3 className="text-white text-xl font-bold mb-6">Todos mis Títulos</h3>
                        <div className="flex flex-col gap-4">

                            {/* Certificate Card 1 */}
                            <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-6 shadow-xl transition-all group">
                                <div className="flex justify-between items-start">
                                    <div className="flex gap-4 items-center">
                                        <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner border border-primary/20 group-hover:bg-primary group-hover:text-white transition-all">
                                            <School size={24} />
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-white text-lg group-hover:text-primary transition-colors leading-tight">Diplomado en Liderazgo</h4>
                                            <p className="text-xs font-medium text-slate-400 mt-1">Emitido: 12 Oct, 2023</p>
                                        </div>
                                    </div>
                                    <button className="p-2.5 rounded-xl bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors border border-white/5">
                                        <Share2 size={18} />
                                    </button>
                                </div>
                                <div className="flex gap-3">
                                    <button className="flex-1 bg-white/5 hover:bg-primary/20 text-white py-4 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-3 transition-all border border-white/10 hover:border-primary/50 group/btn">
                                        <Download size={18} className="text-primary group-hover/btn:scale-110 transition-transform" />
                                        Descargar PDF
                                    </button>
                                </div>
                            </div>

                            {/* Certificate Card 2 */}
                            <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-6 shadow-xl transition-all group">
                                <div className="flex justify-between items-start">
                                    <div className="flex gap-4 items-center">
                                        <div className="size-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner border border-primary/20 group-hover:bg-primary group-hover:text-white transition-all">
                                            <BookOpen size={24} />
                                        </div>
                                        <div>
                                            <h4 className="font-bold text-white text-lg group-hover:text-primary transition-colors leading-tight">Escuela de Obreros</h4>
                                            <p className="text-xs font-medium text-slate-400 mt-1">Emitido: 05 Jun, 2023</p>
                                        </div>
                                    </div>
                                    <button className="p-2.5 rounded-xl bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors border border-white/5">
                                        <Share2 size={18} />
                                    </button>
                                </div>
                                <div className="flex gap-3">
                                    <button className="flex-1 bg-white/5 hover:bg-primary/20 text-white py-4 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-3 transition-all border border-white/10 hover:border-primary/50 group/btn">
                                        <Download size={18} className="text-primary group-hover/btn:scale-110 transition-transform" />
                                        Descargar PDF
                                    </button>
                                </div>
                            </div>

                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}

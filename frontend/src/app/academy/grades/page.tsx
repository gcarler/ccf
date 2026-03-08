"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Bell, BookOpen, History, Languages, ChevronRight } from 'lucide-react';

export default function StudentGrades() {
    const { user, isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen">
                {/* Header */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 flex items-center px-6 py-4 justify-between">
                    <button onClick={() => router.back()} className="text-primary flex size-10 shrink-0 items-center justify-center rounded-full hover:bg-primary/10 transition-colors cursor-pointer">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center">Mis Calificaciones</h1>
                    <div className="flex w-10 items-center justify-end">
                        <button className="flex items-center justify-center rounded-full size-10 bg-primary/10 text-primary transition-all active:scale-95 hover:bg-primary/20">
                            <Bell size={20} />
                        </button>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto pb-24 relative z-10">
                    {/* Summary Card */}
                    <section className="px-6 pt-6 mb-8 animate-in fade-in slide-in-from-top-4 duration-500">
                        <div className="relative overflow-hidden rounded-[2rem] bg-primary p-8 text-white shadow-2xl shadow-primary/30 border border-white/10 group">
                            <div className="absolute -right-10 -top-10 size-48 rounded-full bg-white/10 blur-3xl group-hover:bg-white/20 transition-colors duration-700"></div>
                            <div className="absolute -left-10 -bottom-10 size-32 rounded-full bg-white/5 blur-2xl"></div>

                            <div className="relative flex items-center justify-between z-10">
                                <div className="flex flex-col gap-2">
                                    <span className="text-[10px] font-black uppercase tracking-widest text-primary bg-white px-3 py-1.5 rounded-xl w-fit mb-2 shadow-sm">
                                        ESTUDIANTE
                                    </span>
                                    <h2 className="text-3xl font-black tracking-tight leading-none drop-shadow-md">Resumen Académico</h2>
                                    <p className="text-white/80 text-sm mt-1 font-medium">Has mejorado un 5% este semestre.</p>
                                </div>

                                {/* Circular Progress (GPA) */}
                                <div className="relative flex items-center justify-center shrink-0">
                                    <svg className="size-28 -rotate-90 drop-shadow-lg">
                                        <circle cx="56" cy="56" fill="transparent" r="46" stroke="rgba(255,255,255,0.2)" strokeWidth="10"></circle>
                                        <circle cx="56" cy="56" fill="transparent" r="46" stroke="white" strokeDasharray="289" strokeDashoffset="23.12" strokeLinecap="round" strokeWidth="10" className="transition-all duration-1000 ease-out"></circle>
                                    </svg>
                                    <div className="absolute inset-0 flex flex-col items-center justify-center drop-shadow-md">
                                        <span className="text-3xl font-black tracking-tighter">9.2</span>
                                        <span className="text-[9px] uppercase tracking-widest font-bold opacity-80 border-t border-white/30 pt-1 mt-1">Promedio</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Semester Filter Tabs */}
                    <div className="flex gap-3 px-6 mb-6 overflow-x-auto hide-scrollbar z-10 relative">
                        <button className="px-6 py-3 rounded-2xl bg-primary text-white text-[10px] uppercase tracking-widest font-bold whitespace-nowrap shadow-lg shadow-primary/20 border border-primary/50">
                            Semestre Actual
                        </button>
                        <button className="px-6 py-3 rounded-2xl bg-slate-900 text-slate-400 text-[10px] uppercase tracking-widest font-bold whitespace-nowrap border border-white/5 hover:text-white hover:border-white/20 transition-all">
                            2023 - II
                        </button>
                        <button className="px-6 py-3 rounded-2xl bg-slate-900 text-slate-400 text-[10px] uppercase tracking-widest font-bold whitespace-nowrap border border-white/5 hover:text-white hover:border-white/20 transition-all">
                            2023 - I
                        </button>
                    </div>

                    {/* Grades List */}
                    <div className="px-6 flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
                        <h3 className="text-white text-xl font-bold tracking-tight mb-2">Materias Inscritas</h3>

                        {/* Grade Card 1 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="flex items-center gap-5">
                                <div className="flex items-center justify-center rounded-2xl bg-primary/10 text-primary shrink-0 size-14 shadow-inner group-hover:bg-primary group-hover:text-white transition-all">
                                    <BookOpen size={24} />
                                </div>
                                <div className="flex-1 flex flex-col">
                                    <p className="text-white text-lg font-bold leading-tight group-hover:text-primary transition-colors">Teología Sistemática I</p>
                                    <p className="text-slate-400 text-xs font-medium mt-1">Prof. Dr. Samuel Méndez</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-primary text-2xl font-black drop-shadow-md">9.5<span className="text-xs text-slate-400 font-bold">/10</span></p>
                                    <p className="text-[9px] text-slate-500 uppercase font-black tracking-widest mt-1">Calificación</p>
                                </div>
                            </div>
                            <div className="h-[1px] bg-white/5 w-full"></div>
                            <div className="flex justify-between items-center">
                                <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                    <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
                                    <span className="text-[10px] text-emerald-400 font-black uppercase tracking-widest">Aprobado</span>
                                </div>
                                <div className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                                    Ver detalle
                                    <ChevronRight size={14} />
                                </div>
                            </div>
                        </div>

                        {/* Grade Card 2 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="flex items-center gap-5">
                                <div className="flex items-center justify-center rounded-2xl bg-primary/10 text-primary shrink-0 size-14 shadow-inner group-hover:bg-primary group-hover:text-white transition-all">
                                    <History size={24} />
                                </div>
                                <div className="flex-1 flex flex-col">
                                    <p className="text-white text-lg font-bold leading-tight group-hover:text-primary transition-colors">Historia del Pentecostalismo</p>
                                    <p className="text-slate-400 text-xs font-medium mt-1">Lic. Martha Ruiz</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-primary text-2xl font-black drop-shadow-md">8.8<span className="text-xs text-slate-400 font-bold">/10</span></p>
                                    <p className="text-[9px] text-slate-500 uppercase font-black tracking-widest mt-1">Calificación</p>
                                </div>
                            </div>
                            <div className="h-[1px] bg-white/5 w-full"></div>
                            <div className="flex justify-between items-center">
                                <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                    <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
                                    <span className="text-[10px] text-emerald-400 font-black uppercase tracking-widest">Aprobado</span>
                                </div>
                                <div className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                                    Ver detalle
                                    <ChevronRight size={14} />
                                </div>
                            </div>
                        </div>

                        {/* Grade Card 3 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="flex items-center gap-5">
                                <div className="flex items-center justify-center rounded-2xl bg-primary/10 text-primary shrink-0 size-14 shadow-inner group-hover:bg-primary group-hover:text-white transition-all">
                                    <Languages size={24} />
                                </div>
                                <div className="flex-1 flex flex-col">
                                    <p className="text-white text-lg font-bold leading-tight group-hover:text-primary transition-colors">Griego Bíblico I</p>
                                    <p className="text-slate-400 text-xs font-medium mt-1">Mtro. Esteban Torres</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-primary text-2xl font-black drop-shadow-md">9.2<span className="text-xs text-slate-400 font-bold">/10</span></p>
                                    <p className="text-[9px] text-slate-500 uppercase font-black tracking-widest mt-1">Calificación</p>
                                </div>
                            </div>
                            <div className="h-[1px] bg-white/5 w-full"></div>
                            <div className="flex justify-between items-center">
                                <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                    <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
                                    <span className="text-[10px] text-emerald-400 font-black uppercase tracking-widest">Aprobado</span>
                                </div>
                                <div className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                                    Ver detalle
                                    <ChevronRight size={14} />
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}

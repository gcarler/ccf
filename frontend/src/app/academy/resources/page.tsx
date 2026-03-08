"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Search, Star, BookOpen, FileText, Download, Group, Headphones, PlayCircle } from 'lucide-react';


export default function ResourcesLibrary() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Todos');

    if (!isAuthenticated) return null;

    const tabs = ['Todos', 'Libros', 'Devocionales', 'Guías', 'PDFs'];

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Navigation */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 px-6 pt-8 pb-4">
                    <div className="flex items-center justify-between mb-6">
                        <button onClick={() => router.back()} className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-white/10 transition-colors cursor-pointer text-slate-300">
                            <ArrowLeft size={20} />
                        </button>
                        <h1 className="text-white text-xl font-bold tracking-tight">Biblioteca Virtual</h1>
                        <button className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-white/10 transition-colors cursor-pointer text-primary">
                            <Star size={20} className="fill-current" />
                        </button>
                    </div>

                    {/* Search Bar */}
                    <div className="relative group">
                        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                            <Search className="text-slate-500 group-focus-within:text-primary transition-colors" size={20} />
                        </div>
                        <input
                            className="w-full bg-slate-900/50 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all shadow-inner"
                            placeholder="Buscar libros, estudios, devocionales..."
                            type="text"
                        />
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto pb-24 relative z-10 hide-scrollbar">
                    {/* Categories Tabs */}
                    <div className="flex gap-3 px-6 py-6 overflow-x-auto hide-scrollbar border-b border-white/5">
                        {tabs.map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`flex-none px-6 py-2.5 rounded-2xl text-[11px] uppercase tracking-widest font-black transition-all whitespace-nowrap ${activeTab === tab
                                    ? 'bg-primary text-white shadow-xl shadow-primary/30 border border-primary/20'
                                    : 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-white/20 hover:bg-white/10'
                                    }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    {/* Favorites Section */}
                    <section className="px-6 py-4 animate-in fade-in slide-in-from-right-8 duration-500">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-white tracking-tight">Mis Favoritos</h2>
                        </div>
                        <div className="flex gap-4 overflow-x-auto hide-scrollbar snap-x pb-4">
                            {/* Fav Card 1 */}
                            <div className="flex-shrink-0 w-44 bg-slate-900/50 backdrop-blur-xl rounded-2xl p-4 flex flex-col gap-3 border border-white/5 border-b-4 border-b-primary snap-center group cursor-pointer hover:bg-slate-900/80 transition-colors">
                                <div className="h-28 w-full rounded-xl bg-gradient-to-br from-primary/30 to-blue-600/10 flex items-center justify-center relative overflow-hidden group-hover:from-primary/40 transition-colors">
                                    <BookOpen className="text-primary text-opacity-80 drop-shadow-lg" size={40} strokeWidth={1.5} />
                                    <div className="absolute top-2 right-2">

                                        <Star className="text-yellow-500 fill-yellow-500 drop-shadow-md" size={16} />
                                    </div>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-sm font-bold text-white truncate group-hover:text-primary transition-colors">Teología Sistemática</span>
                                    <span className="text-[10px] uppercase font-black tracking-widest text-slate-500 truncate mt-1">Wayne Grudem</span>
                                </div>
                            </div>

                            {/* Fav Card 2 */}
                            <div className="flex-shrink-0 w-44 bg-slate-900/50 backdrop-blur-xl rounded-2xl p-4 flex flex-col gap-3 border border-white/5 border-b-4 border-b-emerald-500 snap-center group cursor-pointer hover:bg-slate-900/80 transition-colors">
                                <div className="h-28 w-full rounded-xl bg-gradient-to-br from-emerald-500/30 to-teal-600/10 flex items-center justify-center relative overflow-hidden group-hover:from-emerald-500/40 transition-colors">
                                    <FileText className="text-emerald-400 drop-shadow-lg" size={40} strokeWidth={1.5} />
                                    <div className="absolute top-2 right-2">
                                        <Star className="text-yellow-500 fill-yellow-500 drop-shadow-md" size={16} />
                                    </div>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-sm font-bold text-white truncate group-hover:text-emerald-400 transition-colors">Guía de Exégesis</span>
                                    <span className="text-[10px] uppercase font-black tracking-widest text-slate-500 truncate mt-1">Dpto. Académico</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Main Resources List */}
                    <section className="px-6 py-6 flex flex-col gap-5 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                        <h2 className="text-xl font-bold text-white tracking-tight">Recursos Recientes</h2>

                        {/* Resource Item 1 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-5 flex items-center gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="size-16 rounded-2xl bg-rose-500/10 flex items-center justify-center shrink-0 border border-rose-500/20 group-hover:bg-rose-500 group-hover:text-white transition-all text-rose-400">
                                <FileText size={28} />
                            </div>
                            <div className="flex flex-col flex-1 min-w-0">
                                <h3 className="text-base font-bold text-white truncate group-hover:text-rose-400 transition-colors">Historia del Pentecostalismo</h3>
                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-1 mb-3">Varios Autores • 4.2 MB</p>
                                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-rose-500 h-full w-[0%] transition-all duration-1000 group-hover:w-[100%] shadow-[0_0_8px_rgba(244,63,94,0.8)]"></div>
                                </div>
                            </div>
                            <button className="shrink-0 size-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10 hover:bg-rose-500 hover:border-rose-400 transition-colors text-slate-400 hover:text-white">
                                <Download size={20} />
                            </button>
                        </div>

                        {/* Resource Item 2 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-5 flex items-center gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="size-16 rounded-2xl bg-blue-500/10 flex items-center justify-center shrink-0 border border-blue-500/20 group-hover:bg-blue-500 group-hover:text-white transition-all text-blue-400">
                                <BookOpen size={28} />
                            </div>
                            <div className="flex flex-col flex-1 min-w-0">
                                <h3 className="text-base font-bold text-white truncate group-hover:text-blue-400 transition-colors">Manual del Estudiante 2024</h3>
                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-1 mb-3">Seminario Bíblico • 12.8 MB</p>
                                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-blue-500 h-full w-[60%] transition-all duration-1000 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
                                </div>
                            </div>
                            <button className="shrink-0 size-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10 hover:bg-blue-500 hover:border-blue-400 transition-colors text-slate-400 hover:text-white">
                                <Download size={20} />
                            </button>
                        </div>

                        {/* Resource Item 3 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-5 flex items-center gap-5 shadow-xl transition-all group cursor-pointer">
                            <div className="size-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center shrink-0 border border-emerald-500/20 group-hover:bg-emerald-500 group-hover:text-white transition-all text-emerald-400">
                                <Headphones size={28} />
                            </div>
                            <div className="flex flex-col flex-1 min-w-0">
                                <h3 className="text-base font-bold text-white truncate group-hover:text-emerald-400 transition-colors">Reflexión Nocturna</h3>
                                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-1 mb-3">Audio Devocional • 15 MB</p>
                                <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-emerald-500 h-full w-0 group-hover:w-[100%] transition-all duration-1000 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></div>
                                </div>
                            </div>
                            <button className="shrink-0 size-12 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 hover:bg-emerald-500 hover:border-emerald-400 transition-colors text-emerald-400 hover:text-white animate-pulse">
                                <PlayCircle size={24} className="fill-current text-slate-900/50" />
                            </button>
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}

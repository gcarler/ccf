"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Bell, Search, PlusCircle, MessageSquare, ThumbsUp, Grid, Book, History, Verified } from 'lucide-react';
import Link from 'next/link';

export default function TheologicalForum() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Todos');

    if (!isAuthenticated) return null;

    const tabs = [
        { name: 'Todos', icon: <Grid size={14} /> },
        { name: 'Romanos 8', icon: <Book size={14} /> },
        { name: 'Historia', icon: <History size={14} /> },
        { name: 'Doctrina', icon: <Verified size={14} /> },
    ];

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/15 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
                <div className="absolute top-1/2 left-0 w-[500px] h-[500px] bg-[radial-gradient(circle_at_center_left,_var(--tw-gradient-stops))] from-blue-600/10 via-slate-950 to-slate-950 opacity-50 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Navigation */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 px-6 pt-6 pb-4">
                    <div className="flex items-center justify-between mb-6">
                        <button onClick={() => router.back()} className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-white/10 transition-colors cursor-pointer text-slate-300">
                            <ArrowLeft size={20} />
                        </button>
                        <h1 className="text-white text-xl font-bold tracking-tight">Foro Teológico</h1>
                        <button className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-primary/20 transition-colors cursor-pointer text-primary">
                            <Bell size={20} />
                        </button>
                    </div>

                    {/* Search Bar */}
                    <div className="relative group mb-6">
                        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                            <Search className="text-slate-500 group-focus-within:text-primary transition-colors" size={20} />
                        </div>
                        <input
                            className="w-full bg-slate-900/50 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all shadow-inner"
                            placeholder="Buscar debates teológicos..."
                            type="text"
                        />
                    </div>

                    {/* Categories Tabs */}
                    <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-2">
                        {tabs.map((tab) => (
                            <button
                                key={tab.name}
                                onClick={() => setActiveTab(tab.name)}
                                className={`flex h-10 shrink-0 items-center justify-center gap-2 rounded-2xl px-5 text-xs font-bold uppercase tracking-widest transition-all whitespace-nowrap ${activeTab === tab.name
                                        ? 'bg-primary text-white shadow-lg shadow-primary/30 border border-primary/20'
                                        : 'bg-slate-900 border border-white/5 text-slate-400 hover:text-white hover:border-white/20'
                                    }`}
                            >
                                {tab.icon}
                                {tab.name}
                            </button>
                        ))}
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto pb-24 px-6 pt-6 relative z-10 hide-scrollbar space-y-5 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    {/* Create Thread Button */}
                    <button className="w-full flex items-center justify-center gap-3 bg-primary/10 text-primary h-14 rounded-2xl font-bold shadow-none active:scale-95 transition-transform border border-primary/20 hover:bg-primary hover:text-white group">
                        <PlusCircle size={20} className="group-hover:rotate-90 transition-transform" />
                        <span className="uppercase tracking-widest text-[11px] font-black">Crear Nuevo Debate</span>
                    </button>

                    {/* Thread Card 1 */}
                    <Link href="/academy/forum/1" className="block bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 shadow-xl transition-all group">
                        <div className="flex justify-between items-start mb-4">
                            <span className="bg-primary/10 text-primary text-[9px] font-black uppercase tracking-widest px-3 py-1.5 rounded-xl border border-primary/20">Exégesis</span>
                            <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Hace 2 horas</span>
                        </div>
                        <h3 className="text-white font-bold text-xl leading-snug mb-2 group-hover:text-primary transition-colors">Análisis de Romanos 8: La Vida en el Espíritu</h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-5 leading-relaxed">¿Cómo reconciliamos la soberanía de Dios con la responsabilidad humana en este pasaje clave?</p>

                        <div className="flex items-center justify-between border-t border-white/5 pt-4">
                            <div className="flex items-center gap-3">
                                <div className="size-8 rounded-full bg-slate-800 border bg-gradient-to-br from-indigo-500 to-primary flex items-center justify-center border-white/20 shadow-inner text-xs font-black">
                                    DM
                                </div>
                                <span className="text-slate-300 text-xs font-bold">Hno. David Morales</span>
                            </div>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-1.5 text-primary">
                                    <ThumbsUp size={16} className="fill-current" />
                                    <span className="text-xs font-black font-mono">24</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-slate-500 group-hover:text-white transition-colors">
                                    <MessageSquare size={16} />
                                    <span className="text-xs font-black font-mono">12</span>
                                </div>
                            </div>
                        </div>
                    </Link>

                    {/* Thread Card 2 */}
                    <Link href="/academy/forum/2" className="block bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-emerald-500/30 rounded-[2rem] p-6 shadow-xl transition-all group">
                        <div className="flex justify-between items-start mb-4">
                            <span className="bg-emerald-500/10 text-emerald-400 text-[9px] font-black uppercase tracking-widest px-3 py-1.5 rounded-xl border border-emerald-500/20">Historia Eclesiástica</span>
                            <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Ayer</span>
                        </div>
                        <h3 className="text-white font-bold text-xl leading-snug mb-2 group-hover:text-emerald-400 transition-colors">El Avivamiento de Azusa Street y su impacto global</h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-5 leading-relaxed">Explorando las raíces de nuestra fe pentecostal y su relevancia para la iglesia moderna en Latinoamérica.</p>

                        <div className="flex items-center justify-between border-t border-white/5 pt-4">
                            <div className="flex items-center gap-3">
                                <div className="size-8 rounded-full bg-slate-800 border bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center border-white/20 shadow-inner text-xs font-black">
                                    MR
                                </div>
                                <span className="text-slate-300 text-xs font-bold">Maestra Rebeca S.</span>
                            </div>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-1.5 text-emerald-400">
                                    <ThumbsUp size={16} className="fill-current" />
                                    <span className="text-xs font-black font-mono">56</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-slate-500 group-hover:text-white transition-colors">
                                    <MessageSquare size={16} />
                                    <span className="text-xs font-black font-mono">38</span>
                                </div>
                            </div>
                        </div>
                    </Link>

                    {/* Thread Card 3 */}
                    <Link href="/academy/forum/3" className="block bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-blue-500/30 rounded-[2rem] p-6 shadow-xl transition-all group">
                        <div className="flex justify-between items-start mb-4">
                            <span className="bg-blue-500/10 text-blue-400 text-[9px] font-black uppercase tracking-widest px-3 py-1.5 rounded-xl border border-blue-500/20">Doctrina</span>
                            <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Hace 3 días</span>
                        </div>
                        <h3 className="text-white font-bold text-xl leading-snug mb-2 group-hover:text-blue-400 transition-colors">Dones Espirituales: ¿Continuidad o Cesacionismo?</h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-5 leading-relaxed">Un debate respetuoso sobre la vigencia de los carismas en la liturgia contemporánea.</p>

                        <div className="flex items-center justify-between border-t border-white/5 pt-4">
                            <div className="flex items-center gap-3">
                                <div className="size-8 rounded-full bg-slate-800 border bg-gradient-to-br from-blue-500 to-primary flex items-center justify-center border-white/20 shadow-inner text-xs font-black">
                                    SR
                                </div>
                                <span className="text-slate-300 text-xs font-bold">Pastor Samuel Ruiz</span>
                            </div>
                            <div className="flex gap-4">
                                <div className="flex items-center gap-1.5 text-blue-400">
                                    <ThumbsUp size={16} className="fill-current" />
                                    <span className="text-xs font-black font-mono">89</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-slate-500 group-hover:text-white transition-colors">
                                    <MessageSquare size={16} />
                                    <span className="text-xs font-black font-mono">142</span>
                                </div>
                            </div>
                        </div>
                    </Link>

                </main>
            </div>
        </div>
    );
}

"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Search, PlusCircle, HeartHandshake, Share2, BookOpen, CalendarDays, User, MessageSquare } from 'lucide-react';

import Link from 'next/link';

export default function TestimoniesWall() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Todos');

    if (!isAuthenticated) return null;

    const tabs = ['Todos', 'Sanidad', 'Provisión', 'Restauración', 'Milagro'];

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-1/4 -right-1/4 w-[800px] h-[800px] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-100 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 pt-8 pb-4 border-b border-white/5">
                    <div className="flex items-center justify-between">
                        <button onClick={() => router.back()} className="text-primary flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 hover:bg-primary/20 transition-colors cursor-pointer">
                            <ArrowLeft size={20} />
                        </button>
                        <h2 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center">Muro de Testimonios</h2>
                        <button className="flex items-center justify-center size-10 rounded-full hover:bg-white/10 transition-colors cursor-pointer text-slate-400">
                            <Search size={20} />
                        </button>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto pb-32 relative z-10 hide-scrollbar pt-6 px-6">
                    {/* Featured Hero Section */}
                    <div className="relative flex flex-col justify-end overflow-hidden rounded-[2rem] min-h-[320px] shadow-2xl group animate-in fade-in slide-in-from-top-8 duration-700">
                        <div className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 group-hover:scale-105" style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1438232992991-995b7058bbb3?q=80&w=2073&auto=format&fit=crop")' }}>
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent"></div>
                        <div className="absolute inset-0 bg-primary/10 mix-blend-overlay"></div>
                        <div className="relative p-8">
                            <span className="inline-block bg-primary/90 backdrop-blur-sm px-3.5 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest text-white mb-3 shadow-lg">Historias de Fe</span>
                            <h1 className="text-white text-3xl font-black leading-tight drop-shadow-lg tracking-tight">Milagros que Transforman</h1>
                            <p className="text-slate-300 text-sm mt-3 font-medium opacity-90 max-w-sm">Explora lo que Dios está haciendo en nuestra congregación hoy.</p>
                        </div>
                    </div>

                    {/* Action Button */}
                    <div className="my-6 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                        <Link href="/community/testimonies/publish" className="flex w-full items-center justify-center rounded-2xl h-14 bg-primary text-white gap-3 shadow-xl shadow-primary/30 hover:bg-primary-600 transition-all active:scale-95 group border border-primary-400/30">
                            <PlusCircle size={22} className="group-hover:rotate-90 transition-transform duration-300" />
                            <span className="text-sm font-black uppercase tracking-widest text-[11px]">Publicar Testimonio</span>
                        </Link>
                    </div>

                    {/* Filter Tabs */}
                    <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-6 animate-in fade-in slide-in-from-left-8 duration-700 delay-150">
                        {tabs.map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`flex h-10 shrink-0 items-center justify-center rounded-2xl px-5 transition-all text-[11px] font-black uppercase tracking-widest whitespace-nowrap border ${activeTab === tab
                                    ? 'bg-primary text-white shadow-lg shadow-primary/30 border-primary/50'
                                    : 'bg-slate-900 border-white/5 text-slate-400 hover:text-white hover:border-white/20'
                                    }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center justify-between mb-5 animate-in fade-in duration-700 delay-200">
                        <h2 className="text-white text-xl font-bold tracking-tight">Testimonios Destacados</h2>
                    </div>

                    {/* Testimonies List */}
                    <div className="space-y-5 animate-in fade-in slide-in-from-bottom-12 duration-700 delay-300">

                        {/* Testimony Card 1 */}
                        <article className="bg-slate-900/40 backdrop-blur-xl border border-white/5 hover:border-emerald-500/30 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group">
                            <div className="flex justify-between items-start">
                                <div className="flex items-center gap-4">
                                    <div className="size-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-black shadow-inner border border-white/10 shrink-0">
                                        AM
                                    </div>
                                    <div>
                                        <h4 className="text-base font-bold text-white group-hover:text-emerald-400 transition-colors">Andrés Mendoza</h4>
                                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">Hace 2 horas</p>
                                    </div>
                                </div>
                                <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Provisión</span>
                            </div>
                            <div className="relative">
                                <span className="absolute -top-3 -left-2 text-6xl text-white/5 font-serif font-black">&quot;</span>

                                <p className="text-sm leading-relaxed text-slate-300 relative z-10 italic pl-4 border-l-2 border-emerald-500/30">
                                    En un momento de gran necesidad económica, Dios abrió una puerta que parecía imposible. Después de meses buscando empleo, recibí una oferta que superó mis oraciones. ¡Gloria a Dios!
                                </p>
                            </div>
                            <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-1">
                                <div className="flex gap-5">
                                    <button className="flex items-center gap-2 text-slate-400 hover:text-emerald-400 transition-colors group/btn">
                                        <HeartHandshake size={18} className="group-hover/btn:scale-110 transition-transform" />
                                        <span className="text-xs font-black">124 Amén</span>
                                    </button>
                                    <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                                        <Share2 size={18} />
                                        <span className="text-xs font-bold">Compartir</span>
                                    </button>
                                </div>
                            </div>
                        </article>

                        {/* Testimony Card 2 */}
                        <article className="bg-slate-900/40 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group">
                            <div className="flex justify-between items-start">
                                <div className="flex items-center gap-4">
                                    <div className="size-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-primary flex items-center justify-center text-white font-black shadow-inner border border-white/10 shrink-0">
                                        ER
                                    </div>
                                    <div>
                                        <h4 className="text-base font-bold text-white group-hover:text-primary transition-colors">Elena Rodríguez</h4>
                                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">Ayer, 4:30 PM</p>
                                    </div>
                                </div>
                                <span className="bg-primary/10 text-primary border border-primary/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Sanidad</span>
                            </div>
                            <div className="relative">
                                <span className="absolute -top-3 -left-2 text-6xl text-white/5 font-serif font-black">&quot;</span>

                                <p className="text-sm leading-relaxed text-slate-300 relative z-10 italic pl-4 border-l-2 border-primary/30">
                                    Fui sana de una afección crónica en mi espalda durante el servicio de oración del domingo pasado. El dolor que me acompañó por años desapareció por completo. ¡El poder de la fe es real!
                                </p>
                            </div>
                            <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-1">
                                <div className="flex gap-5">
                                    <button className="flex items-center gap-2 text-primary group/btn">
                                        <HeartHandshake size={18} className="fill-current group-hover/btn:scale-110 transition-transform" />
                                        <span className="text-xs font-black">312 Amén</span>
                                    </button>
                                    <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                                        <Share2 size={18} />
                                        <span className="text-xs font-bold">Compartir</span>
                                    </button>
                                </div>
                            </div>
                        </article>

                        {/* Testimony Card 3 (Image content) */}
                        <article className="bg-slate-900/40 backdrop-blur-xl border border-white/5 hover:border-rose-500/30 rounded-[2rem] p-0 flex flex-col shadow-xl transition-all group overflow-hidden">
                            <div className="h-56 w-full bg-cover bg-center transition-transform duration-700 group-hover:scale-105" style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1511895426328-dc8714191300?q=80&w=2070&auto=format&fit=crop")' }}></div>
                            <div className="p-6 flex flex-col gap-5 relative bg-slate-900/40 backdrop-blur-xl">
                                <div className="flex justify-between items-start">
                                    <div className="flex items-center gap-4">
                                        <div className="size-12 rounded-2xl bg-gradient-to-br from-rose-500 to-orange-500 flex items-center justify-center text-white font-black shadow-inner border border-white/10 shrink-0">
                                            FS
                                        </div>
                                        <div>
                                            <h4 className="text-base font-bold text-white group-hover:text-rose-400 transition-colors">Familia Salazar</h4>
                                            <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">Hace 2 días</p>
                                        </div>
                                    </div>
                                    <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Restauración</span>
                                </div>
                                <div className="relative">
                                    <span className="absolute -top-3 -left-2 text-6xl text-white/5 font-serif font-black">&quot;</span>

                                    <p className="text-sm leading-relaxed text-slate-300 relative z-10 italic pl-4 border-l-2 border-rose-500/30">
                                        Dios restauró nuestro matrimonio cuando todo parecía perdido. Hoy servimos juntos con gozo.
                                    </p>
                                </div>
                                <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-1">
                                    <div className="flex gap-5">
                                        <button className="flex items-center gap-2 text-slate-400 hover:text-rose-400 transition-colors group/btn">
                                            <HeartHandshake size={18} className="group-hover/btn:scale-110 transition-transform" />
                                            <span className="text-xs font-black">89 Amén</span>
                                        </button>
                                        <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                                            <Share2 size={18} />
                                            <span className="text-xs font-bold">Compartir</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </article>

                    </div>
                </main>
            </div>
        </div>
    );
}

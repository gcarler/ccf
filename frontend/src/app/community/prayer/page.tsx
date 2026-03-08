"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Church, Search, HandHeart, CalendarDays, User, HeartHandshake } from 'lucide-react';
import Link from 'next/link';

export default function PrayerWall() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Recientes');

    if (!isAuthenticated) return null;

    const tabs = ['Recientes', 'Urgentes', 'Mis Pedidos'];

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds - Ethereal Bg */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/15 via-slate-950/50 to-slate-950 opacity-100 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 pt-10 pb-0 border-b border-white/5">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3 animate-in fade-in slide-in-from-left-4 duration-500">
                            <Church className="text-primary" size={28} />
                            <h1 className="text-2xl font-black tracking-tight text-white drop-shadow-md">Muro de Oración</h1>
                        </div>
                        <Link href="/community/prayer/request" className="bg-primary hover:bg-primary-600 text-white px-5 py-2.5 rounded-full text-sm font-black shadow-lg shadow-primary/30 transition-all active:scale-95 flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-500">
                            Pedir Oración
                        </Link>
                    </div>

                    {/* Filter Tabs */}
                    <div className="flex gap-6 overflow-x-auto hide-scrollbar">
                        {tabs.map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`pb-3 text-sm font-black tracking-wide uppercase transition-all whitespace-nowrap border-b-2 ${activeTab === tab
                                        ? 'border-primary text-primary drop-shadow-[0_0_8px_rgba(66,66,240,0.5)]'
                                        : 'border-transparent text-slate-500 hover:text-slate-300'
                                    }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                </header>

                {/* Main Feed */}
                <main className="flex-1 px-6 py-6 space-y-5 overflow-y-auto relative z-10 hide-scrollbar animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Prayer Card 1 */}
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group hover:border-primary/30">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner border border-primary/20">
                                    <User size={24} />
                                </div>
                                <div>
                                    <p className="text-white text-base font-bold">Anónimo</p>
                                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mt-0.5">Hace 15 min</p>
                                </div>
                            </div>
                            <span className="bg-primary/10 text-primary border border-primary/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Salud</span>
                        </div>
                        <div className="space-y-2.5">
                            <h3 className="text-white font-black text-xl leading-snug group-hover:text-primary transition-colors">Recuperación de Juan Carlos</h3>
                            <p className="text-slate-400 text-sm leading-relaxed">
                                Pedimos oración por la pronta recuperación de nuestro hermano Juan, quien se encuentra en cirugía de emergencia. Confiamos en el poder sanador de Dios.
                            </p>
                        </div>
                        <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-2">
                            <div className="flex items-center gap-2 text-primary">
                                <HandHeart size={16} className="fill-current opacity-80" />
                                <span className="text-xs font-black tracking-wide">124 orando</span>
                            </div>
                            <button className="flex items-center gap-2 bg-primary/10 hover:bg-primary text-primary hover:text-white px-5 py-2.5 rounded-xl transition-all duration-300 active:scale-95 group/btn border border-primary/20 hover:border-primary">
                                <HeartHandshake size={16} className="group-hover/btn:-rotate-12 transition-transform" />
                                <span className="text-xs font-black uppercase tracking-widest">Me uno</span>
                            </button>
                        </div>
                    </div>

                    {/* Prayer Card 2 */}
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group hover:border-emerald-500/30">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white shadow-inner font-black border border-white/10">
                                    MS
                                </div>
                                <div>
                                    <p className="text-white text-base font-bold">Mateo Silva</p>
                                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mt-0.5">Hace 2 horas</p>
                                </div>
                            </div>
                            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Trabajo</span>
                        </div>
                        <div className="space-y-2.5">
                            <h3 className="text-white font-black text-xl leading-snug group-hover:text-emerald-400 transition-colors">Provisión y Nueva Etapa</h3>
                            <p className="text-slate-400 text-sm leading-relaxed">
                                Estoy buscando una nueva oportunidad laboral. Pido oración para que el Señor abra las puertas correctas y me dé sabiduría en las entrevistas esta semana.
                            </p>
                        </div>
                        <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-2">
                            <div className="flex items-center gap-2 text-emerald-400">
                                <HandHeart size={16} className="fill-current opacity-80" />
                                <span className="text-xs font-black tracking-wide">56 orando</span>
                            </div>
                            <button className="flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-white px-5 py-2.5 rounded-xl transition-all duration-300 active:scale-95 group/btn border border-emerald-500/20 hover:border-emerald-500">
                                <HeartHandshake size={16} className="group-hover/btn:-rotate-12 transition-transform" />
                                <span className="text-xs font-black uppercase tracking-widest">Me uno</span>
                            </button>
                        </div>
                    </div>

                    {/* Prayer Card 3 */}
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 flex flex-col gap-5 shadow-xl transition-all group hover:border-rose-500/30">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-slate-400 shadow-inner border border-white/10">
                                    <User size={24} />
                                </div>
                                <div>
                                    <p className="text-white text-base font-bold">Anónimo</p>
                                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mt-0.5">Hace 5 horas</p>
                                </div>
                            </div>
                            <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[9px] uppercase font-black px-3 py-1.5 rounded-xl tracking-widest shadow-sm">Familia</span>
                        </div>
                        <div className="space-y-2.5">
                            <h3 className="text-white font-black text-xl leading-snug group-hover:text-rose-400 transition-colors">Restauración Familiar</h3>
                            <p className="text-slate-400 text-sm leading-relaxed">
                                Por la paz en mi hogar y la reconciliación entre mis hijos. Que el amor de Cristo sea el centro de nuestra convivencia.
                            </p>
                        </div>
                        <div className="flex items-center justify-between pt-4 border-t border-white/5 mt-2">
                            <div className="flex items-center gap-2 text-rose-400">
                                <HandHeart size={16} className="fill-current opacity-80" />
                                <span className="text-xs font-black tracking-wide">89 orando</span>
                            </div>
                            <button className="flex items-center gap-2 bg-rose-500/10 hover:bg-rose-500 text-rose-400 hover:text-white px-5 py-2.5 rounded-xl transition-all duration-300 active:scale-95 group/btn border border-rose-500/20 hover:border-rose-500">
                                <HeartHandshake size={16} className="group-hover/btn:-rotate-12 transition-transform" />
                                <span className="text-xs font-black uppercase tracking-widest">Me uno</span>
                            </button>
                        </div>
                    </div>

                </main>
            </div>
        </div>
    );
}

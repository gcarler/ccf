"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Calendar, Bell, ChevronRight, MapPin, Clock, Video, Share2, Plus, CalendarDays, User, Users } from 'lucide-react';

import Link from 'next/link';

export default function EventsCalendar() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Todos');

    if (!isAuthenticated) return null;

    const tabs = ['Todos', 'Servicios', 'Juveniles', 'Estudios', 'Misiones'];

    const dates = [
        { day: 'Lun', num: '12', active: false },
        { day: 'Mar', num: '13', active: false },
        { day: 'Mié', num: '14', active: true },
        { day: 'Jue', num: '15', active: false },
        { day: 'Vie', num: '16', active: false },
        { day: 'Sáb', num: '17', active: false },
        { day: 'Dom', num: '18', active: false },
    ];

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-primary/20 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
                <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-[radial-gradient(circle_at_bottom_right,_var(--tw-gradient-stops))] from-blue-600/10 via-slate-950 to-slate-950 opacity-50 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 pt-10 pb-4 border-b border-white/5">
                    <div className="flex items-center justify-between mb-8">
                        <div className="animate-in fade-in slide-in-from-left-6 duration-700">
                            <p className="text-[10px] font-black uppercase tracking-[0.4em] text-primary/80">Comunidad El Faro</p>
                            <h1 className="text-3xl font-black tracking-tight text-white mt-1 drop-shadow-md">Calendario</h1>
                        </div>
                        <button className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all group animate-in fade-in slide-in-from-right-6 duration-700">
                            <Bell size={22} className="text-white/70 group-hover:text-white transition-colors" />
                            <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary ring-4 ring-slate-950/40 animate-pulse"></span>
                        </button>
                    </div>

                    <div className="flex items-center justify-between mb-6 animate-in fade-in duration-700 delay-100">
                        <h2 className="text-xl font-bold text-white/90">Enero 2024</h2>
                        <button className="text-[11px] font-black text-primary uppercase tracking-[0.2em] hover:underline transition-all">Ver Todo</button>
                    </div>

                    {/* Horizontal Date Picker */}
                    <div className="flex gap-4 overflow-x-auto hide-scrollbar pb-2 animate-in fade-in slide-in-from-right-12 duration-1000 delay-200">
                        {dates.map((date) => (
                            <div
                                key={date.num}
                                className={`flex flex-col items-center justify-center min-w-[64px] h-24 rounded-[2rem] transition-all cursor-pointer border ${date.active
                                    ? 'bg-primary text-white shadow-[0_12px_24px_rgba(66,66,240,0.4)] border-primary/50 scale-110 z-20'
                                    : 'bg-white/5 text-slate-500 border-white/5 hover:bg-white/10 hover:border-white/20'
                                    }`}
                            >
                                <span className={`text-[10px] font-black uppercase mb-1 ${date.active ? 'text-white/80' : 'text-slate-500'}`}>
                                    {date.day}
                                </span>
                                <span className={`text-xl font-black ${date.active ? 'text-white' : 'text-slate-400'}`}>
                                    {date.num}
                                </span>
                                {date.active && <div className="mt-1 h-1 w-1 rounded-full bg-white shadow-[0_0_8px_#ffffff]"></div>}
                            </div>
                        ))}
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto pb-32 pt-8 px-6 space-y-8 relative z-10 hide-scrollbar">
                    {/* Category Filter */}
                    <div className="flex gap-4 overflow-x-auto hide-scrollbar animate-in fade-in slide-in-from-left-8 duration-700 delay-300">
                        {tabs.map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`shrink-0 text-xs font-black uppercase tracking-widest px-1 py-3 transition-all border-b-2 ${activeTab === tab
                                    ? 'text-primary border-primary drop-shadow-[0_0_8px_rgba(66,66,240,0.5)]'
                                    : 'text-slate-500 border-transparent hover:text-slate-300'
                                    }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center gap-3 animate-in fade-in duration-700 delay-400">
                        <div className="size-2 rounded-full bg-primary shadow-[0_0_8px_#4242f0]"></div>
                        <h2 className="text-[11px] font-black text-slate-500 tracking-[0.25em] uppercase">Eventos destacados</h2>
                    </div>

                    {/* Events List */}
                    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-500">

                        {/* Event Card 1 */}
                        <div className="bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-[3rem] overflow-hidden group shadow-2xl transition-all hover:border-primary/30">
                            <div className="relative aspect-[16/10] overflow-hidden">
                                <div className="absolute inset-0 h-full w-full bg-slate-900 transition-transform duration-1000 group-hover:scale-110">
                                    <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-slate-900/40 to-slate-900 opacity-60"></div>
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <CalendarDays size={64} className="text-white/10" />
                                    </div>
                                </div>

                                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent"></div>
                                <div className="absolute top-6 left-6 flex gap-3">
                                    <span className="rounded-xl bg-primary/90 text-white px-3.5 py-1.5 text-[9px] font-black uppercase tracking-widest backdrop-blur-md shadow-lg">Servicio Especial</span>
                                    <div className="flex items-center gap-1.5 text-white bg-slate-950/50 px-3.5 py-1.5 rounded-xl backdrop-blur-md border border-white/10 shadow-lg">
                                        <Clock size={12} className="text-primary" />
                                        <span className="text-[10px] font-black tracking-tight">19:30</span>
                                    </div>
                                </div>
                            </div>
                            <div className="p-8 space-y-6">
                                <h3 className="text-2xl font-black text-white leading-tight group-hover:text-primary transition-colors">Noche de Avivamiento y Gloria</h3>
                                <div className="flex items-center justify-between border-t border-white/5 pt-6">
                                    <div className="flex -space-x-3">
                                        {[1, 2, 3].map(i => (
                                            <div key={i} className="size-9 rounded-full border-2 border-slate-900 bg-slate-800 flex items-center justify-center text-[10px] font-bold overflow-hidden shadow-md">
                                                <User size={16} />
                                            </div>
                                        ))}
                                        <div className="size-9 rounded-full border-2 border-slate-900 bg-primary text-[10px] font-black text-white flex items-center justify-center shadow-md">+2.5k</div>
                                    </div>
                                    <div className="flex gap-3">
                                        <button className="size-12 bg-white/5 text-white rounded-2xl flex items-center justify-center border border-white/10 hover:bg-white/10 transition-all active:scale-95 shadow-lg">
                                            <Share2 size={20} />
                                        </button>
                                        <button className="bg-primary hover:bg-primary-600 text-white px-8 py-3.5 rounded-2xl text-[11px] font-black uppercase tracking-[0.15em] shadow-xl shadow-primary/30 transition-all active:scale-95 border border-primary-400/20">
                                            Inscribirse
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Event Card 2 */}
                        <div className="bg-slate-900/60 backdrop-blur-xl border border-white/10 rounded-[3rem] overflow-hidden group shadow-2xl transition-all hover:border-emerald-500/30">
                            <div className="relative aspect-[16/10] overflow-hidden">
                                <div className="absolute inset-0 h-full w-full bg-slate-900 transition-transform duration-1000 group-hover:scale-110">
                                    <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/20 via-slate-900/40 to-slate-900 opacity-60"></div>
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <Users size={64} className="text-white/10" />
                                    </div>
                                </div>

                                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent"></div>
                                <div className="absolute top-6 left-6 flex gap-3">
                                    <span className="rounded-xl bg-emerald-500/90 text-white px-3.5 py-1.5 text-[9px] font-black uppercase tracking-widest backdrop-blur-md shadow-lg">Congreso Juvenil</span>
                                    <div className="flex items-center gap-1.5 text-white bg-slate-950/50 px-3.5 py-1.5 rounded-xl backdrop-blur-md border border-white/10 shadow-lg">
                                        <MapPin size={12} className="text-emerald-400" />
                                        <span className="text-[10px] font-black tracking-tight">Auditorio</span>
                                    </div>
                                </div>
                            </div>
                            <div className="p-8 space-y-6">
                                <h3 className="text-2xl font-black text-white leading-tight group-hover:text-emerald-400 transition-colors">Generación de Fuego: 2024</h3>
                                <div className="flex items-center justify-between border-t border-white/5 pt-6">
                                    <div className="animate-pulse">
                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">Entrada Libre</span>
                                    </div>
                                    <div className="flex gap-3">
                                        <button className="size-12 bg-white/5 text-white rounded-2xl flex items-center justify-center border border-white/10 hover:bg-white/10 transition-all active:scale-95 shadow-lg">
                                            <Share2 size={20} />
                                        </button>
                                        <button className="bg-emerald-500 hover:bg-emerald-600 text-white px-8 py-3.5 rounded-2xl text-[11px] font-black uppercase tracking-[0.15em] shadow-xl shadow-emerald-500/20 transition-all active:scale-95 border border-emerald-400/20">
                                            Inscribirse
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </main>

                {/* Floating Action Button */}
                <div className="fixed bottom-24 right-8 z-30 animate-in zoom-in-50 duration-500 delay-1000">
                    <button className="flex h-16 w-16 items-center justify-center rounded-[2rem] bg-primary text-white shadow-2xl shadow-primary/40 border border-primary-400/30 active:scale-90 transition-all hover:bg-primary-600 group">
                        <Plus size={32} className="group-hover:rotate-90 transition-transform duration-300" />
                    </button>
                </div>
            </div>
        </div>
    );
}

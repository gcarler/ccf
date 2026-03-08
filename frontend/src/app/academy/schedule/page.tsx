"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, CalendarDays, MoreHorizontal, Video, Users, MapPin, Search } from 'lucide-react';

export default function StudentSchedule() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-display selection:bg-primary/30 relative overflow-x-hidden">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-50 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen">
                {/* Header */}
                <div className="flex items-center p-6 justify-between sticky top-0 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 z-20">
                    <button onClick={() => router.back()} className="text-primary flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 hover:bg-primary/20 transition-colors">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center">Horario de Clases</h2>
                    <div className="flex w-10 items-center justify-end">
                        <button className="flex items-center justify-center rounded-full size-10 text-primary bg-white/5 hover:bg-white/10 transition-colors">
                            <CalendarDays size={20} />
                        </button>
                    </div>
                </div>

                {/* Horizontal Day Selector */}
                <div className="flex gap-4 p-6 overflow-x-auto hide-scrollbar z-10 relative">
                    <div className="flex flex-col items-center gap-3 cursor-pointer group shrink-0">
                        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-xl shadow-primary/30 border border-primary/50 group-hover:scale-105 transition-transform">
                            <p className="text-sm font-black uppercase tracking-widest">Lun</p>
                        </div>
                        <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(66,66,240,0.8)]"></div>
                    </div>
                    {['Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map((day) => (
                        <div key={day} className="flex flex-col items-center gap-3 cursor-pointer group opacity-40 hover:opacity-100 transition-opacity shrink-0">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-900 border border-white/10 text-slate-400 group-hover:border-primary/50 group-hover:text-white transition-all">
                                <p className="text-sm font-bold uppercase tracking-widest">{day}</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto hide-scrollbar px-6 pt-2 pb-24 z-10 relative">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-primary text-xs font-black uppercase tracking-widest">Lunes, 12 de Junio</h3>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest border border-white/10 px-2 py-1 rounded">Semana 4</span>
                    </div>

                    {/* Timeline Classes */}
                    <div className="relative">
                        {/* Vertical Line */}
                        <div className="absolute left-[11px] top-4 bottom-4 w-[2px] bg-white/5 z-0 rounded-full"></div>

                        {/* Class 1 (Live/Presential) */}
                        <div className="relative z-10 grid grid-cols-[24px_1fr] gap-x-6 mb-8 group">
                            <div className="flex justify-center pt-3">
                                <div className="w-3 h-3 rounded-full bg-primary ring-4 ring-primary/20 shadow-[0_0_10px_rgba(66,66,240,0.8)]"></div>
                            </div>
                            <div className="bg-slate-900/50 backdrop-blur-xl p-6 rounded-[2rem] shadow-xl border border-white/5 hover:border-primary/30 transition-all">
                                <div className="flex justify-between items-start mb-4">
                                    <span className="text-primary text-xs font-black uppercase tracking-widest px-3 py-1.5 bg-primary/10 border border-primary/20 rounded-xl">08:00 - 09:30</span>
                                    <button className="text-slate-500 hover:text-white transition-colors p-1"><MoreHorizontal size={20} /></button>
                                </div>
                                <h4 className="text-white text-xl font-bold mb-3 tracking-tight">Sistemática I</h4>
                                <div className="flex flex-col gap-2">
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <div className="p-1.5 rounded-lg bg-white/5"><Users size={14} className="text-primary-300" /></div>
                                        <span className="font-medium">Prof. Martínez</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <div className="p-1.5 rounded-lg bg-white/5"><MapPin size={14} className="text-rose-400" /></div>
                                        <span className="font-medium">Aula 102 • Edificio A</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Class 2 - Virtual */}
                        <div className="relative z-10 grid grid-cols-[24px_1fr] gap-x-6 mb-8 group">
                            <div className="flex justify-center pt-3">
                                <div className="w-3 h-3 rounded-full bg-slate-700 ring-4 ring-slate-800 transition-colors group-hover:bg-emerald-400 group-hover:ring-emerald-400/20"></div>
                            </div>
                            <div className="bg-slate-900/50 backdrop-blur-xl p-6 rounded-[2rem] shadow-xl border border-white/5 border-l-4 border-l-emerald-500 hover:border-r-emerald-500/30 transition-all relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl"></div>
                                <div className="flex justify-between items-start mb-4 relative z-10">
                                    <span className="text-slate-300 text-xs font-black uppercase tracking-widest px-3 py-1.5 bg-slate-800 rounded-xl border border-white/5">10:00 - 11:30</span>
                                    <div className="p-1.5 bg-emerald-500/10 rounded-xl text-emerald-400 border border-emerald-500/20"><Video size={18} /></div>
                                </div>
                                <h4 className="text-white text-xl font-bold mb-3 tracking-tight relative z-10">Teología Pastoral</h4>
                                <div className="flex flex-col gap-2 relative z-10">
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <div className="p-1.5 rounded-lg bg-white/5"><Users size={14} className="text-primary-300" /></div>
                                        <span className="font-medium">Prof. Rodríguez</span>
                                    </div>
                                    <button className="flex items-center gap-3 text-emerald-400 text-sm font-bold mt-2 bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors w-fit">
                                        <Video size={16} className="fill-current" />
                                        <span className="uppercase tracking-widest text-[10px]">Unirse a Sesión</span>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Class 3 */}
                        <div className="relative z-10 grid grid-cols-[24px_1fr] gap-x-6 mb-8 group">
                            <div className="flex justify-center pt-3">
                                <div className="w-3 h-3 rounded-full bg-slate-700 ring-4 ring-slate-800 transition-colors group-hover:bg-primary group-hover:ring-primary/20"></div>
                            </div>
                            <div className="bg-slate-900/50 backdrop-blur-xl p-6 rounded-[2rem] shadow-xl border border-white/5 hover:border-primary/30 transition-all">
                                <div className="flex justify-between items-start mb-4">
                                    <span className="text-slate-300 text-xs font-black uppercase tracking-widest px-3 py-1.5 bg-slate-800 rounded-xl border border-white/5">13:00 - 14:30</span>
                                    <button className="text-slate-500 hover:text-white transition-colors p-1"><MoreHorizontal size={20} /></button>
                                </div>
                                <h4 className="text-white text-xl font-bold mb-3 tracking-tight">Historia Eclesiástica</h4>
                                <div className="flex flex-col gap-2">
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <div className="p-1.5 rounded-lg bg-white/5"><Users size={14} className="text-primary-300" /></div>
                                        <span className="font-medium">Prof. Gómez</span>
                                    </div>
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <div className="p-1.5 rounded-lg bg-white/5"><MapPin size={14} className="text-rose-400" /></div>
                                        <span className="font-medium">Aula 205 • Biblioteca</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

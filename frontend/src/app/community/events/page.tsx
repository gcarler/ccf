"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Calendar, Bell, ChevronRight, MapPin, Clock, Video, Share2, Plus, CalendarDays, User, Users } from 'lucide-react';

import Link from 'next/link';

import { motion } from 'framer-motion';

export default function EventsCalendar() {
    const { isAuthenticated, user } = useAuth();
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
        <div className="p-8 lg:p-12 space-y-12 max-w-5xl mx-auto animate-in fade-in duration-700">
            {/* Header Section */}
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px]">
                        <div className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]"></div>
                        Comunidad El Faro
                    </div>
                    <h1 className="text-4xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Calendario de Eventos</h1>
                </div>
                
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-black tabular-nums">Enero 2026</h2>
                    <div className="flex gap-1">
                        <button className="p-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] transition-colors">
                            <ChevronRight size={16} className="rotate-180" />
                        </button>
                        <button className="p-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] transition-colors">
                            <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            </header>

            {/* Horizontal Date Picker - Refined */}
            <div className="flex gap-4 overflow-x-auto hide-scrollbar py-4 px-2 -mx-2">
                {dates.map((date, idx) => (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.05 }}
                        key={date.num}
                        className={`flex flex-col items-center justify-center min-w-[72px] h-28 rounded-[2rem] transition-all cursor-pointer border ${date.active
                            ? 'bg-[hsl(var(--primary))] text-white shadow-[0_12px_32px_hsl(var(--primary)/0.3)] border-transparent scale-110 z-10'
                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)]'
                            }`}
                    >
                        <span className={`text-[10px] font-black uppercase mb-1 ${date.active ? 'opacity-80' : 'opacity-60'}`}>
                            {date.day}
                        </span>
                        <span className="text-2xl font-black tabular-nums">
                            {date.num}
                        </span>
                        {date.active && (
                            <motion.div 
                                layoutId="active-dot"
                                className="mt-2 h-1.5 w-1.5 rounded-full bg-white shadow-[0_0_8px_white]" 
                            />
                        )}
                    </motion.div>
                ))}
            </div>

            {/* Main Content Area */}
            <div className="space-y-8">
                {/* Category Filter */}
                <div className="flex gap-8 border-b border-[hsl(var(--border))] px-2">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-4 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative ${activeTab === tab
                                ? 'text-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                        >
                            {tab}
                            {activeTab === tab && (
                                <motion.div 
                                    layoutId="active-tab"
                                    className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]" 
                                />
                            )}
                        </button>
                    ))}
                </div>

                {/* Events Grid - High Density */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-20">
                    {/* Event Card 1 */}
                    <motion.div 
                        whileHover={{ y: -4 }}
                        className="group bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] overflow-hidden shadow-sm hover:shadow-xl hover:border-[hsl(var(--primary)/0.3)] transition-all"
                    >
                        <div className="relative aspect-[16/8] overflow-hidden bg-[hsl(var(--surface-3))]">
                            <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary)/0.2)] via-transparent to-transparent opacity-60"></div>
                            <div className="absolute inset-0 flex items-center justify-center opacity-10 group-hover:scale-110 transition-transform duration-700">
                                <CalendarDays size={80} />
                            </div>
                            
                            <div className="absolute top-6 left-6 flex gap-2">
                                <span className="rounded-xl bg-[hsl(var(--primary))] text-white px-3 py-1 text-[9px] font-black uppercase tracking-widest shadow-lg">Servicio Especial</span>
                                <div className="flex items-center gap-1.5 bg-black/20 backdrop-blur-md px-3 py-1 rounded-xl text-white text-[10px] font-bold">
                                    <Clock size={12} strokeWidth={2.5} />
                                    19:30
                                </div>
                            </div>
                        </div>
                        
                        <div className="p-8">
                            <h3 className="text-xl font-black text-[hsl(var(--text-primary))] leading-tight mb-4 group-hover:text-[hsl(var(--primary))] transition-colors">Noche de Avivamiento y Gloria</h3>
                            
                            <div className="flex items-center justify-between mt-8 pt-6 border-t border-[hsl(var(--border))]">
                                <div className="flex -space-x-2">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className="size-8 rounded-full border-2 border-[hsl(var(--surface-2))] bg-[hsl(var(--surface-3))] flex items-center justify-center text-[10px] font-bold overflow-hidden">
                                            <User size={14} />
                                        </div>
                                    ))}
                                    <div className="size-8 rounded-full border-2 border-[hsl(var(--surface-2))] bg-[hsl(var(--primary))] text-[9px] font-black text-white flex items-center justify-center">+2.5k</div>
                                </div>
                                
                                <button className="h-10 px-6 bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg hover:opacity-90 transition-all active:scale-95">
                                    Reservar
                                </button>
                            </div>
                        </div>
                    </motion.div>

                    {/* Event Card 2 */}
                    <motion.div 
                        whileHover={{ y: -4 }}
                        className="group bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] overflow-hidden shadow-sm hover:shadow-xl hover:border-emerald-500/30 transition-all"
                    >
                        <div className="relative aspect-[16/8] overflow-hidden bg-[hsl(var(--surface-3))]">
                            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 via-transparent to-transparent opacity-60"></div>
                            <div className="absolute inset-0 flex items-center justify-center opacity-10 group-hover:scale-110 transition-transform duration-700">
                                <Users size={80} />
                            </div>
                            
                            <div className="absolute top-6 left-6 flex gap-2">
                                <span className="rounded-xl bg-emerald-500 text-white px-3 py-1 text-[9px] font-black uppercase tracking-widest shadow-lg">Juveniles</span>
                                <div className="flex items-center gap-1.5 bg-black/20 backdrop-blur-md px-3 py-1 rounded-xl text-white text-[10px] font-bold">
                                    <MapPin size={12} strokeWidth={2.5} />
                                    Auditorio
                                </div>
                            </div>
                        </div>
                        
                        <div className="p-8">
                            <h3 className="text-xl font-black text-[hsl(var(--text-primary))] leading-tight mb-4 group-hover:text-emerald-500 transition-colors">Generación de Fuego: 2026</h3>
                            
                            <div className="flex items-center justify-between mt-8 pt-6 border-t border-[hsl(var(--border))]">
                                <div className="px-3 py-1 bg-emerald-500/10 rounded-lg text-emerald-600 text-[10px] font-black uppercase tracking-widest">Entrada Libre</div>
                                
                                <button className="h-10 px-6 bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg hover:opacity-90 transition-all active:scale-95">
                                    Detalles
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>

            {/* Floating Quick Add */}
            <motion.button 
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                className="fixed bottom-12 right-12 size-16 bg-[hsl(var(--primary))] text-white rounded-[2rem] shadow-[0_16px_40px_hsl(var(--primary)/0.4)] flex items-center justify-center z-50 border border-white/20"
            >
                <Plus size={32} strokeWidth={2.5} />
            </motion.button>
        </div>
    );
}


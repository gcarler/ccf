"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    ChevronLeft,
    Search,
    MapPin,
    Users,
    Clock,
    Phone,
    ArrowRight,
    Map
} from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface GloryHouse {
    id: number;
    name: string;
    zone: string;
    leader_name: string;
    schedule: string;
    members_count: number;
}

export default function GroupsPage() {
    const [houses, setHouses] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const fetchHouses = async () => {
            try {
                const res = await fetch(apiUrl('/glory-houses/'));
                if (res.ok) {
                    const data = await res.json();
                    setHouses(data);
                }
            } catch (e) {
                console.error("Error fetching houses", e);
            } finally {
                setLoading(false);
            }
        };
        fetchHouses();
    }, []);

    const filtered = houses.filter(h =>
        h.zone.toLowerCase().includes(searchTerm.toLowerCase()) ||
        h.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 pb-24">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-background-dark/80 backdrop-blur-xl border-b border-slate-200 dark:border-white/5 px-6 py-6">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="size-10 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 hover:text-primary transition-all">
                            <ChevronLeft size={20} />
                        </Link>
                        <h1 className="text-2xl font-black tracking-tight">Casas de Gloria</h1>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-xl text-xs font-bold uppercase tracking-widest">
                        <Map size={16} /> Ver Mapa
                    </button>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-10 space-y-10">

                {/* Hero */}
                <div className="relative overflow-hidden rounded-[3rem] bg-gradient-to-br from-navy-dark to-primary p-12 text-white shadow-2xl border border-white/10">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                    <div className="relative z-10 max-w-2xl">
                        <h2 className="text-4xl font-black mb-4">Comunidad Cerca de Ti</h2>
                        <p className="text-lg text-slate-300 font-medium mb-8 leading-relaxed">Únete a un grupo pequeño en tu zona. Es el lugar perfecto para crecer espiritualmente y formar lazos duraderos.</p>

                        <div className="relative">
                            <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={24} />
                            <input
                                type="text"
                                placeholder="Ingresa tu barrio o zona..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full h-16 pl-14 pr-6 bg-white dark:bg-slate-900 rounded-[2rem] text-slate-900 dark:text-white font-bold text-lg focus:ring-4 focus:ring-primary/50 outline-none shadow-xl border-0"
                            />
                        </div>
                    </div>
                </div>

                {/* List */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filtered.map(house => (
                        <div key={house.id} className="glass dark:bg-slate-900/40 rounded-[2.5rem] p-8 shadow-sm hover:shadow-xl transition-all border border-slate-200 dark:border-white/5 group">
                            <div className="flex items-center justify-between mb-6">
                                <span className="px-4 py-2 bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest rounded-xl">
                                    {house.zone}
                                </span>
                                <div className="flex items-center gap-1.5 text-slate-500 font-bold text-xs bg-slate-100 dark:bg-white/5 px-3 py-1.5 rounded-lg">
                                    <Users size={14} /> {house.members_count}
                                </div>
                            </div>

                            <h3 className="text-2xl font-black mb-6 group-hover:text-primary transition-colors">{house.name}</h3>

                            <div className="space-y-4 mb-8">
                                <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300 font-medium">
                                    <div className="size-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400"><MapPin size={16} /></div>
                                    <span>{house.leader_name}</span>
                                </div>
                                <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300 font-medium">
                                    <div className="size-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400"><Clock size={16} /></div>
                                    <span>{house.schedule}</span>
                                </div>
                            </div>

                            <button className="w-full py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all">
                                Conectar <ArrowRight size={16} />
                            </button>
                        </div>
                    ))}
                </div>

            </main>

            {/* Mobile Nav (Floating Bottom) */}
            <nav className="lg:hidden fixed bottom-6 left-6 right-6 h-20 bg-white/70 dark:bg-slate-900/80 backdrop-blur-3xl px-6 rounded-[2.5rem] border border-white/40 dark:border-white/10 shadow-2xl flex justify-between items-center z-[100]">
                <Link href="/" className="flex flex-col items-center gap-1 text-slate-400">
                    <span className="material-symbols-outlined text-[30px]">home</span>
                    <span className="text-[8px] font-black uppercase tracking-widest">Inicio</span>
                </Link>
                <Link href="/groups" className="flex flex-col items-center gap-1 text-primary">
                    <span className="material-symbols-outlined text-[30px] fill-1" style={{ fontVariationSettings: "'FILL' 1" }}>groups</span>
                    <span className="text-[8px] font-black uppercase tracking-widest">Grupos</span>
                </Link>
                <Link href="/events" className="flex flex-col items-center gap-1 text-slate-400">
                    <span className="material-symbols-outlined text-[30px]">calendar_today</span>
                    <span className="text-[8px] font-black uppercase tracking-widest">Eventos</span>
                </Link>
            </nav>
        </div>
    );
}

"use client";

import React, { useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { Calendar, Clock, MapPin, Users, Search, ChevronRight, Star, Filter, Ticket } from 'lucide-react';
import clsx from 'clsx';

const EVENTS = [
    { id: 1, title: 'Retiro de Jóvenes 2026', date: '2026-05-02', endDate: '2026-05-04', time: '8:00 AM', location: 'Campamento El Buen Pastor', category: 'Retiro', attendees: 120, capacity: 150, featured: true, color: 'from-blue-600 to-indigo-700' },
    { id: 2, title: 'Concierto de Adoración Noches de Gloria', date: '2026-04-20', endDate: null, time: '6:00 PM', location: 'Sede Central - Mocoa', category: 'Adoración', attendees: 350, capacity: 500, featured: true, color: 'from-sky-600 to-blue-700' },
    { id: 3, title: 'Seminario: Finanzas con Fe', date: '2026-04-26', endDate: null, time: '9:00 AM', location: 'Salón Principal CCF', category: 'Seminario', attendees: 45, capacity: 80, featured: false, color: 'from-amber-500 to-orange-600' },
    { id: 4, title: 'Taller de Matrimonios Fuertes', date: '2026-05-10', endDate: '2026-05-11', time: '2:00 PM', location: 'Sede Centro - Pasto', category: 'Taller', attendees: 28, capacity: 40, featured: false, color: 'from-rose-500 to-pink-600' },
    { id: 5, title: 'Cumbre de Líderes CCF 2026', date: '2026-06-01', endDate: '2026-06-03', time: 'Todo el día', location: 'Hotel Mocoa Real', category: 'Cumbre', attendees: 80, capacity: 100, featured: true, color: 'from-emerald-500 to-teal-600' },
    { id: 6, title: 'Día de la Familia — Picnic Pastoral', date: '2026-04-19', endDate: null, time: '10:00 AM', location: 'Parque La Hormiga', category: 'Familia', attendees: 200, capacity: 300, featured: false, color: 'from-lime-500 to-green-600' },
];

const CATEGORIES = ['Todos', 'Retiro', 'Adoración', 'Seminario', 'Taller', 'Cumbre', 'Familia'];

function pct(a: number, c: number) { return Math.round((a / c) * 100); }

export default function EventsPage() {
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('Todos');

    const filtered = EVENTS.filter(e =>
        (cat === 'Todos' || e.category === cat) &&
        e.title.toLowerCase().includes(search.toLowerCase())
    );

    const featured = EVENTS.filter(e => e.featured);

    return (
        <main className="min-h-screen bg-slate-950">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-1.5 px-3 text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-emerald-600/10 to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[11px] font-bold uppercase tracking-wide mb-3">
                        <Calendar size={11} /> Próximos Eventos
                    </span>
                    <h1 className="text-xl font-bold text-white mb-3 tracking-tight">
                        Momentos que<br /><span className="text-emerald-400">Marcan tu Historia</span>
                    </h1>
                    <p className="text-slate-400 text-lg mb-3 max-w-xl mx-auto">
                        Retiros, cultos especiales, seminarios y momentos de comunidad diseñados para transformar tu vida.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar evento..."
                            className="w-full pl-12 pr-5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-slate-500 text-sm outline-none focus:ring-2 focus:ring-emerald-500/30 backdrop-blur" />
                    </div>
                </div>
            </section>

            {/* Featured Events Carousel */}
            <section className="max-w-6xl mx-auto px-3 mb-3">
                <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500 mb-3">
                    <Star size={10} className="inline mr-1.5 text-amber-400" />Eventos Destacados
                </p>
                <div className="grid grid-cols-3 gap-3">
                    {featured.map((ev, i) => (
                        <motion.div key={ev.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                            className={`h-52 rounded-lg bg-gradient-to-br ${ev.color} relative overflow-hidden cursor-pointer group hover:scale-[1.02] transition-all shadow-2xl`}>
                            <div className="absolute inset-0 bg-black/30" />
                            <div className="absolute inset-0 p-3 flex flex-col justify-between">
                                <div className="flex items-start justify-between">
                                    <span className="px-2 py-0.5 rounded-full bg-white/20 backdrop-blur text-white text-[9px] font-bold uppercase tracking-wide">{ev.category}</span>
                                    <div className="text-right">
                                        <p className="text-white/70 text-[9px] font-bold uppercase tracking-wide">{ev.date}</p>
                                        <p className="text-white text-[10px] font-bold">{ev.time}</p>
                                    </div>
                                </div>
                                <div>
                                    <p className="font-semibold text-lg leading-tight">{ev.title}</p>
                                    <div className="flex items-center gap-1 text-white/60 text-[10px] mt-1">
                                        <MapPin size={9} /> {ev.location}
                                    </div>
                                    {/* Progress bar */}
                                    <div className="mt-3 w-full bg-white/20 rounded-full h-1.5">
                                        <div className="bg-[hsl(var(--bg-primary))] rounded-full h-1.5 transition-all" style={{ width: `${pct(ev.attendees, ev.capacity)}%` }} />
                                    </div>
                                    <p className="text-white/50 text-[9px] mt-1">{ev.attendees}/{ev.capacity} inscritos</p>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Filter */}
            <div className="max-w-6xl mx-auto px-3 flex items-center gap-2 flex-wrap mb-3">
                <Filter size={12} className="text-slate-600" />
                {CATEGORIES.map(c => (
                    <button key={c} onClick={() => setCat(c)}
                        className={`px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all ${cat === c ? 'bg-emerald-600 text-white' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}>
                        {c}
                    </button>
                ))}
            </div>

            {/* Events List */}
            <div className="max-w-6xl mx-auto px-3 pb-4 space-y-3">
                {filtered.map((ev, i) => {
                    const occupation = pct(ev.attendees, ev.capacity);
                    return (
                        <motion.div key={ev.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
                            className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-white/10 rounded-lg p-3 flex items-center gap-3 cursor-pointer group transition-all">
                            <div className={`size-7 rounded-lg bg-gradient-to-br ${ev.color} flex items-center justify-center text-white shrink-0`}>
                                <Calendar size={22} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-0.5">
                                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-slate-400 font-bold uppercase tracking-wide">{ev.category}</span>
                                    {ev.featured && <Star size={10} className="text-amber-400 fill-amber-400" />}
                                </div>
                                <p className="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">{ev.title}</p>
                                <div className="flex flex-wrap items-center gap-3 mt-1 text-[10px] text-slate-500">
                                    <span className="flex items-center gap-1"><Calendar size={9} /> {ev.date}{ev.endDate ? ` → ${ev.endDate}` : ''}</span>
                                    <span className="flex items-center gap-1"><Clock size={9} /> {ev.time}</span>
                                    <span className="flex items-center gap-1"><MapPin size={9} /> {ev.location}</span>
                                </div>
                            </div>
                            <div className="shrink-0 text-right space-y-2">
                                <div className="flex items-center gap-2 justify-end">
                                    <Users size={11} className="text-slate-500" />
                                    <span className="text-[10px] text-slate-400">{ev.attendees} / {ev.capacity}</span>
                                </div>
                                <div className="w-24 bg-white/10 rounded-full h-1.5">
                                    <div className={clsx("rounded-full h-1.5", occupation > 80 ? "bg-rose-500" : occupation > 50 ? "bg-amber-500" : "bg-emerald-500")}
                                        style={{ width: `${occupation}%` }} />
                                </div>
                                <button className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-400 hover:text-white transition-colors">
                                    <Ticket size={11} /> Inscribirme <ChevronRight size={10} />
                                </button>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </main>
    );
}


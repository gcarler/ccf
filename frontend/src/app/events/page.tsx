"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Bell, Calendar, ChevronRight, Clock, MapPin, Video, Users, Plus } from 'lucide-react';
import { apiUrl } from '@/lib/api';

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch(apiUrl('/events/'));
        if (res.ok) setEvents(await res.json());
      } catch (e) {
        console.error("Error fetching events", e);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

  // Use current date for header if no events, or use first event's month
  const displayMonth = events.length > 0 ?
    new Date(events[0].fixed_date).toLocaleString('es-ES', { month: 'long', year: 'numeric' }) :
    'Marzo 2026';

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100">
      {/* Abstract Animated Background */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-50">
        <div className="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-primary/20 to-transparent rotate-45"></div>
        <div className="absolute top-0 left-2/4 w-px h-full bg-gradient-to-b from-transparent via-primary/10 to-transparent rotate-45"></div>
        <div className="absolute top-0 left-3/4 w-px h-full bg-gradient-to-b from-transparent via-primary/5 to-transparent rotate-45"></div>
      </div>

      <div className="relative z-10 max-w-[1400px] mx-auto px-6 py-10">

        {/* Page Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.4em] text-primary mb-2">Vida en comunidad</p>
            <h1 className="text-5xl font-black tracking-tight text-slate-900 dark:text-white">Calendario</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden md:block">
              <p className="text-xl font-bold uppercase">{displayMonth}</p>
              <button className="text-[10px] font-black uppercase tracking-widest text-primary hover:underline transition-all">Ver Calendario Completo</button>
            </div>
            <button className="relative size-14 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-500 shadow-xl">
              <Bell size={24} />
              <span className="absolute top-4 right-4 h-2.5 w-2.5 rounded-full bg-primary animate-pulse"></span>
            </button>
          </div>
        </header>

        {/* Desktop Date Selector */}
        <section className="mb-12 overflow-x-auto hide-scrollbar pb-4">
          <div className="flex gap-4">
            {[
              { day: 'Lun', num: '09' },
              { day: 'Mar', num: '10' },
              { day: 'Mié', num: '11', active: true },
              { day: 'Jue', num: '12' },
              { day: 'Vie', num: '13' },
              { day: 'Sáb', num: '14' },
              { day: 'Dom', num: '15' },
              { day: 'Lun', num: '16' },
              { day: 'Mar', num: '17' },
            ].map((d, i) => (
              <div key={i} className={`flex flex-col items-center justify-center min-w-[100px] h-32 rounded-[2rem] transition-all cursor-pointer ${d.active ? 'bg-primary text-white shadow-2xl shadow-primary/40 scale-110 border border-white/20' : 'bg-white dark:bg-slate-800/40 text-slate-400 border border-slate-200 dark:border-white/5 hover:bg-slate-50'}`}>
                <span className={`text-xs font-black uppercase tracking-widest mb-2 ${d.active ? 'text-white/80' : 'text-slate-500'}`}>{d.day}</span>
                <span className="text-3xl font-black">{d.num}</span>
                {d.active && <div className="mt-2 size-1.5 rounded-full bg-white shadow-[0_0_8px_white]"></div>}
              </div>
            ))}
          </div>
        </section>

        {/* Events Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {events.map((event, index) => (
            <div key={event.id || index} className="lg:col-span-1 group relative aspect-[4/5] overflow-hidden rounded-[3rem] shadow-2xl border border-white/10 cursor-pointer">
              <img
                className="absolute inset-0 h-full w-full object-cover opacity-80 transition-transform duration-1000 group-hover:scale-110"
                src={event.image_url || `https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=800`}
                alt={event.name}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent"></div>
              <div className="absolute bottom-10 left-10 right-10 space-y-6">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-primary/20 border border-white/20 px-4 py-1.5 text-[10px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                    {event.event_type}
                  </span>
                  <div className="flex items-center gap-2 text-white/90 bg-black/30 px-4 py-1.5 rounded-full backdrop-blur-sm">
                    <Clock size={14} />
                    <span className="text-xs font-bold">
                      {new Date(event.fixed_date).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
                <h3 className="text-3xl font-black text-white leading-tight">{event.name}</h3>
                <div className="flex items-center justify-between gap-4">
                  <div className="flex flex-col">
                    <span className="text-[8px] font-black text-white/40 uppercase tracking-widest">Ubicación</span>
                    <span className="text-xs font-bold text-white tracking-tighter">{event.description.substring(0, 30)}...</span>
                  </div>
                  <button className="flex-1 py-4 bg-primary text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] shadow-xl shadow-primary/40 hover:bg-primary/90 transition-all">Inscribirse</button>
                </div>
              </div>
            </div>
          ))}
          {events.length === 0 && !loading && (
            <div className="lg:col-span-3 py-20 text-center">
              <p className="text-slate-500 font-bold uppercase tracking-widest">No hay eventos programados próximamente.</p>
            </div>
          )}
        </div>

        {/* Floating Add Button for Admins (Conceptual) */}
        <button className="fixed bottom-10 right-10 size-20 rounded-[2rem] bg-primary text-white shadow-2xl shadow-primary/40 flex items-center justify-center transition-transform active:scale-90 z-50 group border-4 border-white dark:border-slate-900">
          <Plus size={36} className="group-hover:rotate-90 transition-transform duration-300" />
        </button>

      </div>

      {/* Bottom Nav for Mobile */}
      <nav className="lg:hidden fixed bottom-6 left-6 right-6 h-20 bg-white/70 dark:bg-slate-900/80 backdrop-blur-3xl px-6 rounded-[2.5rem] border border-white/40 dark:border-white/10 shadow-2xl flex justify-between items-center z-[100]">
        <Link href="/" className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-symbols-outlined text-[30px]">home</span>
          <span className="text-[8px] font-black uppercase tracking-widest">Inicio</span>
        </Link>
        <Link href="/events" className="flex flex-col items-center gap-1 text-primary">
          <span className="material-symbols-outlined text-[30px] fill-1" style={{ fontVariationSettings: "'FILL' 1" }}>calendar_today</span>
          <span className="text-[8px] font-black uppercase tracking-widest">Eventos</span>
        </Link>
        <Link href="/academy" className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-symbols-outlined text-[30px]">school</span>
          <span className="text-[8px] font-black uppercase tracking-widest">Academia</span>
        </Link>
      </nav>
    </div>
  );
}

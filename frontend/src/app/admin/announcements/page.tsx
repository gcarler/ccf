"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    Menu,
    Bell,
    Share2,
    Bookmark,
    ChevronRight,
    Plus,
    Calendar,
    Megaphone
} from 'lucide-react';

export default function AnnouncementsAdmin() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    const announcements = [
        {
            id: '1',
            category: 'Ministerio de Enseñanza',
            title: 'Inicio de Clases Teológicas',
            date: '12 MAY',
            excerpt: 'Las inscripciones para el nuevo semestre del Instituto Bíblico ya están abiertas. Cupos limitados.',
            featured: false
        },
        {
            id: '2',
            category: 'Administración',
            title: 'Nuevo Horario de Culto',
            date: '10 MAY',
            excerpt: 'A partir del próximo domingo, el servicio matutino iniciará a las 9:30 AM para mayor comodidad.',
            featured: false
        },
        {
            id: '3',
            category: 'Eventos Generales',
            title: 'Vigilia Mensual: "Fuego Santo"',
            date: '08 MAY',
            excerpt: 'Acompáñanos este viernes en una noche de oración ininterrumpida y búsqueda profunda de Dios.',
            featured: false
        },
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all">
                        <Menu size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Anuncios del Ministerio</h1>
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all relative">
                        <Bell size={20} />
                        <span className="absolute top-3 right-3 size-2 bg-primary rounded-full ring-2 ring-slate-950 shadow-[0_0_8px_#4242f0]"></span>
                    </button>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-40 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Featured Section */}
                <section>
                    <div className="relative group overflow-hidden rounded-[2.5rem] h-96 shadow-2xl border border-white/5">
                        <div
                            className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-110"
                            style={{ backgroundImage: `linear-gradient(to top, rgba(16, 16, 34, 0.95) 0%, rgba(16, 16, 34, 0.4) 50%, transparent 100%), url('https://images.unsplash.com/photo-1438232992991-995b7058bbb3?q=80&w=800&auto=format&fit=crop')` }}
                        ></div>
                        <div className="absolute bottom-0 left-0 right-0 p-10 flex flex-col items-start gap-4">
                            <span className="px-4 py-1.5 bg-primary text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-full shadow-lg shadow-primary/40 border border-primary-400/20">Destacado</span>
                            <h2 className="text-white text-3xl font-black leading-tight tracking-tight uppercase">Congreso Internacional de Avivamiento 2024</h2>
                            <p className="text-slate-300 text-sm font-medium line-clamp-2 max-w-lg">Prepárate para tres días de gloria y poder bajo la unción del Espíritu Santo. ¡No te lo pierdas!</p>
                            <button className="mt-4 flex items-center justify-center px-8 py-4 bg-primary text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-2xl shadow-2xl shadow-primary/30 hover:bg-primary-600 active:scale-95 transition-all border border-primary-400/20">
                                Leer Más
                            </button>
                        </div>
                    </div>
                </section>

                {/* Feed Section */}
                <section className="space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <h3 className="text-white text-xl font-black tracking-tight uppercase tracking-widest">Últimas Noticias</h3>
                        <button
                            onClick={() => router.push('/admin/announcements/new')}
                            className="flex items-center gap-2 text-[10px] font-black text-primary uppercase tracking-widest hover:underline"
                        >
                            <Plus size={14} /> Crear Nuevo
                        </button>
                    </div>

                    <div className="flex flex-col gap-6">
                        {announcements.map((ann) => (
                            <div key={ann.id} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex flex-col gap-6 shadow-2xl group hover:border-primary/30 transition-all">
                                <div className="flex justify-between items-start">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-primary text-[10px] font-black uppercase tracking-[0.2em]">{ann.category}</span>
                                        <h4 className="text-white text-lg font-black tracking-tight uppercase tracking-tight group-hover:text-primary transition-colors">{ann.title}</h4>
                                    </div>
                                    <span className="text-slate-600 text-[10px] font-black uppercase tracking-widest bg-white/5 px-3 py-1 rounded-lg border border-white/5">{ann.date}</span>
                                </div>
                                <p className="text-slate-400 text-sm font-medium leading-relaxed">{ann.excerpt}</p>
                                <div className="flex items-center justify-between pt-6 border-t border-white/5">
                                    <div className="flex gap-6">
                                        <button className="text-primary hover:text-white flex items-center gap-2 transition-all">
                                            <Share2 size={18} />
                                            <span className="text-[10px] font-black uppercase tracking-widest">Compartir</span>
                                        </button>
                                        <button className="text-slate-600 hover:text-primary transition-all">
                                            <Bookmark size={18} />
                                        </button>
                                    </div>
                                    <button className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-2 group/btn">
                                        Ver detalles
                                        <ChevronRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            {/* Floating FAB for Mobile compatibility (optional but fits the design) */}
            <button
                onClick={() => router.push('/admin/announcements/new')}
                className="fixed bottom-10 right-10 size-16 rounded-[2rem] bg-primary text-white shadow-2xl shadow-primary/40 flex items-center justify-center hover:scale-110 active:scale-95 transition-all z-50 border border-primary-400/20"
            >
                <Megaphone size={24} />
            </button>
        </div>
    );
}

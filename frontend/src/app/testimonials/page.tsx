"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
    MessageCircle,
    Heart,
    Share2,
    PlusCircle,
    Search,
    ChevronLeft,
    Clock,
    User,
    Loader2,
    Sparkles
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import TestimonialForm from '@/components/TestimonialForm';

interface Testimonial {
    id: number;
    content: string;
    emotion: string;
    created_at: string;
    author_id: number;
}

interface PageContent {
    page_key: string;
    title?: string;
    content?: string;
}

export default function TestimonialsWallPage() {
    const { user, token } = useAuth();
    const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
    const [pageContent, setPageContent] = useState<PageContent | null>(null);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [filter, setFilter] = useState('Todos');

    const fetchData = async () => {
        setLoading(true);
        try {
            const [testRes, contRes] = await Promise.all([
                fetch(apiUrl('/testimonials/')),
                fetch(apiUrl('/content/testimonials_hero'))
            ]);
            if (testRes.ok) setTestimonials(await testRes.json());
            if (contRes.ok) setPageContent(await contRes.json());
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const categories = ['Todos', 'Sanidad', 'Provisión', 'Restauración', 'Fe'];

    const filteredTestimonials = testimonials.filter(t =>
        filter === 'Todos' || t.emotion.toLowerCase() === filter.toLowerCase()
    );

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100">
            {/* Page Header */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-background-dark/80 backdrop-blur-xl border-b border-slate-200 dark:border-white/5 px-6 py-6">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="size-10 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 hover:text-primary transition-all">
                            <ChevronLeft size={20} />
                        </Link>
                        <h1 className="text-2xl font-black tracking-tight">
                            {pageContent?.title || "Muro de Testimonios"}
                        </h1>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="hidden md:flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-white/5 rounded-xl text-xs font-bold text-slate-500">
                            <Search size={16} /> Buscar
                        </button>
                        <button
                            onClick={() => setShowForm(!showForm)}
                            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-2xl text-xs font-black uppercase tracking-widest shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all active:scale-95"
                        >
                            <PlusCircle size={18} /> Publicar mi historia
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-10 space-y-12">

                {/* Hero Banner */}
                <section className="relative h-[400px] rounded-[3rem] overflow-hidden shadow-2xl border border-white/10 group">
                    <img
                        className="absolute inset-0 w-full h-full object-cover scale-105 group-hover:scale-110 transition-transform duration-1000 opacity-80"
                        src="https://images.unsplash.com/photo-1510531704581-5b2870972060?auto=format&fit=crop&q=80"
                        alt="Worship"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-background-dark via-background-dark/40 to-transparent"></div>
                    <div className="absolute bottom-12 left-12 right-12">
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/20 text-primary border border-primary/20 rounded-full text-[10px] font-black uppercase tracking-widest mb-6 backdrop-blur-md">
                            <Sparkles size={14} /> Historias de Fe
                        </div>
                        <h2 className="text-5xl font-black text-white tracking-tight mb-4 drop-shadow-xl">
                            {pageContent?.title || "Milagros que Transforman"}
                        </h2>
                        <p className="text-slate-200 text-lg font-medium max-w-xl opacity-90 leading-relaxed">
                            {pageContent?.content || "Explora lo que Dios está haciendo en nuestra congregación hoy y fortalécete en la fe."}
                        </p>
                    </div>
                </section>

                {/* Categories */}
                <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-2">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            onClick={() => setFilter(cat)}
                            className={`px-6 py-3 rounded-2xl text-xs font-black uppercase tracking-widest transition-all ${filter === cat ? 'bg-primary text-white shadow-xl shadow-primary/20 scale-105' : 'bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 text-slate-500 hover:border-primary/30'}`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>

                {/* Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">

                    {/* Testimonies List (Col 8) */}
                    <div className="lg:col-span-8 space-y-8">
                        {loading ? (
                            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-primary" size={40} /></div>
                        ) : filteredTestimonials.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {filteredTestimonials.map((t) => (
                                    <article key={t.id} className="glass dark:bg-slate-900/40 p-8 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-sm hover:shadow-xl transition-all flex flex-col justify-between group">
                                        <div>
                                            <div className="flex items-start justify-between mb-6">
                                                <div className="flex items-center gap-4">
                                                    <div className="size-12 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                                                        <User size={24} />
                                                    </div>
                                                    <div>
                                                        <p className="font-black text-slate-900 dark:text-white leading-none mb-1">Anónimo</p>
                                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                                                            <Clock size={10} /> {new Date(t.created_at).toLocaleDateString()}
                                                        </p>
                                                    </div>
                                                </div>
                                                <span className="px-3 py-1 bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest rounded-lg border border-primary/10">{t.emotion}</span>
                                            </div>
                                            <p className="text-base text-slate-600 dark:text-slate-300 leading-relaxed italic font-medium mb-8">
                                                &quot;{t.content}&quot;
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-6 pt-6 border-t border-slate-100 dark:border-white/5">
                                            <button className="flex items-center gap-2 text-slate-400 hover:text-rose-500 transition-colors">
                                                <Heart size={18} />
                                                <span className="text-xs font-black uppercase tracking-widest">312</span>
                                            </button>
                                            <button className="flex items-center gap-2 text-slate-400 hover:text-primary transition-colors">
                                                <Share2 size={18} />
                                                <span className="text-xs font-black uppercase tracking-widest">Compartir</span>
                                            </button>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-slate-50 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10 rounded-[3rem] py-24 text-center flex flex-col items-center">
                                <MessageCircle size={48} className="text-slate-300 mb-4" />
                                <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Aún no hay historias en esta categoría.</p>
                            </div>
                        )}
                    </div>

                    {/* Sidebar Form (Col 4) */}
                    <div className="lg:col-span-4">
                        <div className="sticky top-32 glass dark:bg-slate-900/40 p-10 rounded-[3rem] border border-white/10 shadow-2xl overflow-hidden">
                            <div className="absolute top-0 right-0 size-32 bg-primary/5 rounded-full blur-3xl"></div>
                            <div className="relative z-10">
                                <h3 className="text-2xl font-black mb-2">Comparte tu Milagro</h3>
                                <p className="text-sm text-slate-500 font-medium mb-8">Tu historia puede ser la semilla de fe que alguien más necesita hoy.</p>
                                <TestimonialForm
                                    userId={user?.id || 0}
                                    token={token || ""}
                                    onSubmitted={fetchData}
                                />
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}

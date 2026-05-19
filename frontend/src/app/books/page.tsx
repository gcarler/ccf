"use client";

import React, { useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { BookOpen, Search, Download, Star, ExternalLink, Filter } from 'lucide-react';
import clsx from 'clsx';

const BOOKS = [
    { id: 1, title: 'El Discípulo Comprometido', author: 'Juan Carlos Ortiz', category: 'Discipulado', rating: 4.9, free: true, cover: 'from-blue-600 to-indigo-700', desc: 'Un clásico que revolucionará tu comprensión del verdadero discipulado.' },
    { id: 2, title: 'Liderazgo con Propósito', author: 'Rick Warren', category: 'Liderazgo', rating: 4.8, free: false, cover: 'from-emerald-500 to-teal-600', desc: 'Descubre cómo liderar con propósito eterno en cada área de tu vida.' },
    { id: 3, title: 'La Oración que Mueve a Dios', author: 'E.M. Bounds', category: 'Oración', rating: 4.7, free: true, cover: 'from-sky-600 to-blue-700', desc: 'Las enseñanzas más profundas sobre el poder transformador de la oración.' },
    { id: 4, title: 'Gracia Divina para el Matrimonio', author: 'Tim Keller', category: 'Familia', rating: 4.8, free: false, cover: 'from-rose-500 to-pink-600', desc: 'Una perspectiva bíblica profunda sobre el matrimonio como reflejo del evangelio.' },
    { id: 5, title: 'Finanzas con Fe', author: 'Equipo CCF', category: 'Mayordomía', rating: 4.6, free: true, cover: 'from-amber-500 to-orange-600', desc: 'Manual práctico para manejar las finanzas con principios del Reino de Dios.' },
    { id: 6, title: 'Sanidad Interior', author: 'Leanne Payne', category: 'Consejería', rating: 4.7, free: false, cover: 'from-slate-500 to-gray-700', desc: 'Un camino bíblico hacia la restauración emocional y espiritual profunda.' },
];

const CATEGORIES = ['Todos', 'Discipulado', 'Liderazgo', 'Familia', 'Oración', 'Mayordomía', 'Consejería'];

export default function BooksPage() {
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('Todos');
    const [freeOnly, setFreeOnly] = useState(false);

    const filtered = BOOKS.filter(b =>
        (cat === 'Todos' || b.category === cat) &&
        (!freeOnly || b.free) &&
        b.title.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="min-h-screen bg-slate-950">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-20 px-6 text-center relative">
                <div className="absolute inset-0 bg-gradient-to-b from-sky-600/10 to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sky-500/20 text-sky-400 text-[11px] font-black uppercase tracking-widest mb-6">
                        <BookOpen size={11} /> Biblioteca Digital
                    </span>
                    <h1 className="text-5xl font-black text-white mb-4 tracking-tight">
                        Libros que<br /><span className="text-sky-400">Transforman Mentes</span>
                    </h1>
                    <p className="text-slate-400 text-lg mb-8 max-w-xl mx-auto">
                        Colección cuidadosamente seleccionada de los mejores recursos para tu crecimiento espiritual e intelectual.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar libro o autor..."
                            className="w-full pl-12 pr-5 py-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 text-[14px] outline-none focus:ring-2 focus:ring-sky-500/30 backdrop-blur" />
                    </div>
                </div>
            </section>

            {/* Filters */}
            <div className="max-w-6xl mx-auto px-6 flex items-center gap-3 flex-wrap mb-8">
                <Filter size={12} className="text-slate-600" />
                {CATEGORIES.map(c => (
                    <button key={c} onClick={() => setCat(c)}
                        className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${cat === c ? 'bg-sky-600 text-white' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}>
                        {c}
                    </button>
                ))}
                <div className="ml-auto">
                    <button onClick={() => setFreeOnly(!freeOnly)}
                        className={clsx("flex items-center gap-2 px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border",
                            freeOnly ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : "bg-white/5 text-slate-400 border-white/10 hover:text-white")}>
                        <Download size={11} /> Solo Gratuitos
                    </button>
                </div>
            </div>

            {/* Books Grid */}
            <div className="max-w-6xl mx-auto px-6 pb-20">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                    {filtered.map((book, i) => (
                        <motion.div key={book.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                            className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-white/10 rounded-3xl overflow-hidden group cursor-pointer transition-all hover:scale-[1.02]">
                            {/* Cover */}
                            <div className={`h-48 bg-gradient-to-br ${book.cover} relative flex items-center justify-center`}>
                                <BookOpen size={48} className="text-white/30" />
                                <div className="absolute top-3 left-3 flex gap-2">
                                    {book.free && (
                                        <span className="px-2 py-0.5 rounded-full bg-emerald-500 text-white text-[9px] font-black uppercase tracking-widest">
                                            Gratis
                                        </span>
                                    )}
                                    <span className="px-2 py-0.5 rounded-full bg-black/30 backdrop-blur text-white text-[9px] font-bold">
                                        {book.category}
                                    </span>
                                </div>
                                <div className="absolute bottom-3 right-3 flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/30 backdrop-blur">
                                    <Star size={10} className="text-amber-400 fill-amber-400" />
                                    <span className="text-[10px] text-white font-bold">{book.rating}</span>
                                </div>
                            </div>
                            {/* Info */}
                            <div className="p-5">
                                <p className="text-[14px] font-bold text-white leading-snug group-hover:text-sky-400 transition-colors">{book.title}</p>
                                <p className="text-[11px] text-slate-500 mt-1 font-medium">{book.author}</p>
                                <p className="text-[11px] text-slate-400 mt-2 leading-relaxed line-clamp-2">{book.desc}</p>
                                <button className={clsx("mt-4 w-full py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2",
                                    book.free
                                        ? "bg-emerald-500/20 hover:bg-emerald-500 text-emerald-400 hover:text-white"
                                        : "bg-sky-500/20 hover:bg-sky-600 text-sky-400 hover:text-white")}>
                                    {book.free ? <><Download size={13} /> Descargar</> : <><ExternalLink size={13} /> Ver más</>}
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </main>
    );
}


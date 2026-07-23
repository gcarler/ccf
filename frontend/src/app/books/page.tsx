"use client";

import React, { useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { BookOpen, Search, Download, Star, ExternalLink, Filter } from 'lucide-react';
import clsx from 'clsx';

const BOOKS = [
    { id: 1, title: 'El Discípulo Comprometido', author: 'Juan Carlos Ortiz', category: 'Discipulado', rating: 4.9, free: true, cover: 'from-[hsl(var(--info))] to-[hsl(var(--info))]', desc: 'Un clásico que revolucionará tu comprensión del verdadero discipulado.' },
    { id: 2, title: 'Liderazgo con Propósito', author: 'Rick Warren', category: 'Liderazgo', rating: 4.8, free: false, cover: 'from-[hsl(var(--success))] to-[hsl(var(--domain-teal))]', desc: 'Descubre cómo liderar con propósito eterno en cada área de tu vida.' },
    { id: 3, title: 'La Oración que Mueve a Dios', author: 'E.M. Bounds', category: 'Oración', rating: 4.7, free: true, cover: 'from-[hsl(var(--info))] to-[hsl(var(--info))]', desc: 'Las enseñanzas más profundas sobre el poder transformador de la oración.' },
    { id: 4, title: 'Gracia Divina para el Matrimonio', author: 'Tim Keller', category: 'Familia', rating: 4.8, free: false, cover: 'from-[hsl(var(--danger))] to-[hsl(var(--domain-pink))]', desc: 'Una perspectiva bíblica profunda sobre el matrimonio como reflejo del evangelio.' },
    { id: 5, title: 'Finanzas con Fe', author: 'Equipo CCF', category: 'Mayordomía', rating: 4.6, free: true, cover: 'from-[hsl(var(--warning))] to-orange-600', desc: 'Manual práctico para manejar las finanzas con principios del Reino de Dios.' },
    { id: 6, title: 'Sanidad Interior', author: 'Leanne Payne', category: 'Consejería', rating: 4.7, free: false, cover: 'from-[hsl(var(--surface-3))] to-[hsl(var(--bg-muted))]', desc: 'Un camino bíblico hacia la restauración emocional y espiritual profunda.' },
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
        <main className="min-h-screen bg-[hsl(var(--bg-muted))]">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-1.5 px-3 text-center relative">
                <div className="absolute inset-0 bg-gradient-to-b to-[hsl(var(--info)/10%)] to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[hsl(var(--info))]/20 text-[hsl(var(--info))] text-[11px] font-bold uppercase tracking-wide mb-3">
                        <BookOpen size={11} /> Biblioteca Digital
                    </span>
                    <h1 className="text-xl font-bold text-white mb-3 tracking-tight">
                        Libros que<br /><span className="text-[hsl(var(--info))]">Transforman Mentes</span>
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] text-lg mb-3 max-w-xl mx-auto">
                        Colección cuidadosamente seleccionada de los mejores recursos para tu crecimiento espiritual e intelectual.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar libro o autor..."
                            className="w-full pl-12 pr-5 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-[hsl(var(--text-secondary))] text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--info)/30%)] backdrop-blur" />
                    </div>
                </div>
            </section>

            {/* Filters */}
            <div className="max-w-6xl mx-auto px-3 flex items-center gap-3 flex-wrap mb-3">
                <Filter size={12} className="text-[hsl(var(--text-secondary))]" />
                {CATEGORIES.map(c => (
                    <button key={c} onClick={() => setCat(c)}
                        className={`px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all ${cat === c ? 'bg-[hsl(var(--info))] text-white' : 'bg-white/5 text-[hsl(var(--text-secondary))] hover:text-white hover:bg-white/10'}`}>
                        {c}
                    </button>
                ))}
                <div className="ml-auto">
                    <button onClick={() => setFreeOnly(!freeOnly)}
                        className={clsx("flex items-center gap-2 px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all border",
                            freeOnly ? "bg-[hsl(var(--success))]/20 text-[hsl(var(--success))] border-[hsl(var(--success)/100%)]/30" : "bg-white/5 text-[hsl(var(--text-secondary))] border-white/10 hover:text-white")}>
                        <Download size={11} /> Solo Gratuitos
                    </button>
                </div>
            </div>

            {/* Books Grid */}
            <div className="max-w-6xl mx-auto px-3 pb-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {filtered.map((book, i) => (
                        <motion.div key={book.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
                            className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-white/10 rounded-lg overflow-hidden group cursor-pointer transition-all hover:scale-[1.02]">
                            {/* Cover */}
                            <div className={`h-48 bg-gradient-to-br ${book.cover} relative flex items-center justify-center`}>
                                <BookOpen size={48} className="text-white/30" />
                                <div className="absolute top-3 left-3 flex gap-2">
                                    {book.free && (
                                        <span className="px-2 py-0.5 rounded-full bg-[hsl(var(--success))] text-white text-[9px] font-bold uppercase tracking-wide">
                                            Gratis
                                        </span>
                                    )}
                                    <span className="px-2 py-0.5 rounded-full bg-black/30 backdrop-blur text-white text-[9px] font-bold">
                                        {book.category}
                                    </span>
                                </div>
                                <div className="absolute bottom-3 right-3 flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/30 backdrop-blur">
                                    <Star size={10} className="text-[hsl(var(--warning))] fill-[hsl(var(--warning))]" />
                                    <span className="text-[10px] text-white font-bold">{book.rating}</span>
                                </div>
                            </div>
                            {/* Info */}
                            <div className="p-3">
                                <p className="text-sm font-bold text-white leading-snug group-hover:text-[hsl(var(--info))] transition-colors">{book.title}</p>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1 font-medium">{book.author}</p>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-2 leading-relaxed line-clamp-2">{book.desc}</p>
                                <button className={clsx("mt-4 w-full py-2.5 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all flex items-center justify-center gap-2",
                                    book.free
                                        ? "bg-[hsl(var(--success))]/20 hover:bg-[hsl(var(--success))] text-[hsl(var(--success))] hover:text-white"
                                        : "bg-[hsl(var(--info))]/20 hover:bg-[hsl(var(--info))] text-[hsl(var(--info))] hover:text-white")}>
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

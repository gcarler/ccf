"use client";

import React, { useState } from 'react';
import Navbar from '@/components/Navbar';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, Heart, Share2, Search, X, Play, User } from 'lucide-react';

const TESTIMONIALS = [
    { id: 1, name: 'María González', role: 'Miembro desde 2020', category: 'Salvación', text: 'Llegué a la iglesia completamente quebrantada, sin esperanza. A través del amor de esta comunidad y el mensaje de Cristo, mi vida fue restaurada desde los cimientos. Hoy camino en libertad y propósito.', likes: 142, video: false },
    { id: 2, name: 'Carlos Ramírez', role: 'Líder de Jóvenes', category: 'Restauración', text: 'Las adicciones habían destruido mi familia y todo lo que me importaba. Cristo me encontró en mi peor momento y hoy soy libre. Mi familia fue restaurada y ahora sirvo guiando a otros jóvenes en el mismo camino.', likes: 98, video: true },
    { id: 3, name: 'Familia Morales', role: 'Miembros activos', category: 'Matrimonio', text: 'Estábamos al borde del divorcio cuando asistimos por primera vez. La consejería pastoral y el amor de la comunidad nos dio las herramientas para sanar y hoy tenemos el matrimonio más hermoso de nuestra vida.', likes: 201, video: false },
    { id: 4, name: 'Andrea Suárez', role: 'Voluntaria CMS', category: 'Vocación', text: 'Este lugar me ayudó a descubrir mis dones y a entender que Dios me creó para servir en los medios de comunicación. Hoy uso mi creatividad para expandir el reino y nunca he sido más feliz.', likes: 75, video: true },
    { id: 5, name: 'Pedro Castillo', role: 'Diácono', category: 'Sanidad', text: 'Los médicos decían que no había esperanza. Aprendí a orar con fe y la iglesia intercedió conmigo. Hoy estoy completamente sano y mi testimonio ha llevado a muchos a creer en el poder sobrenatural de Dios.', likes: 167, video: false },
    { id: 6, name: 'Luisa Herrera', role: 'Academia CCF', category: 'Educación', text: 'La Academia CCF cambió mi perspectiva del ministerio. Los cursos de liderazgo y teología me equiparon para fundar un grupo de discipulado en mi barrio que hoy cuenta con más de 40 personas.', likes: 89, video: false },
];

const CATEGORIES = ['Todos', 'Salvación', 'Restauración', 'Matrimonio', 'Vocación', 'Sanidad', 'Educación'];

export default function TestimonialsPage() {
    const [search, setSearch] = useState('');
    const [cat, setCat] = useState('Todos');
    const [selected, setSelected] = useState<typeof TESTIMONIALS[0] | null>(null);

    const filtered = TESTIMONIALS.filter(t =>
        (cat === 'Todos' || t.category === cat) &&
        t.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="min-h-screen bg-slate-950">
            <Navbar />
            <div className="pt-28" />

            {/* Hero */}
            <section className="py-20 px-6 text-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-rose-600/10 to-transparent pointer-events-none" />
                <div className="max-w-4xl mx-auto relative">
                    <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/20 text-rose-400 text-[11px] font-black uppercase tracking-widest mb-6">
                        <Heart size={11} /> Historias Reales
                    </span>
                    <h1 className="text-5xl font-black text-white mb-4 tracking-tight">
                        Vidas que han sido<br /><span className="text-rose-400">Transformadas</span>
                    </h1>
                    <p className="text-slate-400 text-lg mb-8 max-w-xl mx-auto">
                        Miles de personas han experimentado el poder de Dios en su vida. Estas son algunas de sus historias.
                    </p>
                    <div className="max-w-lg mx-auto relative">
                        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input value={search} onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar testimonio..."
                            className="w-full pl-12 pr-5 py-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder:text-slate-500 text-[14px] outline-none focus:ring-2 focus:ring-rose-500/30 backdrop-blur" />
                    </div>
                </div>
            </section>

            {/* Category Filter */}
            <div className="max-w-6xl mx-auto px-6 flex items-center gap-2 flex-wrap mb-8">
                {CATEGORIES.map(c => (
                    <button key={c} onClick={() => setCat(c)}
                        className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${cat === c ? 'bg-rose-600 text-white' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}>
                        {c}
                    </button>
                ))}
            </div>

            {/* Grid */}
            <div className="max-w-6xl mx-auto px-6 pb-20">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filtered.map((t, i) => (
                        <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                            className="bg-white/5 hover:bg-white/8 border border-white/5 hover:border-rose-500/20 rounded-3xl p-6 cursor-pointer group transition-all hover:shadow-xl hover:shadow-rose-500/5"
                            onClick={() => setSelected(t)}>
                            {/* Quote */}
                            <div className="text-4xl text-rose-500/30 font-black leading-none mb-3">"</div>
                            <p className="text-[13px] text-slate-300 leading-relaxed line-clamp-4 mb-5 group-hover:text-white transition-colors">
                                {t.text}
                            </p>

                            {/* Footer */}
                            <div className="flex items-center gap-3">
                                <div className="size-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-pink-500/20 flex items-center justify-center text-rose-400 text-sm font-black shrink-0">
                                    <User size={16} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-[12px] font-bold text-white truncate">{t.name}</p>
                                    <p className="text-[10px] text-slate-500">{t.role}</p>
                                </div>
                                <div className="flex flex-col items-end gap-1">
                                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-black uppercase tracking-widest">{t.category}</span>
                                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                                        <Heart size={9} /> {t.likes}
                                        {t.video && <><Play size={9} className="ml-1 text-blue-400" /> Video</>}
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Detail Modal */}
            <AnimatePresence>
                {selected && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6"
                        onClick={() => setSelected(null)}>
                        <motion.div initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            className="w-full max-w-xl bg-slate-900 border border-white/10 rounded-3xl p-8 shadow-2xl">
                            <div className="flex items-start justify-between mb-6">
                                <div className="text-5xl text-rose-500/30 font-black leading-none">"</div>
                                <div className="flex gap-2">
                                    <button className="p-2 rounded-xl bg-white/5 text-slate-400 hover:text-white transition-all">
                                        <Share2 size={16} />
                                    </button>
                                    <button onClick={() => setSelected(null)} className="p-2 rounded-xl bg-white/5 text-slate-400 hover:text-rose-400 transition-all">
                                        <X size={16} />
                                    </button>
                                </div>
                            </div>
                            <p className="text-slate-200 text-[15px] leading-relaxed mb-8">{selected.text}</p>
                            <div className="flex items-center gap-4">
                                <div className="size-14 rounded-2xl bg-gradient-to-br from-rose-500/20 to-pink-500/20 flex items-center justify-center text-rose-400">
                                    <User size={24} />
                                </div>
                                <div>
                                    <p className="font-bold text-white text-base">{selected.name}</p>
                                    <p className="text-slate-500 text-sm">{selected.role}</p>
                                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 font-black uppercase tracking-widest mt-1 inline-block">{selected.category}</span>
                                </div>
                                <div className="ml-auto flex items-center gap-2 text-rose-400">
                                    <Heart size={16} />
                                    <span className="font-bold">{selected.likes}</span>
                                </div>
                            </div>
                            {selected.video && (
                                <button className="mt-6 w-full flex items-center justify-center gap-2 py-3 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all">
                                    <Play size={14} /> Ver Video Testimonio
                                </button>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </main>
    );
}


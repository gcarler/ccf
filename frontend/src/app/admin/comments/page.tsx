"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Bell,
    Check,
    MessageSquare,
    Trash2,
    CornerUpRight,
    Search,
    Filter
} from 'lucide-react';

interface Comment {
    id: string;
    author: string;
    avatar: string;
    time: string;
    context: string;
    text: string;
    type: 'Prédica' | 'Testimonio' | 'Curso';
}

export default function CommentModeration() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeFilter, setActiveFilter] = useState('Todos');

    const comments: Comment[] = [
        {
            id: '1',
            author: 'Samuel Rivera',
            avatar: 'https://i.pravatar.cc/150??u=samuel',
            time: 'Hace 5 min',
            context: 'La Fe que Mueve Montañas',
            text: 'Este mensaje cambió mi perspectiva hoy. Gracias Pastor por estas palabras tan poderosas.',
            type: 'Prédica'
        },
        {
            id: '2',
            author: 'Elena Martínez',
            avatar: 'https://i.pravatar.cc/150?u=elena',
            time: 'Hace 12 min',
            context: 'Testimonio: Sanidad Familiar',
            text: 'Gloria a Dios por este testimonio. Me gustaría saber si hay un grupo de apoyo para estos casos.',
            type: 'Testimonio'
        },
        {
            id: '3',
            author: 'David Castro',
            avatar: 'https://i.pravatar.cc/150?u=david',
            time: 'Hace 1 hora',
            context: 'Curso: Liderazgo Cristiano',
            text: '¿Cuándo se habilita la lección 4? ¡Estoy ansioso por continuar!',
            type: 'Curso'
        },
    ];

    if (!isAuthenticated) return null;

    const filteredComments = activeFilter === 'Todos'
        ? comments
        : comments.filter(c => c.type === activeFilter.slice(0, -1)); // Simple plural to singular hack

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Gestión de Comentarios</h1>
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all relative">
                        <Bell size={20} />
                        <span className="absolute top-3 right-3 size-2 bg-primary rounded-full ring-2 ring-slate-950 shadow-[0_0_8px_#4242f0]"></span>
                    </button>
                </div>

                {/* Filters */}
                <div className="flex px-8 gap-4 overflow-x-auto hide-scrollbar py-6">
                    {['Todos', 'Prédicas', 'Testimonios', 'Cursos'].map((filter) => (
                        <button
                            key={filter}
                            onClick={() => setActiveFilter(filter)}
                            className={`px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border whitespace-nowrap ${activeFilter === filter
                                ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20'
                                : 'bg-white/5 text-slate-500 border-white/5 hover:border-white/10'
                                }`}
                        >
                            {filter}
                        </button>
                    ))}
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-40 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                <div className="flex items-center justify-between px-1">
                    <h3 className="text-white text-xl font-black tracking-tight uppercase tracking-widest">Comentarios Pendientes</h3>
                    <span className="text-[9px] font-black text-primary bg-primary/10 px-4 py-1 rounded-full uppercase tracking-widest border border-primary/20">
                        {filteredComments.length} Pendientes
                    </span>
                </div>

                <div className="space-y-6">
                    {filteredComments.map((comment) => (
                        <div key={comment.id} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 space-y-8 shadow-2xl group hover:border-white/10 transition-all">
                            <div className="flex items-start gap-6">
                                <div className="relative shrink-0">
                                    <div className="size-14 rounded-full border-2 border-primary/30 group-hover:border-primary transition-all shadow-xl shadow-black/40 bg-slate-800 flex items-center justify-center text-white font-black uppercase overflow-hidden">
                                        {comment.author?.charAt(0)}
                                    </div>

                                    <div className="absolute -bottom-1 -right-1 size-6 rounded-full bg-slate-950 flex items-center justify-center border border-white/5 p-1">
                                        <MessageSquare size={12} className="text-primary" />
                                    </div>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center">
                                        <h4 className="text-base font-black text-white tracking-tight group-hover:text-primary transition-colors">{comment.author}</h4>
                                        <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest">{comment.time}</span>
                                    </div>
                                    <p className="text-[10px] font-black text-primary uppercase tracking-widest mt-1">
                                        En: <span className="italic text-slate-400">&quot;{comment.context}&quot;</span>

                                    </p>
                                    <p className="text-sm font-medium text-slate-300 mt-4 leading-relaxed line-clamp-3">
                                        {comment.text}
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-4 pt-8 border-t border-white/5">
                                <button className="flex-[2] py-4 bg-primary hover:bg-primary-600 text-white text-[10px] font-black rounded-2xl transition-all shadow-lg shadow-primary/20 uppercase tracking-[0.2em] border border-primary-400/20 active:scale-95">
                                    Aprobar
                                </button>
                                <button className="flex-[1.5] py-4 bg-white/5 hover:bg-white/10 text-slate-300 border border-white/5 text-[10px] font-black rounded-2xl transition-all uppercase tracking-[0.2em] active:scale-95">
                                    Responder
                                </button>
                                <button className="size-14 flex items-center justify-center rounded-2xl bg-rose-500/10 text-rose-500 border border-rose-500/20 hover:bg-rose-500 hover:text-white transition-all active:scale-95 shadow-lg">
                                    <Trash2 size={20} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
}

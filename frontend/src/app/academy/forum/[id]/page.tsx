"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { MoreVertical, ThumbsUp, MessageSquare, Share2, Send, Hand } from 'lucide-react';
import AcademyDetailShell from '@/components/academy/AcademyDetailShell';

export default function TheologicalDebateDetail({ params }: { params: { id: string } }) {
    const { user, isAuthenticated } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    return (
        <AcademyDetailShell
            title="Detalle de debate"
            description="Profundiza en tu formación compartiendo argumentos y fuentes por nivel académico."
            variant="sky"
            rightAction={
                <button className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-primary/20 transition-colors text-primary">
                    <MoreVertical size={20} />
                </button>
            }
            onBack={() => router.back()}
            contentClassName="space-y-6 pb-32"
        >
                    {/* Main Thread Card (Original Post) */}
                    <div className="bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-[2rem] p-6 shadow-2xl">
                        <div className="flex items-center gap-4 mb-5">
                            <div className="relative">
                                <div className="size-14 rounded-full bg-slate-800 border-2 border-primary/30 flex items-center justify-center shadow-inner text-lg font-black bg-gradient-to-br from-indigo-500 to-primary">
                                    JP
                                </div>
                                <div className="absolute bottom-0 right-0 size-3.5 bg-emerald-500 rounded-full border-2 border-slate-900"></div>
                            </div>
                            <div>
                                <p className="text-white font-bold text-base">Pastor Juan Pérez</p>
                                <p className="text-slate-400 text-xs font-medium">Hace 2 horas • Teología Sistemática</p>
                            </div>
                        </div>

                        <h2 className="text-white text-2xl font-black leading-snug mb-4 tracking-tight">
                            ¿Cómo interpretar la Gracia en el contexto Pentecostal moderno?
                        </h2>

                        <p className="text-slate-300 text-base leading-relaxed mb-8">
                            Hermanos, abro este hilo para discutir las implicaciones teológicas de la Gracia santificante en nuestras congregaciones hoy. ¿Hasta qué punto nuestra experiencia del Espíritu redefine la comprensión tradicional?
                        </p>

                        <div className="flex items-center justify-between border-t border-white/10 pt-5">
                            <div className="flex gap-6">
                                <button className="flex items-center gap-2 text-primary font-bold text-sm hover:text-primary-300 transition-colors">
                                    <Hand size={18} className="fill-current" />
                                    42 Amén
                                </button>
                                <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors font-bold text-sm">
                                    <MessageSquare size={18} />
                                    12
                                </button>
                            </div>
                            <button className="text-slate-400 hover:text-white transition-colors">
                                <Share2 size={20} />
                            </button>
                        </div>
                    </div>

                    {/* Replies Section */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between px-2 mb-2">
                            <h3 className="text-slate-400 text-xs font-black uppercase tracking-widest">Respuestas de la comunidad</h3>
                            <button className="text-primary text-[10px] font-black uppercase tracking-widest hover:underline cursor-pointer">Ver anteriores</button>
                        </div>

                        {/* Reply 1 */}
                        <div className="bg-slate-900/40 rounded-3xl p-5 shadow-sm border border-white/5">
                            <div className="flex items-start gap-4">
                                <div className="relative shrink-0">
                                    <div className="size-10 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold bg-gradient-to-br from-amber-500/20 to-amber-600/20 text-amber-500">
                                        EM
                                    </div>
                                    <div className="absolute bottom-0 right-0 size-2.5 bg-emerald-500 rounded-full border-2 border-slate-900"></div>
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-start mb-2">
                                        <p className="text-white font-bold text-sm">Estudiante Elena M.</p>
                                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Hace 45 min</span>
                                    </div>
                                    <p className="text-slate-300 text-sm leading-relaxed mb-3">
                                        Excelente punto, Pastor. Considero que la experiencia del Espíritu Santo es inseparable de este concepto. No es solo un estado legal, sino una fuerza transformadora viva.
                                    </p>
                                    <div className="flex gap-5">
                                        <button className="text-xs font-bold text-slate-400 hover:text-primary flex items-center gap-1.5 transition-colors">
                                            <ThumbsUp size={14} className="fill-current" /> Amén (15)
                                        </button>
                                        <button className="text-[10px] uppercase tracking-widest font-black text-slate-500 hover:text-white transition-colors">Responder</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Reply 2 (Professor) */}
                        <div className="bg-primary/5 rounded-3xl p-5 shadow-sm border border-primary/20 border-l-4 border-l-primary relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl pointer-events-none"></div>
                            <div className="flex items-start gap-4 relative z-10">
                                <div className="size-10 rounded-full bg-slate-800 border border-primary/30 flex items-center justify-center text-xs font-bold bg-gradient-to-br from-primary to-blue-600 shadow-inner shrink-0 text-white">
                                    RS
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-start mb-2">
                                        <div className="flex items-center gap-2">
                                            <p className="text-white font-bold text-sm">Prof. Roberto Silva</p>
                                            <span className="bg-primary text-white text-[8px] px-2 py-0.5 rounded-md font-black uppercase tracking-widest">DOCENTE</span>
                                        </div>
                                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Hace 12 min</span>
                                    </div>
                                    <p className="text-slate-200 text-sm leading-relaxed mb-3">
                                        Elena tiene razón. Wesley hablaba de la &quot;gracia preveniente&quot;, que encaja perfectamente con nuestra visión neumática. Debemos profundizar en la obra del Espíritu como agente de esa gracia.
                                    </p>

                                    <div className="flex gap-5">
                                        <button className="text-xs font-bold text-slate-400 hover:text-primary flex items-center gap-1.5 transition-colors">
                                            <ThumbsUp size={14} className="fill-current" /> Amén (8)
                                        </button>
                                        <button className="text-[10px] uppercase tracking-widest font-black text-slate-500 hover:text-white transition-colors">Responder</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Reply 3 */}
                        <div className="bg-slate-900/40 rounded-3xl p-5 shadow-sm border border-white/5">
                            <div className="flex items-start gap-4">
                                <div className="size-10 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold shrink-0 text-slate-400">
                                    MT
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-start mb-2">
                                        <p className="text-white font-bold text-sm">Mateo Torres</p>
                                        <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Hace 5 min</span>
                                    </div>
                                    <p className="text-slate-300 text-sm leading-relaxed mb-3">
                                        ¿Podrían recomendar algún libro que trate este vínculo específico entre Gracia y Pentecostalismo?
                                    </p>
                                    <div className="flex gap-5">
                                        <button className="text-xs font-bold text-slate-400 hover:text-primary flex items-center gap-1.5 transition-colors">
                                            <ThumbsUp size={14} className="" /> Amén
                                        </button>
                                        <button className="text-[10px] uppercase tracking-widest font-black text-slate-500 hover:text-white transition-colors">Responder</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                {/* Sticky Bottom Input */}
                <div className="sticky bottom-0 w-full bg-slate-950/90 backdrop-blur-xl border-t border-white/10 p-4 pb-8 rounded-[2rem]">
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold shrink-0 text-white shadow-inner bg-gradient-to-br from-primary/50 to-emerald-500/50">
                            {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
                        </div>
                        <div className="flex-1 relative group">
                            <input
                                className="w-full bg-slate-900 border border-white/10 rounded-full py-3.5 px-5 text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary/50 text-white placeholder-slate-500 transition-all shadow-inner"
                                placeholder="Escribe tu respuesta..."
                                type="text"
                            />
                        </div>
                        <button className="size-12 bg-primary text-white rounded-full flex items-center justify-center shadow-lg shadow-primary/30 active:scale-95 transition-transform hover:bg-primary-600 shrink-0">
                            <Send size={18} className="translate-x-[2px] translate-y-[-1px]" />
                        </button>
                    </div>
                </div>

        </AcademyDetailShell>
    );
}

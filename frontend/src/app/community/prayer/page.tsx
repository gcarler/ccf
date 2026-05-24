"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { HandHeart, CalendarDays, Loader2, PlusCircle, UserCircle, Heart, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface PrayerRequest {
    id: number;
    name: string;
    request: string;
    category: string;
    is_answered: boolean;
    is_anonymous: boolean;
    created_at: string;
}

export default function PrayerWall() {
    const { isAuthenticated, token } = useAuth();
    const [activeTab, setActiveTab] = useState('Recientes');
    const [requests, setRequests] = useState<PrayerRequest[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated) return;

        const fetchRequests = async () => {
            try {
                const data = await apiFetch<PrayerRequest[]>('/prayer/', { token });
                setRequests(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error("Error fetching prayer requests:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchRequests();
    }, [isAuthenticated, token]);

    if (!isAuthenticated) return null;

    const tabs = ['Recientes', 'Urgentes', 'Mis Pedidos'];

    return (
        <div className="p-4 lg:p-4 space-y-3 max-w-6xl mx-auto font-display overflow-hidden">
            <style jsx global>{`
                .ethereal-aura {
                    position: relative;
                }
                .ethereal-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, hsla(var(--primary), 0.15), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.6s ease;
                }
                .ethereal-aura:hover::after {
                    opacity: 1;
                }
                .shimmer-prayer {
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.05),
                        transparent
                    );
                    background-size: 200% 100%;
                    animation: prayer-shimmer 4s infinite linear;
                }
                @keyframes prayer-shimmer {
                    0% { background-position: -200% 0; }
                    100% { background-position: 200% 0; }
                }
                .stacked-glass-prayer {
                    background: rgba(255, 255, 255, 0.6);
                    backdrop-filter: blur(16px) saturate(150%);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .dark .stacked-glass-prayer {
                    background: rgba(30, 31, 33, 0.7);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            `}</style>

            {/* Header Section Cinematic */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-3 relative">
                <div className="absolute -top-20 -left-20 size-10 bg-primary/5 blur-[100px] rounded-full pointer-events-none" />
                
                <motion.div 
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="relative z-10 space-y-2"
                >
                    <div className="flex items-center gap-3 text-primary font-semibold uppercase tracking-wide text-[10px] mb-2 bg-primary/5 w-fit px-4 py-1.5 rounded-full border border-primary/10">
                        <Sparkles size={14} className="animate-pulse" />
                        Interacción Celestial
                    </div>
                    <h1 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none">Muro de <span className="italic text-primary">Oración</span></h1>
                    <p className="text-slate-500 dark:text-slate-400 text-sm font-medium max-w-lg">Comparte tus cargas y apóyanos en intercesión. Tu fe activa el movimiento de Dios.</p>
                </motion.div>
                
                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                >
                    <Link href="/community/prayer/request" className="h-8 px-3 bg-primary text-white rounded-md text-xs font-semibold uppercase tracking-wide shadow-2xl shadow-primary/40 hover:shadow-primary/50 transition-all flex items-center gap-4 group">
                        <PlusCircle size={24} strokeWidth={2.5} className="group-hover:rotate-90 transition-transform duration-500" />
                        Levantar Petición
                    </Link>
                </motion.div>
            </header>

            {/* Content Area */}
            <div className="space-y-4 relative z-10">
                {/* Tabs Cinematic */}
                <div className="flex gap-3 border-b border-slate-100 dark:border-white/5 px-4 overflow-x-auto no-scrollbar">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={clsx(
                                "pb-6 text-[11px] font-semibold uppercase tracking-wide transition-all relative shrink-0",
                                activeTab === tab ? "text-primary" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            )}
                        >
                            {tab}
                            {activeTab === tab && (
                                <motion.div 
                                    layoutId="prayer-tab-cinematic"
                                    className="absolute bottom-[-1px] left-0 right-0 h-1 bg-primary rounded-t-full shadow-[0_0_20px_hsla(var(--primary),0.6)]" 
                                />
                            )}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-12 gap-4">
                        <div className="relative">
                            <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full animate-pulse" />
                            <Loader2 className="animate-spin text-primary relative z-10" size={64} strokeWidth={1.5} />
                        </div>
                        <p className="text-slate-400 font-semibold uppercase tracking-wide text-[10px] animate-pulse">Abriendo conexión espiritual...</p>
                    </div>
                ) : requests.length === 0 ? (
                    <motion.div 
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex flex-col items-center justify-center py-1.5 text-center space-y-3 bg-slate-50/50 dark:bg-white/5 rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10"
                    >
                        <div className="size-10 rounded-lg bg-white dark:bg-white/5 flex items-center justify-center text-slate-300 dark:text-slate-600 border border-slate-100 dark:border-white/5 shadow-xl">
                            <HandHeart size={48} strokeWidth={1} />
                        </div>
                        <div className="space-y-2">
                            <h3 className="text-base font-bold text-slate-800 dark:text-white uppercase tracking-tight">El muro está en silencio</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium max-w-xs mx-auto leading-relaxed">Este es un espacio sagrado. Sé el primero en compartir tu necesidad.</p>
                        </div>
                    </motion.div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <AnimatePresence mode="popLayout">
                            {requests.map((request, idx) => (
                                <motion.div 
                                    layout
                                    initial={{ opacity: 0, y: 30, scale: 0.9 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    transition={{ 
                                        delay: idx * 0.08,
                                        duration: 0.6,
                                        ease: [0.23, 1, 0.32, 1]
                                    }}
                                    key={request.id} 
                                    className="ethereal-aura group p-3 stacked-glass-prayer rounded-lg shadow-sm hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 flex flex-col gap-4 relative overflow-hidden"
                                >
                                    <div className="absolute top-0 left-0 w-full h-1 shimmer-prayer opacity-0 group-hover:opacity-100 transition-opacity" />
                                    
                                    <div className="flex justify-between items-start relative z-10">
                                        <div className="flex items-center gap-3">
                                            <div className="size-7 rounded-lg bg-gradient-to-tr from-slate-100 to-white dark:from-white/10 dark:to-white/5 flex items-center justify-center text-primary border border-white dark:border-white/10 shadow-lg transform group-hover:rotate-6 transition-transform duration-500">
                                                <UserCircle size={28} strokeWidth={1.5} />
                                            </div>
                                            <div>
                                                <p className="text-slate-900 dark:text-white text-base font-bold tracking-tight leading-none">{request.is_anonymous ? 'Anónimo' : request.name}</p>
                                                <p className="text-slate-400 font-semibold uppercase tracking-wide text-[9px] mt-2 flex items-center gap-2">
                                                    <CalendarDays size={10} />
                                                    {new Date(request.created_at).toLocaleDateString('es-ES', { month: 'long', day: 'numeric' })}
                                                </p>
                                            </div>
                                        </div>
                                        <span className="font-semibold px-4 py-1.5 rounded-lg tracking-wide shadow-sm">
                                            {request.category}
                                        </span>
                                    </div>
                                    
                                    <div className="flex-1 relative z-10 px-2">
                                        <p className="text-slate-600 dark:text-slate-300 text-base leading-relaxed font-medium line-clamp-5 italic">
                                            &ldquo;{request.request}&rdquo;
                                        </p>
                                    </div>
                                    
                                    <div className="flex items-center justify-between pt-8 border-t border-slate-100 dark:border-white/5 relative z-10">
                                        <div className="flex items-center gap-3 text-primary/60 group-hover:text-primary transition-colors duration-500">
                                            <div className="size-2.5 rounded-full bg-current animate-pulse shadow-[0_0_12px_currentColor]"></div>
                                            <span className="text-[10px] font-semibold uppercase tracking-wide">En intercesión</span>
                                        </div>
                                        <button className="h-8 px-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-all hover:scale-105 active:scale-95 shadow-xl flex items-center gap-3 group/btn hover:shadow-primary/20">
                                            <Heart size={16} className="group-hover/btn:fill-rose-500 group-hover/btn:text-rose-500 transition-all duration-500" />
                                            Me uno
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>

            {/* Footer Cinematic Insight */}
            <motion.footer 
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                className="pt-20 text-center relative"
            >
                <div className="size-1 rounded-full bg-primary/20 mx-auto mb-3 shadow-[0_0_40px_20px_rgba(var(--primary),0.1)]" />
                <p className="text-slate-400 text-[10px] font-semibold uppercase tracking-wide">La oración es la llave que abre los cielos</p>
            </motion.footer>
        </div>
    );
}


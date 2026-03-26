"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Church, Search, HandHeart, CalendarDays, User, HeartHandshake, Loader2, PlusCircle, UserCircle, Heart } from 'lucide-react';
import Link from 'next/link';
import { apiFetch } from '@/lib/http';

interface PrayerRequest {
    id: number;
    name: string;
    request: string;
    category: string;
    is_answered: boolean;
    is_anonymous: boolean;
    created_at: string;
}

import { motion, AnimatePresence } from 'framer-motion';

export default function PrayerWall() {
    const { isAuthenticated, token, user } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Recientes');
    const [requests, setRequests] = useState<PrayerRequest[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated) return;

        const fetchRequests = async () => {
            try {
                const data = await apiFetch<PrayerRequest[]>('/prayer/', { token });
                setRequests(data);
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
        <div className="p-8 lg:p-12 space-y-12 max-w-5xl mx-auto animate-in fade-in duration-700">
            {/* Header Section */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                <div>
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px] mb-1">
                        <HandHeart size={14} strokeWidth={2.5} />
                        Interacción Espiritual
                    </div>
                    <h1 className="text-4xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Muro de Oración</h1>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium mt-1">Comparte tus cargas y apóyanos en intercesión.</p>
                </div>
                
                <Link href="/community/prayer/request" className="h-14 px-8 bg-[hsl(var(--primary))] text-white rounded-2xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-primary/30 hover:bg-[hsl(var(--primary)/0.9)] transition-all active:scale-95 flex items-center gap-3">
                    <PlusCircle size={20} strokeWidth={2.5} />
                    Pedir Oración
                </Link>
            </header>

            {/* Content Area */}
            <div className="space-y-8">
                {/* Tabs / Filter */}
                <div className="flex gap-8 border-b border-[hsl(var(--border))] px-2">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-4 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative ${activeTab === tab
                                ? 'text-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                        >
                            {tab}
                            {activeTab === tab && (
                                <motion.div 
                                    layoutId="prayer-tab"
                                    className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]" 
                                />
                            )}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="flex flex-col items-center justify-center py-24 gap-6">
                        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={48} strokeWidth={1.5} />
                        <p className="text-[hsl(var(--text-secondary))] font-black uppercase tracking-[0.2em] text-[10px]">Sincronizando peticiones...</p>
                    </div>
                ) : requests.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-32 text-center space-y-6 bg-[hsl(var(--surface-2))] rounded-[3rem] border border-dashed border-[hsl(var(--border))]">
                        <div className="size-24 rounded-[2.5rem] bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                            <HandHeart size={40} strokeWidth={1.5} />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-[hsl(var(--text-primary))] font-black uppercase tracking-[0.1em]">No hay peticiones aún</h3>
                            <p className="text-[hsl(var(--text-secondary))] text-sm font-medium max-w-xs mx-auto">Sé el primero en compartir tu carga o agradecer al Señor.</p>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <AnimatePresence mode="popLayout">
                            {requests.map((request, idx) => (
                                <motion.div 
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    key={request.id} 
                                    className="group surface-card p-8 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] shadow-sm hover:shadow-xl hover:border-[hsl(var(--primary)/0.3)] transition-all flex flex-col gap-6"
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex items-center gap-4">
                                            <div className="size-12 rounded-2xl bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--primary))] border border-[hsl(var(--border))] shadow-inner">
                                                <UserCircle size={24} strokeWidth={1.5} />
                                            </div>
                                            <div>
                                                <p className="text-[hsl(var(--text-primary))] text-sm font-black tracking-tight">{request.is_anonymous ? 'Anónimo' : request.name}</p>
                                                <p className="text-[hsl(var(--text-secondary))] text-[10px] font-black uppercase tracking-widest mt-0.5 opacity-60">
                                                    {new Date(request.created_at).toLocaleDateString()}
                                                </p>
                                            </div>
                                        </div>
                                        <span className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)] text-[9px] uppercase font-black px-3 py-1 rounded-xl tracking-widest">
                                            {request.category}
                                        </span>
                                    </div>
                                    
                                    <div className="flex-1">
                                        <p className="text-[hsl(var(--text-secondary))] text-sm leading-relaxed font-medium line-clamp-4 italic">
                                            &ldquo;{request.request}&rdquo;
                                        </p>
                                    </div>
                                    
                                    <div className="flex items-center justify-between pt-6 border-t border-[hsl(var(--border))]">
                                        <div className="flex items-center gap-2 text-[hsl(var(--primary))]">
                                            <div className="size-2 rounded-full bg-current animate-pulse shadow-[0_0_8px_currentColor]"></div>
                                            <span className="text-[10px] font-black uppercase tracking-widest">En intercesión</span>
                                        </div>
                                        <button className="h-10 px-6 bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--primary))] hover:text-white border border-[hsl(var(--border))] hover:border-transparent rounded-xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 flex items-center gap-2 group/btn">
                                            <Heart size={14} className="group-hover/btn:fill-white" />
                                            Me uno
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>
        </div>
    );
}

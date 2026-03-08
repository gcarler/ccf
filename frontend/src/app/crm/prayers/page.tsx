"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Search,
    Bell,
    Lock,
    Heart,
    CheckCircle2,
    Filter,
    User,
    Stethoscope,
    Users,
    Briefcase,
    MessageSquare
} from 'lucide-react';

interface PrayerRequest {
    id: string;
    userName: string;
    userAvatar: string;
    time: string;
    category: 'Salud' | 'Familia' | 'Trabajo' | 'Otros';
    message: string;
    isRead: boolean;
}

export default function PastoralPrayers() {
    const { isAuthenticated, user } = useAuth();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');

    const [requests, setRequests] = useState<PrayerRequest[]>([
        {
            id: '1',
            userName: 'Juan Pérez',
            userAvatar: 'https://i.pravatar.cc/150?u=1',
            time: 'Hace 2h',
            category: 'Salud',
            message: 'Pastor, pido oración por mi cirugía de la próxima semana. Es un tema delicado y privado que solo mi familia conoce.',
            isRead: false
        },
        {
            id: '2',
            userName: 'María García',
            userAvatar: 'https://i.pravatar.cc/150?u=2',
            time: 'Hace 5h',
            category: 'Familia',
            message: 'Solicito oración por la restauración de mi matrimonio. Estamos pasando por una crisis fuerte. Gracias por su discreción.',
            isRead: false
        },
        {
            id: '3',
            userName: 'Roberto Sosa',
            userAvatar: 'https://i.pravatar.cc/150?u=3',
            time: 'Ayer',
            category: 'Trabajo',
            message: 'Pastor, estoy enfrentando una situación difícil de ética en mi nuevo empleo. Pido sabiduría para actuar correctamente.',
            isRead: true
        }
    ]);

    if (!isAuthenticated) return null;

    const filteredRequests = requests.filter(req =>
        req.userName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        req.message.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const getCategoryIcon = (category: string) => {
        switch (category) {
            case 'Salud': return <Stethoscope size={14} />;
            case 'Familia': return <Users size={14} />;
            case 'Trabajo': return <Briefcase size={14} />;
            default: return <Heart size={14} />;
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col min-h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-6 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Muro Pastoral</h2>
                    <button className="flex size-10 items-center justify-center rounded-full bg-white/5 text-slate-400 hover:text-white transition-all">
                        <Search size={20} />
                    </button>
                </header>

                <main className="flex-1 pb-32 overflow-y-auto hide-scrollbar animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Summary Card */}
                    <section className="px-6 pt-8 pb-4">
                        <div className="relative overflow-hidden bg-gradient-to-br from-primary via-primary-600 to-indigo-800 rounded-[2.5rem] p-8 text-white shadow-2xl shadow-primary/30 group">
                            <div className="absolute top-0 right-0 -mr-16 -mt-16 bg-white/10 size-64 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000"></div>
                            <div className="relative z-10 flex flex-col gap-6">
                                <div className="flex items-center gap-2">
                                    <Bell size={16} className="text-blue-200 animate-pulse" />
                                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-100">Peticiones Nuevas</span>
                                </div>
                                <div className="flex items-baseline gap-4">
                                    <h3 className="text-5xl font-black tracking-tight">{requests.filter(r => !r.isRead).length}</h3>
                                    <span className="text-xs font-bold text-blue-200">+5% hoy</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Section Title */}
                    <section className="px-8 pt-6 pb-2 flex items-center justify-between">
                        <h3 className="text-white text-xl font-black tracking-tight uppercase tracking-[0.1em]">Peticiones Privadas</h3>
                        <button className="text-slate-500 hover:text-primary transition-colors">
                            <Filter size={20} />
                        </button>
                    </section>

                    {/* Requests List */}
                    <section className="px-6 py-4 space-y-6">
                        {filteredRequests.map((req) => (
                            <div
                                key={req.id}
                                className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-6 shadow-xl hover:bg-slate-900/60 hover:border-white/10 transition-all group"
                            >
                                <div className="flex justify-between items-start mb-6">
                                    <div className="flex gap-4">
                                        <div className="size-14 rounded-2xl overflow-hidden border-2 border-white/10 group-hover:border-primary/50 transition-all">
                                            <div className="size-full bg-slate-800 flex items-center justify-center text-white font-black uppercase">
                                                {req.userName?.charAt(0)}
                                            </div>

                                        </div>
                                        <div>
                                            <h4 className="font-black text-white text-lg tracking-tight group-hover:text-primary transition-colors">{req.userName}</h4>
                                            <div className="flex items-center gap-2 text-primary">
                                                <Lock size={12} className="fill-primary" />
                                                <span className="text-[10px] font-black uppercase tracking-widest leading-none">Confidencial</span>
                                            </div>
                                        </div>
                                    </div>
                                    <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">{req.time}</span>
                                </div>

                                <div className="space-y-4 mb-6">
                                    <div className="flex items-center gap-2 text-primary-400/80 px-4 py-1.5 bg-primary/5 rounded-full border border-primary/10 w-fit">
                                        {getCategoryIcon(req.category)}
                                        <span className="text-[10px] font-black uppercase tracking-widest">Motivo: {req.category}</span>
                                    </div>
                                    <div className="bg-slate-950/40 border border-white/5 p-5 rounded-[2rem] relative">
                                        <p className="text-xs text-slate-400 leading-relaxed font-medium italic">&quot;{req.message}&quot;</p>
                                    </div>

                                </div>

                                <div className="flex gap-4">
                                    <button
                                        onClick={() => setRequests(requests.map(r => r.id === req.id ? { ...r, isRead: true } : r))}
                                        className={`flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border ${req.isRead
                                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                            : 'bg-primary text-white border-primary shadow-xl shadow-primary/20 hover:bg-primary-600 active:scale-95'
                                            }`}
                                    >
                                        <CheckCircle2 size={16} />
                                        <span>{req.isRead ? 'Leído' : 'Marcar Leído'}</span>
                                    </button>
                                    <button className="flex-1 flex items-center justify-center gap-2 py-4 bg-white/5 hover:bg-white/10 text-slate-300 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all border border-white/5 active:scale-95">
                                        <Heart size={16} />
                                        <span>Alentar</span>
                                    </button>
                                </div>
                            </div>
                        ))}

                        {filteredRequests.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                                <div className="size-20 rounded-full bg-white/5 flex items-center justify-center text-slate-600 border border-white/5">
                                    <Heart size={40} />
                                </div>
                                <h4 className="text-white font-black">No hay peticiones</h4>
                                <p className="text-slate-500 text-sm max-w-[200px]">Las peticiones confidenciales aparecerán aquí para tu intercesión.</p>
                            </div>
                        )}
                    </section>
                </main>

                {/* Bottom Nav Mockup for Pastoral Context */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-2xl px-8 pb-10 pt-4 border-t border-white/5 flex justify-around items-center">
                    <button onClick={() => router.push('/crm/dashboard')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <User size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Inicio</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-primary">
                        <Lock size={24} className="fill-primary" />
                        <span className="text-[9px] font-black uppercase tracking-widest">Peticiones</span>
                        <div className="size-1 rounded-full bg-primary mt-0.5"></div>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-slate-500">
                        <MessageSquare size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Mensajes</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-slate-500">
                        <User size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Perfil</span>
                    </button>
                </nav>
            </div>
        </div>
    );
}

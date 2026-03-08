"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Search,
    Bell,
    UserPlus,
    ChevronRight,
    Plus,
    Home,
    Users,
    Settings,
    CheckCircle2,
    Clock,
    UserCheck
} from 'lucide-react';

interface Prospect {
    id: string;
    name: string;
    interest: string;
    avatar: string;
    priority: 'Alta' | 'Media' | 'Baja';
}

export default function TaskAssignment() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');

    const prospects: Prospect[] = [
        {
            id: '1',
            name: 'Marta Gómez',
            interest: 'Interesada en curso de bautismo',
            avatar: 'https://i.pravatar.cc/150?u=10',
            priority: 'Alta'
        },
        {
            id: '2',
            name: 'Ricardo Ruiz',
            interest: 'Consulta sobre grupos familiares',
            avatar: 'https://i.pravatar.cc/150?u=11',
            priority: 'Media'
        }
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Mesh Gradient Background */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
                <div className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_bottom_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-6 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                        <ArrowLeft size={18} />
                    </button>
                    <h1 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Asignación de Tareas</h1>
                    <button className="flex size-10 items-center justify-center rounded-full bg-white/5 text-slate-400 hover:text-white transition-all relative">
                        <Bell size={20} />
                        <span className="absolute top-3 right-3 size-2 bg-primary rounded-full ring-2 ring-slate-950"></span>
                    </button>
                </header>

                <main className="flex-1 overflow-y-auto hide-scrollbar pt-6 px-6 pb-32 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    {/* Search */}
                    <section className="mb-8">
                        <div className="relative group">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors" size={18} />
                            <input
                                type="text"
                                placeholder="Buscar contactos pendientes..."
                                className="w-full bg-slate-900/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all outline-none backdrop-blur-xl"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </section>

                    <section className="space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <h2 className="text-white text-xl font-black tracking-tight uppercase tracking-[0.1em]">Nuevos Prospectos</h2>
                            <span className="bg-primary/10 text-primary text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest border border-primary/20">
                                {prospects.length} Pendientes
                            </span>
                        </div>

                        <div className="space-y-4">
                            {prospects.map((prospect) => (
                                <div
                                    key={prospect.id}
                                    className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-6 shadow-xl space-y-6 group hover:bg-slate-900/60 hover:border-white/10 transition-all"
                                >
                                    <div className="flex items-center gap-5">
                                        <div className="size-16 rounded-[1.5rem] overflow-hidden border-2 border-white/10 group-hover:border-primary/50 transition-all">
                                            <div className="size-full bg-slate-800 flex items-center justify-center text-white font-black uppercase">
                                                {prospect.name?.charAt(0)}
                                            </div>

                                        </div>
                                        <div className="flex-1">
                                            <h3 className="text-lg font-black text-white tracking-tight">{prospect.name}</h3>
                                            <p className="text-xs text-slate-500 font-medium">{prospect.interest}</p>
                                        </div>
                                    </div>

                                    <div className="space-y-6 pt-4 border-t border-white/5">
                                        <div>
                                            <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] mb-3 ml-1">Prioridad</p>
                                            <div className="flex gap-2">
                                                {['Alta', 'Media', 'Baja'].map((p) => (
                                                    <button
                                                        key={p}
                                                        className={`flex-1 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all ${prospect.priority === p
                                                            ? (p === 'Alta' ? 'bg-rose-500/10 text-rose-500 border-rose-500/20' :
                                                                p === 'Media' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                                                                    'bg-slate-500/10 text-slate-400 border-slate-500/20')
                                                            : 'bg-white/5 text-slate-600 border-white/5'
                                                            }`}
                                                    >
                                                        {p}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="space-y-3">
                                            <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em] ml-1">Líder Responsable</p>
                                            <div className="relative">
                                                <select className="w-full bg-slate-950/50 border border-white/10 rounded-2xl py-4 px-5 text-xs font-bold text-slate-300 appearance-none focus:ring-2 focus:ring-primary/40 transition-all">
                                                    <option>Seleccionar líder...</option>
                                                    <option>Pastor Juan - 5 tareas activas</option>
                                                    <option>Líder Elena - 2 tareas activas</option>
                                                    <option>Diác. Marcos - 8 tareas activas</option>
                                                </select>
                                                <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-600">
                                                    <ChevronRight size={16} className="rotate-90" />
                                                </div>
                                            </div>
                                        </div>

                                        <button className="w-full bg-primary hover:bg-primary-600 text-white font-black uppercase tracking-[0.2em] text-[10px] py-4 rounded-2xl shadow-2xl shadow-primary/20 transition-all flex items-center justify-center gap-2 border border-primary/40 active:scale-95">
                                            <UserCheck size={16} />
                                            <span>Confirmar Asignación</span>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </main>

                {/* Navigation */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-2xl border-t border-white/5 px-8 pb-10 pt-4 flex justify-between items-center">
                    <button onClick={() => router.push('/crm/dashboard')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Home size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Inicio</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-primary">
                        <UserCheck size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Tareas</span>
                        <div className="size-1 rounded-full bg-primary mt-1 shadow-[0_0_8px_#4242f0]"></div>
                    </button>
                    <div className="relative -top-8 px-2">
                        <button className="bg-primary size-16 rounded-[2rem] text-white shadow-2xl shadow-primary/40 flex items-center justify-center border-4 border-slate-950 hover:scale-110 active:scale-90 transition-all">
                            <Plus size={32} />
                        </button>
                    </div>
                    <button onClick={() => router.push('/crm/contacts')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Users size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Contactos</span>
                    </button>
                    <button onClick={() => router.push('/crm/settings')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Settings size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Ajustes</span>
                    </button>
                </nav>
            </div>
        </div>
    );
}

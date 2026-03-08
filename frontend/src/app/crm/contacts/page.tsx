"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Search, UserPlus, Phone, MessageSquare, Filter, LayoutGrid, List, Users, Settings } from 'lucide-react';

interface Lead {
    id: string;
    name: string;
    source: string;
    time: string;
    status: 'hot' | 'warm' | 'cold';
    avatar: string;
}

export default function LeadManagement() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const [activeFilter, setActiveFilter] = useState('all');

    const leads: Lead[] = [
        {
            id: '1',
            name: 'Juan Pérez',
            source: 'Invitado en Evento',
            time: 'Hace 2h',
            status: 'hot',
            avatar: 'https://i.pravatar.cc/150?u=1'
        },
        {
            id: '2',
            name: 'Elena Rodríguez',
            source: 'Formulario Web',
            time: 'Ayer',
            status: 'warm',
            avatar: 'https://i.pravatar.cc/150?u=2'
        },
        {
            id: '3',
            name: 'Ricardo Morales',
            source: 'Redes Sociales',
            time: '3 días',
            status: 'cold',
            avatar: 'https://i.pravatar.cc/150?u=3'
        },
        {
            id: '4',
            name: 'Sonia Méndez',
            source: 'Invitado Directo',
            time: '1 semana',
            status: 'hot',
            avatar: 'https://i.pravatar.cc/150?u=4'
        }
    ];

    if (!isAuthenticated) return null;

    const filteredLeads = leads.filter(lead => {
        const matchesSearch = lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            lead.source.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesFilter = activeFilter === 'all' ||
            (activeFilter === 'hot' && lead.status === 'hot') ||
            (activeFilter === 'warm' && lead.status === 'warm') ||
            (activeFilter === 'cold' && lead.status === 'cold');
        return matchesSearch && matchesFilter;
    });

    const getStatusStyles = (status: string) => {
        switch (status) {
            case 'hot': return 'bg-rose-500/10 text-rose-500 border-rose-500/20';
            case 'warm': return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
            case 'cold': return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
            default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'hot': return 'Caliente';
            case 'warm': return 'Tibio';
            case 'cold': return 'Frío';
            default: return status;
        }
    };

    const getStatusDot = (status: string) => {
        switch (status) {
            case 'hot': return 'bg-rose-500';
            case 'warm': return 'bg-amber-500';
            case 'cold': return 'bg-slate-500';
            default: return 'bg-slate-500';
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 pt-8 pb-4 border-b border-white/5 space-y-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="size-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary border border-primary/30 shadow-lg shadow-primary/20">
                                <UserPlus size={24} />
                            </div>
                            <div>
                                <h1 className="text-2xl font-black tracking-tight text-white">Nuevos Contactos</h1>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mt-0.5">Gestión de Prospectos</p>
                            </div>
                        </div>
                        <button className="size-12 rounded-2xl bg-primary text-white flex items-center justify-center shadow-2xl shadow-primary/40 active:scale-95 transition-all">
                            <UserPlus size={24} />
                        </button>
                    </div>

                    {/* Search Bar */}
                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors" size={18} />
                        <input
                            type="text"
                            placeholder="Buscar por nombre o fuente..."
                            className="w-full bg-slate-900/60 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all outline-none"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    {/* Filters */}
                    <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-2">
                        {['all', 'hot', 'warm', 'cold'].map((filter) => (
                            <button
                                key={filter}
                                onClick={() => setActiveFilter(filter)}
                                className={`px-6 py-2.5 rounded-full text-xs font-black uppercase tracking-widest transition-all border ${activeFilter === filter
                                    ? 'bg-primary text-white border-primary shadow-lg shadow-primary/20 scale-105'
                                    : 'bg-white/5 text-slate-500 border-white/5 hover:border-white/10'
                                    }`}
                            >
                                {filter === 'all' ? 'Todos' : getStatusLabel(filter)}
                            </button>
                        ))}
                    </div>
                </header>

                {/* Lead List */}
                <main className="flex-1 overflow-y-auto hide-scrollbar pt-6 px-6 pb-32 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    <div className="space-y-4">
                        {filteredLeads.map((lead) => (
                            <div
                                key={lead.id}
                                onClick={() => router.push(`/crm/contacts/${lead.id}`)}
                                className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-5 hover:bg-slate-900/60 hover:border-white/10 transition-all group cursor-pointer"
                            >
                                <div className="flex justify-between items-start mb-6">
                                    <div className="flex gap-4">
                                        <div className="relative">
                                            <div className="size-14 rounded-2xl overflow-hidden border-2 border-white/10 group-hover:border-primary/50 transition-colors bg-slate-800 flex items-center justify-center text-white font-black uppercase">
                                                {lead.name?.charAt(0)}
                                            </div>

                                            <div className={`absolute -bottom-1 -right-1 size-4 rounded-full border-2 border-slate-900 ${getStatusDot(lead.status)}`}></div>
                                        </div>
                                        <div>
                                            <h3 className="font-black text-white text-lg tracking-tight group-hover:text-primary transition-colors">{lead.name}</h3>
                                            <p className="text-xs text-slate-500 font-medium">{lead.source} • <span className="text-slate-600 italic">{lead.time}</span></p>
                                        </div>
                                    </div>
                                    <span className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest border ${getStatusStyles(lead.status)}`}>
                                        {getStatusLabel(lead.status)}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between pt-5 border-t border-white/5">
                                    <button className="text-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:text-primary-400 transition-colors">
                                        <div className="size-6 rounded-lg bg-primary/10 flex items-center justify-center">
                                            <UserPlus size={12} />
                                        </div>
                                        Asignar a Líder
                                    </button>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); }}
                                            className="size-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center hover:bg-emerald-500 hover:text-white transition-all border border-emerald-500/20"
                                        >
                                            <Phone size={18} />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); }}
                                            className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center hover:bg-primary hover:text-white transition-all border border-primary/20"
                                        >
                                            <MessageSquare size={18} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}

                        {filteredLeads.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                                <div className="size-20 rounded-full bg-white/5 flex items-center justify-center text-slate-600 border border-white/5">
                                    <Search size={40} />
                                </div>
                                <h4 className="text-white font-black">No se encontraron contactos</h4>
                                <p className="text-slate-500 text-sm max-w-[200px]">Prueba ajustando los filtros o la búsqueda.</p>
                            </div>
                        )}
                    </div>
                </main>

                {/* Bottom Nav Mockup for CRM Context */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-2xl px-8 pb-10 pt-4 border-t border-white/5 flex justify-around items-center">
                    <button onClick={() => router.push('/crm/dashboard')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <LayoutGrid size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Dashboard</span>
                    </button>
                    <button className="flex flex-col items-center gap-1.5 text-primary">
                        <List size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Contactos</span>
                        <div className="size-1 rounded-full bg-primary mt-0.5"></div>
                    </button>
                    <button onClick={() => router.push('/crm/members')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Users size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Miembros</span>
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

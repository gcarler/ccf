'use client';

import React, { useState, useEffect } from 'react';
import { Home, MapPin, Users, Heart, Search, Filter, Compass, Loader2 } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface GloryHouse {
    id: number;
    name: string;
    zone: string;
    leader_name: string;
    members_count: number;
    schedule: string;
    status: string;
}

export default function GroupsPage() {
    const [groups, setGroups] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(apiUrl('/groups/'))
            .then(res => res.json())
            .then(data => {
                setGroups(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="space-y-8 animate-in fade-in duration-500 pb-20">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
                        <Home className="text-blue-600" /> Casas de Gloria (Grupos)
                    </h1>
                    <p className="text-slate-500 mt-1">Conecta a la congregación en comunidades íntimas de crecimiento y adoración.</p>
                </div>
                <button className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black uppercase tracking-widest shadow-xl shadow-blue-200 transition-all flex items-center gap-2">
                    <Home size={16} /> Nueva Casa
                </button>
            </div>

            {/* Metrics & Search Bar */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="md:col-span-3 flex items-center gap-4">
                    <div className="relative flex-1 group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={20} />
                        <input
                            type="text"
                            placeholder="Buscar por zona, nombre o líder..."
                            className="w-full bg-white border border-slate-200 rounded-2xl py-3 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all text-sm font-medium"
                        />
                    </div>
                    <button className="px-5 py-3 bg-white border border-slate-200 text-slate-500 hover:text-slate-900 rounded-2xl text-xs font-black uppercase tracking-widest shadow-sm flex items-center gap-2">
                        <Filter size={16} /> Filtros
                    </button>
                    <button className="px-5 py-3 bg-slate-900 text-white hover:bg-slate-800 rounded-2xl text-xs font-black uppercase tracking-widest shadow-sm flex items-center gap-2">
                        <Compass size={16} /> Ver Mapa
                    </button>
                </div>

                {/* Micro KPI */}
                <div className="glass-card bg-blue-600 text-white p-4 rounded-3xl flex items-center justify-between shadow-xl shadow-blue-200">
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-widest text-blue-200">Total Grupos</p>
                        <p className="text-3xl font-black">{groups.length}</p>
                    </div>
                    <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center">
                        <Heart size={24} />
                    </div>
                </div>
            </div>

            {/* Groups Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 relative min-h-[300px]">
                {loading && (
                    <div className="absolute inset-0 bg-[#f8fafc]/50 flex items-center justify-center z-10 backdrop-blur-sm">
                        <Loader2 className="animate-spin text-blue-600" size={32} />
                    </div>
                )}
                {groups.map(group => (
                    <div key={group.id} className="glass-card bg-white p-6 border-slate-200 hover:border-blue-300 hover:shadow-2xl hover:shadow-blue-100 transition-all group overflow-hidden relative">
                        <div className="absolute top-0 left-0 w-2 h-full bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>

                        <div className="flex justify-between items-start mb-6">
                            <span className="px-3 py-1 bg-slate-100 text-slate-600 text-[10px] font-black uppercase tracking-widest rounded-lg flex items-center gap-1">
                                <MapPin size={12} /> {group.zone}
                            </span>
                            <span className={`text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg ${group.status === 'Activo' ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'
                                }`}>
                                {group.status}
                            </span>
                        </div>

                        <h3 className="text-xl font-black text-slate-900 leading-tight mb-2 group-hover:text-blue-600 transition-colors">
                            {group.name}
                        </h3>
                        <p className="text-sm font-bold text-slate-500 mb-6 flex items-center gap-2">
                            Líder: {group.leader_name}
                        </p>

                        <div className="grid grid-cols-2 gap-4 py-4 border-y border-slate-100 mb-6">
                            <div>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Miembros</p>
                                <p className="text-lg font-black text-slate-800 flex items-center gap-1"><Users size={16} className="text-blue-500" /> {group.members_count}</p>
                            </div>
                            <div>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Horario</p>
                                <p className="text-sm font-bold text-slate-800 leading-tight">{group.schedule}</p>
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <button className="flex-1 py-2.5 bg-blue-50 hover:bg-blue-600 hover:text-white text-blue-600 rounded-xl text-xs font-black uppercase tracking-widest transition-colors text-center">
                                Administrar
                            </button>
                            <button className="flex-1 py-2.5 bg-slate-50 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-black uppercase tracking-widest transition-colors text-center">
                                Reporte
                            </button>
                        </div>
                    </div>
                ))}

                {/* Create New Card */}
                <div className="glass-card bg-slate-50 border-2 border-dashed border-slate-200 hover:border-blue-400 hover:bg-blue-50/50 transition-all cursor-pointer flex flex-col items-center justify-center p-8 text-center min-h-[300px] group">
                    <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm mb-4 text-slate-400 group-hover:text-blue-600 group-hover:scale-110 transition-all">
                        <Home size={32} />
                    </div>
                    <h3 className="text-lg font-black text-slate-700 group-hover:text-blue-900">Aperturar Casa de Gloria</h3>
                    <p className="text-xs font-bold text-slate-400 mt-2 uppercase tracking-widest max-w-[200px]">Expandiendo el reino en cada barrio y ciudad.</p>
                </div>
            </div>
        </div>
    );
}

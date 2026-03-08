"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Search,
    Church,
    MapPin,
    Edit2,
    PlusCircle,
    User,
    Building2,
    DoorOpen
} from 'lucide-react';

interface Location {
    id: string;
    name: string;
    address: string;
    pastor: string;
    pastorAvatar: string;
    active: boolean;
    type: 'Central' | 'Sede' | 'Anexo';
}

export default function LocationManagement() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();

    const [locations, setLocations] = useState<Location[]>([
        {
            id: '1',
            name: 'Sede Central',
            address: 'Av. Principal 123, Mocoa',
            pastor: 'Juan Pérez',
            pastorAvatar: 'https://i.pravatar.cc/150?u=juan',
            active: true,
            type: 'Central'
        },
        {
            id: '2',
            name: 'Sede Norte',
            address: 'Calle Norte 45, Distrito 2',
            pastor: 'María García',
            pastorAvatar: 'https://i.pravatar.cc/150?u=maria',
            active: true,
            type: 'Sede'
        },
        {
            id: '3',
            name: 'Anexo Sur',
            address: 'Zona Sur KM 12',
            pastor: 'Carlos Ruiz',
            pastorAvatar: 'https://i.pravatar.cc/150?u=carlos',
            active: false,
            type: 'Anexo'
        },
    ]);

    if (!isAuthenticated) return null;

    const toggleLocation = (id: string) => {
        setLocations(locations.map(loc =>
            loc.id === id ? { ...loc, active: !loc.active } : loc
        ));
    };

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                            <ArrowLeft size={18} />
                        </button>
                        <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-tight">Gestión de Sedes</h1>
                    </div>
                    <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all">
                        <Search size={20} />
                    </button>
                </div>
            </div>

            <main className="flex-1 px-8 py-10 pb-48 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">

                <div className="flex items-center justify-between px-1">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Sedes Registradas</h2>
                    <span className="text-[10px] font-black text-primary uppercase tracking-widest bg-primary/10 px-3 py-1 rounded-full border border-primary/20">{locations.length} Sedes en total</span>
                </div>

                <div className="space-y-6">
                    {locations.map((loc) => (
                        <div
                            key={loc.id}
                            className={`bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex flex-col gap-8 shadow-2xl group transition-all ${!loc.active ? 'opacity-60 blur-[0.5px]' : 'hover:border-primary/30'}`}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex gap-6">
                                    <div className={`size-14 rounded-2xl flex items-center justify-center shadow-lg border border-white/5 transition-all ${loc.active ? 'bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white' : 'bg-slate-800 text-slate-500'}`}>
                                        {loc.type === 'Central' ? <Church size={28} /> : loc.type === 'Sede' ? <Building2 size={28} /> : <DoorOpen size={28} />}
                                    </div>
                                    <div className="space-y-1">
                                        <h3 className="text-lg font-black text-white tracking-tight uppercase tracking-tight">{loc.name}</h3>
                                        <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                            <MapPin size={12} className="text-primary" />
                                            {loc.address}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex flex-col items-end gap-3">
                                    <button
                                        onClick={() => toggleLocation(loc.id)}
                                        className={`relative w-12 h-6 rounded-full transition-all duration-300 ${loc.active ? 'bg-primary shadow-[0_0_8px_#4242f0]' : 'bg-slate-800'}`}
                                    >
                                        <div className={`absolute top-1 left-1 size-4 bg-white rounded-full transition-all duration-300 ${loc.active ? 'translate-x-6' : 'translate-x-0'}`}></div>
                                    </button>
                                    <span className={`text-[9px] font-black uppercase tracking-[0.2em] ${loc.active ? 'text-primary' : 'text-slate-600'}`}>
                                        {loc.active ? 'Activa' : 'Inactiva'}
                                    </span>
                                </div>
                            </div>

                            <div className="flex items-center justify-between pt-6 border-t border-white/5">
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-full border border-white/10 bg-slate-800 flex items-center justify-center text-[10px] font-black text-white">
                                        {loc.pastor?.charAt(0)}
                                    </div>

                                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                        Pastor <span className="text-white">{loc.pastor}</span>
                                    </p>
                                </div>
                                <button className="flex items-center gap-2 text-primary hover:text-white text-[10px] font-black uppercase tracking-widest transition-all group/edit">
                                    <Edit2 size={14} className="group-hover/edit:rotate-12 transition-transform" />
                                    Editar
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </main>

            {/* Float Action Button */}
            <div className="fixed bottom-28 left-0 right-0 px-8 z-50">
                <button className="w-full h-18 bg-primary hover:bg-primary-600 text-white font-black rounded-[1.5rem] shadow-2xl shadow-primary/30 hover:scale-[1.02] active:scale-[0.98] transition-all text-[11px] uppercase tracking-[0.2em] border border-primary-400/20 flex items-center justify-center gap-3">
                    <PlusCircle size={20} />
                    Añadir Nueva Sede
                </button>
            </div>
        </div>
    );
}

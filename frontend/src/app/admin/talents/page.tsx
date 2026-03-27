"use client";

import React, { useEffect, useState } from 'react';
import { 
    Search, Filter, Video, Music, Users, Crown, ChevronRight, Award, Zap
} from 'lucide-react';
import { api } from '@/services/apiService';

const SKILL_CATEGORIES = [
    { id: 'media', label: 'Media & Video', icon: Video, color: 'text-red-500' },
    { id: 'musica', label: 'Alabanza', icon: Music, color: 'text-primary' },
    { id: 'liderazgo', label: 'Liderazgo', icon: Crown, color: 'text-amber-500' },
    { id: 'servicio', label: 'Servicio', icon: Users, color: 'text-emerald-500' },
];

export default function TalentSearchPage() {
    const [talents, setTalents] = useState<any[]>([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            setLoading(true);
            api.get<any[]>(`/crm/talents?q=${search}`)
                .then(setTalents)
                .catch(console.error)
                .finally(() => setLoading(false));
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [search]);

    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                    <Award size={12} /> Gestion de Talento Humano
                </div>
                <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                    Buscador de <span className="text-amber-500">Talentos</span>
                </h1>
                <p className="text-muted-foreground text-sm max-w-2xl">
                    Identifica a los miembros segun sus dones y habilidades tecnicas directamente desde la base de datos ministerial.
                </p>
            </div>

            <div className="flex flex-wrap gap-4 items-center">
                <div className="flex-1 min-w-[300px] relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-amber-500 transition-colors" size={20} />
                    <input 
                        type="text" 
                        placeholder="Buscar por nombre o habilidad..."
                        className="w-full bg-[#1e1f21] border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-amber-500/50 transition-all shadow-2xl"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            <div className="space-y-4">
                <h3 className="text-xs font-black text-muted-foreground uppercase tracking-[0.3em] flex items-center gap-2">
                    <Zap size={14} className="text-amber-500" /> {loading ? 'Buscando...' : 'Resultados Reales'}
                </h3>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {talents.map((talent, i) => (
                        <div key={i} className="bg-[#1e1f21] border border-white/5 p-6 rounded-3xl group hover:border-amber-500/30 transition-all flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="w-14 h-14 bg-amber-500/10 rounded-2xl flex items-center justify-center text-amber-500 font-black text-xl">
                                    {talent.first_name.charAt(0)}
                                </div>
                                <div className="space-y-1">
                                    <h4 className="font-bold text-white uppercase">{talent.first_name} {talent.last_name}</h4>
                                    <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">{talent.email}</div>
                                    <div className="flex flex-wrap gap-1 mt-2">
                                        {talent.skills?.map((s: any, idx: number) => (
                                            <span key={idx} className="text-[8px] bg-white/5 text-white/60 px-2 py-0.5 rounded-full border border-white/5 uppercase">
                                                {s.name}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            <button className="p-3 bg-white/5 group-hover:bg-amber-500 group-hover:text-black rounded-2xl transition-all">
                                <ChevronRight size={20} />
                            </button>
                        </div>
                    ))}
                    {!loading && talents.length === 0 && (
                        <div className="col-span-full py-12 text-center text-muted-foreground border border-dashed border-white/10 rounded-3xl uppercase text-[10px] font-black tracking-widest">
                            No se encontraron talentos con los criterios de busqueda
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

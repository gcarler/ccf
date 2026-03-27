"use client";

import React, { useEffect, useState } from 'react';
import { 
    Heart, 
    Waves, 
    Zap, 
    CheckCircle2, 
    Calendar,
    ChevronRight,
    Star,
    Shield
} from 'lucide-react';

interface Milestone {
    milestone_id: number;
    type: string;
    event_date: string;
}

export default function SpiritualTimelinePage() {
    const [milestones, setMilestones] = useState<Milestone[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // En un entorno real usariamos el user_id del token
        fetch('http://localhost:8000/spiritual-life/milestones/00000000-0000-0000-0000-000000000000')
            .then(res => res.json())
            .then(data => setMilestones(Array.isArray(data) ? data : []))
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const MILESTONE_DEFS: Record<string, any> = {
        'Decision_Fe': { label: 'Decisión de Fe', icon: Zap, color: 'text-amber-500', bg: 'bg-amber-500/10' },
        'Bautismo_Aguas': { label: 'Bautismo en Aguas', icon: Waves, color: 'text-cyan-500', bg: 'bg-cyan-500/10' },
        'Bautismo_Espiritu': { label: 'Bautismo del Espíritu', icon: Star, color: 'text-purple-500', bg: 'bg-purple-500/10' },
        'Miembro_Oficial': { label: 'Membresía Oficial', icon: Shield, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    };

    return (
        <div className="p-8 space-y-12 animate-in fade-in duration-1000">
            <div className="text-center space-y-4 max-w-2xl mx-auto">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit mx-auto">
                    <Heart size={12} /> Crecimiento Espiritual
                </div>
                <h1 className="text-5xl font-black tracking-tighter text-white uppercase italic">
                    Mi Ruta de <span className="text-primary">Victoria</span>
                </h1>
                <p className="text-muted-foreground text-sm">
                    Trazamos cada hito de tu caminar con Cristo. Estos momentos definen tu identidad y tu propósito en el Reino.
                </p>
            </div>

            <div className="relative max-w-4xl mx-auto">
                <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-primary/50 via-white/5 to-transparent hidden md:block" />
                
                <div className="space-y-12 relative">
                    {milestones.length > 0 ? milestones.map((m, i) => {
                        const def = MILESTONE_DEFS[m.type] || { label: m.type, icon: CheckCircle2, color: 'text-white', bg: 'bg-white/10' };
                        return (
                            <div key={i} className={`flex flex-col md:flex-row items-center gap-8 ${i % 2 === 0 ? 'md:flex-row-reverse' : ''}`}>
                                <div className="flex-1 w-full">
                                    <div className={`p-8 bg-[#1e1f21] border border-white/5 rounded-3xl group hover:border-primary/30 transition-all duration-500 ${i % 2 === 0 ? 'text-right' : 'text-left'}`}>
                                        <div className={`text-[10px] font-black uppercase tracking-[0.2em] mb-2 ${def.color}`}>
                                            {new Date(m.event_date).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}
                                        </div>
                                        <h3 className="text-2xl font-black text-white italic uppercase tracking-tight group-hover:translate-x-1 transition-transform">
                                            {def.label}
                                        </h3>
                                        <p className="text-muted-foreground text-sm mt-2">
                                            Hito registrado oficialmente en el sistema ministerial CCF.
                                        </p>
                                    </div>
                                </div>

                                <div className="relative z-10">
                                    <div className={`w-16 h-16 ${def.bg} border-2 border-white/5 rounded-2xl flex items-center justify-center ${def.color} shadow-2xl group-hover:scale-110 transition-transform duration-500`}>
                                        <def.icon size={32} />
                                    </div>
                                </div>

                                <div className="flex-1 hidden md:block" />
                            </div>
                        );
                    }) : (
                        <div className="text-center py-20 bg-white/5 rounded-3xl border border-dashed border-white/10">
                            <Zap size={40} className="mx-auto text-muted-foreground/30 mb-4" />
                            <div className="text-muted-foreground font-medium uppercase tracking-widest text-[10px]">Aun no se han registrado hitos en tu linea de tiempo</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

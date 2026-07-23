"use client";

import React from 'react';
import { 
    Users, 
    Heart, 
    Home, 
    UserPlus, 
    MoreVertical, 
    Shield, 
    Baby,
    Smile,
    MessageCircle,
    Star
} from 'lucide-react';

export default function FamilyNucleusPage() {
    return (
        <div className="p-4 space-y-3 animate-in slide-in-from-right-4 duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))] rounded-full text-[10px] font-semibold uppercase tracking-wide w-fit">
                        <Heart size={12} /> Gestion Familiar Ministerial
                    </div>
                    <h1 className="text-lg font-bold tracking-tighter text-white uppercase italic">
                        Mi Núcleo <span className="text-[hsl(var(--destructive))]">Familiar</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Gestiona a los personas de tu casa, vincula sus perfiles y accede a consejería familiar integrada.
                    </p>
                </div>

                <button className="px-4 py-1.5 bg-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.9)] text-white text-xs font-semibold uppercase tracking-wide rounded-lg transition-all shadow-[0_0_20px_hsl(var(--destructive)/0.3)] flex items-center gap-2">
                    <UserPlus size={16} /> Vincular Familiar
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2 space-y-3">
                    <div className="bg-[hsl(var(--surface-1))] border border-white/5 p-4 rounded-md relative overflow-hidden group">
                        <div className="absolute -top-5 -right-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-1000 text-[hsl(var(--destructive))]">
                            <Home size={300} />
                        </div>
                        
                        <div className="relative z-10 space-y-3">
                            <div className="flex items-center gap-4">
                                <div className="w-16 h-8 bg-gradient-to-br from-[hsl(var(--destructive))] to-[hsl(var(--primary))] rounded-md flex items-center justify-center text-white text-lg font-bold shadow-xl">
                                    F
                                </div>
                                <div>
                                    <h2 className="text-lg font-bold text-white tracking-tight uppercase italic">Familia <span className="text-[hsl(var(--destructive))]">Gomez Sanchez</span></h2>
                                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wide flex items-center gap-2">
                                        <Shield size={12} className="text-[hsl(var(--destructive))]" /> Personas Activos: 4
                                    </p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {[
                                    { name: 'Ricardo Gomez', role: 'Padre / Cabeza', status: 'Activo', icon: Smile, color: 'text-[hsl(var(--primary))]' },
                                    { name: 'Maria Sanchez', role: 'Madre', status: 'Activo', icon: Heart, color: 'text-[hsl(var(--destructive)/0.7)]' },
                                    { name: 'Samuel Gomez', role: 'Hijo', status: 'Estudiante', icon: Baby, color: 'text-[hsl(var(--warning)/0.8)]' },
                                    { name: 'Lucia Gomez', role: 'Hija', status: 'Estudiante', icon: Star, color: 'text-[hsl(var(--info))]' },
                                ].map((persona, i) => (
                                    <div key={i} className="bg-white/5 border border-white/5 p-3 rounded-md hover:border-white/10 transition-all flex items-center justify-between group/item">
                                        <div className="flex items-center gap-4">
                                            <div className={`w-12 h-8 bg-white/5 rounded-lg flex items-center justify-center ${persona.color}`}>
                                                <persona.icon size={20} />
                                            </div>
                                            <div>
                                                <div className="text-sm font-bold text-white group-hover/item:text-[hsl(var(--destructive))] transition-colors">{persona.name}</div>
                                                <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-tighter">{persona.role}</div>
                                            </div>
                                        </div>
                                        <button className="p-2 text-muted-foreground hover:text-white transition-colors">
                                            <MoreVertical size={16} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-[hsl(var(--surface-1))] border border-white/5 p-4 rounded-md space-y-4">
                            <h3 className="text-xs font-semibold text-white uppercase tracking-wide flex items-center gap-2">
                                <MessageCircle size={14} className="text-[hsl(var(--destructive))]" /> Consejería Familiar
                            </h3>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Accede a recursos especializados para matrimonios y crianza de hijos según principios bíblicos.
                            </p>
                            <button className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-semibold uppercase tracking-wide rounded-md transition-all border border-white/5">
                                Ver Recursos
                            </button>
                        </div>
                        <div className="bg-[hsl(var(--surface-1))] border border-white/5 p-4 rounded-md space-y-4">
                            <h3 className="text-xs font-semibold text-white uppercase tracking-wide flex items-center gap-2">
                                <Users size={14} className="text-[hsl(var(--destructive))]" /> Grupo en Casa
                            </h3>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Su familia está vinculada a la <span className="text-white font-bold">Grupo en Casa &quot;Norte 1&quot;</span> dirigida por Juan y Paula.
                            </p>
                            <button className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-semibold uppercase tracking-wide rounded-md transition-all border border-white/5">
                                Contactar Líder
                            </button>
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="bg-gradient-to-br from-[hsl(var(--destructive)/0.2)] to-[hsl(var(--primary)/0.2)] border border-[hsl(var(--destructive)/0.2)] p-4 rounded-md space-y-3">
                        <h3 className="text-base font-bold text-white tracking-tighter uppercase italic">Impacto <span className="text-[hsl(var(--destructive))]">Espiritual</span></h3>
                        <div className="space-y-4">
                            {[
                                { label: 'Asistencia Total', value: '92%', color: 'bg-[hsl(var(--destructive))]' },
                                { label: 'Academia Progreso', value: '65%', color: 'bg-[hsl(var(--primary))]' },
                                { label: 'Servicio Voluntario', value: '100%', color: 'bg-[hsl(var(--success))]' },
                            ].map((stat, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide">
                                        <span className="text-white/60">{stat.label}</span>
                                        <span className="text-white">{stat.value}</span>
                                    </div>
                                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                        <div className={`h-full ${stat.color} transition-all duration-1000`} style={{ width: stat.value }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-[hsl(var(--surface-1))] border border-white/5 p-4 rounded-md space-y-3">
                        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Próximos Eventos</h3>
                        <div className="space-y-4">
                            {[
                                { title: 'Cena de Matrimonios', date: 'Viernes 20:00' },
                                { title: 'Escuela de Padres', date: 'Sábado 10:00' },
                            ].map((ev, i) => (
                                <div key={i} className="flex items-center gap-4 group">
                                    <div className="w-10 h-10 bg-white/5 rounded-md flex items-center justify-center text-[hsl(var(--destructive))] group-hover:bg-[hsl(var(--destructive))] group-hover:text-white transition-all">
                                        <Star size={16} />
                                    </div>
                                    <div>
                                        <div className="text-xs font-bold text-white uppercase tracking-tight">{ev.title}</div>
                                        <div className="text-[10px] text-muted-foreground font-bold">{ev.date}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}


"use client";

import React, { useEffect, useState } from 'react';
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
        <div className="p-8 space-y-12 animate-in slide-in-from-right-4 duration-700">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-rose-500/10 text-rose-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                        <Heart size={12} /> Gestion Familiar Ministerial
                    </div>
                    <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                        Mi Núcleo <span className="text-rose-500">Familiar</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Gestiona a los miembros de tu casa, vincula sus perfiles y accede a consejería familiar integrada.
                    </p>
                </div>

                <button className="px-6 py-3 bg-rose-500 hover:bg-rose-600 text-black text-xs font-black uppercase tracking-widest rounded-2xl transition-all shadow-[0_0_20px_rgba(244,63,94,0.3)] flex items-center gap-2">
                    <UserPlus size={16} /> Vincular Familiar
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] relative overflow-hidden group">
                        <div className="absolute -top-10 -right-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-1000 text-rose-500">
                            <Home size={300} />
                        </div>
                        
                        <div className="relative z-10 space-y-8">
                            <div className="flex items-center gap-4">
                                <div className="w-16 h-16 bg-gradient-to-br from-rose-500 to-primary rounded-3xl flex items-center justify-center text-white text-2xl font-black shadow-xl">
                                    F
                                </div>
                                <div>
                                    <h2 className="text-2xl font-black text-white tracking-tight uppercase italic">Familia <span className="text-rose-500">Gomez Sanchez</span></h2>
                                    <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest flex items-center gap-2">
                                        <Shield size={12} className="text-rose-500" /> Miembros Activos: 4
                                    </p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {[
                                    { name: 'Ricardo Gomez', role: 'Padre / Cabeza', status: 'Activo', icon: Smile, color: 'text-blue-400' },
                                    { name: 'Maria Sanchez', role: 'Madre', status: 'Activo', icon: Heart, color: 'text-rose-400' },
                                    { name: 'Samuel Gomez', role: 'Hijo', status: 'Estudiante', icon: Baby, color: 'text-amber-400' },
                                    { name: 'Lucia Gomez', role: 'Hija', status: 'Estudiante', icon: Star, color: 'text-purple-400' },
                                ].map((member, i) => (
                                    <div key={i} className="bg-white/5 border border-white/5 p-5 rounded-3xl hover:border-white/10 transition-all flex items-center justify-between group/item">
                                        <div className="flex items-center gap-4">
                                            <div className={`w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center ${member.color}`}>
                                                <member.icon size={20} />
                                            </div>
                                            <div>
                                                <div className="text-sm font-bold text-white group-hover/item:text-rose-400 transition-colors">{member.name}</div>
                                                <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-tighter">{member.role}</div>
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

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-[#1e1f21] border border-white/5 p-6 rounded-3xl space-y-4">
                            <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                                <MessageCircle size={14} className="text-rose-500" /> Consejería Familiar
                            </h3>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Accede a recursos especializados para matrimonios y crianza de hijos según principios bíblicos.
                            </p>
                            <button className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-white/5">
                                Ver Recursos
                            </button>
                        </div>
                        <div className="bg-[#1e1f21] border border-white/5 p-6 rounded-3xl space-y-4">
                            <h3 className="text-xs font-black text-white uppercase tracking-widest flex items-center gap-2">
                                <Users size={14} className="text-rose-500" /> Casa de Gloria
                            </h3>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">
                                Su familia está vinculada a la <span className="text-white font-bold">Casa de Gloria &quot;Norte 1&quot;</span> dirigida por Juan y Paula.
                            </p>
                            <button className="w-full py-2.5 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all border border-white/5">
                                Contactar Líder
                            </button>
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="bg-gradient-to-br from-rose-500/20 to-primary/20 border border-rose-500/20 p-8 rounded-[2.5rem] space-y-6">
                        <h3 className="text-xl font-black text-white tracking-tighter uppercase italic">Impacto <span className="text-rose-500">Espiritual</span></h3>
                        <div className="space-y-4">
                            {[
                                { label: 'Asistencia Total', value: '92%', color: 'bg-rose-500' },
                                { label: 'Academia Progreso', value: '65%', color: 'bg-primary' },
                                { label: 'Servicio Voluntario', value: '100%', color: 'bg-emerald-500' },
                            ].map((stat, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
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

                    <div className="bg-[#1e1f21] border border-white/5 p-8 rounded-[2.5rem] space-y-6">
                        <h3 className="text-xs font-black text-white uppercase tracking-widest">Próximos Eventos</h3>
                        <div className="space-y-4">
                            {[
                                { title: 'Cena de Matrimonios', date: 'Viernes 20:00' },
                                { title: 'Escuela de Padres', date: 'Sábado 10:00' },
                            ].map((ev, i) => (
                                <div key={i} className="flex items-center gap-4 group">
                                    <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-rose-500 group-hover:bg-rose-500 group-hover:text-black transition-all">
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

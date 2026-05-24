"use client";

import React from 'react';
import {
    Award,
    Crown,
    Star,
    Zap,
    Shield,
    ChevronRight,
    Edit3,
    Heart,
    User,
    Settings
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function MinistryProfilePage() {
    const sidebarSections = [
        {
            title: 'Cuenta',
            items: [
                { id: 'account-profile', label: 'Mi Perfil', href: '/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/account/ministry-profile', icon: Crown },
                { id: 'settings-general', label: 'Configuración', href: '/settings', icon: Settings },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Cuenta" sidebarSections={sidebarSections}>
            <div className="p-4 space-y-3 animate-in fade-in duration-1000">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
                <div className="space-y-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-500 rounded-full text-[10px] font-semibold uppercase tracking-wide w-fit">
                        <Crown size={12} /> Mi Identidad en el Reino
                    </div>
                    <h1 className="text-lg font-bold tracking-tighter text-white uppercase italic">
                        Perfil <span className="text-amber-500">Ministerial</span>
                    </h1>
                    <p className="text-muted-foreground text-sm max-w-xl">
                        Gestiona tus dones, habilidades y oficios eclesiásticos. Tu llamado es nuestra prioridad.
                    </p>
                </div>

                <button className="px-3 py-3 bg-white/5 border border-white/10 hover:bg-white/10 text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all flex items-center gap-2">
                    <Edit3 size={16} /> Editar Perfil
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                <div className="lg:col-span-2 space-y-3">
                    <div className="bg-[#1e1f21] border border-white/5 p-4 rounded-lg space-y-3">
                        <div className="flex items-center gap-3">
                            <div className="w-24 h-24 bg-gradient-to-br from-amber-500 to-primary rounded-lg flex items-center justify-center text-white text-lg font-bold shadow-2xl">
                                R
                            </div>
                            <div className="space-y-1">
                                <h2 className="text-xl font-bold text-white tracking-tight uppercase italic">Ricardo <span className="text-amber-500">Gomez</span></h2>
                                <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-semibold uppercase tracking-wide">
                                    <Shield size={12} className="text-amber-500" /> Miembro Activo <span className="opacity-20">•</span> Desde 2022
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-8 border-t border-white/5">
                            <div className="space-y-4">
                                <h3 className="text-xs font-semibold text-white uppercase tracking-wide flex items-center gap-2">
                                    <Crown size={14} className="text-amber-500" /> Oficios Eclesiásticos
                                </h3>
                                <div className="space-y-2">
                                    {['Evangelista', 'Líder de Faro en Casa'].map((office, i) => (
                                        <div key={i} className="flex items-center gap-3 bg-white/5 p-3 rounded-md border border-white/5">
                                            <div className="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_10px_#f59e0b]" />
                                            <span className="text-sm font-bold text-white uppercase tracking-tight">{office}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="space-y-4">
                                <h3 className="text-xs font-semibold text-white uppercase tracking-wide flex items-center gap-2">
                                    <Zap size={14} className="text-amber-500" /> Mis Dones y Habilidades
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {['Edición Video', 'Diseño Gráfico', 'Intercesión', 'Enseñanza', 'Fotografía'].map((skill, i) => (
                                        <span key={i} className="px-3 py-1.5 bg-white/5 rounded-lg text-[10px] font-bold text-muted-foreground border border-white/5 uppercase tracking-wider">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-[#1e1f21] border border-white/5 p-4 rounded-lg space-y-3">
                        <h3 className="text-xl font-bold text-white tracking-tight uppercase italic">Mis <span className="text-amber-500">Logros</span></h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {[
                                { label: 'Fundamentos', icon: Star, color: 'text-blue-400' },
                                { label: 'Consolidador', icon: Heart, color: 'text-rose-400' },
                                { label: 'Líder 1', icon: Shield, color: 'text-emerald-400' },
                                { label: 'Maestro', icon: Award, color: 'text-sky-400' },
                            ].map((badge, i) => (
                                <div key={i} className="bg-white/5 p-3 rounded-lg flex flex-col items-center gap-3 text-center group hover:bg-white/10 transition-all border border-white/5">
                                    <div className={`w-12 h-8 bg-white/5 rounded-lg flex items-center justify-center ${badge.color} group-hover:scale-110 transition-transform`}>
                                        <badge.icon size={24} />
                                    </div>
                                    <span className="text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">{badge.label}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="bg-gradient-to-br from-amber-500/20 to-primary/20 border border-amber-500/20 p-4 rounded-lg space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-white tracking-tighter uppercase italic">Nivel <span className="text-amber-500">12</span></h3>
                            <Zap size={24} className="text-amber-500 animate-pulse" />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide">
                                <span className="text-white/60">Experiencia Ministerial</span>
                                <span className="text-white">850 / 1000 XP</span>
                            </div>
                            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                                <div className="h-full bg-amber-500 transition-all duration-1000 shadow-[0_0_15px_rgba(245,158,11,0.5)]" style={{ width: '85%' }} />
                            </div>
                        </div>
                        <p className="text-[10px] text-muted-foreground font-medium leading-relaxed italic">
                            &quot;Te faltan 150 XP para alcanzar el nivel de Lider de Proyecto.&quot;
                        </p>
                    </div>

                    <div className="bg-[#1e1f21] border border-white/5 p-4 rounded-lg space-y-3">
                        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Llamados de Servicio</h3>
                        <div className="space-y-4">
                            {[
                                { title: 'Equipo de Media', desc: 'Necesitamos editores de video para el domingo.' },
                                { title: 'Alabanza', desc: 'Audiciones para coros el proximo martes.' },
                            ].map((call, i) => (
                                <div key={i} className="group p-4 bg-white/5 rounded-lg border border-white/5 hover:border-amber-500/30 transition-all cursor-pointer">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-xs font-bold text-white uppercase">{call.title}</span>
                                        <ChevronRight size={14} className="text-muted-foreground group-hover:text-amber-500 transition-all" />
                                    </div>
                                    <p className="text-[10px] text-muted-foreground leading-relaxed">{call.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        </WorkspaceLayout>
    );
}


"use client";

import React from 'react';
import { SITE_NAME } from '@/lib/site-config';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Bell,
    Edit3,
    MapPin,
    Church,
    Contact,
    Share2,
    CreditCard,

    Settings,
    LogOut,
    ChevronRight,
    Sparkles
} from 'lucide-react';

export default function MinistrySettings() {
    const { isAuthenticated, logout } = useAuth();
    const router = useRouter();

    if (!isAuthenticated) return null;

    const handleLogout = () => {
        logout();
        router.push('/login');
    };

    const settingsGroups = [
        {
            title: "Administración General",
            items: [
                { icon: Church, label: "Perfil del Ministerio", sub: "Nombre, misión, visión y logo", path: "/admin/settings/profile" },
                { icon: Sparkles, label: "Experiencia de Usuario", sub: "Activar módulos, IA y marca visual", path: "/admin/settings/experience" },
                { icon: Contact, label: "Información de Contacto", sub: "Teléfonos, correos y atención", path: "/admin/settings/contact" },
                { icon: Share2, label: "Redes Sociales", sub: "Instagram, YouTube, Facebook", path: "/admin/settings/socials" },
            ]
        },
        {
            title: "Operaciones y Pagos",
            items: [
                { icon: MapPin, label: "Gestión de Sedes", sub: "Sucursales y ministerios locales", path: "/admin/settings/locations" },
                { icon: CreditCard, label: "Pagos y Donaciones", sub: "Pasarelas, diezmos y ofrendas", path: "/admin/donations/config" },
                { icon: Settings, label: "Feature Flags y Sistema", sub: "Módulos, toggles y estado global", path: "/admin/settings/system" },
            ]
        }
    ];

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-4 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-bold text-white tracking-tight uppercase tracking-tight">Configuración</h1>
                    <button className="p-3 rounded-lg bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all">
                        <Bell size={20} />
                    </button>
                </div>
            </div>

            <main className="flex-1 px-4 py-1.5 pb-4 space-y-3 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Hero Section */}
                <section className="flex flex-col items-center">
                    <div className="relative group">
                        <div className="size-10 rounded-full border-2 border-primary/20 p-1.5 bg-primary/5 shadow-2xl shadow-primary/10">
                            <div className="size-full rounded-full bg-cover bg-center border-2 border-white/5" style={{ backgroundImage: "url('https://picsum.photos/seed/1544427928-c49cddee14bb/800/600')" }}></div>
                        </div>
                        <button className="absolute bottom-1 right-1 size-10 rounded-full bg-primary text-white border-2 border-slate-950 flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-xl">
                            <Edit3 size={16} />
                        </button>
                    </div>
                    <div className="mt-3 text-center space-y-2">
                        <h2 className="text-xl font-bold text-white tracking-tight uppercase">{SITE_NAME}</h2>
                        <div className="flex items-center justify-center gap-2 text-slate-500 font-bold text-[10px] uppercase tracking-wide">
                            <MapPin size={12} className="text-primary" />
                            Sede Central • Mocoa, Putumayo
                        </div>
                        <div className="mt-4 px-4 py-1.5 bg-primary/10 rounded-full border border-primary/20 inline-block">
                            <span className="text-primary text-[10px] font-semibold uppercase tracking-wide">Admin ID: CCF-2024</span>
                        </div>
                    </div>
                </section>

                {/* Settings Groups */}
                {settingsGroups.map((group, idx) => (
                    <section key={idx} className="space-y-3">
                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-600 ml-1">{group.title}</h3>
                        <div className="space-y-4">
                            {group.items.map((item, iidx) => (
                                <div
                                    key={iidx}
                                    onClick={() => router.push(item.path)}
                                    className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-lg p-3 flex items-center justify-between group cursor-pointer hover:border-white/10 hover:bg-white/5 transition-all active:scale-[0.98]"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="size-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg border border-white/5">
                                            <item.icon size={24} />
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-base font-bold text-white tracking-tight uppercase tracking-tight">{item.label}</p>
                                            <p className="font-semibold text-slate-500 uppercase tracking-wide">{item.sub}</p>
                                        </div>
                                    </div>
                                    <ChevronRight className="text-slate-600 group-hover:text-primary transition-colors" size={20} />
                                </div>
                            ))}
                        </div>
                    </section>
                ))}

                {/* Footer Action */}
                <section className="pt-6">
                    <button
                        onClick={handleLogout}
                        className="w-full h-8 bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white font-black rounded-lg border border-rose-500/20 transition-all flex items-center justify-center gap-3 uppercase text-[11px] tracking-wide shadow-lg shadow-rose-500/5 active:scale-[0.98]"
                    >
                        <LogOut size={20} />
                        Cerrar Sesión Admin
                    </button>
                    <p className="text-center font-semibold text-slate-700 uppercase tracking-wide mt-3">Versión 2.1.0 • Antigravity Engine</p>
                </section>
            </main>
        </div>
    );
}


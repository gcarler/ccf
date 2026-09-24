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
                { icon: Church, label: "Perfil del Ministerio", sub: "Nombre, misión, visión y logo", path: "/plataforma/admin/settings/profile" },
                { icon: Sparkles, label: "Experiencia de Usuario", sub: "Activar módulos, IA y marca visual", path: "/plataforma/admin/settings/experience" },
                { icon: Contact, label: "Información de Contacto", sub: "Teléfonos, correos y atención", path: "/plataforma/admin/settings/contact" },
                { icon: Share2, label: "Redes Sociales", sub: "Instagram, YouTube, Facebook", path: "/plataforma/admin/settings/socials" },
            ]
        },
        {
            title: "Operaciones y Pagos",
            items: [
                { icon: MapPin, label: "Gestión de Sedes", sub: "Sucursales y ministerios locales", path: "/plataforma/admin/settings/locations" },
                { icon: CreditCard, label: "Pagos y Donaciones", sub: "Pasarelas, diezmos y ofrendas", path: "/plataforma/admin/donations/config" },
                { icon: Settings, label: "Feature Flags y Sistema", sub: "Módulos, toggles y estado global", path: "/plataforma/admin/settings/system" },
            ]
        }
    ];

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] font-display">
            {/* Header Area */}
            <div className="bg-[hsl(var(--surface-1))] backdrop-blur-xl border-b border-[hsl(var(--border))] sticky top-0 z-50">
                <div className="px-4 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase">Configuración</h1>
                    <button className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-3))] transition-all">
                        <Bell size={20} />
                    </button>
                </div>
            </div>

            <main className="flex-1 px-4 py-1.5 pb-4 space-y-3 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Hero Section */}
                <section className="flex flex-col items-center">
                    <div className="relative group">
                        <div className="size-10 rounded-full border-2 border-[hsl(var(--primary)/0.2)] p-1.5 bg-[hsl(var(--primary)/0.05)] shadow-2xl shadow-[hsl(var(--primary)/0.1)]">
                            <div className="size-full rounded-full bg-cover bg-center border-2 border-[hsl(var(--border))]" style={{ backgroundImage: "url('https://picsum.photos/seed/1544427928-c49cddee14bb/800/600')" }}></div>
                        </div>
                        <button className="absolute bottom-1 right-1 size-10 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-2 border-[hsl(var(--border))] flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-xl">
                            <Edit3 size={16} />
                        </button>
                    </div>
                    <div className="mt-3 text-center space-y-2">
                        <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase">{SITE_NAME}</h2>
                        <div className="flex items-center justify-center gap-2 text-[hsl(var(--text-secondary))] font-bold text-2xs uppercase tracking-wide">
                            <MapPin size={12} className="text-[hsl(var(--primary))]" />
                            Sede Central • Mocoa, Putumayo
                        </div>
                        <div className="mt-4 px-4 py-1.5 bg-[hsl(var(--primary)/0.1)] rounded-full border border-[hsl(var(--primary)/0.2)] inline-block">
                            <span className="text-[hsl(var(--primary))] text-2xs font-semibold uppercase tracking-wide">Admin ID: CCF-2024</span>
                        </div>
                    </div>
                </section>

                {/* Settings Groups */}
                {settingsGroups.map((group, idx) => (
                    <section key={idx} className="space-y-3">
                        <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-1">{group.title}</h3>
                        <div className="space-y-4">
                            {group.items.map((item, iidx) => (
                                <div
                                    key={iidx}
                                    onClick={() => router.push(item.path)}
                                    className="bg-[hsl(var(--surface-1))] backdrop-blur-xl border border-[hsl(var(--border))] rounded-lg p-3 flex items-center justify-between group cursor-pointer hover:border-[hsl(var(--primary)/0.3)] hover:bg-[hsl(var(--surface-2))] transition-all active:scale-[0.98]"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-[hsl(var(--primary-foreground))] transition-all shadow-lg border border-[hsl(var(--border))]">
                                            <item.icon size={24} />
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-base font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase">{item.label}</p>
                                            <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{item.sub}</p>
                                        </div>
                                    </div>
                                    <ChevronRight className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors" size={20} />
                                </div>
                            ))}
                        </div>
                    </section>
                ))}

                {/* Footer Action */}
                <section className="pt-6">
                    <button
                        onClick={handleLogout}
                        className="w-full h-8 bg-[hsl(var(--destructive)/0.1)] hover:bg-[hsl(var(--destructive))] text-[hsl(var(--destructive))] hover:text-[hsl(var(--primary-foreground))] font-black rounded-lg border border-[hsl(var(--destructive)/0.2)] transition-all flex items-center justify-center gap-3 uppercase text-xs tracking-wide shadow-lg shadow-[hsl(var(--destructive)/0.05)] active:scale-[0.98]"
                    >
                        <LogOut size={20} />
                        Cerrar Sesión Admin
                    </button>
                    <p className="text-center font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide mt-3">Versión 2.1.0 • Antigravity Engine</p>
                </section>
            </main>
        </div>
    );
}

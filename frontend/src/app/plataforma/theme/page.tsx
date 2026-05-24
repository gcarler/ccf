"use client";

import React from "react";
import Link from "next/link";
import { Palette, Settings2, SunMoon, Settings, User, Crown, Shield } from "lucide-react";
import WorkspaceLayout from '@/components/WorkspaceLayout';
import PaletteSelector from "@/app/plataforma/theme/PaletteSelector";
import { useTheme } from "@/app/plataforma/theme/ThemeContext";

export default function ThemePage() {
    const { theme } = useTheme();

    const sidebarSections = [
        {
            title: 'Configuración',
            items: [
                { id: 'settings-general', label: 'General', href: '/settings', icon: Settings },
                { id: 'account-profile', label: 'Mi Perfil', href: '/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/account/ministry-profile', icon: Crown },
                { id: 'settings-roles', label: 'Roles de Acceso', href: '/settings/roles', icon: Shield },
                { id: 'theme-visual', label: 'Tema Visual', href: '/theme', icon: Palette },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Configuración" sidebarSections={sidebarSections}>
            <div className="min-h-full bg-slate-50 dark:bg-[#0f1117]">
            <header className="sticky top-0 z-20 border-b border-slate-200/60 bg-white/80 backdrop-blur-xl dark:border-white/5 dark:bg-[#0f1117]/80">
                <div className="mx-auto flex max-w-4xl items-center justify-between px-3 py-1.5">
                    <div className="flex items-center gap-3">
                        <Palette size={18} className="text-slate-400" />
                        <h1 className="text-[13px] font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">Tema visual</h1>
                    </div>
                    <Link
                        href="/settings"
                        className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 dark:border-white/10 dark:text-slate-300"
                    >
                        <Settings2 size={12} /> Volver a ajustes
                    </Link>
                </div>
            </header>

            <main className="mx-auto max-w-4xl space-y-3 px-3 py-1.5">
                <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1a1d27]">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Modo actual</p>
                            <p className="mt-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
                                {theme === "night" ? "Modo noche" : "Modo dia"}
                            </p>
                        </div>
                        <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-blue-600 dark:bg-blue-500/10 dark:text-blue-300">
                            <SunMoon size={12} /> Personalizacion activa
                        </span>
                    </div>
                </section>

                <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/5 dark:bg-[#1a1d27]">
                    <PaletteSelector />
                </section>
            </main>
        </div>
        </WorkspaceLayout>
    );
}

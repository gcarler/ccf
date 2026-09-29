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
                { id: 'settings-general', label: 'General', href: '/plataforma/settings', icon: Settings },
                { id: 'account-profile', label: 'Mi Perfil', href: '/plataforma/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/plataforma/account/ministry-profile', icon: Crown },
                { id: 'settings-roles', label: 'Roles de Acceso', href: '/plataforma/settings/roles', icon: Shield },
                { id: 'theme-visual', label: 'Tema Visual', href: '/plataforma/theme', icon: Palette },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Configuración" sidebarSections={sidebarSections}>
            <div className="min-h-full bg-[hsl(var(--surface-1))]">
            <header className="sticky top-0 z-20 border-b border-[hsl(var(--border))]/60 bg-[hsl(var(--surface-1))]/80 backdrop-blur-xl">
                <div className="mx-auto flex max-w-4xl items-center justify-between px-3 py-1.5">
                    <div className="flex items-center gap-3">
                        <Palette size={18} className="text-[hsl(var(--text-secondary))]" />
                        <h1 className="text-base font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">Tema visual</h1>
                    </div>
                    <Link
                        href="/plataforma/settings"
                        className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-4 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition hover:border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]"
                    >
                        <Settings2 size={12} /> Volver a ajustes
                    </Link>
                </div>
            </header>

            <main className="mx-auto max-w-4xl space-y-3 px-3 py-1.5">
                <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Modo actual</p>
                            <p className="mt-1 text-sm font-semibold text-[hsl(var(--text-primary))]">
                                {theme === "night" ? "Modo noche" : "Modo dia"}
                            </p>
                        </div>
                        <span className="inline-flex items-center gap-2 rounded-full bg-[hsl(var(--primary))]/10 px-3 py-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                            <SunMoon size={12} /> Personalizacion activa
                        </span>
                    </div>
                </section>

                <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 shadow-sm">
                    <PaletteSelector />
                </section>
            </main>
        </div>
        </WorkspaceLayout>
    );
}

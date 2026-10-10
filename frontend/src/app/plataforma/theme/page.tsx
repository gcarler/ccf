"use client";

import React from "react";
import Link from "next/link";
import { Palette, Settings2, SunMoon, Settings, User, Crown, Shield, ShieldCheck } from "lucide-react";
import WorkspaceLayout from '@/components/WorkspaceLayout';
import PaletteSelector from "@/app/plataforma/theme/PaletteSelector";
import { useTheme } from "@/app/plataforma/theme/ThemeContext";

export default function ThemePage() {
    const { theme, currentScale, currentAccent } = useTheme();

    const sidebarSections = [
        {
            title: 'Configuración',
            items: [
                { id: 'settings-general', label: 'General', href: '/plataforma/settings', icon: Settings },
                { id: 'account-profile', label: 'Mi Perfil', href: '/plataforma/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/plataforma/account/ministry-profile', icon: Crown },
                { id: 'settings-roles', label: 'Roles de Acceso', href: '/plataforma/settings/roles', icon: Shield },
                { id: 'theme-visual', label: 'Tema y Accesibilidad', href: '/plataforma/theme', icon: Palette },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Configuración" sidebarSections={sidebarSections}>
            <div className="min-h-full bg-[hsl(var(--surface-1))]">
                <header className="sticky top-0 z-20 border-b border-[hsl(var(--border))]/60 bg-[hsl(var(--surface-1))]/80 backdrop-blur-xl">
                    <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
                        <div className="flex items-center gap-3">
                            <Palette size={20} className="text-[hsl(var(--primary))]" />
                            <div>
                                <h1 className="text-base font-semibold text-[hsl(var(--text-primary))]">Tema y Accesibilidad</h1>
                                <p className="text-2xs text-[hsl(var(--text-secondary))]">Personalización visual y ergonomía de interfaz</p>
                            </div>
                        </div>
                        <Link
                            href="/plataforma/settings"
                            className="inline-flex items-center gap-2 rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-2xs font-medium text-[hsl(var(--text-secondary))] transition hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                        >
                            <Settings2 size={13} /> Volver a ajustes
                        </Link>
                    </div>
                </header>

                <main className="mx-auto max-w-4xl space-y-4 px-4 py-4">
                    {/* Tarjeta de estado actual consolidado */}
                    <section aria-labelledby="status-heading" className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="space-y-1">
                                <h2 id="status-heading" className="text-2xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                                    Configuración activa
                                </h2>
                                <div className="flex flex-wrap items-center gap-3 text-xs">
                                    <span className="font-semibold text-[hsl(var(--text-primary))]">
                                        {theme === "night" ? "Modo Noche" : "Modo Día"}
                                    </span>
                                    <span className="text-[hsl(var(--border))]">•</span>
                                    <span className="font-semibold text-[hsl(var(--text-primary))]">
                                        Escala {currentScale.label} ({currentScale.percentage})
                                    </span>
                                    <span className="text-[hsl(var(--border))]">•</span>
                                    <span className="font-semibold text-[hsl(var(--text-primary))] inline-flex items-center gap-1.5">
                                        <span
                                            className="w-2.5 h-2.5 rounded-full inline-block"
                                            style={{ backgroundColor: currentAccent.swatch }}
                                        />
                                        {currentAccent.label}
                                    </span>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-[hsl(var(--primary)/0.12)] px-3 py-1 text-2xs font-semibold text-[hsl(var(--primary))]">
                                    <ShieldCheck size={13} /> WCAG AA Conforme
                                </span>
                                <span className="inline-flex items-center gap-1.5 rounded-full border border-[hsl(var(--border))] px-3 py-1 text-2xs font-medium text-[hsl(var(--text-secondary))]">
                                    <SunMoon size={13} /> Personalizado
                                </span>
                            </div>
                        </div>
                    </section>

                    {/* Selector interactivo de temas, escalas y acentos */}
                    <section aria-label="Controles de apariencia y escala" className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm">
                        <PaletteSelector />
                    </section>
                </main>
            </div>
        </WorkspaceLayout>
    );
}

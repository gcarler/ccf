"use client";

import React, { useState } from 'react';
import { SITE_NAME } from '@/lib/site-config';
import { motion } from 'framer-motion';
import {
    Settings, User, Bell, Lock, Palette, Globe, Shield,
    ChevronRight, Moon, Sun, Monitor, Check,
    Languages, Keyboard, Zap, LogOut, Trash2, Crown,
    Monitor as MonitorIcon
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import AppearanceDrawer from '@/components/ui/AppearanceDrawer';
import { useTheme } from '@/app/plataforma/theme/ThemeContext';

export interface SettingsItemConfig {
    id?: string;
    icon: any;
    label: string;
    desc: string;
    href?: string;
    action?: 'appearance';
}

export interface SettingsGroupConfig {
    title: string;
    color: string;
    items: SettingsItemConfig[];
}

const SETTINGS_GROUPS: SettingsGroupConfig[] = [
    {
        title: "Cuenta",
        color: "blue",
        items: [
            { icon: User, label: "Perfil Personal", desc: "Nombre, foto y datos personales", href: "/plataforma/account" },
            { icon: Bell, label: "Notificaciones", desc: "Alertas, recordatorios y emails", href: "#notificaciones" },
            { icon: Lock, label: "Seguridad", desc: "Contraseña y autenticación", href: "#seguridad" },
            { icon: MonitorIcon, label: "Sesiones Activas", desc: "Dispositivos conectados a tu cuenta", href: "/plataforma/admin/settings/sessions" },
        ]
    },
    {
        title: "Apariencia",
        color: "blue",
        items: [
            { id: "appearance-theme", icon: Palette, label: "Tema Visual", desc: "Modo día, noche, paleta de acento y escala", href: "/plataforma/theme", action: "appearance" },
            { icon: Languages, label: "Idioma y Región", desc: "Español (Colombia)", href: "#idioma" },
            { id: "appearance-density", icon: Monitor, label: "Densidad de UI", desc: "Ultra compacta, compacta, cómoda o espaciosa y zoom manual (85%-140%)", href: "#densidad", action: "appearance" },
        ]
    },
    {
        title: "Plataforma",
        color: "emerald",
        items: [
            { icon: Keyboard, label: "Atajos de Teclado", desc: "Ver todos los atajos disponibles", href: "#atajos" },
            { icon: Zap, label: "Integraciones", desc: "Conectar apps y servicios externos", href: "#integraciones" },
            { icon: Globe, label: "API & Webhooks", desc: "Acceso programático a la plataforma", href: "#api" },
        ]
    },
];

const COLOR_MAP: Record<string, string> = {
    blue: "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]",
    sky: "bg-[hsl(var(--info-muted))] text-[hsl(var(--info))]",
    emerald: "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]",
};

export default function SettingsPage() {
    const { logout, user } = useAuth();
    const router = useRouter();
    const { theme, setTheme, currentScale, currentAccent, currentDensity, zoomPercentage } = useTheme();
    const [isAppearanceOpen, setIsAppearanceOpen] = useState(false);

    const sidebarSections = [
        {
            title: 'Configuración',
            items: [
                { id: 'settings-general', label: 'General', href: '/plataforma/settings', icon: Settings },
                { id: 'account-profile', label: 'Mi Perfil', href: '/plataforma/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/plataforma/account/ministry-profile', icon: Crown },
                { id: 'settings-roles', label: 'Roles de Acceso', href: '/plataforma/settings/roles', icon: Shield },
                { id: 'settings-sessions', label: 'Sesiones', href: '/plataforma/admin/settings/sessions', icon: MonitorIcon },
                { id: 'theme-visual', label: 'Tema Visual', href: '/plataforma/theme', icon: Palette },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Configuración" sidebarSections={sidebarSections}>
            <div className="min-h-full bg-[hsl(var(--surface-1))]">
            {/* Header */}
            <div className="sticky top-0 z-30 bg-[hsl(var(--surface-1)/0.8)] backdrop-blur-xl border-b border-[hsl(var(--border))]">
                <div className="max-w-3xl mx-auto px-3 py-1.5 flex items-center gap-3">
                    <Settings size={18} className="text-[hsl(var(--text-secondary))]" />
                    <h1 className="text-base font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))]">
                        Configuración
                    </h1>
                </div>
            </div>

            <div className="max-w-3xl mx-auto px-3 py-8 space-y-3">
                {/* Profile Card */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 flex items-center gap-3 shadow-sm"
                >
                    <div className="size-8 rounded-lg bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-[hsl(var(--primary-foreground))] text-xl font-bold shadow-sm shadow-[hsl(var(--info)/20%)] shrink-0">
                        {(user as any)?.name?.[0] ?? 'A'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-base font-bold text-[hsl(var(--text-primary))] truncate">
                            {(user as any)?.name ?? 'Usuario CCF'}
                        </p>
                        <p className="text-xs text-[hsl(var(--text-secondary))] font-medium truncate">
                            {(user as any)?.email ?? 'usuario@ccf.com'}
                        </p>
                        <span className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] text-2xs font-semibold uppercase tracking-wide">
                            <Shield size={9} /> Admin
                        </span>
                    </div>
                    <button
                        onClick={() => router.push('/plataforma/account')}
                        className="px-[calc(1rem+var(--density-pad-x-delta,0px))] py-[calc(0.5rem+var(--density-pad-y-delta,0px))] text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] border border-[hsl(var(--border))] rounded-md hover:border-[hsl(var(--primary))] transition-all"
                    >
                        Editar
                    </button>
                </motion.div>

                {/* Quick Theme Toggle */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 }}
                    className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm"
                >
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tema Visual y Accesibilidad</p>
                            <p className="text-xs text-[hsl(var(--text-secondary))]">
                                Acento activo: <span className="font-semibold text-[hsl(var(--text-primary))]">{currentAccent.label}</span> · Densidad: <span className="font-semibold text-[hsl(var(--text-primary))]">{currentDensity.label}</span> · Zoom: <span className="font-semibold text-[hsl(var(--text-primary))]">{zoomPercentage}%</span>
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setIsAppearanceOpen(true)}
                            className="text-2xs font-semibold text-[hsl(var(--primary))] hover:underline flex items-center gap-1.5 transition-colors"
                        >
                            <Palette size={13} />
                            <span>Abrir panel de apariencia</span>
                        </button>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => setTheme('day')}
                            className={clsx(
                                "flex flex-col items-center gap-2 py-[calc(0.5rem+var(--density-pad-y-delta,0px))] rounded-md border-2 transition-all text-xs font-semibold uppercase tracking-wide",
                                theme === 'day'
                                    ? "border-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]"
                                    : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]"
                            )}
                        >
                            <Sun size={18} />
                            Modo Día
                            {theme === 'day' && <Check size={10} className="text-[hsl(var(--primary))]" />}
                        </button>
                        <button
                            type="button"
                            onClick={() => setTheme('night')}
                            className={clsx(
                                "flex flex-col items-center gap-2 py-[calc(0.5rem+var(--density-pad-y-delta,0px))] rounded-md border-2 transition-all text-xs font-semibold uppercase tracking-wide",
                                theme === 'night'
                                    ? "border-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]"
                                    : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]"
                            )}
                        >
                            <Moon size={18} />
                            Modo Noche
                            {theme === 'night' && <Check size={10} className="text-[hsl(var(--primary))]" />}
                        </button>
                    </div>
                </motion.div>

                {/* Settings Groups */}
                {SETTINGS_GROUPS.map((group, gi) => (
                    <motion.div
                        key={group.title}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.08 + gi * 0.04 }}
                    >
                        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 ml-1">
                            {group.title}
                        </p>
                        <div className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-sm divide-y divide-[hsl(var(--border))] overflow-hidden">
                            {group.items.map((item, ii) => (
                                <button
                                    key={ii}
                                    type="button"
                                    onClick={() => {
                                        if (item.action === 'appearance') {
                                            setIsAppearanceOpen(true);
                                        } else if (item.href && item.href.startsWith('/')) {
                                            router.push(item.href);
                                        }
                                    }}
                                    className="w-full flex items-center gap-4 px-[calc(0.75rem+var(--density-pad-x-delta,0px))] py-[calc(0.375rem+var(--density-pad-y-delta,0px))] hover:bg-[hsl(var(--surface-2))] transition-all group text-left"
                                >
                                    <div className={clsx("size-9 rounded-md flex items-center justify-center shrink-0", COLOR_MAP[group.color])}>
                                        <item.icon size={16} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-base font-semibold text-[hsl(var(--text-primary))]">{item.label}</p>
                                        <p className="text-xs text-[hsl(var(--text-secondary))] truncate">{item.desc}</p>
                                    </div>
                                    <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0" />
                                </button>
                            ))}
                        </div>
                    </motion.div>
                ))}

                {/* Danger Zone */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--destructive)/0.2)] p-3 shadow-sm space-y-3"
                >
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--destructive))] mb-4">Zona de Peligro</p>
                    <button
                        onClick={() => { logout(); router.push('/login'); }}
                        className="w-full flex items-center gap-3 px-[calc(1rem+var(--density-pad-x-delta,0px))] py-[calc(0.75rem+var(--density-pad-y-delta,0px))] rounded-md text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] transition-all text-sm font-bold"
                    >
                        <LogOut size={16} /> Cerrar Sesión
                    </button>
                    <button className="w-full flex items-center gap-3 px-[calc(1rem+var(--density-pad-x-delta,0px))] py-[calc(0.75rem+var(--density-pad-y-delta,0px))] rounded-md text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] transition-all text-sm font-bold">
                        <Trash2 size={16} /> Eliminar mi cuenta
                    </button>
                </motion.div>

                <p className="text-center text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide pb-8">
                    {SITE_NAME} · Powered by Antigravity
                </p>
            </div>
        </div>
        <AppearanceDrawer
            isOpen={isAppearanceOpen}
            onClose={() => setIsAppearanceOpen(false)}
        />
        </WorkspaceLayout>
    );
}

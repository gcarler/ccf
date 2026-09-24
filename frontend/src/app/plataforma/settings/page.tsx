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

const SETTINGS_GROUPS = [
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
            { icon: Palette, label: "Tema Visual", desc: "Modo claro, oscuro o sistema", href: "/plataforma/theme" },
            { icon: Languages, label: "Idioma y Región", desc: "Español (Colombia)", href: "#idioma" },
            { icon: Monitor, label: "Densidad de UI", desc: "Compacto, normal o cómodo", href: "#densidad" },
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
    const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('system');

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
                        className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] border border-[hsl(var(--border))] rounded-md hover:border-[hsl(var(--primary))] transition-all"
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Tema Visual</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {([
                            { id: 'light', icon: Sun, label: 'Claro' },
                            { id: 'dark', icon: Moon, label: 'Oscuro' },
                            { id: 'system', icon: Monitor, label: 'Sistema' },
                        ] as const).map(t => (
                            <button
                                key={t.id}
                                onClick={() => setTheme(t.id)}
                                className={clsx(
                                    "flex flex-col items-center gap-2 py-1.5 rounded-md border-2 transition-all text-xs font-semibold uppercase tracking-wide",
                                    theme === t.id
                                        ? "border-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]"
                                        : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]"
                                )}
                            >
                                <t.icon size={18} />
                                {t.label}
                                {theme === t.id && <Check size={10} className="text-[hsl(var(--primary))]" />}
                            </button>
                        ))}
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
                                    onClick={() => item.href.startsWith('/') ? router.push(item.href) : null}
                                    className="w-full flex items-center gap-4 px-3 py-1.5 hover:bg-[hsl(var(--surface-2))] transition-all group text-left"
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
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] transition-all text-sm font-bold"
                    >
                        <LogOut size={16} /> Cerrar Sesión
                    </button>
                    <button className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] transition-all text-sm font-bold">
                        <Trash2 size={16} /> Eliminar mi cuenta
                    </button>
                </motion.div>

                <p className="text-center text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide pb-8">
                    {SITE_NAME} · Powered by Antigravity
                </p>
            </div>
        </div>
        </WorkspaceLayout>
    );
}

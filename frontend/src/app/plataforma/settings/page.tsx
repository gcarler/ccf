"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Settings, User, Bell, Lock, Palette, Globe, Shield,
    ChevronRight, Moon, Sun, Monitor, Check,
    Languages, Keyboard, Zap, LogOut, Trash2, Crown
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
            { icon: User, label: "Perfil Personal", desc: "Nombre, foto y datos personales", href: "/account" },
            { icon: Bell, label: "Notificaciones", desc: "Alertas, recordatorios y emails", href: "#notificaciones" },
            { icon: Lock, label: "Seguridad", desc: "Contraseña y autenticación", href: "#seguridad" },
        ]
    },
    {
        title: "Apariencia",
        color: "purple",
        items: [
            { icon: Palette, label: "Tema Visual", desc: "Modo claro, oscuro o sistema", href: "/theme" },
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
    blue: "bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400",
    purple: "bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400",
    emerald: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
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
            {/* Header */}
            <div className="sticky top-0 z-30 bg-white/80 dark:bg-[#0f1117]/80 backdrop-blur-xl border-b border-slate-200/60 dark:border-white/5">
                <div className="max-w-3xl mx-auto px-3 py-1.5 flex items-center gap-3">
                    <Settings size={18} className="text-slate-400" />
                    <h1 className="text-[13px] font-semibold uppercase tracking-wide text-slate-700 dark:text-slate-200">
                        Configuración
                    </h1>
                </div>
            </div>

            <div className="max-w-3xl mx-auto px-3 py-8 space-y-3">
                {/* Profile Card */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white dark:bg-[#1a1d27] rounded-lg border border-slate-200/60 dark:border-white/5 p-3 flex items-center gap-3 shadow-sm"
                >
                    <div className="size-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-500/20 shrink-0">
                        {(user as any)?.name?.[0] ?? 'A'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-base font-bold text-slate-800 dark:text-white truncate">
                            {(user as any)?.name ?? 'Usuario CCF'}
                        </p>
                        <p className="text-[11px] text-slate-400 font-medium truncate">
                            {(user as any)?.email ?? 'usuario@ccf.com'}
                        </p>
                        <span className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[9px] font-semibold uppercase tracking-wide">
                            <Shield size={9} /> Admin
                        </span>
                    </div>
                    <button
                        onClick={() => router.push('/account')}
                        className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-400 hover:text-blue-600 border border-slate-200 dark:border-white/10 rounded-md hover:border-blue-500/50 transition-all"
                    >
                        Editar
                    </button>
                </motion.div>

                {/* Quick Theme Toggle */}
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 }}
                    className="bg-white dark:bg-[#1a1d27] rounded-lg border border-slate-200/60 dark:border-white/5 p-3 shadow-sm"
                >
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-4">Tema Visual</p>
                    <div className="grid grid-cols-3 gap-3">
                        {([
                            { id: 'light', icon: Sun, label: 'Claro' },
                            { id: 'dark', icon: Moon, label: 'Oscuro' },
                            { id: 'system', icon: Monitor, label: 'Sistema' },
                        ] as const).map(t => (
                            <button
                                key={t.id}
                                onClick={() => setTheme(t.id)}
                                className={clsx(
                                    "flex flex-col items-center gap-2 py-1.5 rounded-md border-2 transition-all text-[11px] font-semibold uppercase tracking-wide",
                                    theme === t.id
                                        ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10 text-blue-600"
                                        : "border-slate-200 dark:border-white/5 text-slate-500 hover:border-slate-300 dark:hover:border-white/10"
                                )}
                            >
                                <t.icon size={18} />
                                {t.label}
                                {theme === t.id && <Check size={10} className="text-blue-500" />}
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
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3 ml-1">
                            {group.title}
                        </p>
                        <div className="bg-white dark:bg-[#1a1d27] rounded-lg border border-slate-200/60 dark:border-white/5 shadow-sm divide-y divide-slate-100 dark:divide-white/5 overflow-hidden">
                            {group.items.map((item, ii) => (
                                <button
                                    key={ii}
                                    onClick={() => item.href.startsWith('/') ? router.push(item.href) : null}
                                    className="w-full flex items-center gap-4 px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-all group text-left"
                                >
                                    <div className={clsx("size-9 rounded-md flex items-center justify-center shrink-0", COLOR_MAP[group.color])}>
                                        <item.icon size={16} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200">{item.label}</p>
                                        <p className="text-[11px] text-slate-400 truncate">{item.desc}</p>
                                    </div>
                                    <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500 transition-colors shrink-0" />
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
                    className="bg-white dark:bg-[#1a1d27] rounded-lg border border-rose-100 dark:border-rose-500/10 p-3 shadow-sm space-y-3"
                >
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-rose-400 mb-4">Zona de Peligro</p>
                    <button
                        onClick={() => { logout(); router.push('/login'); }}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all text-[12px] font-bold"
                    >
                        <LogOut size={16} /> Cerrar Sesión
                    </button>
                    <button className="w-full flex items-center gap-3 px-4 py-3 rounded-md text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all text-[12px] font-bold">
                        <Trash2 size={16} /> Eliminar mi cuenta
                    </button>
                </motion.div>

                <p className="text-center text-[10px] text-slate-300 dark:text-slate-700 font-bold uppercase tracking-wide pb-8">
                    CCF Platform v2.1.0 · Powered by Antigravity
                </p>
            </div>
        </div>
        </WorkspaceLayout>
    );
}


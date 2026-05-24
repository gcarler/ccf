"use client";

import React, { useState } from 'react';
import Image from 'next/image';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import {
    User, Mail, Shield, Palette, Bell, Save, Camera, ChevronRight, UserCircle,
    Fingerprint, Moon, Sun, Monitor, Globe, Lock, ShieldCheck, Smartphone, Layout,
    Sparkles, LogOut, Settings as SettingsIcon, Zap, Crown
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import WorkspaceLayout from '@/components/WorkspaceLayout';

export default function AccountSettingsPage() {
    const { user, logout } = useAuth();
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'appearance' | 'notifications'>('profile');
    const [isSaving, setIsSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const formData = {
        username: user?.username || '',
        email: user?.email || '',
        firstName: '',
        lastName: '',
        phone: ''
    };

    const tabs = [
        { id: 'profile', label: 'Mi Perfil', icon: UserCircle },
        { id: 'security', label: 'Seguridad', icon: Shield },
        { id: 'appearance', label: 'Apariencia', icon: Palette },
        { id: 'notifications', label: 'Notificaciones', icon: Bell },
    ];

    const handleSave = async () => {
        setIsSaving(true);
        setTimeout(() => {
            addToast("Preferencias guardadas exitosamente", "success");
            setIsSaving(false);
        }, 8000); // Artificial delay for shimmer effect
    };

    const sidebarSections = [
        {
            title: 'Cuenta',
            items: [
                { id: 'account-profile', label: 'Mi Perfil', href: '/account', icon: User },
                { id: 'account-ministry', label: 'Perfil Ministerial', href: '/account/ministry-profile', icon: Crown },
                { id: 'settings-general', label: 'Configuración', href: '/plataforma/settings', icon: SettingsIcon },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Cuenta" sidebarSections={sidebarSections}>
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF Platform', icon: Layout }, { label: 'Ajustes de Cuenta', icon: SettingsIcon }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                rightActions={
                    <button 
                        onClick={handleSave} disabled={isSaving}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSaving ? <><Sparkles size={14} className="animate-spin" /> Guardando</> : <><Save size={14} /> Guardar Cambios</>}
                    </button>
                }
            />

            {viewType === 'list' && (
                <main className="flex-1 overflow-y-auto p-4">
                    <div className="mx-auto max-w-4xl space-y-4">
                        {tabs.map((tab) => (
                            <button key={tab.id} onClick={() => setActiveTab(tab.id as typeof activeTab)} className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left dark:border-white/10 dark:bg-white/5">
                                <div className="flex items-center gap-4">
                                    <tab.icon size={20} className="text-blue-600" />
                                    <div>
                                        <h3 className="font-bold text-slate-900 dark:text-white">{tab.label}</h3>
                                        <p className="mt-1 text-sm text-slate-500">Configurar {tab.label.toLowerCase()}</p>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </main>
            )}

            {viewType === 'table' && (
                <main className="flex-1 overflow-y-auto p-4">
                    <div className="mx-auto max-w-4xl overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                <tr><th className="px-3 py-1.5">Sección</th><th className="px-3 py-1.5">Estado</th><th className="px-3 py-1.5">Acción</th></tr>
                            </thead>
                            <tbody>
                                {tabs.map((tab) => (
                                    <tr key={tab.id} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-3 py-1.5 font-bold text-slate-900 dark:text-white">{tab.label}</td>
                                        <td className="px-3 py-1.5 text-slate-500">{activeTab === tab.id ? 'Activa' : 'Disponible'}</td>
                                        <td className="px-3 py-1.5"><button onClick={() => setActiveTab(tab.id as typeof activeTab)} className="text-xs font-semibold uppercase tracking-wide text-blue-600">Abrir</button></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </main>
            )}

            {viewType === 'grid' && (
            <div className="flex-1 flex overflow-hidden">
                {/* Internal Sidebar 3.0 */}
                <aside className="w-72 lg:w-80 border-r border-slate-100 dark:border-white/5 bg-slate-50/30 dark:bg-black/10 p-3 space-y-1 shrink-0 relative z-10">
                    <div className="flex items-center gap-2 font-semibold text-slate-400 uppercase tracking-wide mb-3 mt-2">
                        <Zap size={12} className="text-blue-500" /> Configuración Central
                    </div>
                    {tabs.map((tab) => (
                        <button
                            key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                            className={clsx(
                                "w-full flex items-center gap-4 px-3 py-1.5 rounded-lg font-semibold transition-all group relative overflow-hidden",
                                activeTab === tab.id 
                                    ? "bg-white dark:bg-white/5 text-blue-600 dark:text-white shadow-[var(--shadow-premium)] border border-slate-200 dark:border-white/10" 
                                    : "text-slate-500 hover:bg-white/50 dark:hover:bg-white/5"
                            )}
                        >
                            {activeTab === tab.id && <div className="absolute left-0 top-4 bottom-4 w-1 bg-blue-600 rounded-full" />}
                            <tab.icon size={20} strokeWidth={activeTab === tab.id ? 2.5 : 2} className={clsx("transition-transform group-hover:scale-110", activeTab === tab.id ? "text-blue-600" : "text-slate-400")} />
                            {tab.label}
                        </button>
                    ))}

                    <div className="pt-10 mt-3 border-t border-slate-100 dark:border-white/5">
                        <button onClick={logout} className="w-full flex items-center gap-4 px-3 py-1.5 rounded-lg font-semibold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all group">
                            <LogOut size={20} className="group-hover:-translate-x-1 transition-transform" /> Cerrar Sesión
                        </button>
                    </div>
                </aside>

                {/* Content Area 3.0 */}
                <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 bg-white dark:bg-[#1e1f21] relative">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f003_0%,_transparent_50%)] pointer-events-none" />
                    
 <div className="w-full relative z-10">
                        <AnimatePresence mode="wait">
                            {activeTab === 'profile' && (
                                <motion.div 
                                    key="profile" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                    className="space-y-3"
                                >
                                    {/* Profile Hero Card */}
                                    <section className="flex flex-col md:flex-row items-center gap-3 p-4 bg-slate-50 dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/5 shadow-sm group">
                                        <div className="relative group cursor-pointer">
                                            <div className="size-10 rounded-lg bg-white dark:bg-white/5 border-2 border-slate-200 dark:border-white/10 flex items-center justify-center overflow-hidden transition-all group-hover:border-blue-500 group-hover:shadow-2xl group-hover:scale-105 duration-500">
                                                <Image src={`https://ui-avatars.com/api/?name=${user?.username}&background=2563eb&color=fff&size=128`} alt="Avatar" width={128} height={128} unoptimized />
                                            </div>
                                            <div className="absolute -bottom-2 -right-2 size-10 bg-blue-600 text-white rounded-lg flex items-center justify-center shadow-2xl border-4 border-white dark:border-[#1e1f21] group-hover:scale-110 transition-transform">
                                                <Camera size={18} />
                                            </div>
                                        </div>
                                        <div className="space-y-2 text-center md:text-left flex-1 min-w-0">
                                            <h3 className="text-xl font-bold text-slate-800 dark:text-white tracking-tighter">Tu Perfil Público</h3>
                                            <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-sm">Esta es tu identidad dentro de la comunidad CCF.</p>
                                            <div className="flex flex-wrap justify-center md:justify-start gap-2 pt-4">
                                                <div className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg text-[10px] font-semibold uppercase tracking-wide border border-blue-100 dark:border-blue-900/50 flex items-center gap-2"><ShieldCheck size={12} /> {user?.role || 'Miembro'}</div>
                                                <div className="px-3 py-1 bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 rounded-lg text-[10px] font-semibold uppercase tracking-wide border border-slate-200 dark:border-white/10 flex items-center gap-2"><Globe size={12} /> Sede Central</div>
                                            </div>
                                        </div>
                                    </section>

                                    <section className="space-y-3">
                                        <h4 className="font-semibold text-slate-400 uppercase tracking-wide px-4">Información Personal</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            <InputField label="Nombre de Usuario" icon={User} value={formData.username} />
                                            <InputField label="Correo Electrónico" icon={Mail} value={formData.email} />
                                            <InputField label="Nombre Completo" value={formData.firstName} placeholder="Ingresa tu nombre..." />
                                            <InputField label="Teléfono de Contacto" icon={Smartphone} value={formData.phone} placeholder="+1 234 567 890" />
                                        </div>
                                    </section>

                                    <section className="p-4 bg-gradient-to-br from-slate-900 to-[#1e1f21] rounded-lg border border-white/5 text-white flex items-center justify-between shadow-2xl relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 w-64 h-48 bg-blue-600/10 rounded-full blur-[100px] group-hover:scale-110 transition-transform duration-1000" />
                                        <div className="relative z-10 flex items-center gap-3">
                                            <div className="size-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center text-blue-400 shadow-xl group-hover:rotate-12 transition-transform duration-500"><Smartphone size={32} /></div>
                                            <div>
                                                <h4 className="text-xl font-bold tracking-tight">Seguridad Móvil</h4>
                                                <p className="text-slate-400 text-sm font-medium">Verifica tu número para habilitar alertas pastorales por WhatsApp.</p>
                                            </div>
                                        </div>
                                        <button className="relative z-10 px-4 py-1.5 bg-white text-slate-900 rounded-lg font-black text-[11px] uppercase tracking-wide hover:scale-105 active:scale-95 transition-all shadow-xl">Verificar Ahora</button>
                                    </section>
                                </motion.div>
                            )}

                            {activeTab === 'security' && (
                                <motion.div 
                                    key="security" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                    className="space-y-3"
                                >
                                    <div className="p-4 bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                        <div className="flex items-center gap-4">
                                            <div className="size-7 rounded-lg bg-rose-50 dark:bg-rose-900/30 text-rose-500 flex items-center justify-center shadow-inner"><Lock size={24} /></div>
                                            <h3 className="text-lg font-bold tracking-tighter">Cambiar Contraseña</h3>
                                        </div>
                                        <div className="space-y-3">
                                            <InputField type="password" label="Contraseña Actual" placeholder="••••••••" />
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                <InputField type="password" label="Nueva Contraseña" placeholder="Mínimo 8 caracteres" />
                                                <InputField type="password" label="Confirmar Nueva" placeholder="Repite la contraseña" />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="p-4 bg-blue-50/50 dark:bg-blue-500/5 rounded-lg border border-blue-100 dark:border-blue-500/20 flex flex-col md:flex-row items-center justify-between gap-3 group">
                                        <div className="flex items-center gap-3">
                                            <div className="size-8 rounded-lg bg-white dark:bg-white/10 flex items-center justify-center text-blue-600 shadow-xl group-hover:scale-110 transition-transform"><Fingerprint size={32} /></div>
                                            <div>
                                                <h4 className="text-xl font-bold tracking-tight">Doble Factor (2FA)</h4>
                                                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Recomendado para cuentas administrativas y docentes.</p>
                                            </div>
                                        </div>
                                        <div className="h-8 w-14 bg-slate-200 dark:bg-white/10 rounded-full relative cursor-pointer group-hover:bg-blue-600/20 transition-all p-1">
                                            <div className="size-6 bg-white rounded-full shadow-lg" />
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeTab === 'appearance' && (
                                <motion.div 
                                    key="appearance" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                                    className="space-y-3"
                                >
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        <ThemeCard label="Modo Claro" icon={Sun} active />
                                        <ThemeCard label="Modo Noche" icon={Moon} />
                                        <ThemeCard label="Automático" icon={Monitor} />
                                    </div>

                                    <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/5 space-y-3">
                                        <h3 className="font-semibold text-slate-400 uppercase tracking-wide">Idioma y Localización</h3>
                                        <div className="flex items-center justify-between p-3 bg-white dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10 shadow-sm cursor-pointer hover:border-blue-500/30 transition-all group">
                                            <div className="flex items-center gap-4">
                                                <Globe size={24} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
                                                <div>
                                                    <p className="text-sm font-bold tracking-tight">Español (Latinoamérica)</p>
                                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide mt-0.5">Predeterminado</p>
                                                </div>
                                            </div>
                                            <ChevronRight size={20} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>
            </div>
            )}
        </div>
        </WorkspaceLayout>
    );
}

function InputField({ label, icon: Icon, value, placeholder, type = "text" }: any) {
    return (
        <div className="space-y-3">
            <label className="font-semibold text-slate-400 uppercase tracking-wide ml-2 leading-none block">{label}</label>
            <div className="relative group">
                {Icon && <Icon className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" size={18} />}
                <input
                    type={type} defaultValue={value} placeholder={placeholder}
                    className={clsx(
                        "w-full bg-slate-50 dark:bg-black/40 border border-slate-200 dark:border-white/5 rounded-lg py-1.5 pr-6 text-sm font-bold text-slate-700 dark:text-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500/50 focus:bg-white dark:focus:bg-black/60 outline-none transition-all",
                        Icon ? "pl-14" : "pl-6"
                    )}
                />
            </div>
        </div>
    );
}

function ThemeCard({ label, icon: Icon, active }: any) {
    return (
        <div className={clsx(
            "p-4 rounded-lg border-2 cursor-pointer transition-all flex flex-col items-center gap-3 group relative overflow-hidden",
            active 
                ? "border-blue-600 bg-blue-50/50 dark:bg-blue-500/10 shadow-2xl shadow-blue-500/10 scale-[1.02]" 
                : "border-slate-100 dark:border-white/5 hover:border-blue-200 hover:scale-[1.02]"
        )}>
            {active && <div className="absolute top-4 right-4 size-2 rounded-full bg-blue-600 shadow-[0_0_8px_rgba(59,130,246,0.8)]" />}
            <div className={clsx(
                "size-8 rounded-lg flex items-center justify-center transition-all duration-500 group-hover:rotate-12",
                active ? "bg-blue-600 text-white shadow-2xl" : "bg-slate-100 dark:bg-white/5 text-slate-400 group-hover:text-blue-500"
            )}>
                <Icon size={32} />
            </div>
            <span className={clsx("text-[11px] font-semibold uppercase tracking-wide", active ? "text-blue-600 dark:text-white" : "text-slate-500")}>{label}</span>
        </div>
    );
}


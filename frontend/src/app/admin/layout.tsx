"use client";

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import {
    LayoutDashboard,
    MessageSquare,
    CheckSquare,
    Users,
    Settings,
    Bell,
    Search,
    LogOut,
    ArrowLeft,
    TrendingUp,
    FileText,
    Globe
} from 'lucide-react';

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { user, logout } = useAuth();

    return (
        <ProtectedRoute allowedRoles={['admin', 'coordinador', 'docente']}>
            <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 flex overflow-hidden">

                {/* Desktop Sidebar */}
                <aside className="hidden lg:flex w-72 shrink-0 flex-col bg-white/50 dark:bg-slate-900/50 backdrop-blur-3xl border-r border-slate-200 dark:border-white/5 relative z-20 shadow-2xl">
                    <div className="p-8 pb-4">
                        <div className="flex items-center gap-4 mb-10">
                            <div className="size-12 rounded-full bg-gradient-to-tr from-primary to-blue-400 flex items-center justify-center text-white shadow-lg shadow-primary/20">
                                <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>admin_panel_settings</span>
                            </div>
                            <div>
                                <span className="font-black text-xl tracking-tight block leading-none text-slate-900 dark:text-white">Panel</span>
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mt-1 block">Gestión Central</span>
                            </div>
                        </div>

                        <nav className="space-y-2">
                            {[
                                { name: 'Dashboard', icon: LayoutDashboard, href: '/admin' },
                                { name: 'Comunidad', icon: Users, href: '/admin/members' },
                                { name: 'Finanzas', icon: TrendingUp, href: '/admin/finance' },
                                { name: 'Actas', icon: CheckSquare, href: '/admin/actas' },
                                { name: 'Calificar', icon: FileText, href: '/admin/submissions' },
                                { name: 'Moderación', icon: MessageSquare, href: '/admin/testimonials' },
                                { name: 'Gestor Web', icon: Globe, href: '/admin/cms' },
                            ].map((item) => (
                                <Link
                                    key={item.name}
                                    href={item.href}
                                    className={`flex items-center gap-4 p-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all hover:bg-white dark:hover:bg-white/5 hover:shadow-sm group border border-transparent hover:border-slate-200 dark:hover:border-white/5 ${item.name === 'Dashboard' ? 'bg-white dark:bg-white/5 text-primary border-slate-200 dark:border-white/5 shadow-sm' : 'text-slate-500'}`}
                                >
                                    <item.icon size={18} className="group-hover:scale-110 transition-transform" />
                                    <span>{item.name}</span>
                                </Link>
                            ))}
                        </nav>
                    </div>

                    <div className="mt-auto p-8 space-y-4">
                        <Link href="/" className="flex items-center gap-4 p-4 rounded-2xl text-slate-500 font-bold text-xs transition-all hover:bg-slate-100 dark:hover:bg-white/5 border border-transparent">
                            <ArrowLeft size={16} />
                            <span>Volver al Inicio</span>
                        </Link>
                        <button onClick={logout} className="w-full flex items-center gap-4 p-4 rounded-2xl text-rose-500 font-bold text-xs transition-all hover:bg-rose-50 dark:hover:bg-rose-500/10 border border-transparent">
                            <LogOut size={16} />
                            <span>Cerrar Sesión</span>
                        </button>
                    </div>
                </aside>

                {/* Main Dashboard Area */}
                <div className="flex-1 flex flex-col min-w-0 relative h-screen">

                    {/* Top Header */}
                    <header className="h-24 border-b border-slate-200 dark:border-white/5 flex items-center justify-between px-10 bg-white/30 dark:bg-slate-900/30 backdrop-blur-xl sticky top-0 z-10">
                        <div className="flex-1 max-w-md">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors" size={18} />
                                <input
                                    type="text"
                                    placeholder="Buscar miembros, reportes..."
                                    className="w-full h-12 pl-12 pr-4 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-white/10 focus:ring-2 focus:ring-primary focus:border-primary transition-all text-sm font-medium shadow-sm"
                                />
                            </div>
                        </div>

                        <div className="flex items-center gap-6">
                            <button className="relative size-12 rounded-2xl bg-white dark:bg-slate-800 flex items-center justify-center text-slate-500 hover:text-primary transition-all shadow-sm border border-slate-200 dark:border-white/10">
                                <Bell size={20} />
                                <span className="absolute top-3 right-3 size-2.5 bg-rose-500 rounded-full border-2 border-white dark:border-slate-800"></span>
                            </button>
                            <div className="flex items-center gap-4 pl-6 border-l border-slate-200 dark:border-white/10">
                                <div className="text-right hidden sm:block">
                                    <p className="font-bold text-sm leading-none text-slate-900 dark:text-white">{user?.username || 'Admin'}</p>
                                    <p className="text-[10px] font-black text-primary uppercase tracking-widest mt-1 capitalize">{user?.role || 'Administrador'}</p>
                                </div>
                                <div className="size-12 rounded-full bg-slate-200 dark:bg-slate-700 border-2 border-white dark:border-white/10 shadow-md overflow-hidden">
                                    <img src={`https://ui-avatars.com/api/?name=${user?.username || 'A'}&background=1973f0&color=fff`} alt="Admin Profile" className="w-full h-full object-cover" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Content Scrollable Area */}
                    <main className="flex-1 overflow-y-auto p-6 lg:p-10 hide-scrollbar relative bg-slate-50 dark:bg-transparent">
                        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent opacity-80 blur-3xl rounded-full mix-blend-screen pointer-events-none"></div>
                        <div className="max-w-[1400px] mx-auto relative z-10">
                            {children}
                        </div>
                    </main>
                </div>

                {/* Mobile Navigation */}
                <nav className="lg:hidden fixed bottom-0 left-0 right-0 h-20 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border-t border-slate-200 dark:border-white/10 flex justify-around items-center z-[100] pb-2 px-2">
                    {[
                        { icon: 'dashboard', href: '/admin', active: true },
                        { icon: 'groups', href: '/admin/members', active: false },
                        { icon: 'add_circle', href: '#', active: false, special: true },
                        { icon: 'checklist', href: '/admin/submissions', active: false },
                        { icon: 'settings', href: '#', active: false }
                    ].map((item, i) => (
                        item.special ? (
                            <div key={i} className="-mt-10 bg-primary size-14 rounded-full flex items-center justify-center shadow-lg shadow-primary/40 text-white cursor-pointer active:scale-95 transition-transform border-4 border-slate-50 dark:border-slate-950">
                                <span className="material-symbols-outlined text-[32px]">{item.icon}</span>
                            </div>
                        ) : (
                            <Link key={i} href={item.href} className={`flex flex-col items-center gap-1 ${item.active ? 'text-primary' : 'text-slate-400'}`}>
                                <span className={`material-symbols-outlined text-[24px] ${item.active ? 'fill-1' : ''}`} style={item.active ? { fontVariationSettings: "'FILL' 1" } : {}}>{item.icon}</span>
                                <span className="text-[9px] font-bold uppercase tracking-tight">{item.icon === 'dashboard' ? 'Inicio' : item.icon === 'groups' ? 'Miembros' : item.icon === 'checklist' ? 'Tareas' : 'Ajustes'}</span>
                            </Link>
                        )
                    ))}
                </nav>
            </div>
        </ProtectedRoute>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
    GraduationCap, 
    BookOpen, 
    Award, 
    Settings, 
    LayoutDashboard, 
    ArrowLeft,
    Shield,
    Users,
    Search,
    Bell
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';

export default function AcademyLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { user } = useAuth();

    return (
        <ProtectedRoute>
            <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 flex overflow-hidden">
                
                {/* Desktop Sidebar */}
                <aside className="hidden lg:flex w-80 shrink-0 flex-col bg-white dark:bg-slate-900/40 backdrop-blur-2xl border-r border-slate-200 dark:border-white/5 relative z-20">
                    <div className="p-8">
                        <div className="flex items-center gap-4 mb-12">
                            <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-inner">
                                <GraduationCap size={28} />
                            </div>
                            <div>
                                <span className="font-black text-2xl tracking-tight block leading-none">Academia</span>
                                <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mt-1 block">Ruta de Formación</span>
                            </div>
                        </div>

                        <nav className="space-y-2">
                            {[
                                { name: 'Resumen', icon: LayoutDashboard, href: '/academy' },
                                { name: 'Cursos', icon: BookOpen, href: '/academy' },
                                { name: 'Mis Logros', icon: Award, href: '#' },
                                { name: 'Comunidad', icon: Users, href: '#' },
                            ].map((item) => (
                                <Link 
                                    key={item.name} 
                                    href={item.href} 
                                    className={`flex items-center gap-4 p-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition-all hover:bg-primary/5 hover:text-primary group border border-transparent hover:border-primary/10 ${item.name === 'Resumen' ? 'bg-primary/5 text-primary border-primary/10' : 'text-slate-500'}`}
                                >
                                    <item.icon size={18} className="group-hover:scale-110 transition-transform" />
                                    <span>{item.name}</span>
                                </Link>
                            ))}
                        </nav>
                    </div>

                    <div className="mt-auto p-8 space-y-6">
                        <div className="p-6 rounded-3xl bg-gradient-to-br from-primary to-blue-600 text-white shadow-xl shadow-primary/20 relative overflow-hidden group">
                            <div className="absolute -right-4 -top-4 opacity-20 rotate-12 group-hover:rotate-0 transition-transform">
                                <Sparkles size={80} />
                            </div>
                            <p className="text-[10px] font-black uppercase tracking-widest mb-2 opacity-80">Próximo Nivel</p>
                            <p className="font-bold text-lg mb-4">Liderazgo II</p>
                            <div className="h-1.5 w-full bg-white/20 rounded-full overflow-hidden">
                                <div className="h-full bg-white rounded-full shadow-[0_0_8px_white]" style={{ width: '65%' }}></div>
                            </div>
                        </div>

                        <Link href="/" className="flex items-center gap-4 p-4 rounded-2xl text-slate-400 font-black uppercase tracking-widest text-[10px] transition-all hover:bg-rose-500/10 hover:text-rose-500 border border-transparent">
                            <ArrowLeft size={16} />
                            <span>Volver al Inicio</span>
                        </Link>
                    </div>
                </aside>

                {/* Main Dashboard Area */}
                <div className="flex-1 flex flex-col min-w-0 relative h-screen">
                    
                    {/* Top Header / Search */}
                    <header className="h-24 border-b border-slate-200 dark:border-white/5 flex items-center justify-between px-10 bg-white/50 dark:bg-transparent backdrop-blur-md sticky top-0 z-10">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors" size={18} />
                                <input 
                                    type="text" 
                                    placeholder="Buscar lecciones, materiales o cursos..." 
                                    className="w-full h-12 pl-12 pr-4 bg-slate-100 dark:bg-white/5 rounded-xl border-0 ring-1 ring-slate-200 dark:ring-white/5 focus:ring-2 focus:ring-primary transition-all text-sm font-medium"
                                />
                            </div>
                        </div>

                        <div className="flex items-center gap-6">
                            <button className="relative size-12 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 hover:text-primary transition-all">
                                <Bell size={20} />
                                <span className="absolute top-3 right-3 size-2 bg-rose-500 rounded-full border-2 border-white dark:border-slate-900"></span>
                            </button>
                            <div className="flex items-center gap-4 pl-6 border-l border-slate-200 dark:border-white/10">
                                <div className="text-right hidden sm:block">
                                    <p className="font-bold text-sm leading-none">{user?.username || 'Usuario'}</p>
                                    <p className="text-[10px] font-black text-primary uppercase tracking-widest mt-1 capitalize">{user?.role || 'Estudiante'}</p>
                                </div>
                                <div className="size-12 rounded-2xl bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800 border-2 border-white dark:border-white/5 shadow-lg overflow-hidden">
                                    <img src={`https://ui-avatars.com/api/?name=${user?.username || 'U'}&background=1973f0&color=fff`} alt="Profile" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Content Scrollable Area */}
                    <main className="flex-1 overflow-y-auto p-10 hide-scrollbar bg-slate-50/50 dark:bg-transparent">
                        <div className="max-w-[1400px] mx-auto">
                            {children}
                        </div>
                    </main>
                </div>

                {/* Mobile Navigation (Bottom Nav) */}
                <nav className="lg:hidden fixed bottom-6 left-6 right-6 h-20 bg-white/70 dark:bg-slate-900/80 backdrop-blur-3xl px-6 rounded-[2.5rem] border border-white/40 dark:border-white/10 shadow-2xl flex justify-between items-center z-[100]">
                        <Link href="/" className="flex flex-col items-center gap-1 text-slate-400">
                            <span className="material-symbols-outlined text-[30px]">home</span>
                            <span className="text-[8px] font-black uppercase tracking-widest">Inicio</span>
                        </Link>
                        <Link href="/academy" className="flex flex-col items-center gap-1 text-primary">
                            <span className="material-symbols-outlined text-[30px] fill-1" style={{ fontVariationSettings: "'FILL' 1" }}>school</span>
                            <span className="text-[8px] font-black uppercase tracking-widest">Academia</span>
                        </Link>
                        <Link href="/academy/profile" className="flex flex-col items-center gap-1 text-slate-400">
                            <span className="material-symbols-outlined text-[30px]">person</span>
                            <span className="text-[8px] font-black uppercase tracking-widest">Perfil</span>
                        </Link>
                </nav>
            </div>
        </ProtectedRoute>
    );
}

import { Sparkles } from 'lucide-react';

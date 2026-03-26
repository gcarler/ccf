"use client";

import React, { useState, useEffect } from 'react';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import ProtectedRoute from '@/components/ProtectedRoute';
import Tooltip from '@/components/ui/Tooltip';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
    Search,
    Bell,
    Settings,
    Layout,
    PanelLeft,
    PanelLeftClose,
    Sparkles,
    Sun,
    Moon,
    User,
    LogOut,
    ExternalLink,
    ShieldCheck
} from 'lucide-react';
import { useTheme } from '@/app/theme/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import * as Popover from '@radix-ui/react-popover';
import { usePathname } from 'next/navigation';

export default function WorkspaceLayout({
    children,
    sidebarTitle,
    sidebarSections = []
}: {
    children: React.ReactNode,
    sidebarTitle: string,
    sidebarSections?: any[]
}) {
    const { theme, toggleTheme } = useTheme();
    const { user, logout } = useAuth();
    const pathname = usePathname();
    const [sidebarMode, setSidebarMode] = useState<'full' | 'mini' | 'hidden'>('full');
    const [showInbox, setShowInbox] = useState(false);
    const [showAiChat, setShowAiChat] = useState(false);

    useEffect(() => {
        const savedMode = localStorage.getItem('ccf_sidebar_mode') as 'full' | 'mini' | 'hidden';
        if (savedMode) setSidebarMode(savedMode);
    }, []);

    const cycleSidebar = () => {
        setSidebarMode(prev => {
            const next = prev === 'full' ? 'mini' : prev === 'mini' ? 'hidden' : 'full';
            localStorage.setItem('ccf_sidebar_mode', next);
            return next;
        });
    };

    return (
        <ProtectedRoute>
            <div className="flex h-screen w-full bg-white dark:bg-[#1e1f21] overflow-hidden transition-colors duration-500 font-sans">
                
                <AnimatePresence mode="popLayout">
                    {sidebarMode !== 'hidden' && (
                        <motion.div 
                            initial={{ x: -100, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -100, opacity: 0 }}
                            className="flex shrink-0 z-50"
                        >
                            <WorkspaceMiniSidebar isMini={sidebarMode === 'mini'} />
                            {sidebarMode === 'full' && (
                                <WorkspaceMainSidebar title={sidebarTitle} sections={sidebarSections} />
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="flex-1 flex flex-col min-w-0 relative">
                    <header className="h-12 border-b border-slate-100 dark:border-white/5 flex items-center justify-between px-4 bg-white dark:bg-[#1e1f21] shrink-0 z-40">
                        <div className="flex items-center gap-3">
                            <Tooltip content="Cambiar navegación">
                                <button onClick={cycleSidebar} className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-500 transition-all border border-transparent">
                                    {sidebarMode === 'full' ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
                                </button>
                            </Tooltip>
                            
                            <div className="flex items-center gap-2">
                                <div className="size-6 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm">
                                    <Layout size={14} />
                                </div>
                                <span className="text-[13px] font-black text-slate-800 dark:text-slate-200 tracking-tight">CCF Platform</span>
                            </div>
                        </div>

                        <div className="hidden md:flex items-center bg-slate-100 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-lg px-3 py-1.5 w-64 lg:w-96 cursor-pointer hover:bg-slate-200 transition-all group">
                            <Search size={14} className="text-slate-400 group-hover:text-blue-500" />
                            <span className="text-[11px] font-bold text-slate-400 ml-2">Presiona Ctrl+K para buscar...</span>
                        </div>

                        <div className="flex items-center gap-1">
                            <Tooltip content="Alternar Tema">
                                <HeaderIcon icon={theme === 'night' ? Sun : Moon} onClick={toggleTheme} />
                            </Tooltip>
                            
                            <div className="relative group/bell">
                                <Tooltip content="Notificaciones">
                                    <HeaderIcon icon={Bell} onClick={() => setShowInbox(!showInbox)} />
                                </Tooltip>
                                <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-white dark:border-[#1e1f21]"></span>
                            </div>

                            <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                            
                            {/* Profile Popover */}
                            <Popover.Root>
                                <Popover.Trigger asChild>
                                    <button className="size-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-[10px] font-black text-white cursor-pointer shadow-lg active:scale-95 transition-all">
                                        {user?.username?.substring(0, 2).toUpperCase() || 'U'}
                                    </button>
                                </Popover.Trigger>
                                <Popover.Portal>
                                    <Popover.Content className="z-[10000] w-64 bg-white dark:bg-[#1e1f21] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/10 p-2 animate-in fade-in zoom-in-95 duration-200" align="end" sideOffset={8}>
                                        <div className="p-4 space-y-4">
                                            <div className="flex items-center gap-3">
                                                <div className="size-12 rounded-2xl bg-blue-600 flex items-center justify-center text-xl font-black text-white shadow-xl">
                                                    {user?.username?.substring(0, 1).toUpperCase()}
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-black text-slate-800 dark:text-white truncate tracking-tight">{user?.username}</p>
                                                    <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest flex items-center gap-1"><ShieldCheck size={10} /> {user?.role || 'Miembro'}</p>
                                                </div>
                                            </div>
                                            <div className="h-[1px] bg-slate-100 dark:bg-white/5 w-full" />
                                            <div className="space-y-1">
                                                <ProfileMenuItem icon={User} label="Mi Perfil" href="/account" />
                                                <ProfileMenuItem icon={Settings} label="Ajustes de Workspace" href="/admin/settings" />
                                                <ProfileMenuItem icon={ExternalLink} label="Ayuda y Feedback" href="/support" />
                                            </div>
                                            <div className="h-[1px] bg-slate-100 dark:bg-white/5 w-full" />
                                            <button 
                                                onClick={logout}
                                                className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all text-[12px] font-bold"
                                            >
                                                <LogOut size={16} /> Cerrar Sesión
                                            </button>
                                        </div>
                                    </Popover.Content>
                                </Popover.Portal>
                            </Popover.Root>
                        </div>
                    </header>

                    <main className="flex-1 overflow-y-auto scrollbar-thin bg-white dark:bg-[#1e1f21]">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={pathname}
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -5 }}
                                transition={{ duration: 0.2 }}
                                className="h-full"
                            >
                                {children}
                            </motion.div>
                        </AnimatePresence>
                    </main>
                </div>

                <WorkspaceInbox isOpen={showInbox} onClose={() => setShowInbox(false)} />

                <button 
                    onClick={() => setShowAiChat(true)}
                    className="fixed bottom-6 right-6 size-12 rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center shadow-2xl hover:scale-110 active:scale-90 transition-all z-50 group overflow-hidden"
                >
                    <div className="absolute inset-0 bg-gradient-to-tr from-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <Sparkles size={20} className="relative z-10" />
                </button>
            </div>
        </ProtectedRoute>
    );
}

function HeaderIcon({ icon: Icon, onClick }: { icon: any, onClick?: () => void }) {
    return (
        <button onClick={onClick} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-all active:scale-95">
            <Icon size={18} />
        </button>
    );
}

function ProfileMenuItem({ icon: Icon, label, href }: any) {
    return (
        <Link href={href} className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-all text-[12px] font-bold group">
            <Icon size={16} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
            {label}
        </Link>
    );
}

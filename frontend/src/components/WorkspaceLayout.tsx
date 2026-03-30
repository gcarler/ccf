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
    ShieldCheck,
    PanelLeftOpen,
    X,
    GripVertical,
    ChevronLeft
} from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '@/app/theme/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import * as Popover from '@radix-ui/react-popover';
import { usePathname, useRouter } from 'next/navigation';
import { useCreation } from '@/context/CreationContext';
import UniversalCreationModal from '@/components/ui/UniversalCreationModal';

interface WorkspaceLayoutProps {
    children: React.ReactNode;
    sidebarTitle?: string;
    sidebarSections?: any[];
    allowedRoles?: string[];
    // Stack Support
    depth?: number;
    parentTitle?: string;
    onBack?: () => void;
    customSidebar?: React.ReactNode;
    hideMainSidebar?: boolean;
}

export default function WorkspaceLayout({ 
    children, 
    sidebarTitle = "CCF Platform", 
    sidebarSections: _sidebarSections,
    allowedRoles,
    depth = 1,
    parentTitle,
    onBack,
    customSidebar,
    hideMainSidebar = false
}: WorkspaceLayoutProps) {
    const sidebarSections = _sidebarSections && _sidebarSections.length > 0 ? _sidebarSections : [{ label: 'General' }];
    const { theme, toggleTheme } = useTheme();
    const { user, logout } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const [blackSidebarVisible, setBlackSidebarVisible] = useState(true);
    const [graySidebarMode, setGraySidebarMode] = useState<'full' | 'mini' | 'hidden'>('full');
    const [showInbox, setShowInbox] = useState(false);
    const { isModalOpen, closeModal, defaultType } = useCreation();

    useEffect(() => {
        const savedBlack = localStorage.getItem('ccf_black_sidebar') !== 'false';
        setBlackSidebarVisible(savedBlack);
        const savedGray = localStorage.getItem('ccf_gray_sidebar') as 'full' | 'mini' | 'hidden';
        if (savedGray) setGraySidebarMode(savedGray);
    }, []);

    const handleSetGrayMode = (mode: 'full' | 'mini' | 'hidden') => {
        setGraySidebarMode(mode);
        localStorage.setItem('ccf_gray_sidebar', mode);
    };

    const handleSetBlackMode = (visible: boolean) => {
        setBlackSidebarVisible(visible);
        localStorage.setItem('ccf_black_sidebar', visible ? 'true' : 'false');
    };

    return (
        <ProtectedRoute allowedRoles={allowedRoles}>
            <div className="flex h-screen w-full bg-slate-50 dark:bg-[#111213] overflow-hidden transition-colors duration-500 font-sans relative">
                
                {/* GLOBAL CREATION MODAL */}
                <UniversalCreationModal 
                    isOpen={isModalOpen}
                    onClose={closeModal}
                    initialType={defaultType}
                />

                {/* LAYER 1: GLOBAL DOMAINS (BLACK) */}
                <AnimatePresence mode="popLayout">
                    {blackSidebarVisible && (
                        <motion.div 
                            initial={{ x: -80, width: 0, opacity: 0 }}
                            animate={{ x: 0, width: 'auto', opacity: 1 }}
                            exit={{ x: -80, width: 0, opacity: 0 }}
                            className="flex shrink-0 z-50 h-[100dvh] py-[10vh] pl-4"
                        >
                            <WorkspaceMiniSidebar onHide={() => handleSetBlackMode(false)} />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* LAYER 2: WORKSPACE (WHITE/GRAY) */}
                <main className="flex-1 flex flex-col min-w-0 relative">
                    <div className="flex h-full w-full">
                        {/* Sidebar Gray: Sections */}
                        {!hideMainSidebar && (
                            <div className={clsx(
                                "h-full shrink-0 overflow-hidden transition-all duration-300",
                                graySidebarMode === 'full' ? "w-72" : graySidebarMode === 'mini' ? "w-20" : "w-0"
                            )}>
                                {customSidebar || (
                                    <WorkspaceMainSidebar 
                                        title={sidebarTitle} 
                                        sections={sidebarSections} 
                                        isMini={graySidebarMode === 'mini'}
                                    />
                                )}
                            </div>
                        )}

                        {/* Content Area */}
                        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#141517] shadow-2xl relative z-10">
                            {/* Toolbar Contextual (Local) */}
                            <div className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-4 shrink-0">
                                {depth > 1 && (
                                    <button 
                                        onClick={onBack}
                                        className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-colors text-slate-400"
                                    >
                                        <ChevronLeft size={20} />
                                    </button>
                                )}
                                
                                <div className="flex-1 flex items-center gap-2 overflow-hidden">
                                    {parentTitle && (
                                        <>
                                            <span className="text-[11px] font-black uppercase tracking-widest text-slate-400 whitespace-nowrap">{parentTitle}</span>
                                            <span className="text-slate-300">/</span>
                                        </>
                                    )}
                                    <h1 className="text-[15px] font-black text-slate-800 dark:text-white truncate">{sidebarTitle}</h1>
                                </div>

                                <div className="flex items-center gap-2">
                                    {/* Global View Controls */}
                                    <button 
                                        onClick={toggleTheme}
                                        className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
                                    >
                                        {theme === 'day' ? <Moon size={18} /> : <Sun size={18} />}
                                    </button>
                                    <button 
                                        onClick={() => setShowInbox(!showInbox)}
                                        className={clsx(
                                            "p-2 rounded-xl transition-all relative",
                                            showInbox ? "bg-blue-50 text-blue-600 shadow-sm" : "text-slate-400 hover:text-slate-600"
                                        )}
                                    >
                                        <Bell size={18} />
                                        <div className="absolute top-2 right-2 size-2 bg-rose-500 rounded-full border-2 border-white dark:border-[#141517]" />
                                    </button>
                                    
                                    <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-2" />
                                    
                                    {/* User Menu */}
                                    <Popover.Root>
                                        <Popover.Trigger asChild>
                                            <button className="flex items-center gap-2 p-1 pl-3 bg-slate-100 dark:bg-white/5 rounded-2xl hover:bg-slate-200 dark:hover:bg-white/10 transition-all border border-transparent hover:border-slate-200 dark:hover:border-white/10">
                                                <span className="text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300">{user?.username || 'Usuario'}</span>
                                                <div className="size-8 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-lg">
                                                    {user?.username?.substring(0, 2).toUpperCase() || 'U'}
                                                </div>
                                            </button>
                                        </Popover.Trigger>
                                        <Popover.Portal>
                                            <Popover.Content sideOffset={8} align="end" className="z-[100] w-64 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-3xl shadow-2xl p-2 outline-none animate-in fade-in zoom-in-95 duration-200">
                                                <div className="p-4 border-b border-slate-100 dark:border-white/5 mb-2">
                                                    <p className="text-xs font-black uppercase tracking-widest text-slate-400 mb-1">Sesión activa</p>
                                                    <p className="text-sm font-bold truncate">{user?.email}</p>
                                                </div>
                                                <Link href="/account">
                                                    <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 rounded-2xl transition-colors">
                                                        <User size={16} /> Mi Perfil
                                                    </button>
                                                </Link>
                                                <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-2xl transition-colors">
                                                    <LogOut size={16} /> Cerrar Sesión
                                                </button>
                                            </Popover.Content>
                                        </Popover.Portal>
                                    </Popover.Root>
                                </div>
                            </div>

                            {/* View Content */}
                            <div className="flex-1 overflow-hidden relative">
                                {children}
                            </div>
                        </div>
                    </div>

                    {/* Inbox Overlay */}
                    <AnimatePresence>
                        {showInbox && (
                            <motion.div 
                                initial={{ x: 400, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                exit={{ x: 400, opacity: 0 }}
                                className="absolute top-14 right-0 bottom-0 w-96 z-[100] bg-white dark:bg-[#1e1f21] border-l border-slate-100 dark:border-white/5 shadow-2xl"
                            >
                                <WorkspaceInbox onClose={() => setShowInbox(false)} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>

                {/* Visibility Controls (Floating) */}
                {!blackSidebarVisible && (
                    <motion.button 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        onClick={() => handleSetBlackMode(true)}
                        className="fixed left-4 bottom-10 z-[60] p-3 bg-slate-900 text-white rounded-2xl shadow-2xl hover:scale-110 active:scale-95 transition-all group"
                    >
                        <Tooltip content="Mostrar barra lateral" position="right">
                            <PanelLeftOpen size={20} />
                        </Tooltip>
                    </motion.button>
                )}
            </div>
        </ProtectedRoute>
    );
}

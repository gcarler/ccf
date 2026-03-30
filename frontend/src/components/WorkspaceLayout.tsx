"use client";

import React, { useState, useEffect, useMemo } from 'react';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import ProtectedRoute from '@/components/ProtectedRoute';
import Tooltip from '@/components/ui/Tooltip';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
    Search, Bell, Settings, Layout, PanelLeft, PanelLeftClose,
    Sparkles, Sun, Moon, User, LogOut, PanelLeftOpen, X,
    ChevronLeft, Target, GraduationCap, Users, Globe,
    Home, Inbox, CheckSquare, Folder, Calendar, LayoutDashboard,
    FileText, MessageCircle
} from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '@/app/theme/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import * as Popover from '@radix-ui/react-popover';
import { usePathname, useRouter } from 'next/navigation';
import { useCreation } from '@/context/CreationContext';
import UniversalCreationModal from '@/components/ui/UniversalCreationModal';

// Configuración de Secciones por Módulo (Capa 2)
const MODULE_CONFIGS: Record<string, any> = {
    projects: {
        title: "Portfolio Proyectos",
        sections: [
            {
                title: "Gestión",
                items: [
                    { id: 'projects-home', label: 'Ver Portfolio', href: '/projects', icon: Layout },
                    { id: 'projects-tasks', label: 'Mis Tareas', href: '/tasks', icon: CheckSquare },
                    { id: 'projects-team', label: 'Gestión de Equipo', href: '/projects/team', icon: Users },
                ]
            },
            {
                title: "Inteligencia",
                items: [
                    { id: 'projects-calendar', label: 'Calendario Global', href: '/calendar', icon: Calendar },
                    { id: 'projects-auto', label: 'Automatizaciones', href: '/projects/automations', icon: Zap },
                ]
            }
        ]
    },
    crm: {
        title: "CRM Comunidad",
        sections: [
            {
                title: "Operaciones",
                items: [
                    { id: 'crm-home', label: 'Directorio', href: '/crm', icon: Users },
                    { id: 'crm-groups', label: 'Casas de Gloria', href: '/crm/groups', icon: Home },
                    { id: 'crm-events', label: 'Eventos', href: '/crm/events', icon: Calendar },
                ]
            },
            {
                title: "Atención",
                items: [
                    { id: 'crm-help', label: 'Consejería', href: '/crm/counseling', icon: Heart },
                    { id: 'crm-prayer', label: 'Peticiones', href: '/crm/prayers', icon: Sparkles },
                ]
            }
        ]
    },
    academy: {
        title: "Academia CCF",
        sections: [
            {
                title: "Aprendizaje",
                items: [
                    { id: 'academy-home', label: 'Catálogo', href: '/academy', icon: BookOpen },
                    { id: 'academy-my', label: 'Mis Cursos', href: '/academy/my', icon: GraduationCap },
                ]
            }
        ]
    }
};

function Zap({ size, className }: any) { return <Sparkles size={size} className={className} />; }
function Heart({ size, className }: any) { return <MessageCircle size={size} className={className} />; }
function BookOpen({ size, className }: any) { return <GraduationCap size={size} className={className} />; }

export default function WorkspaceLayout({ 
    children, 
    sidebarTitle: manualTitle, 
    sidebarSections: manualSections,
    allowedRoles,
    depth = 1,
    parentTitle,
    onBack,
    customSidebar
}: any) {
    const { theme, toggleTheme } = useTheme();
    const { user, logout } = useAuth();
    const pathname = usePathname();
    const [blackSidebarVisible, setBlackSidebarVisible] = useState(true);
    const [graySidebarMode, setGraySidebarMode] = useState<'full' | 'mini' | 'hidden'>('full');
    const [showInbox, setShowInbox] = useState(false);
    const { isModalOpen, closeModal, defaultType } = useCreation();

    // Lógica de Resolución de Capa 2 (Sidebar Gris)
    const moduleContext = useMemo(() => {
        const root = pathname?.split('/')[1] || '';
        return MODULE_CONFIGS[root] || { title: "CCF Platform", sections: [] };
    }, [pathname]);

    const displayTitle = manualTitle || moduleContext.title;
    const displaySections = manualSections || moduleContext.sections;

    return (
        <ProtectedRoute allowedRoles={allowedRoles}>
            <div className="flex h-screen w-full bg-slate-50 dark:bg-[#111213] overflow-hidden font-display relative">
                
                <UniversalCreationModal isOpen={isModalOpen} onClose={closeModal} initialType={defaultType} />

                {/* CAPA 1: Dominios (Negro) */}
                <AnimatePresence mode="popLayout">
                    {blackSidebarVisible && (
                        <motion.div initial={{ x: -80, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: -80, opacity: 0 }} className="flex shrink-0 z-50 h-screen py-[10vh] pl-4">
                            <WorkspaceMiniSidebar onHide={() => setBlackSidebarVisible(false)} />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* CAPA 2 & 3: Workspace (Gris/Contenido) */}
                <main className="flex-1 flex flex-col min-w-0 relative">
                    <div className="flex h-full w-full">
                        {/* Sidebar 2: Secciones dinámicas que dependen del modulo */}
                        <div className={clsx(
                            "h-full shrink-0 overflow-hidden transition-all duration-300",
                            graySidebarMode === 'full' ? "w-72" : graySidebarMode === 'mini' ? "w-20" : "w-0"
                        )}>
                            {customSidebar || (
                                <WorkspaceMainSidebar 
                                    title={displayTitle} 
                                    sections={displaySections} 
                                    isMini={graySidebarMode === 'mini'}
                                />
                            )}
                        </div>

                        {/* CAPA 3: Vista Activa */}
                        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#141517] shadow-2xl relative z-10 border-l border-slate-100 dark:border-white/5">
                            <header className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-4 shrink-0">
                                {depth > 1 && (
                                    <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-full text-slate-400"><ChevronLeft size={20} /></button>
                                )}
                                <div className="flex-1 flex items-center gap-2 overflow-hidden">
                                    <h1 className="text-[14px] font-black text-slate-800 dark:text-white truncate uppercase tracking-widest">{displayTitle}</h1>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button onClick={toggleTheme} className="p-2 text-slate-400">{theme === 'day' ? <Moon size={18} /> : <Sun size={18} />}</button>
                                    <button onClick={() => setShowInbox(!showInbox)} className="p-2 text-slate-400"><Bell size={18} /></button>
                                    <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-2" />
                                    <div className="size-8 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-xs">{user?.username?.substring(0, 2).toUpperCase()}</div>
                                </div>
                            </header>

                            <div className="flex-1 overflow-hidden relative">
                                {children}
                            </div>
                        </div>
                    </div>

                    <AnimatePresence>
                        {showInbox && (
                            <motion.div initial={{ x: 400 }} animate={{ x: 0 }} exit={{ x: 400 }} className="absolute top-14 right-0 bottom-0 w-96 z-[100] bg-white dark:bg-[#1e1f21] border-l border-slate-100 dark:border-white/5 shadow-2xl">
                                <WorkspaceInbox onClose={() => setShowInbox(false)} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>

                {!blackSidebarVisible && (
                    <button onClick={() => setBlackSidebarVisible(true)} className="fixed left-4 bottom-10 z-[60] p-3 bg-slate-900 text-white rounded-2xl shadow-2xl hover:scale-110 active:scale-95 transition-all">
                        <PanelLeftOpen size={20} />
                    </button>
                )}
            </div>
        </ProtectedRoute>
    );
}

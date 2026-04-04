"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import MeshChat from '@/components/ui/MeshChat';
import ProtectedRoute from '@/components/ProtectedRoute';
import Tooltip from '@/components/ui/Tooltip';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import {
    Bell, Layout, PanelLeft, PanelLeftClose,
    Sun, Moon, User, LogOut, PanelLeftOpen, X,
    ChevronLeft, Target, GraduationCap, Users, Globe,
    Home, Inbox, CheckSquare, Folder, Calendar, LayoutDashboard,
    FileText, MessageCircle, Settings2, ShieldCheck, Zap, Bot, Settings,
    BookOpen, Link2
} from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '@/app/theme/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import * as Popover from '@radix-ui/react-popover';
import { usePathname, useRouter } from 'next/navigation';
import { useCreation } from '@/context/CreationContext';
import UniversalCreationModal from '@/components/ui/UniversalCreationModal';
import ThemeToggle from '@/components/ui/ThemeToggle';

// ── Layer Context (importamos el provider aquí) ──────────────────
import { SidebarLayerProvider, useSidebarLayers } from '@/context/SidebarLayerContext';

// ── Module configs (Sidebar 2 sections) ─────────────────────────
const MODULE_CONFIGS: Record<string, any> = {
    projects: {
        title: "Portfolio",
        sections: [
            {
                title: "Gestión",
                items: [
                    { id: 'projects-home',  label: 'Portfolio',   href: '/projects',  icon: Layout },
                    { id: 'projects-tasks', label: 'Mis Tareas',  href: '/tasks',     icon: CheckSquare },
                    { id: 'projects-team',  label: 'Equipo',      href: '/projects/team', icon: Users },
                ]
            },
            {
                title: "Herramientas",
                items: [
                    { id: 'projects-calendar', label: 'Calendario',      href: '/calendar',              icon: Calendar },
                    { id: 'projects-auto',     label: 'Automatizaciones', href: '/projects/automations',  icon: Zap },
                ]
            }
        ]
    },
    tasks: {
        title: "Productividad",
        sections: [
            {
                title: "Mis espacios",
                items: [
                    { id: 'tasks-all',      label: 'Todas las tareas', href: '/tasks',    icon: CheckSquare },
                    { id: 'tasks-calendar', label: 'Calendario',       href: '/calendar', icon: Calendar },
                ]
            }
        ]
    },
    calendar: {
        title: "Calendario",
        sections: [
            {
                title: "Vistas",
                items: [
                    { id: 'cal-month', label: 'Por Mes',  href: '/calendar', icon: Calendar },
                ]
            }
        ]
    },
    crm: {
        title: "Comunidad",
        sections: [
            {
                title: "Directorios",
                items: [
                    { id: 'crm-home',   label: 'Miembros',       href: '/crm',        icon: Users },
                    { id: 'crm-groups', label: 'Casas de Gloria', href: '/crm/groups', icon: Home },
                ]
            }
        ]
    },
    academy: {
        title: "Academia",
        sections: [
            {
                title: "Estudio",
                items: [
                    { id: 'academy-home',    label: 'Inicio',   href: '/academy',         icon: GraduationCap },
                    { id: 'academy-courses', label: 'Cursos',   href: '/academy/courses',  icon: BookOpen },
                    { id: 'academy-profile', label: 'Mi cuenta', href: '/academy/account', icon: User },
                ]
            }
        ]
    },
    finances: {
        title: "Finanzas",
        sections: [
            {
                title: "Reportes",
                items: [
                    { id: 'fin-home',         label: 'Resumen',        href: '/finances',              icon: LayoutDashboard },
                    { id: 'fin-transparency', label: 'Transparencia',   href: '/finances/transparency', icon: FileText },
                ]
            }
        ]
    },
    inbox: {
        title: "Bandeja",
        sections: [
            {
                title: "Filtros",
                items: [
                    { id: 'inbox-all',      label: 'Todo',       href: '/inbox',           icon: Inbox },
                    { id: 'inbox-mentions', label: 'Menciones',  href: '/inbox#menciones', icon: MessageCircle },
                    { id: 'inbox-tasks',    label: 'Tareas',     href: '/inbox#tareas',    icon: CheckSquare },
                    { id: 'inbox-ai',       label: 'MESH AI',    href: '/inbox#ai',        icon: Bot },
                ]
            }
        ]
    },
    cms: {
        title: "Sitio Web",
        sections: [
            {
                title: "Contenido",
                items: [
                    { id: 'cms-home',         label: 'Inicio CMS',      href: '/cms',               icon: LayoutDashboard },
                    { id: 'cms-pages',        label: 'Páginas',         href: '/cms/pages',         icon: FileText },
                    { id: 'cms-menus',        label: 'Menús del sitio', href: '/cms/menus',         icon: Link2 },
                    { id: 'cms-testimonials', label: 'Testimonios',      href: '/cms/testimonials',  icon: MessageCircle },
                    { id: 'cms-content',      label: 'Landing Hero',     href: '/cms/content',       icon: FileText },
                    { id: 'cms-events',       label: 'Eventos públicos', href: '/cms/events',        icon: Calendar },
                ]
            }
        ]
    },
    wiki: {
        title: "Conocimiento",
        sections: [
            {
                title: "Espacios",
                items: [
                    { id: 'wiki-home',      label: 'Inicio Wiki',   href: '/wiki',         icon: LayoutDashboard },
                    { id: 'wiki-docs',      label: 'Documentos',    href: '/wiki/docs',    icon: FileText },
                    { id: 'wiki-knowledge', label: 'Base Pastoral', href: '/wiki/pastoral', icon: BookOpen },
                ]
            }
        ]
    },
    groups: {
        title: "Comunidad",
        sections: [
            {
                title: "Células",
                items: [
                    { id: 'groups-all',    label: 'Casas de Bendición', href: '/groups',        icon: Home },
                    { id: 'groups-family', label: 'Núcleos Familiares', href: '/groups/family',  icon: Users },
                    { id: 'groups-crm',   label: 'Directorio CRM',     href: '/crm',            icon: ShieldCheck },
                ]
            }
        ]
    },
    'spiritual-life': {
        title: "Vida Espiritual",
        sections: [
            {
                title: "Mi Caminar",
                items: [
                    { id: 'sl-home',  label: 'Panel Espiritual',  href: '/spiritual-life',              icon: BookOpen },
                    { id: 'sl-tl',    label: 'Línea de Tiempo',   href: '/spiritual-life/timeline',     icon: Calendar },
                    { id: 'sl-certs', label: 'Mis Certificados',  href: '/spiritual-life/certificates', icon: FileText },
                ]
            },
            {
                title: "Formación",
                items: [
                    { id: 'sl-academy', label: 'Academia CCF', href: '/academy', icon: GraduationCap },
                ]
            }
        ]
    },
};

// ─────────────────────────────────────────────────────────────────
// PUBLIC API: WorkspaceLayout wraps children with the layer provider
// ─────────────────────────────────────────────────────────────────
export default function WorkspaceLayout({
    children,
    sidebarTitle: manualTitle,
    sidebarSections: manualSections,
    allowedRoles,
    depth = 1,
    onBack,
    customSidebar
}: any) {
    return (
        <SidebarLayerProvider>
            <WorkspaceLayoutInner
                manualTitle={manualTitle}
                manualSections={manualSections}
                allowedRoles={allowedRoles}
                depth={depth}
                onBack={onBack}
                customSidebar={customSidebar}
            >
                {children}
            </WorkspaceLayoutInner>
        </SidebarLayerProvider>
    );
}

// ─────────────────────────────────────────────────────────────────
// INNER LAYOUT — has access to SidebarLayerContext
// ─────────────────────────────────────────────────────────────────
function WorkspaceLayoutInner({
    children, manualTitle, manualSections,
    allowedRoles, depth, onBack, customSidebar
}: any) {
    const { theme } = useTheme();
    const { user, logout } = useAuth();
    const pathname = usePathname();
    const [showInbox, setShowInbox] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const [isMounted, setIsReady] = useState(false);
    const { isModalOpen, closeModal, defaultType } = useCreation();

    // ── Layer state ──────────────────────────────────────────────
    const { layers, toggleLayer, openLayer, closeLayer } = useSidebarLayers();

    // S1 visibility is controlled by layers.S1 (always true, but kept in sync)
    const s1Visible = layers.S1;
    const s2Mode = layers.S2 ? 'full' : 'hidden'; // simplified: no mini in S2 for now

    useEffect(() => {
        setIsReady(true);
    }, []);

    const moduleContext = useMemo(() => {
        const root = pathname?.split('/')[1] || '';
        return MODULE_CONFIGS[root] || { title: "CCF Platform", sections: [] };
    }, [pathname]);

    const displayTitle = manualTitle || moduleContext.title;
    const displaySections = manualSections || moduleContext.sections;

    // Toggle S2 through 3 states: full → mini → hidden → full
    const [s2DetailMode, setS2DetailMode] = useState<'full' | 'mini' | 'hidden'>('full');

    const cycleS2 = useCallback(() => {
        setS2DetailMode(m => m === 'full' ? 'mini' : m === 'mini' ? 'hidden' : 'full');
    }, []);

    const s2Width = s2DetailMode === 'full' ? 'w-72' : s2DetailMode === 'mini' ? 'w-16' : 'w-0';

    if (!isMounted) return <div className="h-screen w-full bg-white dark:bg-[#111213]" />;

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username;

    return (
        <ProtectedRoute allowedRoles={allowedRoles}>
            {/* ROOT: overflow-x hidden para evitar desbordamiento horizontal */}
            <div className="flex h-screen w-full bg-slate-50 dark:bg-[#111213] overflow-hidden font-display relative transition-colors duration-500">

                {/* ── PAGE LOAD INDICATOR ──────────────────────────────── */}
                <motion.div
                    className="absolute top-0 left-0 right-0 h-[2px] bg-blue-600 z-[10000]"
                    initial={{ scaleX: 0, originX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.4 }}
                />

                <UniversalCreationModal isOpen={isModalOpen} onClose={closeModal} initialType={defaultType} />

                {/* ═══════════════════════════════════════════════════════
                    SIDEBAR 1 — Navegación Primaria
                    z-index: 50 (máxima autoridad visual)
                    Ancho fijo 64px, siempre visible
                    Shadow derecha pronunciada para marcar jerarquía
                ════════════════════════════════════════════════════════ */}
                <AnimatePresence mode="popLayout">
                    {s1Visible && (
                        <motion.div
                            key="sidebar1"
                            initial={{ x: -80, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -80, opacity: 0 }}
                            transition={{ type: 'tween', duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                            className="flex shrink-0 z-50 h-screen py-[10vh] pl-4"
                            // Sombra más pronunciada = máxima jerarquía
                            style={{ filter: 'drop-shadow(8px 0 24px rgba(0,0,0,0.15))' }}
                        >
                            <WorkspaceMiniSidebar onHide={() => closeLayer('S1')} />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ═══════════════════════════════════════════════════════
                    CONTENT AREA (S2 + Main) — flex-1 dinámico
                ════════════════════════════════════════════════════════ */}
                <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
                    <div className="flex h-full w-full overflow-hidden">

                        {/* ══════════════════════════════════════════════════
                            SIDEBAR 2 — Navegación de Módulo
                            z-index: 40 (debajo de S1)
                            Colapsable: full → mini → hidden
                            Shadow derecha moderada
                        ═══════════════════════════════════════════════════ */}
                        <div
                            className={clsx(
                                "h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out relative",
                                s2Width
                            )}
                            style={{
                                zIndex: 40,
                                boxShadow: s2DetailMode !== 'hidden'
                                    ? '4px 0 16px rgba(0,0,0,0.06), 1px 0 4px rgba(0,0,0,0.04)'
                                    : 'none',
                            }}
                        >
                            {customSidebar || (
                                <WorkspaceMainSidebar
                                    title={displayTitle}
                                    sections={displaySections}
                                    isMini={s2DetailMode === 'mini'}
                                    onToggle={cycleS2}
                                    isCollapsed={s2DetailMode !== 'full'}
                                />
                            )}
                        </div>

                        {/* ══════════════════════════════════════════════════
                            CAPA 3 (Content + optional S3 + optional RIGHT)
                            El contenido principal usa flex-grow para
                            adaptarse al espacio restante dinámicamente
                        ═══════════════════════════════════════════════════ */}
                        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#141517] shadow-2xl relative z-10 border-l border-slate-100 dark:border-white/5 overflow-hidden">

                            {/* ── TOOLBAR / HEADER ───────────────────────── */}
                            <header className="h-14 border-b border-slate-100/80 dark:border-white/[0.05] flex items-center px-5 gap-3 shrink-0 bg-white dark:bg-[#141517] z-[60] relative">
                                {depth > 1 && (
                                    <button
                                        onClick={onBack}
                                        className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all text-slate-400"
                                    >
                                        <ChevronLeft size={20} />
                                    </button>
                                )}

                                {/* Module title with accent dot */}
                                <div className="flex-1 flex items-center gap-3 overflow-hidden min-w-0">
                                    <div className="flex items-center gap-2.5 min-w-0">
                                        <div className="size-2 rounded-full bg-blue-500 shrink-0 shadow-[0_0_6px_2px_rgba(59,130,246,0.4)]" />
                                        <h1 className="text-[13px] font-bold text-slate-800 dark:text-slate-100 truncate tracking-tight leading-none">
                                            {displayTitle}
                                        </h1>
                                    </div>
                                </div>

                                {/* ── Right toolbar actions ──────────────── */}
                                <div className="flex items-center gap-0.5">
                                    {/* S2 Toggle */}
                                    <Tooltip content={
                                        s2DetailMode === 'hidden' ? 'Mostrar panel'
                                        : s2DetailMode === 'mini' ? 'Expandir panel'
                                        : 'Contraer panel'
                                    }>
                                        <button
                                            onClick={cycleS2}
                                            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                                            aria-label="Toggle sidebar de módulo"
                                        >
                                            {s2DetailMode === 'hidden'
                                                ? <PanelLeftOpen size={17} />
                                                : s2DetailMode === 'mini'
                                                    ? <PanelLeft size={17} />
                                                    : <PanelLeftClose size={17} />
                                            }
                                        </button>
                                    </Tooltip>

                                    <ThemeToggle variant="pill" />

                                    <button
                                        onClick={() => setShowInbox(!showInbox)}
                                        className="p-2 text-slate-400 hover:text-blue-600 relative rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                                        aria-label="Notificaciones"
                                    >
                                        <Bell size={17} />
                                        <span className="absolute top-1.5 right-1.5 size-1.5 bg-rose-500 rounded-full ring-1 ring-white dark:ring-[#141517]" />
                                    </button>

                                    <div className="w-px h-5 bg-slate-200 dark:bg-white/10 mx-2" />

                                    {/* User chip — premium */}
                                    <button className="flex items-center gap-2 h-9 pl-2.5 pr-1 bg-slate-50 dark:bg-white/[0.06] border border-slate-200 dark:border-white/[0.07] rounded-xl hover:bg-slate-100 dark:hover:bg-white/10 transition-all group">
                                        <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors max-w-[80px] truncate">
                                            {displayName}
                                        </span>
                                        <div className="size-7 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-black text-[10px] shadow-md">
                                            {displayName?.substring(0, 2).toUpperCase()}
                                        </div>
                                    </button>
                                </div>
                            </header>

                            {/* ── PAGE CONTENT (children go here) ─────── */}
                            <div className="flex-1 overflow-hidden relative">
                                {children}
                            </div>
                        </div>
                    </div>

                    {/* Inbox drawer */}
                    <WorkspaceInbox isOpen={showInbox} onClose={() => setShowInbox(false)} />

                    {/* MESH AI Chat */}
                    <MeshChat isOpen={showChat} onClose={() => setShowChat(false)} />

                    {/* Floating MESH AI trigger */}
                    <motion.button
                        initial={{ scale: 0, rotate: -45 }}
                        animate={{ scale: 1, rotate: 0 }}
                        whileHover={{ scale: 1.1, rotate: 5 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => setShowChat(true)}
                        className="fixed bottom-8 right-8 z-[500] size-14 rounded-[1.5rem] bg-gradient-to-tr from-purple-600 to-indigo-600 text-white shadow-2xl shadow-purple-500/40 flex items-center justify-center border border-white/20 group"
                        aria-label="Abrir MESH AI"
                    >
                        <Bot size={28} className="group-hover:animate-pulse" />
                        <div className="absolute -top-1 -right-1 size-4 bg-emerald-500 rounded-full border-2 border-white dark:border-[#111213]" />
                    </motion.button>
                </main>

                {/* S1 restore button (if somehow hidden) */}
                {!s1Visible && (
                    <motion.button
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        onClick={() => openLayer('S1')}
                        className="fixed left-4 bottom-10 z-[60] p-3 bg-slate-900 text-white rounded-2xl shadow-2xl hover:scale-110 active:scale-95 transition-all"
                        aria-label="Mostrar navegación principal"
                    >
                        <PanelLeftOpen size={20} />
                    </motion.button>
                )}
            </div>
        </ProtectedRoute>
    );
}

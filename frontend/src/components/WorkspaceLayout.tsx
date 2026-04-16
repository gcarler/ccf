"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import MeshChat from '@/components/ui/MeshChat';
import ProtectedRoute from '@/components/ProtectedRoute';
import Tooltip from '@/components/ui/Tooltip';
import { useAuth } from '@/context/AuthContext';
import {
    Bell, Layout,
    ChevronLeft, Users, 
    Home, Inbox, CheckSquare, Folder, Calendar, LayoutDashboard,
    FileText, MessageCircle, ShieldCheck, Zap, Bot, Settings,
    BookOpen, Link2, UserPlus, Heart, Scan, PieChart, Contact, KanbanSquare, Mail, ChevronRight
} from 'lucide-react';
import clsx from 'clsx';
import { useTheme } from '@/app/theme/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { useCreation } from '@/context/CreationContext';
import UniversalCreationModal from '@/components/ui/UniversalCreationModal';
import ThemeToggle from '@/components/ui/ThemeToggle';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';

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
        title: "Comunidad CRM",
        sections: [
            {
                title: "Actividad y Métricas",
                items: [
                    { id: 'crm-analytics', label: 'Panel Analítico', href: '/crm/analytics', icon: PieChart }
                ]
            },
            {
                title: "Directorio Pastoral",
                items: [
                    { id: 'crm-members',    label: 'Miembros',          href: '/crm/members',    icon: Users },
                    { id: 'crm-groups',     label: 'Casas de Gloria',   href: '/crm/groups',     icon: Home },
                    { id: 'crm-contacts',   label: 'Contactos/Leads',   href: '/crm/contacts',   icon: UserPlus },
                    { id: 'crm-volunteers', label: 'Voluntariado',      href: '/crm/volunteers', icon: ShieldCheck },
                ]
            },
            {
                title: "Consolidación",
                items: [
                    { id: 'crm-pipeline',   label: 'Pipeline pastoral', href: '/crm/pipeline',   icon: KanbanSquare },
                    { id: 'crm-counseling', label: 'Consejería',        href: '/crm/counseling', icon: Heart },
                    { id: 'crm-prayers',    label: 'Muro de Oración',   href: '/crm/prayers',    icon: MessageCircle },
                    { id: 'crm-tasks',      label: 'Tareas Asignadas',  href: '/crm/tasks',      icon: CheckSquare },
                ]
            },
            {
                title: "Herramientas",
                items: [
                    { id: 'crm-events',    label: 'Eventos',       href: '/crm/events',    icon: Calendar },
                    { id: 'crm-scanner',   label: 'Escáner ASST',  href: '/crm/scanner',   icon: Scan },
                    { id: 'crm-messaging', label: 'Mensajería',    href: '/crm/messaging', icon: Mail },
                    { id: 'crm-mycard',    label: 'Mi Carnet',     href: '/crm/my-card',   icon: Contact },
                    { id: 'crm-settings',  label: 'Configuración', href: '/crm/settings',  icon: Settings },
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
                    { id: 'academy-home',    label: 'Inicio',   href: '/academy',         icon: BookOpen },
                    { id: 'academy-courses', label: 'Cursos',   href: '/academy/courses',  icon: BookOpen },
                    { id: 'academy-profile', label: 'Mi cuenta', href: '/academy/account', icon: Contact },
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
                    { id: 'sl-academy', label: 'Academia CCF', href: '/academy', icon: BookOpen },
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
    customSidebar,
    ...toolbarProps
}: any) {
    return (
        <WorkspaceLayoutInner
            manualTitle={manualTitle}
            manualSections={manualSections}
            allowedRoles={allowedRoles}
            depth={depth}
            onBack={onBack}
            customSidebar={customSidebar}
            {...toolbarProps}
        >
            {children}
        </WorkspaceLayoutInner>
    );
}

// ─────────────────────────────────────────────────────────────────
// INNER LAYOUT — has access to SidebarLayerContext
// ─────────────────────────────────────────────────────────────────
function WorkspaceLayoutInner({
    children, manualTitle, manualSections,
    allowedRoles, depth, onBack, customSidebar,
    // Toolbar props
    breadcrumbs, viewType, setViewType, availableViews,
    rightActions, leftActions, onSearch, onFilter, onAdd, onAddOption
}: any) {
    const { user } = useAuth();
    const pathname = usePathname();
    const [showInbox, setShowInbox] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const [isMounted, setIsReady] = useState(false);
    const { isModalOpen, closeModal, defaultType } = useCreation();

    // ── Layer state ──────────────────────────────────────────────
    const { layers, openLayer } = useSidebarLayers();

    // S1 visibility is controlled by layers.S1 (always true, but kept in sync)
    const s1Visible = layers.S1;

    useEffect(() => {
        setIsReady(true);
    }, []);

    const moduleContext = useMemo(() => {
        const root = pathname?.split('/')[1] || '';
        return MODULE_CONFIGS[root] || { title: "CCF Platform", sections: [] };
    }, [pathname]);

    const displayTitle = manualTitle || moduleContext.title;
    const displaySections = manualSections || moduleContext.sections;

    // Toggle S2 between full and hidden. Mini mode is now managed manually via dragging.
    const s2LocalKey = `s2mode_${pathname?.split('/')[1] || 'default'}`;
    const [s2DetailMode, setS2DetailMode] = useState<'full' | 'hidden'>(() => {
        if (typeof window === 'undefined') return 'full';
        const saved = localStorage.getItem(s2LocalKey);
        return (saved === 'hidden' ? 'hidden' : 'full');
    });

    const cycleS2 = useCallback(() => {
        setS2DetailMode(m => {
            const next = m === 'full' ? 'hidden' : 'full';
            localStorage.setItem(s2LocalKey, next);
            return next;
        });
    }, [s2LocalKey]);

    // Resizing logic for S2
    const minS2Width = 64; // Permite reducirse a sólo los iconos (64px)
    const snapThreshold = 130; // Debajo de esto se 'snappea' a 64px
    const maxS2Width = 480;

    const [s2WidthNum, setS2WidthNum] = useState<number>(() => {
        if (typeof window === 'undefined') return 280;
        const saved = localStorage.getItem('s2Width');
        return saved ? parseInt(saved, 10) : 280;
    });
    const [isDraggingS2, setIsDraggingS2] = useState(false);
    const startPosRef = useRef<number>(0);
    const startWidthRef = useRef<number>(0);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('s2Width', s2WidthNum.toString());
        }
    }, [s2WidthNum]);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDraggingS2) return;
            const delta = e.clientX - startPosRef.current;
            let newWidth = startWidthRef.current + delta;
            
            if (newWidth < snapThreshold) {
                newWidth = minS2Width;
            }

            if (newWidth > maxS2Width) newWidth = maxS2Width;
            setS2WidthNum(newWidth);
        };
        const handleMouseUp = () => setIsDraggingS2(false);

        if (isDraggingS2) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        } else {
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
    }, [isDraggingS2]);

    const handleMouseDownS2 = (e: React.MouseEvent) => {
        setIsDraggingS2(true);
        startPosRef.current = e.clientX;
        startWidthRef.current = s2WidthNum;
        e.preventDefault();
    };

    const isMiniSidebar = s2DetailMode === 'full' && s2WidthNum <= snapThreshold;
    const currentS2Width = s2DetailMode === 'full' ? `${s2WidthNum}px` : '0px';

    if (!isMounted) return <div className="h-screen w-full bg-white dark:bg-[#111213]" />;

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username;

    // Combined Right Actions for WorkspaceToolbar
    const defaultRightActions = (
        <div className="flex items-center gap-0.5">
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
    );

    return (
        <ProtectedRoute allowedRoles={allowedRoles}>
            <div className="flex h-screen w-full bg-slate-50 dark:bg-[#111213] overflow-hidden font-display relative transition-colors duration-500">

                <motion.div
                    className="absolute top-0 left-0 right-0 h-[2px] bg-blue-600 z-[10000]"
                    initial={{ scaleX: 0, originX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.4 }}
                />

                <UniversalCreationModal isOpen={isModalOpen} onClose={closeModal} initialType={defaultType} />

                <AnimatePresence mode="popLayout">
                    {s1Visible && (
                        <motion.div
                            key="sidebar1"
                            initial={{ x: -80, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -80, opacity: 0 }}
                            transition={{ type: 'tween', duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                            className="flex shrink-0 z-50 h-screen py-[10vh] pl-4"
                            style={{ filter: 'drop-shadow(8px 0 24px rgba(0,0,0,0.15))' }}
                        >
                            <WorkspaceMiniSidebar onHide={() => {}} />
                        </motion.div>
                    )}
                </AnimatePresence>

                <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
                    <div className="flex h-full w-full overflow-hidden">
                        <div
                            className={clsx(
                                "h-full shrink-0 relative flex",
                                !isDraggingS2 && "transition-[width] duration-300 ease-in-out"
                            )}
                            style={{
                                zIndex: 40,
                                width: currentS2Width,
                            }}
                        >
                            <div className="w-full h-full overflow-hidden" style={{
                                boxShadow: s2DetailMode !== 'hidden'
                                    ? '4px 0 16px rgba(0,0,0,0.06), 1px 0 4px rgba(0,0,0,0.04)'
                                    : 'none',
                            }}>
                                {customSidebar || (
                                <WorkspaceMainSidebar
                                        title={displayTitle}
                                        sections={displaySections}
                                        isMini={isMiniSidebar}
                                        onToggle={cycleS2}
                                        isCollapsed={s2DetailMode !== 'full'}
                                    />
                                )}
                            </div>

                            {s2DetailMode === 'full' && (
                                <div
                                    className="absolute top-0 right-[-3px] w-1.5 h-full cursor-col-resize z-50 group flex items-center justify-center"
                                    onMouseDown={handleMouseDownS2}
                                >
                                    <div className={clsx(
                                        "w-[2px] h-full bg-blue-500 opacity-0 transition-opacity",
                                        isDraggingS2 ? "opacity-100" : "group-hover:opacity-100"
                                    )} />
                                </div>
                            )}
                        </div>

                        <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#141517] shadow-2xl relative z-10 border-l border-slate-100 dark:border-white/5 overflow-hidden">

                            {/* ── UNIFIED TOOLBAR / HEADER ───────────────────────── */}
                            {breadcrumbs ? (
                                <WorkspaceToolbar
                                    breadcrumbs={breadcrumbs}
                                    viewType={viewType}
                                    setViewType={setViewType}
                                    availableViews={availableViews}
                                    leftActions={
                                        <>
                                            {depth > 1 && (
                                                <button
                                                    onClick={onBack}
                                                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-all text-slate-400 mr-1"
                                                >
                                                    <ChevronLeft size={16} />
                                                </button>
                                            )}
                                            {leftActions}
                                        </>
                                    }
                                    rightActions={
                                        <div className="flex items-center gap-2">
                                            {rightActions}
                                            {defaultRightActions}
                                        </div>
                                    }
                                    onSearch={onSearch}
                                    onFilter={onFilter}
                                    onAdd={onAdd}
                                    onAddOption={onAddOption}
                                />
                            ) : (
                                <header className="h-14 border-b border-slate-100/80 dark:border-white/[0.05] flex items-center px-5 gap-3 shrink-0 bg-white dark:bg-[#141517] z-[60] relative">
                                    {depth > 1 && (
                                        <button
                                            onClick={onBack}
                                            className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all text-slate-400"
                                        >
                                            <ChevronLeft size={20} />
                                        </button>
                                    )}

                                    <div className="flex-1 flex items-center gap-3 overflow-hidden min-w-0">
                                        <div className="flex items-center gap-2.5 min-w-0">
                                            <div className="size-2 rounded-full bg-blue-500 shrink-0 shadow-[0_0_6px_2px_rgba(59,130,246,0.4)]" />
                                            <h1 className="text-[13px] font-bold text-slate-800 dark:text-slate-100 truncate tracking-tight leading-none">
                                                {displayTitle}
                                            </h1>
                                        </div>
                                    </div>
                                    {defaultRightActions}
                                </header>
                            )}

                            <div className="flex-1 overflow-hidden relative">
                                {children}
                            </div>
                        </div>
                    </div>

                    <WorkspaceInbox isOpen={showInbox} onClose={() => setShowInbox(false)} />
                    <MeshChat isOpen={showChat} onClose={() => setShowChat(false)} />

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

                {!s1Visible && (
                    <motion.button
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        onClick={() => openLayer('S1')}
                        className="fixed left-8 bottom-[88px] z-[60] size-8 bg-slate-900 text-white rounded-xl shadow-md hover:bg-slate-800 hover:scale-110 active:scale-95 transition-all flex items-center justify-center border border-white/10 dark:border-[#111213]"
                        aria-label="Mostrar navegación principal"
                    >
                        <ChevronRight size={16} strokeWidth={2.5} />
                    </motion.button>
                )}

                {s2DetailMode === 'hidden' && (
                    <Tooltip content="Mostrar panel de módulo" side="right">
                        <motion.button
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            onClick={cycleS2}
                            className="fixed left-8 bottom-6 z-[60] size-8 bg-slate-900 text-white rounded-xl shadow-md hover:bg-slate-800 hover:-translate-y-1 active:scale-95 active:translate-y-0 transition-all flex items-center justify-center border border-white/10 dark:border-[#111213]"
                            aria-label="Mostrar panel de módulo"
                        >
                            <ChevronRight size={16} strokeWidth={2.5} />
                        </motion.button>
                    </Tooltip>
                )}
            </div>
        </ProtectedRoute>
    );
}

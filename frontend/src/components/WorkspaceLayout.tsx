"use client";

import ErrorBoundary from '@/components/ErrorBoundary';
import ProtectedRoute from '@/components/ProtectedRoute';
import MeshChat from '@/components/ui/MeshChat';
import ThemeToggle from '@/components/ui/ThemeToggle';
import Tooltip from '@/components/ui/Tooltip';
import UniversalCreationDrawer from '@/components/ui/UniversalCreationDrawer';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { useCreation } from '@/context/CreationContext';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import { Bell,Bot,ChevronLeft,ChevronRight,LogOut,Maximize2,Minimize2,Settings,User } from 'lucide-react';
import { usePathname } from 'next/navigation';
import React,{ useCallback,useEffect,useMemo,useRef,useState } from 'react';

// â”€â”€ Layer Context (importamos el provider aquÃ­) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import { MODULE_CONFIGS } from '@/components/workspace/moduleConfigs';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// PUBLIC API: WorkspaceLayout wraps children with the layer provider
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function WorkspaceLayout({
    children,
    sidebarTitle: manualTitle,
    sidebarSections: manualSections,
    allowedRoles,
    allowedPermissions,
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
            allowedPermissions={allowedPermissions}
            depth={depth}
            onBack={onBack}
            customSidebar={customSidebar}
            {...toolbarProps}
        >
            {children}
        </WorkspaceLayoutInner>
    );
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// INNER LAYOUT â€” has access to SidebarLayerContext
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function WorkspaceLayoutInner({
    children, manualTitle, manualSections,
    allowedRoles, allowedPermissions, depth, onBack, customSidebar,
    // Toolbar props
    breadcrumbs, viewType, setViewType, availableViews,
    rightActions, leftActions, onSearch, onFilter, onColumns, onGroup, onMore, onAdd, onAddOption
}: any) {
    const { user, hasModuleAccess, logout } = useAuth();
    const pathname = usePathname();
    const moduleKey = pathname?.split('/')[2] || 'default';
    const [showInbox, setShowInbox] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const [isMounted, setIsReady] = useState(true);
    const [isFocusMode, setIsFocusMode] = useState(false);
    const { isModalOpen, closeModal, defaultType } = useCreation();
    const previousLayerStateRef = useRef<{ s1: boolean; s2: boolean } | null>(null);

    // â”€â”€ Layer state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const { layers, openLayer, closeLayer } = useSidebarLayers();

    // S1 visibility is controlled by layers.S1 (always true, but kept in sync)
    const s1Visible = layers.S1;

    useEffect(() => {
        const savedS1 = localStorage.getItem('workspace:s1') !== 'hidden';
        const savedS2 = localStorage.getItem(`workspace:s2:${moduleKey}`) !== 'hidden';
        const savedFocusMode = localStorage.getItem(`workspace:focus:${moduleKey}`) === '1';

        if (savedS1) openLayer('S1');
        else closeLayer('S1');

        if (savedS2) openLayer('S2');
        else closeLayer('S2');

        previousLayerStateRef.current = null;
        setIsFocusMode(savedFocusMode);

        if (savedFocusMode) {
            previousLayerStateRef.current = { s1: savedS1, s2: savedS2 };
            closeLayer('S1');
            closeLayer('S2');
        }

        setIsReady(true);
    }, [closeLayer, moduleKey, openLayer]);

    const moduleContext = useMemo(() => {
        const root = pathname?.split('/')[2] || '';
        return MODULE_CONFIGS[root] || { title: "CCF Platform", sections: [] };
    }, [pathname]);

    const displayTitle = manualTitle || moduleContext.title;
    const displaySections = manualSections || moduleContext.sections;
    // Module prefix → permission mapping for sidebar section filtering
    const MODULE_PATH_PERM_MAP: Record<string, string> = {
        '/plataforma/evangelism': 'evangelism',
        '/plataforma/crm': 'crm',
        '/plataforma/finances': 'finance',
        '/plataforma/cms': 'cms',
        '/plataforma/community': 'community',
        '/plataforma/spiritual-life': 'spiritual_life',
        '/plataforma/wiki': 'cms',
    };
    const filteredDisplaySections = useMemo(() => {
        if (!Array.isArray(displaySections)) return displaySections;
        return displaySections
            .map((section: any) => ({
                ...section,
                items: Array.isArray(section?.items)
                    ? section.items.filter((item: any) => {
                        const href = String(item?.href || '');
                        for (const [prefix, permModule] of Object.entries(MODULE_PATH_PERM_MAP)) {
                            if (href.startsWith(prefix)) {
                                return hasModuleAccess(permModule, 'read');
                            }
                        }
                        return true;
                    })
                    : section?.items,
            }))
            .filter((section: any) => !Array.isArray(section?.items) || section.items.length > 0);
    }, [displaySections, hasModuleAccess]);

    const cycleS2 = useCallback(() => {
        if (layers.S2) closeLayer('S2');
        else openLayer('S2');
    }, [closeLayer, layers.S2, openLayer]);

    const toggleFocusMode = useCallback(() => {
        setIsFocusMode((enabled) => {
            const next = !enabled;

            if (next) {
                previousLayerStateRef.current = { s1: layers.S1, s2: layers.S2 };
                closeLayer('S1');
                closeLayer('S2');
            } else {
                const previous = previousLayerStateRef.current;
                if (previous?.s1) openLayer('S1');
                else closeLayer('S1');
                if (previous?.s2) openLayer('S2');
                else closeLayer('S2');
                previousLayerStateRef.current = null;
            }

            localStorage.setItem(`workspace:focus:${moduleKey}`, next ? '1' : '0');
            return next;
        });
    }, [closeLayer, layers.S1, layers.S2, moduleKey, openLayer]);

    useEffect(() => {
        if (!isMounted || isFocusMode) return;
        localStorage.setItem('workspace:s1', layers.S1 ? 'visible' : 'hidden');
        localStorage.setItem(`workspace:s2:${moduleKey}`, layers.S2 ? 'visible' : 'hidden');
    }, [isFocusMode, isMounted, layers.S1, layers.S2, moduleKey]);

    useRegisterCommands(`workspace-${moduleKey}`, [
        {
            id: `workspace-${moduleKey}-focus`,
            label: isFocusMode ? 'Salir de modo enfoque' : 'Entrar en modo enfoque',
            description: 'Oculta barras laterales para trabajar a pantalla completa',
            group: 'Workspace',
            action: toggleFocusMode,
        },
        {
            id: `workspace-${moduleKey}-toggle-s1`,
            label: layers.S1 ? 'Ocultar navegacion principal' : 'Mostrar navegacion principal',
            group: 'Workspace',
            action: () => (layers.S1 ? closeLayer('S1') : openLayer('S1')),
        },
        {
            id: `workspace-${moduleKey}-toggle-s2`,
            label: layers.S2 ? 'Ocultar panel de modulo' : 'Mostrar panel de modulo',
            group: 'Workspace',
            action: cycleS2,
        },
    ]);

    // Resizing logic for S2
    const minS2Width = 64; // Permite reducirse a sÃ³lo los iconos (64px)
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

    const isMiniSidebar = layers.S2 && s2WidthNum <= snapThreshold;
    const currentS2Width = layers.S2 ? `${s2WidthNum}px` : '0px';

    if (!isMounted) return (
        <div className="h-screen w-full bg-[hsl(var(--bg-primary))] dark:bg-[#111213] flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="size-8 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-xs">
                    CCF
                </div>
                <div className="size-1.5 rounded-full bg-[hsl(var(--primary))] animate-pulse" />
            </div>
        </div>
    );

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username;

    // ── User dropdown menu (Gmail-style) ──
    function UserMenuDropdown({ displayName, logout }: { displayName: string; logout: () => void }) {
        const [isOpen, setIsOpen] = useState(false);
        const menuRef = useRef<HTMLDivElement>(null);

        useEffect(() => {
            const handleClickOutside = (e: MouseEvent) => {
                if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                    setIsOpen(false);
                }
            };
            document.addEventListener('mousedown', handleClickOutside);
            return () => document.removeEventListener('mousedown', handleClickOutside);
        }, []);

        return (
            <div className="relative" ref={menuRef}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="flex items-center gap-1.5 h-7 pl-2 pr-1 bg-slate-50 dark:bg-white/[0.06] border border-slate-200 dark:border-white/[0.07] rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-all group"
                >
                    <span className="text-[10px] font-semibold text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors max-w-[80px] truncate">
                        {displayName}
                    </span>
                    <div className="size-5 rounded-md bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-[8px]">
                        {displayName?.substring(0, 2).toUpperCase()}
                    </div>
                </button>

                <AnimatePresence>
                    {isOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: 5, scale: 0.96 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 5, scale: 0.96 }}
                            transition={{ duration: 0.12, ease: "easeOut" }}
                            className="absolute top-9 right-0 w-56 bg-[hsl(var(--bg-primary))] dark:bg-[#252628] border border-slate-200 dark:border-white/10 rounded-lg shadow-xl py-2 z-[100] origin-top-right"
                        >
                            {/* Header */}
                            <div className="px-3 pb-2 mb-1 border-b border-slate-100 dark:border-white/5">
                                <p className="text-xs font-bold text-slate-900 dark:text-white">{displayName}</p>
                                <p className="text-[10px] text-slate-400 dark:text-slate-500 truncate">{user?.username}</p>
                            </div>

                            {/* Options */}
                            <div className="px-1.5 flex flex-col gap-0.5">
                                <button
                                    onClick={() => { setIsOpen(false); }}
                                    className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-all text-left"
                                >
                                    <User size={14} className="text-slate-400" />
                                    <span>Mi perfil</span>
                                </button>
                                <button
                                    onClick={() => { setIsOpen(false); }}
                                    className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-all text-left"
                                >
                                    <Settings size={14} className="text-slate-400" />
                                    <span>Configuración</span>
                                </button>
                            </div>

                            {/* Logout */}
                            <div className="mt-1 pt-1 border-t border-slate-100 dark:border-white/5 px-1.5">
                                <button
                                    onClick={() => { setIsOpen(false); logout(); }}
                                    className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-left"
                                >
                                    <LogOut size={14} />
                                    <span className="font-semibold">Cerrar sesión</span>
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        );
    }

    // Combined Right Actions for WorkspaceToolbar
    const defaultRightActions = (
        <div className="flex items-center gap-0.5">
            <ThemeToggle variant="pill" />

            <button
                onClick={toggleFocusMode}
                className={clsx(
                    "p-1.5 rounded-md transition-all",
                    isFocusMode
                        ? "bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))]"
                        : "text-slate-400 hover:text-[hsl(var(--primary))] hover:bg-slate-100 dark:hover:bg-white/5"
                )}
                aria-label={isFocusMode ? "Salir de modo enfoque" : "Entrar en modo enfoque"}
                title={isFocusMode ? "Salir de modo enfoque" : "Modo enfoque"}
            >
                {isFocusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>

            <button
                onClick={() => setShowInbox(!showInbox)}
                className="p-1.5 text-slate-400 hover:text-[hsl(var(--primary))] relative rounded-md hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                aria-label="Notificaciones"
            >
                <Bell size={14} />
                <span className="absolute top-1 right-1 size-1 bg-rose-500 rounded-full ring-1 ring-white dark:ring-[#141517]" />
            </button>

            <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />

            <UserMenuDropdown displayName={displayName} logout={logout} />
        </div>
    );

    return (
        <ProtectedRoute allowedRoles={allowedRoles} allowedPermissions={allowedPermissions}>
            <div className="workspace-platform flex flex-col h-screen w-full bg-slate-50 dark:bg-[#111213] overflow-hidden font-display relative transition-colors duration-500">

                <motion.div
                    className="absolute top-0 left-0 right-0 h-[2px] bg-[hsl(var(--primary))] z-[10000]"
                    initial={{ scaleX: 0, originX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.4 }}
                />

                <UniversalCreationDrawer isOpen={isModalOpen} onClose={closeModal} initialType={defaultType} />

                {/* ── UNIFIED TOOLBAR / HEADER (100% WIDTH) ── */}
                <div className="w-full shrink-0 z-[60]">
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
                            onColumns={onColumns}
                            onGroup={onGroup}
                            onMore={onMore}
                            onAdd={onAdd}
                            onAddOption={onAddOption}
                        />
                    ) : (
                        <header className="h-10 border-b border-slate-100/80 dark:border-white/[0.05] flex items-center px-3 gap-2 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] relative">
                            {depth > 1 && (
                                <button
                                    onClick={onBack}
                                    className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-all text-slate-400"
                                >
                                    <ChevronLeft size={14} />
                                </button>
                            )}

                            <div className="flex-1 flex items-center gap-2 overflow-hidden min-w-0">
                                <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="size-1.5 rounded-full bg-[hsl(var(--primary))] shrink-0" />
                                    <h1 className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate tracking-tight leading-none">
                                        {displayTitle}
                                    </h1>
                                </div>
                            </div>
                            {defaultRightActions}
                        </header>
                    )}
                </div>

                <div className="flex flex-1 min-h-0 w-full overflow-hidden">
                    <AnimatePresence mode="popLayout">
                        {s1Visible && (
                            <motion.div
                                key="sidebar1"
                                initial={{ x: -80, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                exit={{ x: -80, opacity: 0 }}
                                transition={{ type: 'tween', duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
                                className="flex shrink-0 z-50 h-full py-1.5 pl-4"
                                style={{ filter: 'drop-shadow(8px 0 24px rgba(0,0,0,0.15))' }}
                            >
                                <WorkspaceMiniSidebar onHide={() => closeLayer('S1')} />
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <main className="flex-1 flex min-w-0 relative overflow-hidden">
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
                                boxShadow: layers.S2
                                    ? '4px 0 16px rgba(0,0,0,0.06), 1px 0 4px rgba(0,0,0,0.04)'
                                    : 'none',
                            }}>
                                {customSidebar || (
                                <WorkspaceMainSidebar
                                        title={displayTitle}
                                        sections={filteredDisplaySections}
                                        isMini={isMiniSidebar}
                                        onToggle={cycleS2}
                                        isCollapsed={!layers.S2}
                                    />
                                )}
                            </div>

                            {layers.S2 && (
                                <div
                                    className="absolute top-0 right-[-3px] w-1.5 h-full cursor-col-resize z-50 group flex items-center justify-center"
                                    onMouseDown={handleMouseDownS2}
                                >
                                    <div className={clsx(
                                        "w-[2px] h-full bg-[hsl(var(--primary))] opacity-0 transition-opacity",
                                        isDraggingS2 ? "opacity-100" : "group-hover:opacity-100"
                                    )} />
                                </div>
                            )}
                        </div>

                        <div className="flex-1 flex flex-col min-w-0 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] shadow-[inset_1px_0_0_rgba(0,0,0,0.03)] dark:shadow-none relative z-10 border-l border-slate-100 dark:border-white/5 overflow-hidden">
                            <div className="flex-1 overflow-hidden relative">
                                <ErrorBoundary moduleName={displayTitle}>
                                    {children}
                                </ErrorBoundary>
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
                            className="fixed bottom-8 right-8 z-[500] size-7 rounded-lg bg-gradient-to-tr from-sky-600 to-sky-600 text-white shadow-2xl shadow-sky-500/40 flex items-center justify-center border border-white/20 group"
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
                            className="fixed left-8 bottom-[88px] z-[60] size-8 bg-slate-900 text-white rounded-md shadow-md hover:bg-slate-800 hover:scale-110 active:scale-95 transition-all flex items-center justify-center border border-white/10 dark:border-[#111213]"
                            aria-label="Mostrar navegación principal"
                        >
                            <ChevronRight size={16} strokeWidth={2.5} />
                        </motion.button>
                    )}

                    {!layers.S2 && (
                        <Tooltip content="Mostrar panel de módulo" side="right">
                            <motion.button
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                onClick={cycleS2}
                                className="fixed left-8 bottom-6 z-[60] size-8 bg-slate-900 text-white rounded-md shadow-md hover:bg-slate-800 hover:-translate-y-1 active:scale-95 active:translate-y-0 transition-all flex items-center justify-center border border-white/10 dark:border-[#111213]"
                                aria-label="Mostrar panel de módulo"
                            >
                                <ChevronRight size={16} strokeWidth={2.5} />
                            </motion.button>
                        </Tooltip>
                    )}
                </div>
            </div>
        </ProtectedRoute>
    );
}

"use client";

import ErrorBoundary from '@/components/ErrorBoundary';
import ProtectedRoute from '@/components/ProtectedRoute';
import MeshChat from '@/components/ui/MeshChat';
import ThemeToggle from '@/components/ui/ThemeToggle';
import Tooltip from '@/components/ui/Tooltip';
import UniversalCreationDrawer from '@/components/ui/UniversalCreationDrawer';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import type { NavSection } from '@/components/WorkspaceMainSidebar';
import WorkspaceMainSidebar from '@/components/WorkspaceMainSidebar';
import WorkspaceMiniSidebar from '@/components/WorkspaceMiniSidebar';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { useCreation } from '@/context/CreationContext';
import clsx from 'clsx';
import { filterWorkspaceSectionsByAccess } from '@/lib/workspaceAccess';
import { SITE_NAME } from '@/lib/site-config';
import { AnimatePresence,motion } from 'framer-motion';
import { Bell,Bot,ChevronLeft,ChevronRight,LayoutPanelLeft,LogOut,Maximize2,Menu,Minimize2,Settings,User } from 'lucide-react';
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
    const { user, hasModuleAccess, hasPermission, logout } = useAuth();
    const pathname = usePathname();
    const moduleKey = pathname?.split('/')[2] || 'default';
    const [showInbox, setShowInbox] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const [isMounted, setIsReady] = useState(false);
    const [isFocusMode, setIsFocusMode] = useState(false);
    const [viewportMode, setViewportMode] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
    const { isModalOpen, closeModal, defaultType } = useCreation();
    const previousLayerStateRef = useRef<{ s1: boolean; s2: boolean } | null>(null);

    // â”€â”€ Layer state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const { layers, openLayer, closeLayer } = useSidebarLayers();

    // S1 visibility is controlled by layers.S1 (always true, but kept in sync)
    const s1Visible = layers.S1;
    const isMobileViewport = viewportMode === 'mobile';
    const isTabletViewport = viewportMode === 'tablet';
    const isCompactViewport = viewportMode !== 'desktop';

    useEffect(() => {
        const syncViewportMode = () => {
            const width = window.innerWidth;
            if (width < 768) setViewportMode('mobile');
            else if (width < 1180) setViewportMode('tablet');
            else setViewportMode('desktop');
        };

        syncViewportMode();
        window.addEventListener('resize', syncViewportMode);
        return () => window.removeEventListener('resize', syncViewportMode);
    }, []);

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

    useEffect(() => {
        if (!isMounted || isFocusMode) return;

        if (isMobileViewport) {
            closeLayer('S1');
            closeLayer('S2');
            return;
        }

        if (isTabletViewport) {
            closeLayer('S1');
            openLayer('S2');
        }
    }, [closeLayer, isFocusMode, isMobileViewport, isMounted, isTabletViewport, openLayer]);

    useEffect(() => {
        if (!isCompactViewport) return;
        closeLayer('S1');
        if (isMobileViewport) closeLayer('S2');
    }, [closeLayer, isCompactViewport, isMobileViewport, pathname]);

    useEffect(() => {
        if (!isCompactViewport) return;
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key !== 'Escape') return;
            closeLayer('S1');
            closeLayer('S2');
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [closeLayer, isCompactViewport]);

    const moduleContext = useMemo(() => {
        const root = pathname?.split('/')[2] || '';
        return MODULE_CONFIGS[root] || { title: SITE_NAME, sections: [] };
    }, [pathname]);

    const displayTitle = manualTitle || moduleContext.title;
    const displaySections = (manualSections || moduleContext.sections) as NavSection[] | undefined;
    const filteredDisplaySections = useMemo(() => {
        return filterWorkspaceSectionsByAccess(displaySections, { hasModuleAccess, hasPermission });
    }, [displaySections, hasModuleAccess, hasPermission]);

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
        if (isTabletViewport && s2WidthNum > 340) {
            setS2WidthNum(320);
        }
    }, [isTabletViewport, s2WidthNum]);

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

    const inlineS1Visible = s1Visible && !isCompactViewport;
    const inlineS2Visible = layers.S2 && !isMobileViewport;
    const tabletS2Width = Math.min(Math.max(s2WidthNum, 240), 340);
    const resolvedS2Width = isTabletViewport ? tabletS2Width : s2WidthNum;
    const isMiniSidebar = inlineS2Visible && resolvedS2Width <= snapThreshold;
    const currentS2Width = inlineS2Visible ? `${resolvedS2Width}px` : '0px';

    const openPrimaryNavigation = useCallback(() => {
        if (isMobileViewport) closeLayer('S2');
        openLayer('S1');
    }, [closeLayer, isMobileViewport, openLayer]);

    const openModuleNavigation = useCallback(() => {
        if (isMobileViewport) closeLayer('S1');
        openLayer('S2');
    }, [closeLayer, isMobileViewport, openLayer]);

    const closeCompactNavigation = useCallback(() => {
        if (!isCompactViewport) return;
        closeLayer('S1');
        closeLayer('S2');
    }, [closeLayer, isCompactViewport]);

    if (!isMounted) return (
        <div className="h-screen w-full bg-[hsl(var(--bg-primary))] dark:bg-[#111213] flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="size-8 rounded-xl bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-white font-bold text-xs">
                    CCF
                </div>
                <div className="size-1.5 rounded-full bg-[hsl(var(--primary))] animate-pulse" />
            </div>
        </div>
    );

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username;

    const responsiveNavigationActions = (
        <div className="hidden items-center gap-1 md:flex xl:hidden">
            <button
                onClick={openPrimaryNavigation}
                className="flex size-8 items-center justify-center rounded-md text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5 dark:hover:text-white"
                aria-label="Abrir navegación principal"
                title="Navegación principal"
            >
                <Menu size={16} />
            </button>
            <button
                onClick={openModuleNavigation}
                className="flex size-8 items-center justify-center rounded-md text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5 dark:hover:text-white"
                aria-label="Abrir navegación del módulo"
                title="Navegación del módulo"
            >
                <LayoutPanelLeft size={16} />
            </button>
        </div>
    );

    // Combined Right Actions for WorkspaceToolbar
    const defaultRightActions = (
        <div className="flex items-center gap-0.5">
            <ThemeToggle variant="pill" />

            <button
                onClick={toggleFocusMode}
                className={clsx(
                    "p-1.5 rounded-md transition-all",
                    isFocusMode
                        ? "bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10 dark:text-[hsl(var(--primary))]"
                        : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"
                )}
                aria-label={isFocusMode ? "Salir de modo enfoque" : "Entrar en modo enfoque"}
                title={isFocusMode ? "Salir de modo enfoque" : "Modo enfoque"}
            >
                {isFocusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>

            <button
                onClick={() => setShowInbox(!showInbox)}
                className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] relative rounded-md hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                aria-label="Notificaciones"
            >
                <Bell size={14} />
                <span className="absolute top-1 right-1 size-1 bg-[hsl(var(--danger))] rounded-full ring-1 ring-white dark:ring-[#141517]" />
            </button>

            <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />

            <UserMenuDropdown displayName={displayName} username={user?.username} logout={logout} />
        </div>
    );

    return (
        <ProtectedRoute allowedRoles={allowedRoles} allowedPermissions={allowedPermissions}>
            <div className="workspace-platform flex h-[100dvh] w-full flex-col overflow-hidden bg-[hsl(var(--surface-1))] font-display transition-colors duration-500 dark:bg-[#111213]">

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
                                    {responsiveNavigationActions}
                                    {depth > 1 && (
                                        <button
                                            onClick={onBack}
                                            className="p-1.5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg transition-all text-[hsl(var(--text-secondary))] mr-1"
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
                        <header className="h-10 border-b border-[hsl(var(--border))]/80 dark:border-white/[0.05] flex items-center px-3 gap-2 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] relative">
                            {responsiveNavigationActions}
                            {depth > 1 && (
                                <button
                                    onClick={onBack}
                                    className="p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md transition-all text-[hsl(var(--text-secondary))]"
                                >
                                    <ChevronLeft size={14} />
                                </button>
                            )}

                            <div className="flex-1 flex items-center gap-2 overflow-hidden min-w-0">
                                <div className="flex items-center gap-1.5 min-w-0">
                                    <div className="size-1.5 rounded-full bg-[hsl(var(--primary))] shrink-0" />
                                    <h1 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate tracking-tight leading-none">
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
                        {inlineS1Visible && (
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
                                !isDraggingS2 && "transition-[width] duration-300 ease-in-out",
                                !inlineS2Visible && "pointer-events-none"
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
                                {customSidebar ? (
                                    <div className="flex flex-col h-full">
                                        <div className="flex-1 overflow-hidden">{customSidebar}</div>
                                        <div className="shrink-0 border-t border-[hsl(var(--border))] dark:border-white/5 p-2 flex justify-end">
                                            <Tooltip content={layers.S2 ? 'Contraer panel' : 'Expandir panel'} side="right">
                                                <button
                                                    onClick={cycleS2}
                                                    className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 transition-all duration-200"
                                                    aria-label={layers.S2 ? 'Contraer sidebar' : 'Expandir sidebar'}
                                                >
                                                    {layers.S2 ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
                                                </button>
                                            </Tooltip>
                                        </div>
                                    </div>
                                ) : (
                                <WorkspaceMainSidebar
                                        title={displayTitle}
                                        sections={filteredDisplaySections}
                                        isMini={isMiniSidebar}
                                        onToggle={cycleS2}
                                        isCollapsed={!layers.S2}
                                    />
                                )}
                            </div>

                            {inlineS2Visible && !isTabletViewport && (
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

                        <div className="flex-1 flex flex-col min-w-0 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] shadow-[inset_1px_0_0_rgba(0,0,0,0.03)] dark:shadow-none relative z-10 border-l border-[hsl(var(--border))] dark:border-white/5 overflow-hidden">
                            <div className="workspace-content flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin relative">
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
                            className="fixed bottom-20 right-4 z-[500] flex size-10 items-center justify-center rounded-lg border border-white/20 bg-gradient-to-tr from-[hsl(var(--info))] to-[hsl(var(--info))] text-white shadow-2xl shadow-[hsl(var(--info))]/40 group sm:bottom-8 sm:right-8 sm:size-9"
                            aria-label="Abrir MESH AI"
                        >
                            <Bot size={20} className="group-hover:animate-pulse" />
                            <div className="absolute -top-1 -right-1 size-4 bg-[hsl(var(--success))] rounded-full border-2 border-white dark:border-[#111213]" />
                        </motion.button>

                        <div className="fixed bottom-4 left-1/2 z-[520] flex -translate-x-1/2 items-center gap-1 rounded-xl border border-[hsl(var(--border))] bg-white/95 p-1 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[#141517]/95 md:hidden">
                            <button
                                onClick={openPrimaryNavigation}
                                className="flex h-10 min-w-12 items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                                aria-label="Abrir navegación principal"
                            >
                                <Menu size={18} />
                            </button>
                            <button
                                onClick={openModuleNavigation}
                                className="flex h-10 min-w-12 items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                                aria-label="Abrir navegación del módulo"
                            >
                                <LayoutPanelLeft size={18} />
                            </button>
                        </div>
                    </main>

                    {!isCompactViewport && !s1Visible && (
                        <motion.button
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            onClick={() => openLayer('S1')}
                            className="fixed left-2 z-[60] size-10 bg-black text-white rounded-lg shadow-lg hover:bg-black/80 hover:scale-110 active:scale-95 transition-all flex items-center justify-center"
                            style={{ bottom: '4.5rem' }}
                            aria-label="Mostrar navegación principal"
                        >
                            <ChevronRight size={20} strokeWidth={2.5} />
                        </motion.button>
                    )}
                    {!isCompactViewport && !layers.S2 && (
                        <motion.button
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.1 }}
                            onClick={() => openLayer('S2')}
                            className="fixed left-2 z-[60] size-10 bg-black text-white rounded-lg shadow-lg hover:bg-black/80 hover:scale-110 active:scale-95 transition-all flex items-center justify-center"
                            style={{ bottom: '2rem' }}
                            aria-label="Mostrar panel de módulo"
                        >
                            <ChevronRight size={20} strokeWidth={2.5} />
                        </motion.button>
                    )}
                </div>

                <AnimatePresence>
                    {isCompactViewport && s1Visible && (
                        <motion.div
                            key="mobile-primary-nav"
                            className="fixed inset-0 z-[900] bg-[hsl(var(--bg-muted))]/40 backdrop-blur-sm"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => closeLayer('S1')}
                        >
                            <motion.div
                                className="absolute bottom-0 left-0 top-0 w-[88px] p-3"
                                initial={{ x: -96 }}
                                animate={{ x: 0 }}
                                exit={{ x: -96 }}
                                transition={{ type: 'tween', duration: 0.2 }}
                                onClick={(event) => {
                                    event.stopPropagation();
                                    if ((event.target as HTMLElement).closest('a')) closeCompactNavigation();
                                }}
                            >
                                <WorkspaceMiniSidebar onHide={() => closeLayer('S1')} />
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <AnimatePresence>
                    {isMobileViewport && layers.S2 && (
                        <motion.div
                            key="mobile-module-nav"
                            className="fixed inset-0 z-[890] bg-[hsl(var(--bg-muted))]/40 backdrop-blur-sm"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => closeLayer('S2')}
                        >
                            <motion.div
                                className="absolute bottom-0 left-0 top-0 w-[min(88vw,360px)] bg-[hsl(var(--bg-primary))] shadow-2xl dark:bg-[#0f1113]"
                                initial={{ x: '-100%' }}
                                animate={{ x: 0 }}
                                exit={{ x: '-100%' }}
                                transition={{ type: 'tween', duration: 0.22 }}
                                onClick={(event) => {
                                    event.stopPropagation();
                                    if ((event.target as HTMLElement).closest('a')) closeCompactNavigation();
                                }}
                            >
                                {customSidebar || (
                                    <WorkspaceMainSidebar
                                        title={displayTitle}
                                        sections={filteredDisplaySections}
                                        isMini={false}
                                        onToggle={() => closeLayer('S2')}
                                        isCollapsed={false}
                                    />
                                )}
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </ProtectedRoute>
    );
}

function UserMenuDropdown({ displayName, username, logout }: { displayName: string; username?: string; logout: () => void }) {
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
                className="flex items-center gap-1.5 h-7 pl-2 pr-1 bg-[hsl(var(--surface-1))] dark:bg-white/[0.06] border border-[hsl(var(--border))] dark:border-white/[0.07] rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all group"
            >
                <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-primary))] dark:group-hover:text-white transition-colors max-w-[80px] truncate">
                    {displayName}
                </span>
                <div className="size-5 rounded-md bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center text-white font-bold text-[8px]">
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
                        className="absolute top-9 right-0 w-56 bg-[hsl(var(--bg-primary))] dark:bg-[#252628] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg shadow-xl py-2 z-[100] origin-top-right"
                    >
                        <div className="px-3 pb-2 mb-1 border-b border-[hsl(var(--border))] dark:border-white/5">
                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">{displayName}</p>
                            <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] truncate">{username}</p>
                        </div>

                        <div className="px-1.5 flex flex-col gap-0.5">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all text-left"
                            >
                                <User size={14} className="text-[hsl(var(--text-secondary))]" />
                                <span>Mi perfil</span>
                            </button>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all text-left"
                            >
                                <Settings size={14} className="text-[hsl(var(--text-secondary))]" />
                                <span>Configuración</span>
                            </button>
                        </div>

                        <div className="mt-1 pt-1 border-t border-[hsl(var(--border))] dark:border-white/5 px-1.5">
                            <button
                                onClick={() => { setIsOpen(false); logout(); }}
                                className="w-full flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-left"
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

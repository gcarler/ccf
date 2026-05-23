"use client";


import React, { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    ChevronDown, Plus,
    ChevronLeft, ChevronRight, Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Tooltip from '@/components/ui/Tooltip';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

interface NavItem {
    id: string;
    label: string;
    href: string;
    icon?: React.ElementType;
    count?: number;
    color?: string;
    suffix?: string;
    onClick?: () => void;
}

interface NavSection {
    title?: string;
    items: NavItem[];
    canAdd?: boolean;
}

interface Props {
    title: string;
    sections?: NavSection[];
    isMini?: boolean;
    onToggle?: () => void;    // callback para colapsar/expandir desde el footer
    isCollapsed?: boolean;    // estado actual para el ícono del botón
}

// ─── Sección expandible genérica ──────────────────────────────────────────────
function SidebarSection({
    title,
    children,
    canAdd,
    defaultOpen = true,
    isMini,
}: {
    title?: string;
    children: React.ReactNode;
    canAdd?: boolean;
    defaultOpen?: boolean;
    isMini?: boolean;
}) {
    const [open, setOpen] = useState(defaultOpen);
    if (isMini) return <div className="mb-0.5">{children}</div>;
    return (
        <div className="mb-0.5">
            {title && (
                <div
                    onClick={() => setOpen(v => !v)}
                    className="flex items-center justify-between px-2.5 py-0.5 cursor-pointer group/hdr"
                >
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 group-hover/hdr:text-slate-600 dark:group-hover/hdr:text-slate-300 transition-colors select-none">
                        {title}
                    </span>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover/hdr:opacity-100 transition-opacity">
                        {canAdd && (
                            <button
                                onClick={e => { e.stopPropagation(); }}
                                className="p-0.5 rounded hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                <Plus size={10} />
                            </button>
                        )}
                        <ChevronDown size={10} className={clsx('text-slate-300 transition-transform', !open && '-rotate-90')} />
                    </div>
                </div>
            )}
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden"
                    >
                        {children}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─── Nav item ───────────────────────────────────────────────────────────────
function NavRow({
    item,
    isActive,
    isMini,
}: {
    item: NavItem;
    isActive: boolean;
    isMini?: boolean;
}) {
    const Icon = item.icon ?? Circle;
    // Items that have a drill-down chevron (indicated by suffix or specific metadata)
    return (
        <Link
            href={item.href}
            onClick={() => {
                if (item.onClick) {
                    item.onClick();
                }
            }}
        >
            <div className={clsx(
                'relative flex items-center gap-1.5 px-2 py-1.5 mx-1.5 rounded-md transition-all duration-150 group cursor-pointer',
                isActive
                    ? 'bg-blue-600/10 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-white/[0.04] hover:text-slate-900 dark:hover:text-white'
            )}>
                {/* Active indicator bar */}
                {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-blue-600 rounded-full -ml-1.5" />
                )}
                {item.color ? (
                    <span
                        className="size-5 rounded shrink-0 flex items-center justify-center text-[9px] font-bold text-white"
                        style={{ backgroundColor: item.color }}
                    >
                        {item.label.charAt(0)}
                    </span>
                ) : (
                    <Icon size={14} className={clsx(
                        'shrink-0 transition-colors',
                        isActive ? 'text-blue-500' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                    )} />
                )}
                {!isMini && (
                    <>
                        <span className={clsx(
                            'text-xs flex-1 truncate leading-none',
                            isActive ? 'font-bold' : 'font-medium'
                        )}>{item.label}</span>
                        {item.count !== undefined && (
                            <span className={clsx(
                                'px-1 py-px rounded text-[9px] font-bold leading-none shrink-0',
                                isActive
                                    ? 'bg-blue-200 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300'
                                    : 'bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400'
                            )}>
                                {item.count}
                            </span>
                        )}
                        <ChevronRight size={10} className={clsx(
                            'shrink-0 transition-all duration-150',
                            isActive ? 'opacity-80 text-blue-500' : 'opacity-0 group-hover:opacity-100 text-slate-400 translate-x-1 group-hover:translate-x-0'
                        )} />
                    </>
                )}
            </div>
        </Link>
    );
}


export default function WorkspaceMainSidebar({ title, sections, isMini, onToggle, isCollapsed }: Props) {
    const pathname = usePathname();
    const { 
        sidebarStack, 
        popSidebarPanel, 
        resetSidebarStack, 
        stackDirection 
    } = useSidebarLayers();

    // Auto-reset when navigating to a different top-level module
    const currentModule = pathname?.split('/')[1] ?? '';
    const prevModuleRef = useRef(currentModule);
    useEffect(() => {
        if (prevModuleRef.current !== currentModule) {
            prevModuleRef.current = currentModule;
            resetSidebarStack();
        }
    }, [currentModule, resetSidebarStack]);

    // Determine current level to render
    const currentLevelIndex = sidebarStack.length;
    const isDrillDown = currentLevelIndex > 0;
    const currentPanel = isDrillDown ? sidebarStack[currentLevelIndex - 1] : null;

    const displayTitle = currentPanel?.title ?? title;

    // Find the single best matching href to prevent multiple active items
    const activeHref = useMemo(() => {
        if (!sections || !pathname) return '';
        let bestMatch = '';
        sections.forEach(group => {
            group.items.forEach(item => {
                if (pathname === item.href) {
                    bestMatch = item.href;
                } else if (item.href !== '/' && pathname.startsWith(item.href)) {
                    // Only match if it's a true subpath (e.g. follows with a slash)
                    const nextChar = pathname[item.href.length];
                    if (!nextChar || nextChar === '/' || nextChar === '?') {
                        if (item.href.length > bestMatch.length) {
                            bestMatch = item.href;
                        }
                    }
                }
            });
        });
        return bestMatch;
    }, [pathname, sections]);

    return (
        <aside className="h-full flex flex-col bg-white dark:bg-[#0f1113] transition-colors duration-500 ease-in-out relative overflow-hidden">
            <div className="shrink-0 border-b border-slate-100 dark:border-white/[0.04] relative z-20 bg-white/80 dark:bg-[#0f1113]/80 backdrop-blur-xl">
                {/* 1. Breadcrumbs (Opcional pero recomendado para contexto) */}
                {!isMini && (
                    <div className="px-3 pt-2 pb-0.5 flex items-center gap-1.5 overflow-hidden min-h-[18px]">
                        <span
                            onClick={() => resetSidebarStack()}
                            className={clsx(
                                "text-[9px] font-semibold uppercase tracking-wide transition-all cursor-pointer",
                                isDrillDown ? "text-slate-400 hover:text-blue-500" : "text-blue-600"
                            )}
                        >
                            {title}
                        </span>
                        {isDrillDown && sidebarStack.map((level, i) => (
                            <React.Fragment key={level.id}>
                                <div className="size-[3px] rounded-full bg-slate-300 dark:bg-white/10 shrink-0" />
                                <span className={clsx(
                                    "text-[9px] font-semibold uppercase tracking-wide truncate transition-all",
                                    i === sidebarStack.length - 1 ? "text-slate-900 dark:text-white" : "text-slate-400"
                                )}>
                                    {level.title}
                                </span>
                            </React.Fragment>
                        ))}
                    </div>
                )}

                {/* 2. Header Anatomy: Botón Atrás + Título */}
                <div className="h-10 flex items-center px-3 gap-2">
                    {!isMini && (
                        <>
                            {isDrillDown && (
                                <motion.button
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    whileHover={{ x: -2 }}
                                    onClick={() => {
                                        if (currentPanel?.onBack) currentPanel.onBack();
                                        popSidebarPanel();
                                    }}
                                    className="p-1 -ml-1 rounded-md bg-slate-50 dark:bg-white/5 text-slate-500 hover:text-blue-600 hover:bg-white dark:hover:bg-white/10 transition-all flex items-center justify-center shrink-0 border border-slate-100 dark:border-white/5 active:scale-90"
                                >
                                    <ChevronLeft size={14} strokeWidth={2.5} />
                                </motion.button>
                            )}
                            <h2 className={clsx(
                                "text-sm font-bold text-slate-900 dark:text-white truncate tracking-tight flex-1",
                                isDrillDown && "italic"
                            )}>
                                {displayTitle}
                            </h2>
                        </>
                    )}
                </div>
            </div>

            {/* 3. Body: Contenido con animación de Slide Direccional */}
            <div className="flex-1 relative overflow-hidden bg-slate-50/30 dark:bg-black/5">
                <AnimatePresence mode="popLayout" custom={stackDirection} initial={false}>
                    <motion.div
                        key={isDrillDown && currentPanel ? currentPanel.id : 'base'}
                        custom={stackDirection}
                        variants={{
                            enter: (dir: string) => ({
                                x: dir === 'forward' ? '100%' : '-100%',
                                opacity: 0
                            }),
                            center: {
                                x: 0,
                                opacity: 1
                            },
                            exit: (dir: string) => ({
                                x: dir === 'forward' ? '-100%' : '100%',
                                opacity: 0
                            })
                        }}
                        initial="enter"
                        animate="center"
                        exit="exit"
                        transition={{ 
                            type: 'spring', 
                            damping: 32, 
                            stiffness: 300,
                            mass: 0.6,
                            restDelta: 0.001
                        }}
                        className="absolute inset-0 overflow-y-auto scrollbar-hide py-3 space-y-0.5"
                    >
                        {isDrillDown && currentPanel ? currentPanel.content : (
                            <>
                                {sections && sections.length > 0 && sections.map((group, idx) => (
                                    <SidebarSection
                                        key={group.title ?? idx}
                                        title={group.title}
                                        canAdd={group.canAdd}
                                        isMini={isMini}
                                        defaultOpen
                                    >
                                        {group.items.map(item => {
                                            const isActive = item.href === activeHref;
                                            return (
                                                <NavRow key={item.id} item={item} isActive={isActive} isMini={isMini} />
                                            );
                                        })}
                                    </SidebarSection>
                                ))}

                                {/* Fallback content */}
                                {!sections?.length && !isMini && (
                                    <div className="px-3 py-1.5 text-center space-y-3 opacity-40">
                                        <Circle size={40} className="mx-auto text-slate-200" />
                                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Sin contenido</p>
                                    </div>
                                )}
                            </>
                        )}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* ── Footer S2: Expand/Collapse toggle ── */}
            <div className={clsx(
                "shrink-0 border-t border-slate-100 dark:border-white/5 p-2 flex items-center",
                isMini ? "flex-col gap-2 justify-center" : "justify-end"
            )}>
                {/* Collapse / Expand toggle */}
                {onToggle && (
                    <Tooltip content={isCollapsed ? 'Expandir panel' : 'Contraer panel'} side="right">
                        <button
                            onClick={onToggle}
                            className="p-2 rounded-md text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200 shrink-0"
                            aria-label={isCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
                        >
                            {isCollapsed
                                ? <ChevronRight size={16} />
                                : <ChevronLeft size={16} />
                            }
                        </button>
                    </Tooltip>
                )}
            </div>
        </aside>
    );
}

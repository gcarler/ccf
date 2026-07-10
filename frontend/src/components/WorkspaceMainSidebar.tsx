"use client";


import React, { useState, useEffect, useRef, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import OptimizedImage from '@/components/ui/OptimizedImage';
import {
    ChevronDown, Plus,
    ChevronLeft, ChevronRight, Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Tooltip from '@/components/ui/Tooltip';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { SITE_NAME } from '@/lib/site-config';
import { useSiteBranding } from '@/lib/site-branding';

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
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] group-hover/hdr:text-[hsl(var(--text-secondary))] dark:group-hover/hdr:text-[hsl(var(--text-secondary))] transition-colors select-none">
                        {title}
                    </span>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover/hdr:opacity-100 transition-opacity">
                        {canAdd && (
                            <button
                                onClick={e => { e.stopPropagation(); }}
                                className="p-0.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]"
                            >
                                <Plus size={10} />
                            </button>
                        )}
                        <ChevronDown size={10} className={clsx('text-[hsl(var(--text-secondary))] transition-transform', !open && '-rotate-90')} />
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
            prefetch={false}
            onClick={() => {
                if (item.onClick) {
                    item.onClick();
                }
            }}
        >
            <div className={clsx(
                'relative flex items-center gap-1.5 px-2 py-1.5 mx-1.5 rounded-md transition-all duration-150 group cursor-pointer',
                isActive
                    ? 'bg-blue-600/10 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-blue-300'
                    : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]/80 dark:hover:bg-white/[0.04] hover:text-navy-dark dark:hover:text-white'
            )}>
                {/* Active indicator bar */}
                {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-[hsl(var(--primary))] rounded-full -ml-1.5" />
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
                        isActive ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))] dark:group-hover:text-[hsl(var(--text-secondary))]'
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
                                    ? 'bg-blue-200 dark:bg-blue-500/20 text-[hsl(var(--primary))] dark:text-blue-300'
                                    : 'bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                            )}>
                                {item.count}
                            </span>
                        )}
                        <ChevronRight size={10} className={clsx(
                            'shrink-0 transition-all duration-150',
                            isActive ? 'opacity-80 text-[hsl(var(--primary))]' : 'opacity-0 group-hover:opacity-100 text-[hsl(var(--text-secondary))] translate-x-1 group-hover:translate-x-0'
                        )} />
                    </>
                )}
            </div>
        </Link>
    );
}


export default function WorkspaceMainSidebar({ title, sections, isMini, onToggle, isCollapsed }: Props) {
    const pathname = usePathname();
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
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
        <aside className="h-full flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#0f1113] transition-colors duration-500 ease-in-out relative overflow-hidden">
            <div className="shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.04] relative z-20 bg-white/80 dark:bg-[#0f1113]/80 backdrop-blur-xl">
                {!isMini && (
                    <div className="px-3 pt-3 pb-2 flex items-center gap-2.5">
                        {logoUrl ? (
                            <OptimizedImage
                                src={logoUrl}
                                alt={logoName || SITE_NAME}
                                width={28}
                                height={28}
                                className="size-7 object-contain shrink-0"
                            />
                        ) : (
                            <div className="size-7 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white font-black text-[10px] shrink-0">
                                CCF
                            </div>
                        )}
                        <div className="min-w-0">
                            <p className="text-[10px] font-black uppercase tracking-[0.25em] text-[hsl(var(--text-primary))] dark:text-white truncate">
                                {logoName || SITE_NAME}
                            </p>
                            <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))] truncate">
                                {displayTitle}
                            </p>
                        </div>
                    </div>
                )}
                {/* 1. Breadcrumbs (Opcional pero recomendado para contexto) */}
                {!isMini && (
                    <div className="px-3 pt-2 pb-0.5 flex items-center gap-1.5 overflow-hidden min-h-[18px]">
                        <span
                            onClick={() => resetSidebarStack()}
                            className={clsx(
                                "text-[9px] font-semibold uppercase tracking-wide transition-all cursor-pointer",
                                isDrillDown ? "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]" : "text-[hsl(var(--primary))]"
                            )}
                        >
                            {title}
                        </span>
                        {isDrillDown && sidebarStack.map((level, i) => (
                            <React.Fragment key={level.id}>
                                <div className="size-[3px] rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 shrink-0" />
                                <span className={clsx(
                                    "text-[9px] font-semibold uppercase tracking-wide truncate transition-all",
                                    i === sidebarStack.length - 1 ? "text-[hsl(var(--text-primary))] dark:text-white" : "text-[hsl(var(--text-secondary))]"
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
                                    className="p-1 -ml-1 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10 transition-all flex items-center justify-center shrink-0 border border-[hsl(var(--border))] dark:border-white/5 active:scale-90"
                                >
                                    <ChevronLeft size={14} strokeWidth={2.5} />
                                </motion.button>
                            )}
                            <h2 className={clsx(
                                "text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white truncate tracking-tight flex-1",
                                isDrillDown && "italic"
                            )}>
                                {displayTitle}
                            </h2>
                        </>
                    )}
                </div>
            </div>

            {/* 3. Body: Contenido con animación de Slide Direccional */}
            <div className="flex-1 relative overflow-hidden bg-[hsl(var(--surface-1))]/30 dark:bg-black/5">
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
                                        <Circle size={40} className="mx-auto text-[hsl(var(--text-secondary))]" />
                                        <p className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin contenido</p>
                                    </div>
                                )}
                            </>
                        )}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* ── Footer S2: Expand/Collapse toggle ── */}
            <div className={clsx(
                "shrink-0 border-t border-[hsl(var(--border))] dark:border-white/5 p-2 flex items-center",
                isMini ? "flex-col gap-2 justify-center" : "justify-end"
            )}>
                {/* Collapse / Expand toggle */}
                {onToggle && (
                    <Tooltip content={isCollapsed ? 'Expandir panel' : 'Contraer panel'} side="right">
                        <button
                            onClick={onToggle}
                            className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200 shrink-0"
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

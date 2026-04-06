"use client";


import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    ChevronDown, Plus, Settings2,
    Hash, PanelLeftClose, PanelLeftOpen, Circle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Tooltip from '@/components/ui/Tooltip';

interface NavItem {
    id: string;
    label: string;
    href: string;
    icon?: React.ElementType;
    count?: number;
    color?: string;
    suffix?: string;
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
    if (isMini) return <div className="mb-1">{children}</div>;
    return (
        <div className="mb-1">
            {title && (
                <div
                    onClick={() => setOpen(v => !v)}
                    className="flex items-center justify-between px-4 py-1 cursor-pointer group/hdr"
                >
                    <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 group-hover/hdr:text-slate-600 dark:group-hover/hdr:text-slate-300 transition-colors select-none">
                        {title}
                    </span>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover/hdr:opacity-100 transition-opacity">
                        {canAdd && (
                            <button
                                onClick={e => { e.stopPropagation(); }}
                                className="p-0.5 rounded hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                <Plus size={12} />
                            </button>
                        )}
                        <ChevronDown size={11} className={clsx('text-slate-300 transition-transform', !open && '-rotate-90')} />
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
    return (
        <Link href={item.href}>
            <div className={clsx(
                'relative flex items-center gap-2.5 px-3 py-2 mx-2 rounded-lg transition-all duration-150 group cursor-pointer',
                isActive
                    ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/[0.04] hover:text-slate-900 dark:hover:text-white'
            )}>
                {/* Active indicator bar */}
                {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-500 rounded-full -ml-2" />
                )}
                {item.color ? (
                    <span
                        className="size-4 rounded shrink-0 flex items-center justify-center text-[10px] font-black text-white"
                        style={{ backgroundColor: item.color }}
                    >
                        {item.label.charAt(0)}
                    </span>
                ) : (
                    <Icon size={15} className={clsx(
                        'shrink-0 transition-colors',
                        isActive ? 'text-blue-500' : 'text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300'
                    )} />
                )}
                {!isMini && (
                    <>
                        <span className={clsx(
                            'text-[13px] flex-1 truncate leading-none',
                            isActive ? 'font-semibold' : 'font-medium'
                        )}>{item.label}</span>
                        {item.suffix && (
                            <span className="text-[10px] text-slate-400 shrink-0 truncate max-w-[80px]">{item.suffix}</span>
                        )}
                        {item.count !== undefined && item.count > 0 && (
                            <span className={clsx(
                                'px-1.5 py-0.5 rounded-md text-[9px] font-black leading-none shrink-0',
                                isActive
                                    ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-300'
                                    : 'bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400'
                            )}>
                                {item.count}
                            </span>
                        )}
                    </>
                )}
            </div>
        </Link>
    );
}

export default function WorkspaceMainSidebar({ title, sections, isMini, onToggle, isCollapsed }: Props) {
    const pathname = usePathname();

    return (
        <aside className="h-full flex flex-col bg-white dark:bg-[#1e1f21] transition-colors duration-300 ease-in-out">
            {/* Module title header */}
            <div className="h-[50px] flex items-center px-4 border-b border-slate-100 dark:border-white/[0.05] shrink-0">
                {!isMini && (
                    <h2 className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate tracking-tight">
                        {title}
                    </h2>
                )}
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-0">
                {/* ── Custom sections from parent ── */}
                {sections && sections.length > 0 && sections.map((group, idx) => (
                    <SidebarSection
                        key={group.title ?? idx}
                        title={group.title}
                        canAdd={group.canAdd}
                        isMini={isMini}
                        defaultOpen
                    >
                        {group.items.map(item => {
                            const isActive = pathname === item.href ||
                                !!(item.href !== '/' && pathname?.startsWith(item.href));
                            return (
                                <NavRow key={item.id} item={item} isActive={isActive} isMini={isMini} />
                            );
                        })}
                    </SidebarSection>
                ))}

                {/* ── ClickUp-style fallback ── */}
                {!sections?.length && !isMini && (
                    <>
                        <SidebarSection title="Favoritos">
                            <div className="px-4 py-3">
                                <p className="text-[11px] text-slate-300 dark:text-slate-600">
                                    Haz clic en ☆ para añadir favoritos.
                                </p>
                            </div>
                        </SidebarSection>

                        <SidebarSection title="Canales" canAdd>
                            <NavRow
                                item={{ id: 'ch-welcome', label: 'Welcome', href: '#', icon: Hash }}
                                isActive={false}
                            />
                            <div className="flex items-center gap-2 px-5 py-1.5 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer transition-colors">
                                <Plus size={13} />
                                Añadir canal
                            </div>
                        </SidebarSection>
                    </>
                )}
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
                            className="p-2 rounded-xl text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200 shrink-0"
                            aria-label={isCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
                        >
                            {isCollapsed
                                ? <PanelLeftOpen size={16} />
                                : <PanelLeftClose size={16} />
                            }
                        </button>
                    </Tooltip>
                )}
            </div>
        </aside>
    );
}

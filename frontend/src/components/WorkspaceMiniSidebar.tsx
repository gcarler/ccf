"use client";


import React, { useCallback } from 'react';
import {
    Layout,
    Users,
    GraduationCap,
    Globe,
    Settings,
    ChevronLeft,
    Plus,
    Target,
    DollarSign,
    CalendarDays,
    Inbox,
    Heart,
    BookOpen,
    Shield,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import Tooltip from '@/components/ui/Tooltip';
import clsx from 'clsx';
import { useCreation } from '@/context/CreationContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

export default function WorkspaceMiniSidebar({ onHide }: { onHide: () => void }) {
    const pathname = usePathname();
    const { openModal } = useCreation();
    const { resetSidebarStack } = useSidebarLayers();

    const primaryItems = [
        { id: 'projects', icon: Target,       href: '/projects',  label: 'Proyectos' },
        { id: 'tasks',    icon: Layout,        href: '/tasks',     label: 'Mis Tareas' },
        { id: 'calendar', icon: CalendarDays,  href: '/calendar',  label: 'Calendario' },
    ];

    const moduleItems = [
        { id: 'academy',       icon: GraduationCap, href: '/academy',        label: 'Academia' },
        { id: 'crm',           icon: Users,         href: '/crm',            label: 'Pastoral' },
        { id: 'community',     icon: Globe,         href: '/community',      label: 'Comunidad' },
        { id: 'finances',      icon: DollarSign,    href: '/finances',       label: 'Finanzas' },
        { id: 'cms',           icon: Globe,         href: '/cms',            label: 'Sitio Web' },
        { id: 'wiki',          icon: BookOpen,      href: '/wiki',           label: 'Wiki' },
        { id: 'spiritual-life',icon: Heart,         href: '/spiritual-life', label: 'Vida Espiritual' },
        { id: 'admin',         icon: Shield,        href: '/admin',          label: 'Admin' },
    ];

    const NavItem = ({ id, icon: Icon, href, label, badge }: any) => {
        const isActive = pathname?.startsWith(href);
        return (
            <Tooltip key={id} content={label} side="right">
                <Link href={href} className="relative" onClick={() => resetSidebarStack()}>
                    <div className={clsx(
                        "size-10 rounded-2xl flex items-center justify-center transition-all duration-200 cursor-pointer",
                        isActive
                            ? "bg-blue-600/10 dark:bg-white/10 text-blue-600 dark:text-white shadow-inner"
                            : "text-slate-400 dark:text-slate-500 hover:bg-black/5 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-300"
                    )}>
                        <Icon size={19} className={clsx(isActive && "text-blue-500")} />
                        {badge && (
                            <span className="absolute -top-0.5 -right-0.5 size-4 rounded-full bg-rose-500 text-white text-[8px] font-black flex items-center justify-center border-2 border-white dark:border-black">
                                {badge}
                            </span>
                        )}
                    </div>
                </Link>
            </Tooltip>
        );
    };

    return (
        <aside className="w-16 h-full bg-white dark:bg-black border-r border-slate-100 dark:border-white/5 rounded-[2rem] flex flex-col items-center py-5 gap-1 shadow-2xl relative overflow-hidden">
            {/* Global Add Button */}
            <button
                onClick={() => openModal('task')}
                className="size-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-lg shadow-blue-500/40 group relative mb-4"
            >
                <Plus size={20} />
                <div className="absolute left-14 px-2 py-1 bg-slate-800 text-white text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-[100]">
                    Creación Rápida
                </div>
            </button>

            {/* Primary workspace items */}
            {primaryItems.map(item => <NavItem key={item.id} {...item} />)}

            {/* Separator */}
            <div className="w-6 h-px bg-slate-100 dark:bg-white/10 my-2" />

            {/* Module items */}
            {moduleItems.map(item => <NavItem key={item.id} {...item} />)}

            {/* Separator */}
            <div className="w-6 h-px bg-slate-100 dark:bg-white/10 my-2" />

            {/* Inbox with badge */}
            <NavItem id="inbox" icon={Inbox} href="/inbox" label="Bandeja" badge={3} />

            {/* ── Footer: solo Settings + Collapse (SIN ThemeToggle — ya está en el header) */}
            <div className="mt-auto flex flex-col items-center gap-1 pb-1">
                <Tooltip content="Ajustes" side="right">
                    <Link href="/settings">
                        <div className="size-10 rounded-2xl flex items-center justify-center text-slate-400 dark:text-slate-500 hover:bg-black/5 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-300 transition-all duration-200 cursor-pointer">
                            <Settings size={19} />
                        </div>
                    </Link>
                </Tooltip>

                <Tooltip content="Ocultar barra" side="right">
                    <button
                        onClick={onHide}
                        className="size-10 rounded-2xl flex items-center justify-center text-slate-400 dark:text-slate-600 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/10 transition-all duration-200 group"
                        aria-label="Ocultar sidebar principal"
                    >
                        <ChevronLeft size={19} />
                    </button>
                </Tooltip>
            </div>
        </aside>
    );
}

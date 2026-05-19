"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import {
    LayoutDashboard,
    MessageCircle,
    Feather,
    CalendarRange,
    Link2,
    FileText,
    Globe,
    ChevronRight,
    Palette,
    PanelsTopLeft,
    ImageIcon,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { canEditCms, canManageSites } from '@/lib/cms/permissions';

// ── Tabs compartidos en todas las páginas del módulo CMS ──────────
const CMS_TABS = [
    { id: 'resumen',     label: 'Resumen',      href: '/cms',               icon: LayoutDashboard },
    { id: 'paginas',     label: 'Páginas',      href: '/cms/pages',         icon: FileText },
    { id: 'testimonios', label: 'Testimonios',  href: '/cms/testimonials',  icon: MessageCircle },
    { id: 'hero',        label: 'Landing Hero', href: '/cms/content',       icon: Feather },
    { id: 'eventos',     label: 'Eventos',      href: '/cms/events',        icon: CalendarRange },
    { id: 'menus',       label: 'Menús',        href: '/cms/menus',         icon: Link2 },
    { id: 'media',       label: 'Media',        href: '/cms/media',         icon: ImageIcon },
    { id: 'builder',     label: 'Builder',      href: '/cms/builder',       icon: PanelsTopLeft },
    { id: 'themes',      label: 'Temas',        href: '/cms/themes',        icon: Palette },
    { id: 'sites',       label: 'Sitios',       href: '/cms/sites',         icon: Globe },
] as const;

// Sub-páginas que ya renderizan sus propios tabs (cms/page.tsx los tiene inline)
// Para evitar duplicación, el layout sólo inyecta los tabs en las SUB-páginas
const ROOT_CMS_PATH = '/cms';

function CmsTabsToolbar() {
    const pathname = usePathname();
    const { user } = useAuth();
    const canEdit = canEditCms(user?.role);
    const canManage = canManageSites(user?.role);
    const availableTabs = CMS_TABS.filter((tab) => {
        if (tab.id === 'sites') return canManage;
        if (tab.id !== 'resumen') return canEdit;
        return true;
    });

    const activeTab = availableTabs.find(t => {
        if (t.href === ROOT_CMS_PATH) return pathname === ROOT_CMS_PATH;
        return pathname ? pathname.startsWith(t.href) : false;
    })?.id ?? 'resumen';

    // No inyectar en la raíz /cms porque esa página ya tiene sus propios tabs inline
    if (pathname === ROOT_CMS_PATH) return null;

    const activeLabel = availableTabs.find(t => t.id === activeTab)?.label ?? 'CMS';

    return (
        <div className="shrink-0 border-b border-slate-100 dark:border-white/[0.05] bg-white dark:bg-[#141517]">
            {/* Breadcrumbs row */}
            <div className="flex items-center gap-1.5 px-5 pt-2.5 pb-0">
                <Globe size={11} className="text-slate-400" />
                <span className="text-[11px] text-slate-400">Sitio Web</span>
                <ChevronRight size={10} className="text-slate-300" />
                <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-200">
                    {activeLabel}
                </span>
            </div>

            {/* Tabs row */}
            <div className="flex items-center gap-0 px-4 pt-1">
                {availableTabs.map(tab => {
                    const Icon = tab.icon;
                    const isActive = tab.id === activeTab;
                    return (
                        <Link
                            key={tab.id}
                            href={tab.href}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-[2px] transition-all whitespace-nowrap',
                                isActive
                                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                                    : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300'
                            )}
                        >
                            <Icon size={13} />
                            {tab.label}
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}

export default function CmsLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout>
            <CmsContent>{children}</CmsContent>
        </WorkspaceLayout>
    );
}

// Separate client component so usePathname works inside the server-renderable layout
function CmsContent({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isRoot = pathname === ROOT_CMS_PATH;

    if (isRoot) {
        // Root /cms has its own tabs inline — pass through directly
        return <>{children}</>;
    }

    return (
        <div className="flex flex-col h-full">
            <CmsTabsToolbar />
            <div className="flex-1 overflow-hidden">
                {children}
            </div>
        </div>
    );
}


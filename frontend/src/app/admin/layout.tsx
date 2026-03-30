"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    LayoutDashboard, 
    Users, 
    TrendingUp, 
    CheckSquare,
    FileText,
    MessageSquare,
    Globe,
    Megaphone,
    Search,
    Settings,
    Heart,
    BarChart3,
    Shield
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Gestión',
        items: [
            { id: 'dashboard', label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
            { id: 'users', label: 'Usuarios & Permisos', href: '/admin/users', icon: Shield },
            { id: 'radar', label: 'Radar del Pastor', href: '/admin/dashboard/radar', icon: BarChart3 },
            { id: 'comunidad', label: 'Comunidad', href: '/admin/members', icon: Users },
        ]
    },
    {
        title: 'Ministerial',
        items: [
            { id: 'milestones', label: 'Hitos Espirituales', href: '/admin/spiritual-life/milestones', icon: Heart },
            { id: 'candidates', label: 'Candidatos Bautismo', href: '/admin/analytics/candidates', icon: Users },
            { id: 'finanzas', label: 'Finanzas', href: '/admin/finance', icon: TrendingUp },
        ]
    },
    {
        title: 'Operaciones',
        items: [
            { id: 'assets', label: 'Inventario de Activos', href: '/admin/inventory', icon: CheckSquare },
            { id: 'actas', label: 'Actas', href: '/admin/actas', icon: CheckSquare },
            { id: 'submissions', label: 'Calificaciones', href: '/admin/submissions', icon: FileText },
        ]
    },
    {
        title: 'Gestor Web (CMS)',
        items: [
            { id: 'cms', label: 'Páginas Web', href: '/admin/cms', icon: Globe },
            { id: 'announcements', label: 'Anuncios', href: '/admin/announcements', icon: Megaphone },
        ]
    }
];

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname() ?? '';

    // If a route manages its own deep layer, avoid double-rendering
    const isDeepLayer = pathname.includes('/settings/system') || pathname.includes('/settings/roles') || pathname.includes('/members/');
    if (isDeepLayer) {
        return <div className="h-full w-full">{children}</div>;
    }

    const getSidebarTitle = () => {
        if ((pathname || '') === '/admin') return 'Panel / Dashboard';
        const segments = (pathname || '').split('/');
        const last = segments[segments.length - 1];
        return `Panel / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    return (
        <WorkspaceLayout 
            sidebarTitle={getSidebarTitle()} 
            sidebarSections={SIDEBAR_SECTIONS}
            allowedRoles={['admin', 'coordinador', 'docente']}
        >
            <div className="h-full w-full">
                {children}
            </div>
        </WorkspaceLayout>
    );
}

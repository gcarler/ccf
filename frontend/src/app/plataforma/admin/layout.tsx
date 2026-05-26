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
    Globe,
    Megaphone,
    Heart,
    BarChart3,
    Shield,
    Church,
    Home,
    Lock,
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Gestión',
        items: [
            { id: 'dashboard', label: 'Dashboard', href: '/plataforma/admin', icon: LayoutDashboard },
            { id: 'access', label: 'Acceso', href: '/plataforma/admin/access', icon: Lock },
            { id: 'users', label: 'Usuarios & Permisos', href: '/plataforma/admin/users', icon: Shield },
            { id: 'radar', label: 'Radar del Pastor', href: '/plataforma/admin/dashboard/radar', icon: BarChart3 },
            { id: 'comunidad', label: 'Comunidad', href: '/plataforma/admin/members', icon: Users },
        ]
    },
    {
        title: 'Ministerial',
        items: [
            { id: 'ministerios', label: 'Ministerios', href: '/plataforma/admin/ministerios', icon: Church },
            { id: 'familias', label: 'Familias', href: '/plataforma/admin/familias', icon: Home },
            { id: 'milestones', label: 'Hitos Espirituales', href: '/plataforma/admin/spiritual-life/milestones', icon: Heart },
            { id: 'candidates', label: 'Candidatos Bautismo', href: '/plataforma/admin/analytics/candidates', icon: Users },
            { id: 'finanzas', label: 'Finanzas', href: '/plataforma/admin/finance', icon: TrendingUp },
        ]
    },
    {
        title: 'Operaciones',
        items: [
            { id: 'assets', label: 'Inventario de Activos', href: '/plataforma/admin/inventory', icon: CheckSquare },
            { id: 'actas', label: 'Actas', href: '/plataforma/admin/actas', icon: CheckSquare },
            { id: 'submissions', label: 'Calificaciones', href: '/plataforma/admin/submissions', icon: FileText },
        ]
    },
    {
        title: 'Gestor Web (CMS)',
        items: [
            { id: 'cms', label: 'Páginas Web', href: '/plataforma/admin/cms', icon: Globe },
            { id: 'announcements', label: 'Anuncios', href: '/plataforma/admin/announcements', icon: Megaphone },
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
        if ((pathname || '') === '/plataforma/admin') return 'Panel / Dashboard';
        const segments = (pathname || '').split('/');
        const last = segments[segments.length - 1];
        return `Panel / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    return (
        <WorkspaceLayout
            sidebarTitle={getSidebarTitle()}
            sidebarSections={SIDEBAR_SECTIONS}
            allowedRoles={['admin', 'coordinador', 'docente']}
            allowedPermissions={['system:config']}
        >
            <div className="h-full w-full">
                {children}
            </div>
        </WorkspaceLayout>
    );
}


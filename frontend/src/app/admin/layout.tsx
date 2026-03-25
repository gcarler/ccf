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
    BarChart3
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Gestión',
        items: [
            { id: 'dashboard', label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
            { id: 'comunidad', label: 'Comunidad', href: '/admin/members', icon: Users },
            { id: 'finanzas', label: 'Finanzas', href: '/admin/finance', icon: TrendingUp },
            { id: 'donaciones', label: 'Donaciones', href: '/admin/donations/config', icon: Heart },
        ]
    },
    {
        title: 'Operaciones',
        items: [
            { id: 'actas', label: 'Actas', href: '/admin/actas', icon: CheckSquare },
            { id: 'submissions', label: 'Calificaciones', href: '/admin/submissions', icon: FileText },
            { id: 'moderation', label: 'Moderación', href: '/admin/testimonials', icon: MessageSquare },
            { id: 'reports', label: 'Reportes', href: '/admin/reports', icon: BarChart3 },
        ]
    },
    {
        title: 'Gestor Web (CMS)',
        items: [
            { id: 'cms', label: 'Páginas Web', href: '/admin/cms', icon: Globe },
            { id: 'announcements', label: 'Anuncios', href: '/admin/announcements', icon: Megaphone },
            { id: 'comments', label: 'Comentarios', href: '/admin/comments', icon: MessageSquare },
        ]
    },
    {
        title: 'Sistema',
        items: [
            { id: 'settings', label: 'Configuración', href: '/admin/settings', icon: Settings },
        ]
    }
];

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname() ?? '';

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
        >
            <div className="h-full w-full">
                {children}
            </div>
        </WorkspaceLayout>
    );
}

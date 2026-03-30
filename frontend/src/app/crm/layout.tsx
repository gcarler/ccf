"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    LayoutDashboard, 
    Inbox, 
    CheckCircle2, 
    Target,
    Layers,
    Heart,
    Home as HouseIcon,
    Users,
    ShieldCheck,
    Calendar,
    QrCode,
    Settings,
    BarChart3
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Favoritos',
        items: [
            { id: 'dashboard', label: 'Inicio', href: '/crm', icon: LayoutDashboard },
            { id: 'analytics', label: 'Analítica', href: '/crm/analytics', icon: BarChart3 },
            { id: 'messaging', label: 'Mensajería', href: '/crm/messaging', icon: Inbox },
            { id: 'projects', label: 'Proyectos', href: '/crm/pipeline', icon: Target },
        ]
    },
    {
        title: 'Ministerio',
        canAdd: true,
        items: [
            { id: 'pipeline', label: 'Consolidación', href: '/crm/pipeline', icon: Layers },
            { id: 'counseling', label: 'Consejería', href: '/crm/counseling', icon: Heart },
            { id: 'groups', label: 'Casas de Gloria', href: '/crm/groups', icon: HouseIcon },
        ]
    },
    {
        title: 'Comunidad',
        canAdd: true,
        items: [
            { id: 'members', label: 'Miembros', href: '/crm/members', icon: Users },
            { id: 'volunteers', label: 'Servidores', href: '/crm/volunteers', icon: ShieldCheck },
            { id: 'events', label: 'Eventos', href: '/crm/events', icon: Calendar },
        ]
    },
    {
        title: 'Personal',
        items: [
            { id: 'card', label: 'Mi Carnet', href: '/crm/my-card', icon: QrCode },
            { id: 'settings', label: 'Configuración', href: '/crm/settings', icon: Settings },
        ]
    }
];

export default function CrmLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const getSidebarTitle = () => {
        if (!pathname || pathname === '/crm') return 'CRM / Dashboard';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `CRM / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    return (
        <WorkspaceLayout 
            sidebarTitle={getSidebarTitle()} 
            sidebarSections={SIDEBAR_SECTIONS}
        >
            <div className="bg-[#f8f9fb] min-h-full">
                {children}
            </div>
        </WorkspaceLayout>
    );
}


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
    PieChart,
    UserPlus,
    KanbanSquare,
    MessageCircle,
    Mail,
    Contact,
    Scan
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Actividad y Métricas',
        items: [
            { id: 'analytics', label: 'Panel Analítico', href: '/crm/analytics', icon: PieChart },
        ]
    },
    {
        title: 'Directorio Pastoral',
        items: [
            { id: 'members', label: 'Miembros', href: '/crm/members', icon: Users },
            { id: 'groups', label: 'Casas de Gloria', href: '/crm/groups', icon: HouseIcon },
            { id: 'contacts', label: 'Contactos/Leads', href: '/crm/contacts', icon: UserPlus },
            { id: 'volunteers', label: 'Voluntariado', href: '/crm/volunteers', icon: ShieldCheck },
        ]
    },
    {
        title: 'Consolidación',
        items: [
            { id: 'pipeline', label: 'Pipeline pastoral', href: '/crm/pipeline', icon: KanbanSquare },
            { id: 'counseling', label: 'Consejería', href: '/crm/counseling', icon: Heart },
            { id: 'prayers', label: 'Muro de Oración', href: '/crm/prayers', icon: MessageCircle },
            { id: 'tasks', label: 'Tareas Asignadas', href: '/crm/tasks', icon: CheckCircle2 },
        ]
    },
    {
        title: 'Herramientas',
        items: [
            { id: 'events', label: 'Eventos', href: '/crm/events', icon: Calendar },
            { id: 'scanner', label: 'Escáner ASST', href: '/crm/scanner', icon: Scan },
            { id: 'messaging', label: 'Mensajería', href: '/crm/messaging', icon: Mail },
            { id: 'card', label: 'Mi Carnet', href: '/crm/my-card', icon: Contact },
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
        if (pathname === '/crm') return 'CRM Pastoral';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `CRM / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    return (
        <WorkspaceLayout 
            sidebarTitle={getSidebarTitle()} 
            sidebarSections={SIDEBAR_SECTIONS}
        >
            <div className="bg-white dark:bg-[#1e1f21] h-full overflow-hidden">
                {children}
            </div>
        </WorkspaceLayout>
    );
}


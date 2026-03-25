"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    LayoutDashboard, 
    BookOpen, 
    BarChart3,
    FileCheck,
    FolderOpen,
    Calendar,
    MessagesSquare,
    UserCircle,
    FileText
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Principal',
        items: [
            { id: 'dashboard', label: 'Resumen', href: '/academy', icon: LayoutDashboard },
            { id: 'courses', label: 'Cursos', href: '/academy', icon: BookOpen },
            { id: 'curriculum', label: 'Plan de Estudio', href: '/academy/curriculum', icon: FileText },
        ]
    },
    {
        title: 'Mi Progreso',
        items: [
            { id: 'grades', label: 'Calificaciones', href: '/academy/grades', icon: BarChart3 },
            { id: 'certificates', label: 'Certificados', href: '/academy/certificates', icon: FileCheck },
        ]
    },
    {
        title: 'Recursos',
        items: [
            { id: 'resources', label: 'Materiales', href: '/academy/resources', icon: FolderOpen },
            { id: 'schedule', label: 'Horarios', href: '/academy/schedule', icon: Calendar },
            { id: 'forum', label: 'Foro Estudiantil', href: '/academy/forum', icon: MessagesSquare },
        ]
    },
    {
        title: 'Personal',
        items: [
            { id: 'profile', label: 'Mi Perfil', href: '/academy/profile', icon: UserCircle },
        ]
    }
];

export default function AcademyLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname() ?? '';

    const getSidebarTitle = () => {
        if (pathname === '/academy') return 'Academia / Resumen';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `Academia / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
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

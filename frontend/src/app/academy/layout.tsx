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
    FileText,
    GraduationCap,
    ShieldCheck
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
    },
    {
        title: 'Equipo Académico',
        items: [
            { id: 'teacher', label: 'Panel Docente', href: '/academy/teacher', icon: GraduationCap },
            { id: 'coordination', label: 'Coordinación', href: '/academy/coordination', icon: ShieldCheck },
        ]
    }
];

export default function AcademyLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname() ?? '';

    // If the route manages its own deep layer (like course viewer), don't wrap it in the general layout.
    const isDeepLayer = pathname.includes('/course/') || pathname.includes('/assessments/');
    if (isDeepLayer) {
        return <div className="h-full bg-[#f8f9fb]">{children}</div>;
    }

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

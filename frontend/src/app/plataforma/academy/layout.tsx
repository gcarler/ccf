"use client";

import React from 'react';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
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
            { id: 'dashboard', label: 'Resumen', href: '/plataforma/academy', icon: LayoutDashboard },
            { id: 'courses', label: 'Cursos', href: '/plataforma/academy', icon: BookOpen },
            { id: 'curriculum', label: 'Plan de Estudio', href: '/plataforma/academy/curriculum', icon: FileText },
        ]
    },
    {
        title: 'Mi Progreso',
        items: [
            { id: 'grades', label: 'Calificaciones', href: '/plataforma/academy/grades', icon: BarChart3 },
            { id: 'certificates', label: 'Certificados', href: '/plataforma/academy/certificates', icon: FileCheck },
        ]
    },
    {
        title: 'Recursos',
        items: [
            { id: 'resources', label: 'Materiales', href: '/plataforma/academy/resources', icon: FolderOpen },
            { id: 'schedule', label: 'Horarios', href: '/plataforma/academy/schedule', icon: Calendar },
            { id: 'forum', label: 'Foro Estudiantil', href: '/plataforma/academy/forum', icon: MessagesSquare },
        ]
    },
    {
        title: 'Personal',
        items: [
            { id: 'profile', label: 'Mi Perfil', href: '/plataforma/academy/profile', icon: UserCircle },
        ]
    },
    {
        title: 'Equipo Académico',
        items: [
            { id: 'teacher', label: 'Panel Docente', href: '/plataforma/academy/teacher', icon: GraduationCap },
            { id: 'coordination', label: 'Coordinación', href: '/plataforma/academy/coordination', icon: ShieldCheck },
        ]
    }
];

export default function AcademyLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    const getSidebarTitle = () => {
        if (!pathname) return 'Academia CCF';
        if (pathname === '/plataforma/academy') return 'Academia CCF';
        if (pathname.includes('/course/')) return 'Currículo del Curso';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `Academia / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    return (
        <ModuleErrorBoundary moduleName="Academia">
            <WorkspaceLayout
                sidebarTitle={getSidebarTitle()}
                sidebarSections={SIDEBAR_SECTIONS}
                allowedPermissions={['academy:read', 'academy:study', 'academy:edit', 'academy:manage']}
            >
                <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] h-full">
                    {children}
                </div>
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}


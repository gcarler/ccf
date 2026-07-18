"use client";

import React, { useMemo } from 'react';
import { usePathname } from 'next/navigation';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { useAuth } from '@/context/AuthContext';
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

// Fuente única de la sidebar Academy (ACAD-HIGH-004).
// Si moduleConfigs.ts declara una sección "academy" en el futuro, debe importar
// de aquí para evitar drift. Hoy el layout local es la fuente efectiva y este
// módulo se exporta también como constante reutilizable.
type AcademyLevel = 'read' | 'study' | 'edit' | 'manage';

export const ACADEMY_SIDEBAR_SECTIONS = [
    {
        title: 'Principal',
        items: [
            { id: 'dashboard', label: 'Resumen', href: '/plataforma/academy', icon: LayoutDashboard, level: 'read' as AcademyLevel },
            { id: 'courses', label: 'Cursos', href: '/plataforma/academy', icon: BookOpen, level: 'read' as AcademyLevel },
            { id: 'curriculum', label: 'Plan de Estudio', href: '/plataforma/academy/curriculum', icon: FileText, level: 'read' as AcademyLevel },
        ],
    },
    {
        title: 'Mi Progreso',
        items: [
            { id: 'grades', label: 'Calificaciones', href: '/plataforma/academy/grades', icon: BarChart3, level: 'study' as AcademyLevel },
            { id: 'certificates', label: 'Certificados', href: '/plataforma/academy/certificates', icon: FileCheck, level: 'study' as AcademyLevel },
        ],
    },
    {
        title: 'Recursos',
        items: [
            { id: 'resources', label: 'Materiales', href: '/plataforma/academy/resources', icon: FolderOpen, level: 'read' as AcademyLevel },
            { id: 'schedule', label: 'Horarios', href: '/plataforma/academy/schedule', icon: Calendar, level: 'read' as AcademyLevel },
            { id: 'forum', label: 'Foro Estudiantil', href: '/plataforma/academy/forum', icon: MessagesSquare, level: 'read' as AcademyLevel },
        ],
    },
    {
        title: 'Personal',
        items: [
            { id: 'profile', label: 'Mi Perfil', href: '/plataforma/academy/profile', icon: UserCircle, level: 'read' as AcademyLevel },
        ],
    },
    {
        title: 'Equipo Académico',
        items: [
            // ACAD-HIGH-001: Panel Docente requiere academy:edit, Coordinación academy:manage.
            // El sidebar ya no los muestra a usuarios con sólo :read o :study.
            { id: 'teacher', label: 'Panel Docente', href: '/plataforma/academy/teacher', icon: GraduationCap, level: 'edit' as AcademyLevel },
            { id: 'coordination', label: 'Coordinación', href: '/plataforma/academy/coordination', icon: ShieldCheck, level: 'manage' as AcademyLevel },
        ],
    },
];

function _filterSectionsByCapability(
    sections: typeof ACADEMY_SIDEBAR_SECTIONS,
    hasModuleAccess: ReturnType<typeof useAuth>['hasModuleAccess'],
) {
    return sections
        .map((section) => ({
            ...section,
            items: section.items.filter((item) => hasModuleAccess('academy', item.level)),
        }))
        .filter((section) => section.items.length > 0);
}

export default function AcademyLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { hasModuleAccess } = useAuth();

    const visibleSections = useMemo(
        () => _filterSectionsByCapability(ACADEMY_SIDEBAR_SECTIONS, hasModuleAccess),
        [hasModuleAccess]
    );

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
                sidebarSections={visibleSections}
                allowedPermissions={['academy:read', 'academy:study', 'academy:edit', 'academy:manage']}
            >
                <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] h-full">
                    {children}
                </div>
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}


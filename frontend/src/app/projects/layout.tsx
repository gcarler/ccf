"use client";

import React, { useState, useEffect } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { usePathname } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { Layout as LayoutIcon, Target } from 'lucide-react';
import type { ProjectRecord } from '@/types/projects';

export default function ProjectsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const { token } = useAuth();
    const [projects, setProjects] = useState<ProjectRecord[]>([]);

    useEffect(() => {
        const fetchProjects = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectRecord[]>('/projects', { token });
                if (Array.isArray(data)) {
                    setProjects(data);
                }
            } catch (err) {
                console.error("Error cargando proyectos en el sidebar:", err);
            }
        };
        fetchProjects();
    }, [token]);

    const getSidebarTitle = () => {
        if (!pathname || pathname === '/projects') return 'Portfolio';
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        return `Portfolio / ${last.charAt(0).toUpperCase() + last.slice(1)}`;
    };

    // Construir dinámicamente las secciones para el WorkspaceMainSidebar
    const sidebarSections = [
        {
            title: 'Inicio',
            items: [
                { id: 'portfolio', label: 'Ver Portfolio', href: '/projects', icon: LayoutIcon }
            ]
        },
        {
            title: 'Proyectos Activos',
            canAdd: true,
            items: projects.map(p => ({
                id: `proj-${p.id}`,
                label: p.title,
                href: `/projects/${p.id}`,
                icon: Target,
                count: p.tasks?.length || 0
            }))
        }
    ];

    const isProjectDetail = pathname?.startsWith('/projects/') && pathname !== '/projects';

    return (
        <ProtectedRoute>
            <WorkspaceLayout 
                sidebarTitle={getSidebarTitle()} 
                sidebarSections={sidebarSections}
                hideMainSidebar={isProjectDetail}
            >
                <div className="bg-[#f8f9fb] dark:bg-[#141517] min-h-screen">
                    {children}
                </div>
            </WorkspaceLayout>
        </ProtectedRoute>
    );
}

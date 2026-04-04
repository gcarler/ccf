"use client";

import React, { useState, useEffect } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { usePathname } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { Layout as LayoutIcon, Workflow } from 'lucide-react';
import type { ProjectRecord } from '@/types/projects';

export default function ProjectsLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const { token } = useAuth();
    const [projects, setProjects] = useState<ProjectRecord[]>([]);

    useEffect(() => {
        const fetchProjects = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectRecord[]>('/projects', { token });
                if (Array.isArray(data)) setProjects(data);
            } catch { }
        };
        fetchProjects();
    }, [token]);

    const sidebarSections = [
        {
            title: 'Inicio',
            items: [
                { id: 'portfolio', label: 'Portfolio', href: '/projects', icon: LayoutIcon }
            ]
        },
        {
            title: 'Proyectos Activos',
            canAdd: true,
            items: projects.slice(0, 20).map(p => ({
                id: `proj-${p.id}`,
                label: p.title,
                href: `/projects/${p.id}`,
                icon: Workflow,
                count: (p.tasks?.length ?? 0) > 0 ? (p.tasks!.length as number) : undefined
            }))
        }
    ];

    return (
        <ProtectedRoute>
            <WorkspaceLayout
                sidebarTitle="Portfolio"
                sidebarSections={sidebarSections}
            >
                <div className="bg-white dark:bg-[#1e1f21] h-full">
                    {children}
                </div>
            </WorkspaceLayout>
        </ProtectedRoute>
    );
}

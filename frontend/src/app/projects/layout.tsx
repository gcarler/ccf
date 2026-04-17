"use client";

import React, { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    LayoutDashboard, 
    CheckCircle2, 
    Users, 
    Settings, 
    List as ListIcon, 
    Clock, 
    Plus,
    Home
} from 'lucide-react';
import Link from 'next/link';

export default function ProjectsLayout({ children }: { children: React.ReactNode }) {
    const { token } = useAuth();
    const router = useRouter();
    const params = useParams();
    const [projects, setProjects] = useState<any[]>([]);

    useEffect(() => {
        if (!token) return;
        apiFetch<any[]>('/projects/', { token })
            .then(setProjects)
            .catch(() => setProjects([{ id: 1, title: 'Campaña Faro 2026' }]));
    }, [token]);

    const projectSections = [
        {
            id: 'global',
            label: 'Global',
            items: [
                { id: 'all-projects', label: 'Todos los Proyectos', icon: LayoutDashboard, href: '/projects' },
                { id: 'my-tasks', label: 'Mis Tareas', icon: CheckCircle2, href: '/tasks' },
            ]
        },
        {
            id: 'projects',
            label: 'Proyectos Activos',
            items: projects.map(p => ({
                id: `project-${p.id}`,
                label: p.title,
                icon: Home,
                href: `/projects/${p.id}`
            }))
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Proyectos CCF" sidebarSections={projectSections}>
            {children}
        </WorkspaceLayout>
    );
}

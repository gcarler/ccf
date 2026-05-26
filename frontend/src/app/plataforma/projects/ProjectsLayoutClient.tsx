"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { LayoutDashboard, CheckCircle2, Home, Circle, ChevronLeft } from 'lucide-react';
import { usePathname } from 'next/navigation';

export default function ProjectsLayoutClient({ children, initialProjects }: { children: React.ReactNode, initialProjects: any[] }) {
    const { token } = useAuth();
    const pathname = usePathname();
    // Path format: /projects/[id] or /projects/[id]/tasks
    const pathParts = pathname?.split('/') || [];
    // Si la ruta es /projects/algocomo43 o /projects/43/algo, el ID suele estar en la posición 2
    // Pero descartamos rutas conocidas globales como /projects/tasks, /projects/inbox, etc.
    const rawId = pathParts[2];
    const isGlobalRoute = ['tasks', 'inbox', 'general', 'comments', 'team', 'responses', 'more', 'automations', 'welcome', undefined].includes(rawId);
    const projectId = isGlobalRoute ? undefined : rawId;

    const [projects, setProjects] = useState<any[]>(initialProjects || []);
    const [currentProject, setCurrentProject] = useState<any>(null);

    useEffect(() => {
        if (!token) return;

        const loadData = () => {
            if (projectId) {
                // Contexto: Dentro de un proyecto
                apiFetch<any>(`/projects/${projectId}`, { token })
                    .then(data => setCurrentProject(data))
                    .catch(err => console.error("Error fetching project for sidebar", err));
            } else {
                // Contexto: Vista global de proyectos
                apiFetch<any[]>('/projects/', { token })
                    .then(data => setProjects(Array.isArray(data) ? data : []))
                    .catch(err => {
                        console.error("Error fetching projects for sidebar", err);
                        // No vaciamos los proyectos si hay un error para conservar los cargados por SSR
                    });
                setCurrentProject(null);
            }
        };

        loadData();

        const handleProjectUpdated = (e: any) => {
            // Si hay un proyecto actual y el evento especifica un ID distinto, lo ignoramos
            if (projectId && e.detail?.projectId && String(e.detail.projectId) !== String(projectId)) return;
            loadData();
        };

        window.addEventListener('project-updated', handleProjectUpdated);
        return () => window.removeEventListener('project-updated', handleProjectUpdated);
    }, [token, projectId]);

    let projectSections: any[] = [];

    if (projectId && currentProject) {
        const tasks = Array.isArray(currentProject.tasks) ? currentProject.tasks : [];
        projectSections = [
            {
                id: 'global',
                title: 'Navegación',
                items: [
                    {
                        id: 'all-projects',
                        label: 'Todos los Proyectos',
                        icon: ChevronLeft,
                        href: '/plataforma/projects'
                    },
                ]
            },
            {
                id: 'tasks',
                title: 'Plan de Acción',
                items: tasks.length > 0 ? tasks.map((t: any) => ({
                    id: `task-${t.id}`,
                    label: t.title,
                    icon: t.status === 'completed' ? CheckCircle2 : Circle,
                    href: `/projects/${projectId}?task=${t.id}`,
                    onClick: () => {
                        // Aquí en el futuro podemos abrir el RightPanel con el detalle de la tarea
                    }
                })) : [
                    { id: 'no-tasks', label: 'Sin tareas', icon: Circle, href: '#' }
                ]
            }
        ];
    } else {
        projectSections = [
            {
                id: 'global',
                title: 'Global',
                items: [
                    { id: 'all-projects', label: 'Todos los Proyectos', icon: LayoutDashboard, href: '/plataforma/projects' },
                    { id: 'my-tasks', label: 'Mis Tareas', icon: CheckCircle2, href: '/plataforma/tasks' },
                ]
            },
            {
                id: 'projects',
                title: 'Proyectos Activos',
                items: projects.map(p => ({
                    id: `project-${p.id}`,
                    label: p.title,
                    icon: Home,
                    href: `/projects/${p.id}`
                }))
            }
        ];
    }

    return (
        <WorkspaceLayout sidebarTitle={currentProject ? currentProject.title : "Proyectos CCF"} sidebarSections={projectSections} allowedPermissions={['projects:read']}>
            {children}
        </WorkspaceLayout>
    );
}

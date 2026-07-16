"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { LayoutDashboard, CheckCircle2, Home, Circle, ChevronLeft } from 'lucide-react';
import { useParams, usePathname } from 'next/navigation';
import { GLOBAL_PROJECT_ROUTES } from '@/lib/projects/routes';
import { toast } from "sonner";

export default function ProjectsLayoutClient({ children, initialProjects }: { children: React.ReactNode, initialProjects: Array<{ id: string; title: string; status?: string; color?: string | null }> }) {
    const { token } = useAuth();
    const params = useParams() as { id?: string | string[] } | null;
    const pathname = usePathname();
    // Prefer next/navigation `useParams()` over path splitting to remain stable
    // across future rewrites/basePath changes. Fall back to pathname parsing only
    // if params are unavailable (e.g., older Next.js mock environments).
    const rawParam = Array.isArray(params?.id) ? params?.id[0] : params?.id;
    const pathParts = pathname?.split('/') || [];
    const pathDerivedId = pathParts[3];
    const rawId = rawParam ?? pathDerivedId;
    // Only the explicit global sub-routes should bypass project context.
    // Any other segment under /plataforma/projects is treated as a project id.
    const projectId = !rawId || GLOBAL_PROJECT_ROUTES.has(rawId) ? undefined : rawId;

    const [projects, setProjects] = useState<Array<{ id: string; title: string; status?: string; color?: string | null }>>(initialProjects || []);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [currentProject, setCurrentProject] = useState<any>(null);

    useEffect(() => {
        if (!token) return;

        const loadData = () => {
            if (projectId) {
                // Contexto: Dentro de un proyecto
                apiFetch<Record<string, unknown>>(`/projects/${projectId}`, { token })
                    .then(data => setCurrentProject(data))
                    .catch(() => toast.error("Error fetching project for sidebar"));
            } else {
                // Contexto: Vista global de proyectos
                apiFetch<Array<{ id: string; title: string }>>('/projects', { token })
                    .then(data => setProjects(Array.isArray(data) ? data : []))
                    .catch(() => {
                        toast.error("Error fetching projects for sidebar");
                        // No vaciamos los proyectos si hay un error para conservar los cargados por SSR
                    });
                setCurrentProject(null);
            }
        };

        loadData();

        const handleProjectUpdated = (e: Event) => {
            const detail = (e as CustomEvent).detail;
            if (projectId && detail?.projectId && String(detail.projectId) !== String(projectId)) return;
            loadData();
        };

        window.addEventListener('project-updated', handleProjectUpdated as EventListener);
        return () => window.removeEventListener('project-updated', handleProjectUpdated as EventListener);
    }, [token, projectId]);

    let projectSections: Array<{ id?: string; title: string; items: Array<{ id: string; label: string; href: string; icon?: React.ComponentType<{ size?: number | string }> }> }> = [];

    if (projectId && currentProject) {
        const tasks: Array<{ id: string; title: string; status?: string }> = Array.isArray(currentProject.tasks) ? currentProject.tasks : [];
        projectSections = [
            {
                id: 'global',
                title: 'Navegación',
                items: [
                    {
                        id: 'all-projects',
                        label: 'Todos los Proyectos',
                        icon: ChevronLeft,
                        href: '/plataforma/projects/list#projects-list'
                    },
                ]
            },
            {
                id: 'tasks',
                title: 'Plan de Acción',
                items: tasks.length > 0 ? tasks.map((t) => ({
                    id: `task-${t.id}`,
                    label: t.title,
                    icon: t.status === 'completed' ? CheckCircle2 : Circle,
                    href: `/plataforma/projects/${projectId}?task=${t.id}`,
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
                    { id: 'all-projects', label: 'Todos los Proyectos', icon: LayoutDashboard, href: '/plataforma/projects/list#projects-list' },
                    { id: 'my-tasks', label: 'Mis Tareas', icon: CheckCircle2, href: '/plataforma/projects/tasks' },
                ]
            },
            {
                id: 'projects',
                title: 'Proyectos Activos',
                items: projects.map(p => ({
                    id: `project-${p.id}`,
                    label: p.title,
                    icon: Home,
                    href: `/plataforma/projects/${p.id}?view=list`
                }))
            }
        ];
    }

    return (
        <ModuleErrorBoundary moduleName="Proyectos">
            <WorkspaceLayout sidebarTitle={currentProject ? currentProject.title : "Proyectos CCF"} sidebarSections={projectSections} allowedPermissions={['projects:read']}>
                {children}
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}

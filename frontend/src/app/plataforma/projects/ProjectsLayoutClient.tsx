"use client";

import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { LayoutDashboard, CheckCircle2, Home, Circle, ChevronLeft } from 'lucide-react';
import { useParams, usePathname } from 'next/navigation';
import { GLOBAL_PROJECT_ROUTES } from '@/lib/projects/routes';
import { PROJECTS_LIST_ROUTE } from '@/app/plataforma/projects/projectsLinks';
import { toast } from "sonner";
import { getAllProjectSummaries } from '@/lib/projects/api';
import type { ProjectRecord, ProjectSummaryPageResponse, ProjectSummaryRecord } from '@/types/projects';

interface ProjectsLayoutClientProps {
    children: React.ReactNode;
    initialProjectPage?: ProjectSummaryPageResponse | null;
}

export default function ProjectsLayoutClient({ children, initialProjectPage }: ProjectsLayoutClientProps) {
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

    const [projects, setProjects] = useState<ProjectSummaryRecord[]>(initialProjectPage?.items ?? []);
    const [currentProject, setCurrentProject] = useState<ProjectRecord | null>(null);
    const initialPageAvailable = useRef(Boolean(initialProjectPage));

    useEffect(() => {
        if (!token) {
            setCurrentProject(null);
            return;
        }

        let isCurrentRequest = true;
        let requestGeneration = 0;
        let activeController: AbortController | null = null;

        const loadData = (reuseInitialPage = false) => {
            const generation = ++requestGeneration;
            activeController?.abort();
            const controller = new AbortController();
            activeController = controller;
            if (projectId) {
                // Avoid showing the previous project's task links while the new context loads.
                setCurrentProject(null);
                apiFetch<ProjectRecord>(`/projects/${projectId}`, { token, signal: controller.signal })
                    .then(data => {
                        if (isCurrentRequest && generation === requestGeneration) setCurrentProject(data);
                    })
                    .catch(() => {
                        if (isCurrentRequest && generation === requestGeneration && !controller.signal.aborted) {
                            toast.error("Error fetching project for sidebar");
                        }
                    });
            } else {
                const initialPage = reuseInitialPage ? initialProjectPage ?? undefined : undefined;
                getAllProjectSummaries(token, { signal: controller.signal, initialPage })
                    .then(data => {
                        if (isCurrentRequest && generation === requestGeneration) setProjects(data);
                    })
                    .catch(() => {
                        if (!isCurrentRequest || controller.signal.aborted || generation !== requestGeneration) return;
                        toast.error("Error fetching projects for sidebar");
                        // No vaciamos los proyectos si hay un error para conservar los cargados por SSR
                    });
                setCurrentProject(null);
            }
        };

        const reuseInitialPage = initialPageAvailable.current && !projectId;
        if (reuseInitialPage) initialPageAvailable.current = false;
        loadData(reuseInitialPage);

        const handleProjectUpdated = (e: Event) => {
            const detail = (e as CustomEvent<{ projectId?: string }>).detail;
            if (projectId && detail?.projectId && String(detail.projectId) !== String(projectId)) return;
            loadData(false);
        };

        window.addEventListener('project-updated', handleProjectUpdated as EventListener);
        return () => {
            isCurrentRequest = false;
            activeController?.abort();
            window.removeEventListener('project-updated', handleProjectUpdated as EventListener);
        };
    }, [token, projectId, initialProjectPage]);

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
                        href: PROJECTS_LIST_ROUTE
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
                    { id: 'all-projects', label: 'Todos los Proyectos', icon: LayoutDashboard, href: PROJECTS_LIST_ROUTE },
                    { id: 'my-tasks', label: 'Mis Tareas', icon: CheckCircle2, href: '/plataforma/projects/tasks' },
                ]
            },
            {
                id: 'projects',
                title: 'Proyectos',
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
            <WorkspaceLayout sidebarTitle={currentProject ? currentProject.title : "Proyectos CCF"} sidebarSections={projectSections} allowedPermissions={['projects:read']} hideWorkspaceHeader>
                {children}
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}

"use client";

import { Folder, Layers, Plus, Search } from 'lucide-react';
import clsx from 'clsx';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import type { ViewType } from '@/components/ViewSwitcher';
import type { CalendarEvent } from '@/components/ui/UniversalCalendarView';
import type { GanttItem } from '@/components/ui/UniversalGanttView';
import ProjectsShell from '@/components/projects/ProjectsShell';
import ProjectCreationDrawer from '@/components/projects/ProjectCreationDrawer';
import { useAuth } from '@/context/AuthContext';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { DSCard } from '@/design';
import { DSChart } from '@/design';
import { DSMetric } from '@/design';
import { apiFetch } from '@/lib/http';
import { useProjects } from '@/hooks/useProjects';
import type { ProjectRecord, ProjectSummaryPageResponse } from '@/types/projects';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';

import { getProjectMetricHref, PROJECTS_LIST_ANCHOR } from './projectsLinks';

// Light views loaded synchronously
import ProjectsGridView from './views/ProjectsGridView';
import ProjectsListView from './views/ProjectsListView';
import ProjectsTableView from './views/ProjectsTableView';
import ProjectsBoardView from './views/ProjectsBoardView';

// Heavy views loaded on demand (client-only to avoid SSR issues with DOM libraries)
function ViewSkeleton() {
    return <div className="h-[360px] animate-pulse rounded-lg bg-[hsl(var(--surface-2))]" />;
}

const ProjectsCalendarView = dynamic(() => import('./views/ProjectsCalendarView'), { ssr: false, loading: ViewSkeleton });
const ProjectsGanttView = dynamic(() => import('./views/ProjectsGanttView'), { ssr: false, loading: ViewSkeleton });
const ProjectsWikiView = dynamic(() => import('./views/ProjectsWikiView'), { ssr: false, loading: ViewSkeleton });

const PROJECT_VIEWS: ViewType[] = ['dashboard', 'grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];
const PROJECTS_PAGE_SIZE = 50;
const PROJECT_VIEW_LABELS: Record<ViewType, string> = {
    dashboard: 'Resumen',
    grid: 'Tarjetas',
    table: 'Tabla',
    list: 'Lista',
    board: 'Tablero',
    kanban: 'Kanban',
    calendar: 'Calendario',
    gantt: 'Gantt',
    wiki: 'Wiki',
    chat: 'Chat',
};

interface ProjectsClientProps {
    initialProjects: ProjectRecord[];
    initialViewType?: ViewType;
}

export default function ProjectsClient({ initialProjects, initialViewType = 'grid' }: ProjectsClientProps) {
    const { token, loading: authLoading } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [projects, setProjects] = useState<ProjectRecord[]>(initialProjects);
    const [projectTotal, setProjectTotal] = useState(initialProjects.length);
    const [projectOffset, setProjectOffset] = useState(0);
    const [isLoadingProjects, setIsLoadingProjects] = useState(initialProjects.length === 0);
    const [projectsLoadError, setProjectsLoadError] = useState(false);
    const [projectLoadAttempt, setProjectLoadAttempt] = useState(0);
    const [dashboard, setDashboard] = useState<{
        cards?: Array<{ title: string; value: string; trend?: string | null; tone?: string | null; icon?: string | null }>;
        workload_distribution?: Array<{ label: string; value: number }>;
        delayed_tasks_count?: number;
    } | null>(null);
    const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
    const [dashboardLoadError, setDashboardLoadError] = useState(false);
    const [dashboardLoadAttempt, setDashboardLoadAttempt] = useState(0);
    const [viewType, setViewType] = useState<ViewType>(initialViewType);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [isCreating, setIsCreating] = useState(false);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const { updateProject, deleteProject } = useProjects();
    const projectsListRef = useRef<HTMLDivElement | null>(null);
    const projectRequestSequence = useRef(0);
    const projectQueryKey = `${projectOffset}:${search.trim()}:${statusFilter}`;
    const projectQueryKeyRef = useRef(projectQueryKey);
    projectQueryKeyRef.current = projectQueryKey;

    // Reload projects from the backend when the token becomes available.
    // The SSR (page.tsx → fetchProjects) cannot authenticate because the
    // JWT lives in sessionStorage (client-only), so initialProjects is
    // often []. This useEffect fetches the real list client-side.
    useEffect(() => {
        if (authLoading) return;
        if (!token) {
            setIsLoadingProjects(false);
            return;
        }
        const requestId = ++projectRequestSequence.current;
        const timeoutId = window.setTimeout(() => {
            setIsLoadingProjects(true);
            setProjectsLoadError(false);
            void apiFetch<ProjectSummaryPageResponse>('/projects/summary-page', {
                token,
                cache: 'no-store',
                query: {
                    offset: projectOffset,
                    limit: PROJECTS_PAGE_SIZE,
                    search: search.trim() || undefined,
                    status: statusFilter === 'all' ? undefined : statusFilter,
                },
            }).then((data) => {
                if (requestId !== projectRequestSequence.current) return;
                if (!Array.isArray(data?.items) || !Number.isFinite(data.total)) {
                    throw new Error('Invalid project page response');
                }
                setProjects(data.items);
                setProjectTotal(data.total);
            }).catch(() => {
                if (requestId !== projectRequestSequence.current) return;
                setProjectsLoadError(true);
                toast.error('No se pudieron cargar los proyectos. Inténtalo de nuevo.');
            }).finally(() => {
                if (requestId === projectRequestSequence.current) setIsLoadingProjects(false);
            });
        }, search.trim() ? 250 : 0);
        return () => {
            window.clearTimeout(timeoutId);
            projectRequestSequence.current += 1;
        };
    }, [token, authLoading, projectLoadAttempt, projectOffset, search, statusFilter]);

    const handleSearchChange = useCallback((value: string) => {
        setSearch(value);
        setProjectOffset(0);
    }, []);

    const handleStatusFilterChange = useCallback((value: string) => {
        setStatusFilter(value);
        setProjectOffset(0);
    }, []);

    const handleProjectPageChange = useCallback((nextOffset: number) => {
        setProjectOffset(Math.max(0, nextOffset));
    }, []);

    // Search/status are server-side, so this page reflects the full tenant dataset.
    const filtered = projects;

    /*
     * Existing callback handlers update the currently loaded page optimistically.
     */
    const handleUpdateProject = useCallback(
        async (projectId: string, patch: Partial<ProjectRecord>) => {
            let previousProject: ProjectRecord | undefined;
            setProjects((prev) => {
                previousProject = prev.find((p) => p.id === projectId);
                if (!previousProject) return prev;
                return prev.map((p) => (p.id === projectId ? { ...p, ...patch } : p));
            });
            const updated = await updateProject(projectId, patch);
            if (!updated) {
                if (previousProject) {
                    setProjects((prev) =>
                        prev.map((p) => (p.id === projectId ? previousProject! : p))
                    );
                }
                toast.error('No se pudo actualizar el proyecto. Se conservaron los datos guardados.');
            } else if (updated && (patch.status !== undefined || patch.title !== undefined || patch.description !== undefined)) {
                setProjectLoadAttempt((attempt) => attempt + 1);
            }
        },
        [updateProject]
    );

    const handleDeleteProject = useCallback(
        async (projectId: string) => {
            const requestQueryKey = projectQueryKeyRef.current;
            const previousIndex = projects.findIndex((project) => project.id === projectId);
            const previous = previousIndex >= 0 ? projects[previousIndex] : undefined;
            if (!previous) return;
            setProjects((prev) => prev.filter((project) => project.id !== projectId));
            const ok = await deleteProject(projectId);
            const isSameQuery = projectQueryKeyRef.current === requestQueryKey;
            if (!ok) {
                if (isSameQuery) {
                    setProjects((prev) => {
                        if (prev.some((project) => project.id === projectId)) return prev;
                        const restored = [...prev];
                        restored.splice(Math.min(previousIndex, restored.length), 0, previous);
                        return restored;
                    });
                } else {
                    setProjectLoadAttempt((attempt) => attempt + 1);
                }
                toast.error('No se pudo eliminar el proyecto. La lista se sincronizó con el servidor.');
            } else if (isSameQuery) {
                setProjectTotal((total) => Math.max(0, total - 1));
                if (filtered.length === 1 && projectOffset > 0) {
                    setProjectOffset((offset) => Math.max(0, offset - PROJECTS_PAGE_SIZE));
                } else {
                    setProjectLoadAttempt((attempt) => attempt + 1);
                }
            } else {
                setProjectLoadAttempt((attempt) => attempt + 1);
            }
        },
        [deleteProject, filtered.length, projectOffset, projects]
    );

    useEffect(() => {
        if (viewType !== 'dashboard') return;
        if (authLoading) return;
        if (!token) {
            setIsLoadingDashboard(false);
            return;
        }
        let isCurrentRequest = true;
        const loadDashboard = async () => {
            setIsLoadingDashboard(true);
            setDashboardLoadError(false);
            try {
                const data = await apiFetch<{
                    cards?: Array<{ title: string; value: string; trend?: string | null; tone?: string | null; icon?: string | null }>;
                    workload_distribution?: Array<{ label: string; value: number }>;
                    delayed_tasks_count?: number;
                }>('/dashboard/projects', { token });
                if (isCurrentRequest) setDashboard(data);
            } catch {
                if (isCurrentRequest) {
                    setDashboardLoadError(true);
                    toast.error('No se pudo cargar el resumen del proyecto');
                }
            } finally {
                if (isCurrentRequest) setIsLoadingDashboard(false);
            }
        };
        void loadDashboard();
        return () => {
            isCurrentRequest = false;
        };
    }, [authLoading, dashboardLoadAttempt, token, viewType]);

    useEffect(() => {
        const view = searchParams?.get('view');
        if (!view) return;
        if ((PROJECT_VIEWS as string[]).includes(view)) {
            setViewType(view as ViewType);
        }
    }, [searchParams]);

    // Scroll del listado al entrar en la vista list. Disparado por
    // `onAnimationComplete` del motion.div (no por un setTimeout fijo):
    // AnimatePresence mode="wait" completa la animación de salida (~300ms)
    // ANTES de montar la vista nueva, así que un timer de 100ms disparaba con
    // `projectsListRef` aún null y el scroll se saltaba en silencio
    // (fix 2026-08-02, carrera 100ms vs ~300ms).
    const scrollTriggeredViewRef = useRef<ViewType | null>(null);
    const handleListViewAnimationComplete = useCallback(() => {
        if (viewType !== 'list') {
            scrollTriggeredViewRef.current = null;
            return;
        }
        // Scroll una sola vez por transición a la vista list (no en cada re-render).
        if (scrollTriggeredViewRef.current === viewType) return;
        scrollTriggeredViewRef.current = viewType;
        projectsListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, [viewType]);

    const showsStatusFilter = ['dashboard', 'grid', 'table', 'list', 'board', 'kanban'].includes(viewType);

    const handleCreateProject = async (data: {
        title: string;
        description: string;
        status: string;
        owner_id: string | null;
        color: string;
    }) => {
        if (isCreating) return;
        setIsCreating(true);
        try {
            const created = await apiFetch<ProjectRecord>('/projects', {
                method: 'POST',
                token,
                body: {
                    title: data.title.trim() || 'Nuevo Proyecto',
                    description: data.description || '',
                    color: data.color,
                    status: data.status,
                    owner_id: data.owner_id,
                },
            });
            // The active page is server-filtered and may be offset. Reconcile
            // from the API instead of injecting a row that might not match it.
            setProjectLoadAttempt((attempt) => attempt + 1);
            setShowCreateForm(false);
            toast.success('Proyecto creado');
            window.dispatchEvent(new CustomEvent('project-updated'));
            setTimeout(() => router.push(`/plataforma/projects/${created.id}?view=list`), 200);
        } catch (e) {
            toast.error('Error al crear el proyecto');
        } finally {
            setIsCreating(false);
        }
    };

    const projectCommands = useMemo(
        () =>
            filtered.slice(0, 7).map((project) => ({
                id: `project-${project.id}`,
                label: project.title,
                description: project.description || 'Ver proyecto',
                icon: Folder,
                group: 'Proyectos',
                action: () => router.push(`/plataforma/projects/${project.id}?view=list`),
            })),
        [filtered, router]
    );

    useRegisterCommands('projects-quick-links', projectCommands);

    const handleEventClick = useCallback(
        (event: CalendarEvent) => router.push(`/plataforma/projects/${event.id}?view=list`),
        [router]
    );

    const handleGanttItemClick = useCallback(
        (item: GanttItem) => router.push(`/plataforma/projects/${item.id}?view=list`),
        [router]
    );

    const renderView = () => {
        if (isLoadingProjects && projects.length === 0) {
            return (
                <div role="status" aria-label="Cargando proyectos" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 6 }, (_, index) => (
                        <div key={index} aria-hidden="true" className="h-40 animate-pulse rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]" />
                    ))}
                </div>
            );
        }

        if (projectsLoadError && projects.length === 0) {
            return (
                <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-6 py-12 text-center">
                    <Folder size={40} className="text-[hsl(var(--muted-foreground))]" aria-hidden="true" />
                    <div>
                        <h2 className="text-base font-semibold text-[hsl(var(--text-primary))]">No pudimos cargar tus proyectos</h2>
                        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">Revisa tu conexión e inténtalo nuevamente.</p>
                    </div>
                    <button
                        type="button"
                        onClick={() => setProjectLoadAttempt((attempt) => attempt + 1)}
                        className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90"
                    >
                        Reintentar
                    </button>
                </div>
            );
        }

        if (filtered.length === 0) {
            // Wrap the empty state inside the anchor container for the list
            // view so that the #projects-dashboard hash target always exists
            // when the user clicks the "Proyectos" metric card.
            const emptyState = (
                <EmptyProjectsState
                    search={search}
                    onShowCreate={() => setShowCreateForm(true)}
                />
            );
            if (viewType === 'list') {
                return (
                    <div id={PROJECTS_LIST_ANCHOR} ref={projectsListRef}>
                        {emptyState}
                    </div>
                );
            }
            return emptyState;
        }

        switch (viewType) {
            case 'dashboard':
                return <ProjectsGridView projects={filtered} onUpdate={handleUpdateProject} onDelete={handleDeleteProject} />;
            case 'grid':
                return <ProjectsGridView projects={filtered} onUpdate={handleUpdateProject} onDelete={handleDeleteProject} />;
            case 'list':
                return (
                    <div id={PROJECTS_LIST_ANCHOR} ref={projectsListRef}>
                        <ProjectsListView projects={filtered} onUpdate={handleUpdateProject} />
                    </div>
                );
            case 'table':
                return <ProjectsTableView projects={filtered} onUpdate={handleUpdateProject} />;
            case 'board':
            case 'kanban':
                return <ProjectsBoardView projects={filtered} onUpdate={handleUpdateProject} onDelete={handleDeleteProject} />;
            case 'calendar':
                return <ProjectsCalendarView projects={filtered} onEventClick={handleEventClick} />;
            case 'gantt':
                return <ProjectsGanttView projects={filtered} onItemClick={handleGanttItemClick} />;
            case 'wiki':
                return <ProjectsWikiView />;
            default:
                return null;
        }
    };

    return (
            <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Folder }, { label: 'Centro de Comando', icon: Layers }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={PROJECT_VIEWS}
                onSearch={handleSearchChange}
            rightActions={
                <button
                    onClick={() => setShowCreateForm(true)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-all bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95"
                >
                    <Plus size={14} />
                    Nuevo Proyecto
                </button>
            }
        >
            <ProjectCreationDrawer
                isOpen={showCreateForm}
                onClose={() => setShowCreateForm(false)}
                onSubmit={handleCreateProject}
            />

            <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor="projects-mobile-view">Vista de proyectos</label>
                <select
                    id="projects-mobile-view"
                    aria-label="Vista de proyectos"
                    value={viewType}
                    onChange={(event) => setViewType(event.target.value as ViewType)}
                    className="h-10 min-w-0 flex-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 text-sm text-[hsl(var(--text-primary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/40 sm:hidden"
                >
                    {PROJECT_VIEWS.map((view) => (
                        <option key={view} value={view}>{PROJECT_VIEW_LABELS[view]}</option>
                    ))}
                </select>
                <label className="sr-only" htmlFor="projects-mobile-search">Buscar proyectos</label>
                <div className="relative min-w-0 flex-1 lg:hidden">
                    <Search size={15} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" />
                    <input
                        id="projects-mobile-search"
                        type="search"
                        aria-label="Buscar proyectos"
                        placeholder="Buscar proyectos"
                        value={search}
                        onChange={(event) => handleSearchChange(event.target.value)}
                        className="h-10 w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] pl-9 pr-3 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/40"
                    />
                </div>
            </div>

            {projectsLoadError && projects.length > 0 && (
                <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        No se pudo actualizar la lista; se conservan los resultados anteriores.
                    </p>
                    <button
                        type="button"
                        onClick={() => setProjectLoadAttempt((attempt) => attempt + 1)}
                        className="rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-sm font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                    >
                        Reintentar proyectos
                    </button>
                </div>
            )}

            {viewType === 'dashboard' && <>
            {/* Project summary metrics */}
            <section data-testid="projects-overview" className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {isLoadingDashboard ? (
                    <div role="status" aria-label="Cargando resumen" className="col-span-full grid grid-cols-1 gap-3 md:grid-cols-4">
                        {Array.from({ length: 4 }, (_, index) => (
                            <div key={index} aria-hidden="true" className="h-24 animate-pulse rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]" />
                        ))}
                    </div>
                ) : dashboardLoadError ? (
                    <div role="alert" className="col-span-full flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3">
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">No pudimos cargar las métricas del resumen.</p>
                        <button
                            type="button"
                            onClick={() => setDashboardLoadAttempt((attempt) => attempt + 1)}
                            className="rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-sm font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                        >
                            Reintentar métricas
                        </button>
                    </div>
                ) : dashboard?.cards?.length ? dashboard.cards.map((card, idx) => {
                    const label = (card.title || '').toLowerCase();
                    return (
                        <DSMetric
                            key={idx}
                            label={card.title}
                            value={card.value}
                            trend={card.trend ?? undefined}
                            tone={card.tone as 'blue' | 'emerald' | 'amber' | undefined}
                            href={getProjectMetricHref(label)}
                            onClick={() => {
                                const targetUrl = getProjectMetricHref(label);
                                if (targetUrl.includes('view=list')) {
                                    setViewType('list');
                                }
                            }}
                        />
                    );
                }) : (
                    <p className="col-span-full rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
                        Aún no hay métricas disponibles para mostrar.
                    </p>
                )}
            </section>

            {/* Workload and overdue-task overview */}
            {!isLoadingDashboard && !dashboardLoadError && <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                <div className="lg:col-span-2">
                    <Link href="/plataforma/projects/team" className="block">
                        <DSCard className="hover:border-[hsl(var(--primary))]/30 transition-all cursor-pointer">
                            <h2 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
                                Carga de Trabajo del Equipo
                            </h2>
                            <DSChart
                                type="bar"
                                data={dashboard?.workload_distribution?.map((w) => ({
                                    label: w.label,
                                    value: w.value,
                                }))}
                                color="hsl(var(--warning))"
                                height={220}
                            />
                        </DSCard>
                    </Link>
                </div>
                <div>
                    <Link href="/plataforma/projects/tasks?view=list&scope=all" className="block">
                        <DSCard className="hover:border-[hsl(var(--destructive))]/30 transition-all cursor-pointer">
                            <h2 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
                                Estado de Tareas
                            </h2>
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">Tareas Atrasadas</span>
                                    <span className="text-sm font-semibold text-[hsl(var(--destructive))]">{dashboard?.delayed_tasks_count || 0}</span>
                                </div>
                                <p className="text-2xs text-[hsl(var(--muted-foreground))] italic">
                                    Revisa los hitos críticos para anticipar posibles cuellos de botella.
                                </p>
                            </div>
                        </DSCard>
                    </Link>
                </div>
            </div>}
            </>}

            {/* Status filters belong to project-oriented views, not calendar/wiki navigation. */}
            {showsStatusFilter && <div className="flex items-center gap-2 flex-wrap">
                {['all', 'planning', 'active', 'on_hold', 'completed', 'archived'].map((status) => (
                    <button
                        key={status}
                        onClick={() => handleStatusFilterChange(status)}
                        className={clsx(
                            'px-3 py-1 rounded-full text-2xs font-bold uppercase tracking-wide border transition-colors',
                            statusFilter === status
                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                                : 'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'
                        )}
                    >
                        {status === 'all' ? 'Todos' :
                         status === 'planning' ? 'Planificación' :
                         status === 'active' ? 'Activo' :
                         status === 'on_hold' ? 'En Pausa' :
                         status === 'completed' ? 'Completado' :
                         'Archivado'}
                    </button>
                ))}
            </div>}

            {viewType === 'dashboard' && <div className="h-px bg-[hsl(var(--border))] my-8" />}

            <div className="relative">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={viewType + (filtered.length === 0 ? '-empty' : '')}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        onAnimationComplete={handleListViewAnimationComplete}
                        className="pb-4"
                    >
                        {renderView()}
                    </motion.div>
                </AnimatePresence>
            </div>
            {(projectTotal > PROJECTS_PAGE_SIZE || projectOffset > 0) && (
                <nav
                    aria-label="Paginación de proyectos"
                    aria-busy={isLoadingProjects}
                    className="flex flex-col gap-3 border-t border-[hsl(var(--border))] py-4 sm:flex-row sm:items-center sm:justify-between"
                >
                    <p className="text-sm text-[hsl(var(--muted-foreground))]" aria-live="polite">
                        {projectTotal === 0
                            ? 'Sin proyectos'
                            : `Mostrando ${projectOffset + 1}–${Math.min(projectOffset + filtered.length, projectTotal)} de ${projectTotal} proyectos`}
                        {isLoadingProjects ? ' · Actualizando' : ''}
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            onClick={() => handleProjectPageChange(projectOffset - PROJECTS_PAGE_SIZE)}
                            disabled={projectOffset === 0 || isLoadingProjects}
                            className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Anterior
                        </button>
                        <button
                            type="button"
                            onClick={() => handleProjectPageChange(projectOffset + PROJECTS_PAGE_SIZE)}
                            disabled={projectOffset + filtered.length >= projectTotal || isLoadingProjects}
                            className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Siguiente
                        </button>
                    </div>
                </nav>
            )}
        </ProjectsShell>
    );
}

function EmptyProjectsState({ search, onShowCreate }: { search: string; onShowCreate: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <Folder size={48} className="text-[hsl(var(--muted-foreground))] mb-4" />
            <h3 className="text-lg font-bold text-[hsl(var(--foreground))]">No hay proyectos</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1 mb-4 max-w-md">
                {search ? 'Ningún proyecto coincide con tu búsqueda.' : 'Crea tu primer proyecto para empezar.'}
            </p>
            {!search && (
                <button
                    onClick={onShowCreate}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95"
                >
                    <Plus size={16} /> Crear proyecto
                </button>
            )}
        </div>
    );
}

"use client";

import { Folder, Layers, Plus } from 'lucide-react';
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
import type { ProjectRecord } from '@/types/projects';
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
    return <div className="h-[360px] animate-pulse rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5" />;
}

const ProjectsCalendarView = dynamic(() => import('./views/ProjectsCalendarView'), { ssr: false, loading: ViewSkeleton });
const ProjectsGanttView = dynamic(() => import('./views/ProjectsGanttView'), { ssr: false, loading: ViewSkeleton });
const ProjectsWikiView = dynamic(() => import('./views/ProjectsWikiView'), { ssr: false, loading: ViewSkeleton });

const PROJECT_VIEWS: ViewType[] = ['grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

interface ProjectsClientProps {
    initialProjects: ProjectRecord[];
    initialViewType?: ViewType;
}

export default function ProjectsClient({ initialProjects, initialViewType = 'grid' }: ProjectsClientProps) {
    const { token } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const [projects, setProjects] = useState<ProjectRecord[]>(initialProjects);
    const [dashboard, setDashboard] = useState<{
        cards?: Array<{ label: string; title?: string; value: number; icon?: string; color?: string; trend?: number }>;
        workload_distribution?: Array<{ name: string; tasks: number }>;
        delayed_tasks_count?: number;
    } | null>(null);
    const [viewType, setViewType] = useState<ViewType>(initialViewType);
    const [search, setSearch] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const { updateProject, deleteProject } = useProjects();
    const projectsListRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!token) return;
        const loadDashboard = async () => {
            try {
                const data = await apiFetch<{
                    cards?: Array<{ label: string; value: number }>;
                    workload_distribution?: Array<{ name: string; tasks: number }>;
                    delayed_tasks_count?: number;
                }>('/dashboard/projects', { token });
                setDashboard(data);
            } catch (err) {
                toast.error('Error al cargar dashboard');
            }
        };
        loadDashboard();
    }, [token]);

    useEffect(() => {
        const view = searchParams?.get('view');
        if (!view) return;
        if ((PROJECT_VIEWS as string[]).includes(view)) {
            setViewType(view as ViewType);
        }
    }, [searchParams]);

    useEffect(() => {
        if (viewType !== 'list') return;

        const timer = setTimeout(() => {
            projectsListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);

        return () => clearTimeout(timer);
    }, [viewType]);

    // Quality filter: hide projects with nonsensical/test names
    const isValidProject = (p: ProjectRecord) => {
        const t = (p.title || '').trim();
        if (t.length < 2) return false;
        if (/^(.)\1+$/i.test(t)) return false;
        return true;
    };

    const filtered = projects
        .filter(isValidProject)
        .filter(
            (p) =>
                p.title.toLowerCase().includes(search.toLowerCase()) ||
                (p.description || '').toLowerCase().includes(search.toLowerCase())
        );

    const handleUpdateProject = useCallback(
        async (projectId: string, patch: Partial<ProjectRecord>) => {
            let previousProject: ProjectRecord | undefined;
            setProjects((prev) => {
                previousProject = prev.find((p) => p.id === projectId);
                if (!previousProject) return prev;
                return prev.map((p) => (p.id === projectId ? { ...p, ...patch } : p));
            });
            const updated = await updateProject(projectId, patch);
            if (!updated && previousProject) {
                setProjects((prev) =>
                    prev.map((p) => (p.id === projectId ? previousProject! : p))
                );
            }
        },
        [updateProject]
    );

    const handleDeleteProject = useCallback(
        async (projectId: string) => {
            let previous: ProjectRecord | undefined;
            setProjects((prev) => {
                previous = prev.find((p) => p.id === projectId);
                return prev.filter((p) => p.id !== projectId);
            });
            const ok = await deleteProject(projectId);
            if (!ok && previous) {
                setProjects((prev) => [...prev, previous!]);
            }
        },
        [deleteProject]
    );

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
            setProjects((prev) => [created, ...prev]);
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
        if (filtered.length === 0) {
            return (
                <EmptyProjectsState
                    search={search}
                    onShowCreate={() => setShowCreateForm(true)}
                />
            );
        }

        switch (viewType) {
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
            onSearch={setSearch}
            rightActions={
                <button
                    onClick={() => setShowCreateForm(true)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-all bg-[hsl(var(--primary))] text-white shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95"
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

            {/* 📊 Project Metrics */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {dashboard?.cards?.map((card, idx) => {
                    const label = (card.title || card.label).toLowerCase();
                    return (
                        <DSMetric
                            key={idx}
                            label={card.title || card.label}
                            value={String(card.value)}
                            trend={
                                card.trend != null
                                    ? `${card.trend > 0 ? '+' : ''}${card.trend}%`
                                    : undefined
                            }
                            tone={card.color as 'blue' | 'emerald' | 'amber' | undefined}
                            href={getProjectMetricHref(label)}
                            onClick={() => {
                                const targetUrl = getProjectMetricHref(label);
                                if (targetUrl.includes('view=list')) {
                                    setViewType('list');
                                }
                            }}
                        />
                    );
                })}
            </section>

            {/* 📈 Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                <div className="lg:col-span-2">
                    <Link href="/plataforma/projects/team" className="block">
                        <DSCard className="hover:border-[hsl(var(--primary))]/30 transition-all cursor-pointer">
                            <h2 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
                                Carga de Trabajo del Equipo
                            </h2>
                            <DSChart
                                type="bar"
                                data={dashboard?.workload_distribution?.map((w) => ({
                                    label: w.name,
                                    value: w.tasks,
                                }))}
                                color="hsl(var(--warning))"
                                height={220}
                            />
                        </DSCard>
                    </Link>
                </div>
                <div>
                    <Link href="/plataforma/projects/tasks?view=list&scope=all" className="block">
                        <DSCard className="hover:border-[hsl(var(--danger)/40%)]/30 transition-all cursor-pointer">
                            <h2 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">
                                Estado de Tareas
                            </h2>
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-[hsl(var(--text-secondary))]">Tareas Atrasadas</span>
                                    <span className="text-sm font-semibold text-[hsl(var(--danger))]">{dashboard?.delayed_tasks_count || 0}</span>
                                </div>
                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full w-[15%] bg-[hsl(var(--danger))]" />
                                </div>
                                <p className="text-2xs text-[hsl(var(--text-secondary))] italic">
                                    Se recomienda revisar los hitos críticos para evitar cuellos de botella.
                                </p>
                            </div>
                        </DSCard>
                    </Link>
                </div>
            </div>

            <div className="h-px bg-white/5 my-8" />

            <div className="relative">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={viewType + (filtered.length === 0 ? '-empty' : '')}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="pb-4"
                    >
                        {renderView()}
                    </motion.div>
                </AnimatePresence>
            </div>
        </ProjectsShell>
    );
}

function EmptyProjectsState({ search, onShowCreate }: { search: string; onShowCreate: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center">
            <Folder size={48} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-4" />
            <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">No hay proyectos</h3>
            <p className="text-sm text-[hsl(var(--text-secondary))] mt-1 mb-4 max-w-md">
                {search ? 'Ningún proyecto coincide con tu búsqueda.' : 'Crea tu primer proyecto para empezar.'}
            </p>
            {!search && (
                <button
                    onClick={onShowCreate}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95"
                >
                    <Plus size={16} /> Crear proyecto
                </button>
            )}
        </div>
    );
}

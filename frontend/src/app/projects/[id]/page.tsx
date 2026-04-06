"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
    Target, Calendar as CalendarIcon, BarChart3, Settings,
    KanbanSquare, Zap, Table2,
    BookOpen, Plus, List, ChevronDown, Filter,
    X, Search, UserRound, Share2, Sparkles, Star, MoreHorizontal,
    Columns, Layers, Users, Flag, FileText, MessageSquare, FormInput,
    Milestone, PinIcon, LayoutTemplate, Clock, GitBranch
} from 'lucide-react';
import * as Popover from '@radix-ui/react-popover';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

import { ProjectKanbanBoard } from '@/components/projects/ProjectKanbanBoard';
import { ProjectMasterView } from '@/components/projects/ProjectMasterView';
import ProjectCalendarView from '@/components/projects/ProjectCalendarView';
import ProjectListView from '@/components/projects/ProjectListView';
import GanttView from '@/components/projects/GanttView';
import TaskDetailPanel from '@/components/projects/TaskDetailPanel';
import TaskRouteTree, { RouteNode } from '@/components/projects/TaskRouteTree';
import ProjectActivityFeed from '@/components/projects/ProjectActivityFeed';
import ProjectWikiEditor from '@/components/projects/ProjectWikiEditor';
import ProjectWhiteboard from '@/components/projects/ProjectWhiteboard';
import RightPanel from '@/components/ui/RightPanel';
import Sidebar3 from '@/components/ui/Sidebar3';
import TaskTableView from '@/components/projects/TaskTableView';

import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';
import Skeleton from '@/components/ui/Skeleton';

type ViewTab = 'lista' | 'kanban' | 'calendario' | 'gantt' | 'tabla' | 'wiki';

const VIEW_TABS: { id: ViewTab; label: string; icon: React.ElementType }[] = [
    { id: 'lista',      label: 'Lista',      icon: List },
    { id: 'kanban',     label: 'Tablero',    icon: KanbanSquare },
    { id: 'calendario', label: 'Calendario', icon: CalendarIcon },
    { id: 'gantt',      label: 'Gantt',      icon: BarChart3 },
    { id: 'tabla',      label: 'Tabla',      icon: Table2 },
    { id: 'wiki',       label: 'Wiki',       icon: BookOpen },
];

export default function ProjectDetailPage() {
    const params = useParams<{ id: string }>();
    const id = params?.id ?? '';
    const { token } = useAuth();
    const { addToast } = useToast();

    const [project, setProject] = useState<ProjectRecord | null>(null);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<ViewTab>('lista');
    const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(null);
    const [isWhiteboardOpen, setIsWhiteboardOpen] = useState(false);
    // Quick-add inline state
    const [quickAddStatus, setQuickAddStatus] = useState<string | null>(null);
    const [quickAddTitle, setQuickAddTitle] = useState('');
    // Dropdown popover state
    const [popoverOpen, setPopoverOpen] = useState(false);

    // Layer context — RIGHT panel for activity feed, S3 for route tree
    const { layers, toggleLayer, openLayer, closeLayer } = useSidebarLayers();

    useEffect(() => {
        const fetchProject = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<ProjectRecord>(`/projects/${id}`, { token, cache: 'no-store' });
                setProject(data);
                setTasks(data.tasks || []);
            } catch (err) {
                console.error(err);
                addToast('Error al cargar el proyecto', 'error');
            } finally {
                setLoading(false);
            }
        };
        fetchProject();
    }, [id, token, addToast]);

    const handleOpenTask = (task: ProjectTaskRecord) => {
        setSelectedTask(task);
        // Close S3 if it was showing a previous route
        closeLayer('S3');
    };

    const handleCloseTask = () => {
        setSelectedTask(null);
        closeLayer('S3');
    };

    // Build the route tree for the selected task
    const buildRouteTree = useCallback((): RouteNode[] => {
        if (!project) return [];
        return [
            {
                id: 'workspace',
                label: 'CCF Platform',
                type: 'workspace',
                children: [
                    {
                        id: 'portfolio',
                        label: 'Portfolio',
                        type: 'portfolio',
                        children: [
                            {
                                id: `project-${project.id}`,
                                label: project.title,
                                type: 'project',
                                children: tasks.map(t => ({
                                    id: `task-${t.id}`,
                                    label: t.title,
                                    type: 'task' as const,
                                    active: t.id === selectedTask?.id,
                                })),
                            },
                        ],
                    },
                ],
            },
        ];
    }, [project, tasks, selectedTask]);

    const handleVerRuta = () => {
        openLayer('S3');
    };

    const handleAddTask = async (status: string, dueDate?: string, title?: string) => {
        if (dueDate && title && project) {
            // Calendar: create task directly from its own inline input
            try {
                const newTask = await apiFetch<ProjectTaskRecord>(`/projects/${project.id}/tasks`, {
                    method: 'POST', token,
                    body: { title: title.trim(), status, priority: 'normal', due_date: dueDate }
                });
                setTasks(prev => [newTask, ...prev]);
                addToast('Tarea creada', 'success');
            } catch { addToast('Error al crear tarea', 'error'); }
            return;
        }
        // List/Table view: open inline quick-add
        setQuickAddStatus(status);
        setQuickAddTitle('');
    };

    const handleQuickAddConfirm = async () => {
        if (!quickAddTitle.trim() || !project) return;
        try {
            const newTask = await apiFetch<ProjectTaskRecord>(`/projects/${project.id}/tasks`, {
                method: 'POST', token,
                body: { title: quickAddTitle.trim(), status: quickAddStatus, priority: 'normal' }
            });
            setTasks(prev => [newTask, ...prev]);
            addToast('Tarea creada', 'success');
        } catch { addToast('Error al crear tarea', 'error'); }
        setQuickAddStatus(null);
        setQuickAddTitle('');
    };

    const handleQuickAddCancel = () => {
        setQuickAddStatus(null);
        setQuickAddTitle('');
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full p-10 space-y-6 bg-white dark:bg-[#1e1f21]">
                <Skeleton className="h-12 w-2/3 rounded-xl" />
                <Skeleton className="h-8 w-1/2 rounded-xl" />
                <Skeleton className="h-96 rounded-2xl" />
            </div>
        );
    }

    if (!project) return null;

    const completedTasks = tasks.filter((t) => t.status === 'done').length;
    const progress = tasks.length ? Math.round((completedTasks / tasks.length) * 100) : 0;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display">

            {/* ── CAPA A: BARRA SUPERIOR (breadcrumb + acciones globales) ───── */}
            <header className="h-10 flex items-center justify-between px-4 border-b border-slate-100 dark:border-white/5 shrink-0 bg-white dark:bg-[#1e1f21]">
                {/* Breadcrumb */}
                <div className="flex items-center gap-1.5 text-[12px] text-slate-500 overflow-hidden">
                    <span className="inline-flex items-center justify-center size-4 rounded bg-violet-600 text-white text-[9px] font-black shrink-0">P</span>
                    <span className="hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer truncate">Portfolio</span>
                    <span className="text-slate-300 dark:text-slate-600">/</span>
                    <span className="hover:text-slate-700 dark:hover:text-slate-300 cursor-pointer truncate">Proyectos</span>
                    <span className="text-slate-300 dark:text-slate-600">/</span>
                    <span className="flex items-center gap-1 font-bold text-slate-700 dark:text-slate-200 truncate cursor-pointer hover:text-violet-600 dark:hover:text-violet-400">
                        <span className="inline-block">⤢</span>
                        {project.title}
                    </span>
                    <Star size={12} className="text-slate-300 hover:text-amber-400 cursor-pointer shrink-0 ml-1 transition-colors" />
                </div>

                {/* Actions right */}
                <div className="flex items-center gap-1.5 shrink-0">
                    <ActionBtn icon={Users} label="Agentes" dot />
                    <ActionBtn icon={Zap} label="Automatizar" />
                    <ActionBtn icon={Sparkles} label="Ask AI" gradient />
                    <ActionBtn icon={Share2} label="Compartir" />
                    {/* ── Activity panel trigger (RIGHT layer) ── */}
                    <button
                        onClick={() => toggleLayer('RIGHT')}
                        title={layers.RIGHT ? 'Ocultar actividad' : 'Ver actividad'}
                        className={clsx(
                            'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all',
                            layers.RIGHT
                                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600'
                                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                        )}
                        aria-label="Toggle panel de actividad"
                        aria-expanded={layers.RIGHT}
                    >
                        <Clock size={13} />
                        <span>Actividad</span>
                    </button>
                </div>
            </header>

            {/* ── CAPA B: TAB BAR + sub-toolbar ─────────────────────────────── */}
            <div className="shrink-0 border-b border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21]">
                {/* Tab row */}
                <div className="flex items-center gap-0 px-2 overflow-x-auto scrollbar-none">
                    <button className="px-3 py-2.5 text-[12px] font-medium text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 whitespace-nowrap transition-colors border-r border-slate-100 dark:border-white/5 mr-2">
                        + Añadir canal
                    </button>
                    {VIEW_TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium whitespace-nowrap transition-all relative',
                                activeTab === tab.id
                                    ? 'text-slate-900 dark:text-white'
                                    : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                            )}
                        >
                            <tab.icon size={13} />
                            {tab.label}
                            {activeTab === tab.id && (
                                <motion.div
                                    layoutId="projectActiveTab"
                                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600 rounded-full"
                                />
                            )}
                        </button>
                    ))}
                    <button className="px-3 py-2.5 text-[12px] font-medium text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 whitespace-nowrap transition-colors ml-1">
                        + Vista
                    </button>
                </div>

                {/* Sub-toolbar */}
                {activeTab === 'lista' && (
                    <div className="flex items-center justify-between px-4 py-1.5 border-t border-slate-100 dark:border-white/5">
                        {/* Left: group + columns */}
                        <div className="flex items-center gap-2">
                            <SubFilterBtn icon={Layers} label="Grupo: Estado" />
                            <SubFilterBtn label="Subtareas" />
                            <SubFilterBtn icon={Columns} label="Columnas" />
                        </div>
                        {/* Right: filter + actions + Add Tarea */}
                        <div className="flex items-center gap-1.5">
                            <SubActionBtn icon={Filter} label="Filtro" />
                            <SubActionBtn label="Cerrada" withDot />
                            <SubActionBtn icon={UserRound} label="Persona asignada" />
                            {/* Avatar */}
                            <div className="size-6 rounded-full bg-violet-600 text-white flex items-center justify-center text-[9px] font-black">A</div>
                            <SubActionBtn icon={Search} />
                            <SubActionBtn icon={Settings} label="Personalizar" />
                            {/* Split "Añadir Tarea" button with ClickUp-style dropdown */}
                            <Popover.Root open={popoverOpen} onOpenChange={setPopoverOpen}>
                                <div className="flex items-center ml-1">
                                    <button
                                        onClick={() => {
                                            handleAddTask('todo');
                                            setPopoverOpen(false);
                                        }}
                                        className="h-7 flex items-center gap-1.5 px-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-bold rounded-l-lg hover:bg-slate-700 dark:hover:bg-slate-100 transition-colors"
                                    >
                                        Nuevo
                                    </button>
                                    <Popover.Trigger asChild>
                                        <button className="h-7 w-7 flex items-center justify-center bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-bold rounded-r-lg border-l border-white/20 dark:border-slate-900/20 hover:bg-slate-700 dark:hover:bg-slate-100 transition-colors">
                                            <ChevronDown size={13} />
                                        </button>
                                    </Popover.Trigger>
                                </div>
                                <Popover.Portal>
                                    <Popover.Content
                                        sideOffset={6}
                                        align="end"
                                        className="z-[9000] w-72 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-2xl p-0 overflow-hidden animate-in fade-in zoom-in-95"
                                    >
                                        {/* Header 2 columns */}
                                        <div className="grid grid-cols-2 border-b border-slate-100 dark:border-white/5">
                                            <div className="px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-slate-400 border-r border-slate-100 dark:border-white/5">
                                                Crear
                                            </div>
                                            <div className="px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-slate-400">
                                                Gestionar
                                            </div>
                                        </div>
                                        {/* Content 2 columns */}
                                        <div className="grid grid-cols-2">
                                            {/* Crear column */}
                                            <div className="border-r border-slate-100 dark:border-white/5 py-1">
                                                {[
                                                    {
                                                        icon: Flag, label: 'Tarea',
                                                        action: () => { handleAddTask('todo'); setPopoverOpen(false); }
                                                    },
                                                    {
                                                        icon: Milestone, label: 'Hito',
                                                        action: () => {
                                                            setQuickAddStatus('todo');
                                                            setQuickAddTitle('[Hito] ');
                                                            setPopoverOpen(false);
                                                        }
                                                    },
                                                    {
                                                        icon: MessageSquare, label: 'Nota de reunión',
                                                        action: () => {
                                                            setQuickAddStatus('todo');
                                                            setQuickAddTitle('[Reunión] ');
                                                            setPopoverOpen(false);
                                                        }
                                                    },
                                                    {
                                                        icon: FormInput, label: 'Respuesta de formulario',
                                                        action: () => {
                                                            setQuickAddStatus('todo');
                                                            setQuickAddTitle('[Formulario] ');
                                                            setPopoverOpen(false);
                                                        }
                                                    },
                                                    {
                                                        icon: Plus, label: 'Crear tipo de tarea',
                                                        action: () => { addToast('Tipos de tarea personalizados — próximamente', 'info'); setPopoverOpen(false); }
                                                    },
                                                    {
                                                        icon: List, label: 'Tarea de otra lista',
                                                        action: () => { addToast('Vinculación entre listas — próximamente', 'info'); setPopoverOpen(false); }
                                                    },
                                                ].map(item => (
                                                    <button
                                                        key={item.label}
                                                        onClick={item.action}
                                                        className="w-full flex items-center gap-2.5 px-3 py-2 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-left"
                                                    >
                                                        <item.icon size={13} className="text-slate-400 shrink-0" />
                                                        <span className="truncate">{item.label}</span>
                                                    </button>
                                                ))}
                                            </div>
                                            {/* Gestionar column */}
                                            <div className="py-1">
                                                {[
                                                    {
                                                        icon: PinIcon, label: 'Anclar plantilla',
                                                        action: () => { addToast('Plantillas — próximamente', 'info'); setPopoverOpen(false); }
                                                    },
                                                    {
                                                        icon: LayoutTemplate, label: 'Explorar plantillas',
                                                        action: () => { addToast('Biblioteca de plantillas — próximamente', 'info'); setPopoverOpen(false); }
                                                    },
                                                ].map(item => (
                                                    <button
                                                        key={item.label}
                                                        onClick={item.action}
                                                        className="w-full flex items-center gap-2.5 px-3 py-2 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-left"
                                                    >
                                                        <item.icon size={13} className="text-slate-400 shrink-0" />
                                                        <span className="truncate">{item.label}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </Popover.Content>
                                </Popover.Portal>
                            </Popover.Root>
                        </div>
                    </div>
                )}
            </div>

            {/* ── CAPA C: CONTENIDO PRINCIPAL + S3 + TASK PANEL ──────────────── */}
            <div className="flex-1 flex overflow-hidden">

                {/* S3 — Route Tree (slides in from left within content area) */}
                <Sidebar3 title="Ver Ruta" subtitle="Arquitectura de la tarea" width={260}>
                    <TaskRouteTree
                        breadcrumb={[
                            { label: 'CCF Platform', type: 'workspace' },
                            { label: 'Portfolio', type: 'portfolio' },
                            { label: project.title, type: 'project' },
                            { label: selectedTask?.title ?? 'Tarea', type: 'task' },
                        ]}
                        tree={buildRouteTree()}
                        activeId={selectedTask ? `task-${selectedTask.id}` : undefined}
                    />
                </Sidebar3>

                {/* View content */}
                <div className="flex-1 overflow-hidden min-w-0">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.15 }}
                            className="h-full"
                        >
                            {activeTab === 'lista' && (
                                <ProjectListView
                                    tasks={tasks}
                                    projectId={project.id}
                                    onOpenTask={handleOpenTask}
                                    onAddTask={handleAddTask}
                                    onTasksChange={setTasks}
                                    quickAddStatus={quickAddStatus}
                                    quickAddTitle={quickAddTitle}
                                    onQuickAddTitleChange={setQuickAddTitle}
                                    onQuickAddConfirm={handleQuickAddConfirm}
                                    onQuickAddCancel={handleQuickAddCancel}
                                />
                            )}
                            {activeTab === 'kanban' && (
                                <ProjectKanbanBoard
                                    project={project}
                                    tasks={tasks}
                                    onTasksChange={setTasks}
                                    onOpenTask={handleOpenTask}
                                    onAddTask={async (status) => handleAddTask(status)}
                                />
                            )}
                            {activeTab === 'calendario' && (
                                <ProjectCalendarView
                                    tasks={tasks}
                                    onTaskClick={handleOpenTask}
                                    onAddTask={handleAddTask}
                                />
                            )}
                            {activeTab === 'gantt' && <GanttView tasks={tasks} onTaskClick={handleOpenTask} />}
                            {activeTab === 'tabla' && (
                                <TaskTableView
                                    tasks={tasks}
                                    onOpenTask={handleOpenTask}
                                    onAddTask={handleAddTask}
                                    quickAddStatus={quickAddStatus}
                                    quickAddTitle={quickAddTitle}
                                    onQuickAddTitleChange={setQuickAddTitle}
                                    onQuickAddConfirm={handleQuickAddConfirm}
                                    onQuickAddCancel={handleQuickAddCancel}
                                />
                            )}
                            {activeTab === 'wiki' && (
                                <ProjectWikiEditor
                                    project_id={project.id}
                                    initialContent={project.description || ''}
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>

                {/* ── RIGHT PANEL: Actividad (push mode) ─── */}
                {!selectedTask && (
                    <RightPanel title="Actividad Reciente" width={300}>
                        <ProjectActivityFeed activities={[]} />
                    </RightPanel>
                )}

                {/* ── TASK DETAIL PANEL (non-blocking, no backdrop, resizable) ── */}
                <AnimatePresence>
                    {selectedTask && (
                        <TaskDetailPanel
                            task={selectedTask}
                            projectTitle={project.title}
                            onClose={handleCloseTask}
                            onUpdate={(updated) => setTasks(tasks.map(t => t.id === updated.id ? updated : t))}
                            onDelete={(id) => setTasks(tasks.filter(t => t.id !== id))}
                            onVerRutaClick={handleVerRuta}
                        />
                    )}
                </AnimatePresence>
            </div>

            {/* ── WHITEBOARD ──────────────────────────────────────────────────── */}
            <ProjectWhiteboard
                isOpen={isWhiteboardOpen}
                project_id={project.id}
                onClose={() => setIsWhiteboardOpen(false)}
            />
        </div>
    );
}

// ── Helper UI Components ───────────────────────────────────────────────────────
function ActionBtn({ icon: Icon, label, dot, gradient }: { icon?: React.ElementType; label: string; dot?: boolean; gradient?: boolean }) {
    return (
        <button className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all',
            gradient
                ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:opacity-90'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
        )}>
            {Icon && <Icon size={13} />}
            <span>{label}</span>
            {dot && <span className="size-1.5 rounded-full bg-rose-500 ml-0.5" />}
        </button>
    );
}

function SubFilterBtn({ icon: Icon, label }: { icon?: React.ElementType; label?: string }) {
    return (
        <button className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-200 transition-colors border border-slate-200 dark:border-white/10">
            {Icon && <Icon size={11} />}
            {label && <span>{label}</span>}
        </button>
    );
}

function SubActionBtn({ icon: Icon, label, withDot }: { icon?: React.ElementType; label?: string; withDot?: boolean }) {
    return (
        <button className="flex items-center gap-1 px-1.5 py-1 rounded-md text-[11px] font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
            {Icon && <Icon size={12} />}
            {label && <span>{label}</span>}
            {withDot && <span className="size-1.5 rounded-full bg-emerald-500 ml-0.5" />}
        </button>
    );
}

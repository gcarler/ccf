"use client";

import React, { useState, useRef, useMemo, useCallback } from 'react';
import {
    ZoomIn,
    ZoomOut,
    RotateCcw,
    Maximize2,
    Layers,
    FolderKanban,
    CheckCircle2,
    Clock,
    AlertCircle,
    User,
    Workflow as WorkflowIcon,
    GitFork,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';
import type { PhaseDef } from '@/context/ProjectUpdateContext';
import { TaskStatusBadge, TaskPriorityBadge, ProjectStatusBadge } from '@/components/projects/badges';
import { AvatarInitial } from '@/components/ui/AvatarInitial';

export interface ProjectWorkflowViewProps {
    project?: ProjectRecord | null;
    tasks: ProjectTaskRecord[];
    phases?: readonly PhaseDef[];
    onOpenTask: (task: ProjectTaskRecord) => void;
}

interface LayoutNode {
    id: string;
    level: 1 | 2 | 3 | 4 | 5;
    title: string;
    subtitle?: string;
    status?: string;
    priority?: string;
    assigneeName?: string;
    progress?: number;
    subtasksCount?: number;
    task?: ProjectTaskRecord;
    x: number;
    y: number;
    width: number;
    height: number;
    parentId?: string;
    childrenIds: string[];
}

interface LayoutConnection {
    id: string;
    parentId: string;
    childId: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

const DEFAULT_PHASES: PhaseDef[] = [
    { slug: 'backlog', name: 'Planificación', color: '#64748b', order_index: 0 },
    { slug: 'todo', name: 'Por hacer', color: '#3b82f6', order_index: 1 },
    { slug: 'in_progress', name: 'En progreso', color: '#f59e0b', order_index: 2 },
    { slug: 'review', name: 'Revisión', color: '#8b5cf6', order_index: 3 },
    { slug: 'done', name: 'Completado', color: '#10b981', order_index: 4 },
];

const NODE_WIDTH = 260;
const TASK_HEIGHT = 90;
const PHASE_HEIGHT = 70;
const ROOT_HEIGHT = 100;
const LEVEL_GAP_X = 140;
const ROW_GAP_Y = 24;

export default function ProjectWorkflowView({
    project,
    tasks = [],
    phases,
    onOpenTask,
}: ProjectWorkflowViewProps) {
    const containerRef = useRef<HTMLDivElement>(null);

    // Canvas pan and zoom state
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 60, y: 60 });
    const [isDragging, setIsDragging] = useState(false);
    const dragStartRef = useRef({ x: 0, y: 0 });
    const panStartRef = useRef({ x: 0, y: 0 });

    // Effective phases
    const effectivePhases = useMemo(() => {
        if (phases && phases.length > 0) return phases;
        return DEFAULT_PHASES;
    }, [phases]);

    // Build hierarchical layout
    const { nodes, connections, bounds } = useMemo(() => {
        const nodeList: LayoutNode[] = [];
        const connList: LayoutConnection[] = [];

        // Level 1: Project Root
        const rootId = 'node-root-project';
        const rootWidth = 270;
        const rootX = 60;

        // Group tasks into top-level and subtasks
        const subtasksByParent: Record<string, ProjectTaskRecord[]> = {};
        const topLevelTasks: ProjectTaskRecord[] = [];

        tasks.forEach(task => {
            if (task.parent_id) {
                if (!subtasksByParent[task.parent_id]) {
                    subtasksByParent[task.parent_id] = [];
                }
                subtasksByParent[task.parent_id].push(task);
            } else {
                topLevelTasks.push(task);
            }
        });

        // Group top-level tasks by phase
        const tasksByPhase: Record<string, ProjectTaskRecord[]> = {};
        effectivePhases.forEach(ph => {
            tasksByPhase[ph.slug] = [];
        });

        topLevelTasks.forEach(task => {
            const status = (task.status || 'todo').toLowerCase();
            if (tasksByPhase[status]) {
                tasksByPhase[status].push(task);
            } else {
                // If task status doesn't match any phase, assign to first phase or backlog
                const fallbackSlug = effectivePhases[0]?.slug || 'todo';
                if (!tasksByPhase[fallbackSlug]) {
                    tasksByPhase[fallbackSlug] = [];
                }
                tasksByPhase[fallbackSlug].push(task);
            }
        });

        // Calculate rows required per phase
        let currentY = 60;
        const phaseChildrenIds: string[] = [];

        const xLevel2 = rootX + rootWidth + LEVEL_GAP_X;
        const xLevel3 = xLevel2 + NODE_WIDTH + LEVEL_GAP_X;
        const xLevel4 = xLevel3 + NODE_WIDTH + LEVEL_GAP_X;

        // Iterate phases to position nodes
        effectivePhases.forEach(phase => {
            const phaseTasks = tasksByPhase[phase.slug] || [];
            const phaseNodeId = `node-phase-${phase.slug}`;
            phaseChildrenIds.push(phaseNodeId);

            const phaseStartY = currentY;
            const taskChildrenIds: string[] = [];

            if (phaseTasks.length === 0) {
                // Empty phase placeholder height
                currentY += PHASE_HEIGHT + ROW_GAP_Y;
            } else {
                phaseTasks.forEach(task => {
                    const taskId = `node-task-${task.id}`;
                    taskChildrenIds.push(taskId);

                    const subtasks = subtasksByParent[task.id] || task.subtasks || [];
                    const subtaskChildrenIds: string[] = [];

                    let taskRowStartY = currentY;

                    if (subtasks.length === 0) {
                        currentY += TASK_HEIGHT + ROW_GAP_Y;
                    } else {
                        subtasks.forEach(subtask => {
                            const subtaskId = `node-subtask-${subtask.id}`;
                            subtaskChildrenIds.push(subtaskId);

                            nodeList.push({
                                id: subtaskId,
                                level: 4,
                                title: subtask.title,
                                status: subtask.status,
                                priority: subtask.priority,
                                assigneeName: subtask.assignee_id ? `Asignado (${subtask.assignee_id.slice(0, 4)})` : undefined,
                                progress: subtask.physical_progress_pct,
                                task: subtask,
                                x: xLevel4,
                                y: currentY,
                                width: NODE_WIDTH,
                                height: TASK_HEIGHT,
                                parentId: taskId,
                                childrenIds: [],
                            });

                            currentY += TASK_HEIGHT + ROW_GAP_Y;
                        });
                    }

                    // Top-level activity position
                    const taskY = subtasks.length > 0
                        ? taskRowStartY + (currentY - ROW_GAP_Y - taskRowStartY - TASK_HEIGHT) / 2
                        : taskRowStartY;

                    nodeList.push({
                        id: taskId,
                        level: 3,
                        title: task.title,
                        subtitle: phase.name,
                        status: task.status,
                        priority: task.priority,
                        assigneeName: task.assignee_id ? `Asignado (${task.assignee_id.slice(0, 4)})` : undefined,
                        progress: task.physical_progress_pct,
                        subtasksCount: subtasks.length,
                        task,
                        x: xLevel3,
                        y: taskY,
                        width: NODE_WIDTH,
                        height: TASK_HEIGHT,
                        parentId: phaseNodeId,
                        childrenIds: subtaskChildrenIds,
                    });
                });
            }

            // Phase Node position (centered over its tasks)
            const phaseEndY = Math.max(currentY - ROW_GAP_Y, phaseStartY + PHASE_HEIGHT);
            const phaseY = phaseStartY + (phaseEndY - phaseStartY - PHASE_HEIGHT) / 2;

            nodeList.push({
                id: phaseNodeId,
                level: 2,
                title: phase.name,
                subtitle: `${phaseTasks.length} ${phaseTasks.length === 1 ? 'actividad' : 'actividades'}`,
                x: xLevel2,
                y: phaseY,
                width: NODE_WIDTH,
                height: PHASE_HEIGHT,
                parentId: rootId,
                childrenIds: taskChildrenIds,
            });

            // Extra space between phases
            currentY += ROW_GAP_Y;
        });

        // Root project position (centered across all phases)
        const totalHeight = Math.max(currentY, ROOT_HEIGHT + 120);
        const rootY = Math.max(60, (totalHeight - ROOT_HEIGHT) / 2);

        nodeList.unshift({
            id: rootId,
            level: 1,
            title: project?.title || 'Proyecto CCF',
            subtitle: `${tasks.length} actividades en total`,
            status: project?.status || 'active',
            x: rootX,
            y: rootY,
            width: rootWidth,
            height: ROOT_HEIGHT,
            childrenIds: phaseChildrenIds,
        });

        // Build connections
        const nodeMap = new Map<string, LayoutNode>();
        nodeList.forEach(n => nodeMap.set(n.id, n));

        nodeList.forEach(node => {
            node.childrenIds.forEach(childId => {
                const child = nodeMap.get(childId);
                if (child) {
                    connList.push({
                        id: `conn-${node.id}-${child.id}`,
                        parentId: node.id,
                        childId: child.id,
                        x1: node.x + node.width,
                        y1: node.y + node.height / 2,
                        x2: child.x,
                        y2: child.y + child.height / 2,
                    });
                }
            });
        });

        const maxX = Math.max(...nodeList.map(n => n.x + n.width), 1200) + 100;
        const maxY = Math.max(...nodeList.map(n => n.y + n.height), 800) + 100;

        return {
            nodes: nodeList,
            connections: connList,
            bounds: { width: maxX, height: maxY },
        };
    }, [project, tasks, effectivePhases]);

    // Pan & Drag handlers
    const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
        // Only start pan if clicking the canvas background
        if ((e.target as HTMLElement).closest('[data-interactive="true"]')) return;
        setIsDragging(true);
        dragStartRef.current = { x: e.clientX, y: e.clientY };
        panStartRef.current = { ...pan };
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!isDragging) return;
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;
        setPan({
            x: panStartRef.current.x + dx,
            y: panStartRef.current.y + dy,
        });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.1 : -0.1;
            setZoom(prev => Math.min(2.5, Math.max(0.3, Number((prev + delta).toFixed(2)))));
        } else {
            // Scroll pans vertically
            setPan(prev => ({
                x: prev.x - e.deltaX * 0.8,
                y: prev.y - e.deltaY * 0.8,
            }));
        }
    };

    // Zoom Controls
    const handleZoomIn = () => setZoom(prev => Math.min(2.5, Number((prev + 0.15).toFixed(2))));
    const handleZoomOut = () => setZoom(prev => Math.max(0.3, Number((prev - 0.15).toFixed(2))));
    const handleResetZoom = () => {
        setZoom(1);
        setPan({ x: 60, y: 60 });
    };

    const handleFitView = () => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const scaleX = (rect.width - 120) / bounds.width;
        const scaleY = (rect.height - 120) / bounds.height;
        const newZoom = Math.min(1.2, Math.max(0.35, Math.min(scaleX, scaleY)));
        setZoom(Number(newZoom.toFixed(2)));
        setPan({ x: 40, y: 40 });
    };

    return (
        <div
            data-testid="project-workflow-canvas-container"
            ref={containerRef}
            className="relative w-full h-full overflow-hidden select-none bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg shadow-sm"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        >
            {/* Background Canvas Grid Pattern */}
            <svg
                className="absolute inset-0 w-full h-full pointer-events-none opacity-40"
                xmlns="http://www.w3.org/2000/svg"
            >
                <defs>
                    <pattern
                        id="workflow-grid-dots"
                        x={pan.x % (24 * zoom)}
                        y={pan.y % (24 * zoom)}
                        width={24 * zoom}
                        height={24 * zoom}
                        patternUnits="userSpaceOnUse"
                    >
                        <circle
                            cx={2 * zoom}
                            cy={2 * zoom}
                            r={1.2 * zoom}
                            fill="hsl(var(--border))"
                        />
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#workflow-grid-dots)" />
            </svg>

            {/* Transform Layer (Pan & Zoom) */}
            <div
                data-testid="workflow-transform-layer"
                className="absolute top-0 left-0 transition-transform duration-75 origin-top-left"
                style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                    width: bounds.width,
                    height: bounds.height,
                }}
            >
                {/* SVG Connectors between nodes */}
                <svg
                    data-testid="workflow-svg-connectors"
                    className="absolute inset-0 w-full h-full pointer-events-none z-10"
                    width={bounds.width}
                    height={bounds.height}
                >
                    <defs>
                        <linearGradient id="conn-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.8" />
                            <stop offset="100%" stopColor="hsl(var(--info))" stopOpacity="0.8" />
                        </linearGradient>
                    </defs>
                    {connections.map(conn => {
                        const dx = conn.x2 - conn.x1;
                        const pathD = `M ${conn.x1} ${conn.y1} C ${conn.x1 + dx * 0.45} ${conn.y1}, ${conn.x2 - dx * 0.45} ${conn.y2}, ${conn.x2} ${conn.y2}`;
                        return (
                            <g key={conn.id}>
                                <path
                                    d={pathD}
                                    fill="none"
                                    stroke="hsl(var(--border))"
                                    strokeWidth="2.5"
                                    className="transition-colors hover:stroke-[hsl(var(--primary))]"
                                />
                                <circle cx={conn.x1} cy={conn.y1} r="3.5" fill="hsl(var(--primary))" />
                                <circle cx={conn.x2} cy={conn.y2} r="3.5" fill="hsl(var(--primary))" />
                            </g>
                        );
                    })}
                </svg>

                {/* Render Nodes */}
                <div className="absolute inset-0 z-20">
                    {nodes.map(node => {
                        // Level 1: Project Node
                        if (node.level === 1) {
                            return (
                                <div
                                    key={node.id}
                                    data-testid={`workflow-node-${node.id}`}
                                    className="absolute p-4 rounded-xl border-2 border-[hsl(var(--primary)/0.6)] bg-[hsl(var(--surface-1))] shadow-lg flex flex-col justify-between"
                                    style={{
                                        left: node.x,
                                        top: node.y,
                                        width: node.width,
                                        height: node.height,
                                    }}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                                            <WorkflowIcon size={14} />
                                            Proyecto
                                        </span>
                                        <ProjectStatusBadge value={node.status} />
                                    </div>
                                    <h2 className="text-base font-bold text-[hsl(var(--text-primary))] truncate" title={node.title}>
                                        {node.title}
                                    </h2>
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium">
                                        {node.subtitle}
                                    </p>
                                </div>
                            );
                        }

                        // Level 2: Component / Phase Node
                        if (node.level === 2) {
                            return (
                                <div
                                    key={node.id}
                                    data-testid={`workflow-node-${node.id}`}
                                    className="absolute p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.6)] backdrop-blur shadow-sm flex flex-col justify-center"
                                    style={{
                                        left: node.x,
                                        top: node.y,
                                        width: node.width,
                                        height: node.height,
                                    }}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="flex items-center gap-1 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                            <FolderKanban size={13} />
                                            Fase / Componente
                                        </span>
                                        <span className="text-2xs font-bold px-1.5 py-0.5 rounded-full bg-[hsl(var(--surface-3))] text-[hsl(var(--text-primary))]">
                                            {node.subtitle?.split(' ')[0] ?? 0}
                                        </span>
                                    </div>
                                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate mt-1" title={node.title}>
                                        {node.title}
                                    </h3>
                                </div>
                            );
                        }

                        // Level 3 & 4: Task / Subtask Nodes
                        const isSubtask = node.level >= 4;
                        return (
                            <div
                                key={node.id}
                                data-testid={`workflow-node-${node.id}`}
                                data-interactive="true"
                                role="button"
                                tabIndex={0}
                                aria-label={`${isSubtask ? 'Subactividad' : 'Actividad'}: ${node.title}`}
                                onClick={() => node.task && onOpenTask(node.task)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        if (node.task) onOpenTask(node.task);
                                    }
                                }}
                                className={clsx(
                                    "absolute p-3 rounded-lg border transition-all cursor-pointer shadow-sm flex flex-col justify-between",
                                    "bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary))] hover:shadow-md active:scale-[0.99]",
                                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2",
                                    isSubtask ? "border-[hsl(var(--border)/0.8)] opacity-95" : "border-[hsl(var(--border))]"
                                )}
                                style={{
                                    left: node.x,
                                    top: node.y,
                                    width: node.width,
                                    height: node.height,
                                }}
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate flex-1" title={node.title}>
                                        {node.title}
                                    </span>
                                    <AvatarInitial name={node.assigneeName || 'CCF'} size="sm" />
                                </div>

                                <div className="flex items-center justify-between gap-1.5 pt-1 border-t border-[hsl(var(--border)/0.5)]">
                                    <div className="flex items-center gap-1">
                                        <TaskStatusBadge value={node.status} />
                                        <TaskPriorityBadge value={node.priority} hideDot />
                                    </div>

                                    {Boolean(node.subtasksCount) && (
                                        <span className="text-2xs font-medium text-[hsl(var(--text-secondary))] flex items-center gap-0.5">
                                            <GitFork size={11} />
                                            {node.subtasksCount}
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Empty state overlay when no tasks */}
            {tasks.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="p-6 rounded-xl bg-[hsl(var(--surface-1)/0.9)] backdrop-blur border border-[hsl(var(--border))] text-center shadow-lg pointer-events-auto max-w-sm">
                        <WorkflowIcon className="size-10 text-[hsl(var(--primary))] mx-auto mb-3" />
                        <h4 className="text-base font-bold text-[hsl(var(--text-primary))]">
                            Lienzo de Workflow Vacío
                        </h4>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
                            Aún no hay actividades en este proyecto. Crea actividades para visualizarlas en el flujo de trabajo.
                        </p>
                    </div>
                </div>
            )}

            {/* Floating Zoom & Controls Toolbar */}
            <div
                data-interactive="true"
                className="absolute bottom-4 right-4 flex items-center gap-1 p-1 bg-[hsl(var(--surface-1)/0.9)] backdrop-blur rounded-lg border border-[hsl(var(--border))] shadow-md z-30"
            >
                <button
                    type="button"
                    onClick={handleZoomIn}
                    aria-label="Acercar"
                    title="Acercar (+)"
                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))]"
                >
                    <ZoomIn size={15} />
                </button>
                <span
                    data-testid="workflow-zoom-level"
                    className="text-xs font-semibold text-[hsl(var(--text-primary))] px-2 min-w-[44px] text-center"
                >
                    {Math.round(zoom * 100)}%
                </span>
                <button
                    type="button"
                    onClick={handleZoomOut}
                    aria-label="Alejar"
                    title="Alejar (-)"
                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))]"
                >
                    <ZoomOut size={15} />
                </button>
                <div className="w-[1px] h-4 bg-[hsl(var(--border))] mx-0.5" />
                <button
                    type="button"
                    onClick={handleResetZoom}
                    aria-label="Restablecer vista"
                    title="Restablecer vista (100%)"
                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))]"
                >
                    <RotateCcw size={14} />
                </button>
                <button
                    type="button"
                    onClick={handleFitView}
                    aria-label="Ajustar al lienzo"
                    title="Ajustar al lienzo"
                    className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))]"
                >
                    <Maximize2 size={14} />
                </button>
            </div>
        </div>
    );
}

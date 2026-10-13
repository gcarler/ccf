"use client";

import React, { useState, useRef, useMemo, useEffect } from 'react';
import {
    ZoomIn,
    ZoomOut,
    RotateCcw,
    Maximize2,
    Layers,
    Workflow as WorkflowIcon,
    GitFork,
    DollarSign,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord, ProjectComponent, ProjectComponentDetail, ProjectComponentsBreakdown } from '@/types/projects';
import type { PhaseDef } from '@/context/ProjectUpdateContext';
import { TaskStatusBadge, TaskPriorityBadge, ProjectStatusBadge } from '@/components/projects/badges';
import { AvatarInitial } from '@/components/ui/AvatarInitial';
import { useOptionalAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

export interface ProjectWorkflowViewProps {
    project?: ProjectRecord | null;
    tasks: ProjectTaskRecord[];
    components?: (ProjectComponent | ProjectComponentDetail)[];
    phases?: readonly PhaseDef[];
    onOpenTask: (task: ProjectTaskRecord) => void;
}

interface LayoutNode {
    id: string;
    level: number;
    levelLabel: string;
    title: string;
    subtitle?: string;
    code?: string;
    budget?: number;
    color?: string;
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

const ROOT_WIDTH = 270;
const ROOT_HEIGHT = 100;
const COMP_WIDTH = 260;
const COMP_HEIGHT = 80;
const TASK_WIDTH = 260;
const TASK_HEIGHT = 90;
const LEVEL_GAP_X = 140;
const ROW_GAP_Y = 24;

function getLevelLabel(level: number): string {
    if (level === 1) return 'Nivel 1 · Proyecto';
    if (level === 2) return 'Nivel 2 · Componente';
    if (level === 3) return 'Nivel 3 · Actividad';
    if (level === 4) return 'Nivel 4 · Subactividad';
    if (level === 5) return 'Nivel 5 · Tarea';
    return `Nivel ${level} · Tarea`;
}

export default function ProjectWorkflowView({
    project,
    tasks = [],
    components: propComponents,
    onOpenTask,
}: ProjectWorkflowViewProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const auth = useOptionalAuth();
    const token = auth?.token;

    // Canvas pan and zoom state
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 60, y: 60 });
    const [isDragging, setIsDragging] = useState(false);
    const dragStartRef = useRef({ x: 0, y: 0 });
    const panStartRef = useRef({ x: 0, y: 0 });

    // Components state (either from props or fetched from components-breakdown)
    const [fetchedComponents, setFetchedComponents] = useState<ProjectComponentDetail[]>([]);

    useEffect(() => {
        if (propComponents && propComponents.length > 0) return;
        if (!project?.id) return;

        let isMounted = true;
        apiFetch<ProjectComponentsBreakdown>(`/projects/${project.id}/components-breakdown`, { token })
            .then(res => {
                if (isMounted && res?.components) {
                    setFetchedComponents(res.components);
                }
            })
            .catch(() => {
                // Silently fallback if endpoint unavailable or offline
            });

        return () => { isMounted = false; };
    }, [project?.id, propComponents, token]);

    const effectiveComponents = useMemo(() => {
        if (propComponents && propComponents.length > 0) {
            return propComponents;
        }
        return fetchedComponents;
    }, [propComponents, fetchedComponents]);

    // Build hierarchical layout with arbitrary depth recursion
    const { nodes, connections, bounds } = useMemo(() => {
        const nodeList: LayoutNode[] = [];
        const connList: LayoutConnection[] = [];

        // Level 1: Project Root Node
        const rootId = 'node-root-project';
        const rootX = 60;
        const xLevel2 = rootX + ROOT_WIDTH + LEVEL_GAP_X;
        const xLevel3 = xLevel2 + COMP_WIDTH + LEVEL_GAP_X;

        // Map tasks by ID and build adjacency tree (childrenMap)
        const taskMap = new Map<string, ProjectTaskRecord>();
        const childrenMap = new Map<string, ProjectTaskRecord[]>();

        tasks.forEach(task => {
            taskMap.set(task.id, task);
        });

        tasks.forEach(task => {
            if (task.parent_id && taskMap.has(task.parent_id)) {
                if (!childrenMap.has(task.parent_id)) {
                    childrenMap.set(task.parent_id, []);
                }
                childrenMap.get(task.parent_id)!.push(task);
            }
        });

        // Determine components list
        interface CompItem {
            id: string;
            code: string;
            name: string;
            budget?: number;
            color?: string;
            isSynthetic?: boolean;
        }

        const compItems: CompItem[] = [];
        const knownCompIds = new Set<string>();

        if (effectiveComponents.length > 0) {
            effectiveComponents.forEach(c => {
                knownCompIds.add(c.id);
                compItems.push({
                    id: c.id,
                    code: c.code || 'COMP',
                    name: c.name,
                    budget: c.budget_allocated,
                    color: c.color || '#3b82f6',
                });
            });
        }

        // Check if there are root tasks with no component or with unknown component_id
        const hasUnassignedTasks = tasks.some(t => {
            const isRoot = !t.parent_id || !taskMap.has(t.parent_id);
            return isRoot && (!t.component_id || !knownCompIds.has(t.component_id));
        });

        if (compItems.length === 0) {
            // No components defined in project yet: provide default general component
            compItems.push({
                id: 'comp-default',
                code: 'COMP-01',
                name: 'Componente General',
                color: '#3b82f6',
                isSynthetic: true,
            });
        } else if (hasUnassignedTasks) {
            // Append general component for tasks without explicit component assignment
            compItems.push({
                id: 'comp-general',
                code: 'GRAL',
                name: 'Actividades Generales',
                color: '#64748b',
                isSynthetic: true,
            });
        }

        let currentY = 60;
        const compChildrenIds: string[] = [];

        // Recursive subtree layout function for tasks at any arbitrary depth (Level 3, 4, 5, ... N)
        const visitedTasks = new Set<string>();

        function layoutTaskSubtree(task: ProjectTaskRecord, level: number): { topY: number; bottomY: number; centerY: number } {
            visitedTasks.add(task.id);
            const taskId = `node-task-${task.id}`;
            const x = xLevel3 + (level - 3) * (TASK_WIDTH + LEVEL_GAP_X);
            const children = (childrenMap.get(task.id) || []).filter(c => !visitedTasks.has(c.id));

            if (children.length === 0) {
                const y = currentY;
                currentY += TASK_HEIGHT + ROW_GAP_Y;

                nodeList.push({
                    id: taskId,
                    level,
                    levelLabel: getLevelLabel(level),
                    title: task.title,
                    status: task.status,
                    priority: task.priority,
                    assigneeName: task.assignee_id ? `Asignado (${task.assignee_id.slice(0, 4)})` : undefined,
                    progress: task.physical_progress_pct,
                    task,
                    x,
                    y,
                    width: TASK_WIDTH,
                    height: TASK_HEIGHT,
                    childrenIds: [],
                });

                return { topY: y, bottomY: y + TASK_HEIGHT, centerY: y };
            }

            // Has children: recursively layout each child subtree
            const childIds: string[] = [];
            const childCenterYs: number[] = [];
            let minChildY = Infinity;
            let maxChildY = -Infinity;

            children.forEach(child => {
                childIds.push(`node-task-${child.id}`);
                const res = layoutTaskSubtree(child, level + 1);
                childCenterYs.push(res.centerY);
                minChildY = Math.min(minChildY, res.topY);
                maxChildY = Math.max(maxChildY, res.bottomY);
            });

            // Parent node is vertically centered relative to its direct children
            const y = childCenterYs.length > 0
                ? (childCenterYs[0] + childCenterYs[childCenterYs.length - 1]) / 2
                : minChildY;

            nodeList.push({
                id: taskId,
                level,
                levelLabel: getLevelLabel(level),
                title: task.title,
                status: task.status,
                priority: task.priority,
                assigneeName: task.assignee_id ? `Asignado (${task.assignee_id.slice(0, 4)})` : undefined,
                progress: task.physical_progress_pct,
                subtasksCount: children.length,
                task,
                x,
                y,
                width: TASK_WIDTH,
                height: TASK_HEIGHT,
                childrenIds: childIds,
            });

            return { topY: minChildY, bottomY: maxChildY, centerY: y };
        }

        // Layout each Component (Level 2) and its root activities
        compItems.forEach(comp => {
            const compNodeId = `node-comp-${comp.id}`;
            compChildrenIds.push(compNodeId);

            // Filter direct root activities under this component
            const isSynthetic = comp.isSynthetic;
            const rootTasks = tasks.filter(t => {
                const isRoot = !t.parent_id || !taskMap.has(t.parent_id);
                if (!isRoot) return false;

                if (comp.id === 'comp-default') return true;
                if (comp.id === 'comp-general') {
                    return !t.component_id || !knownCompIds.has(t.component_id);
                }
                return t.component_id === comp.id;
            });

            const compStartY = currentY;
            const taskChildrenIds: string[] = [];

            if (rootTasks.length === 0) {
                // Empty component row
                currentY += COMP_HEIGHT + ROW_GAP_Y;
                nodeList.push({
                    id: compNodeId,
                    level: 2,
                    levelLabel: getLevelLabel(2),
                    code: comp.code,
                    title: comp.name,
                    subtitle: '0 actividades',
                    budget: comp.budget,
                    color: comp.color,
                    x: xLevel2,
                    y: compStartY,
                    width: COMP_WIDTH,
                    height: COMP_HEIGHT,
                    parentId: rootId,
                    childrenIds: [],
                });
            } else {
                const rootCenterYs: number[] = [];
                rootTasks.forEach(task => {
                    const taskNodeId = `node-task-${task.id}`;
                    taskChildrenIds.push(taskNodeId);
                    const res = layoutTaskSubtree(task, 3);
                    rootCenterYs.push(res.centerY);
                });

                const compY = (rootCenterYs[0] + rootCenterYs[rootCenterYs.length - 1]) / 2;

                nodeList.push({
                    id: compNodeId,
                    level: 2,
                    levelLabel: getLevelLabel(2),
                    code: comp.code,
                    title: comp.name,
                    subtitle: `${rootTasks.length} ${rootTasks.length === 1 ? 'actividad' : 'actividades'}`,
                    budget: comp.budget,
                    color: comp.color,
                    x: xLevel2,
                    y: compY,
                    width: COMP_WIDTH,
                    height: COMP_HEIGHT,
                    parentId: rootId,
                    childrenIds: taskChildrenIds,
                });
            }

            currentY += ROW_GAP_Y;
        });

        // Level 1: Project Root position (centered across all components)
        const totalHeight = Math.max(currentY, ROOT_HEIGHT + 120);
        const rootY = Math.max(60, (totalHeight - ROOT_HEIGHT) / 2);

        nodeList.unshift({
            id: rootId,
            level: 1,
            levelLabel: getLevelLabel(1),
            title: project?.title || 'Proyecto CCF',
            subtitle: `${compItems.length} ${compItems.length === 1 ? 'componente' : 'componentes'} · ${tasks.length} actividades`,
            status: project?.status || 'active',
            budget: project?.budget_allocated ?? undefined,
            x: rootX,
            y: rootY,
            width: ROOT_WIDTH,
            height: ROOT_HEIGHT,
            childrenIds: compChildrenIds,
        });

        // Build connections list from parent-child relationships
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

        const maxX = Math.max(...nodeList.map(n => n.x + n.width), 1200) + 120;
        const maxY = Math.max(...nodeList.map(n => n.y + n.height), 800) + 120;

        return {
            nodes: nodeList,
            connections: connList,
            bounds: { width: maxX, height: maxY },
        };
    }, [project, tasks, effectiveComponents]);

    // Pan & Drag handlers
    const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
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
                                    className="absolute p-4 rounded-xl border-2 border-[hsl(var(--primary)/0.7)] bg-[hsl(var(--surface-1))] shadow-lg flex flex-col justify-between"
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
                                            {node.levelLabel}
                                        </span>
                                        <ProjectStatusBadge value={node.status} />
                                    </div>
                                    <h2 className="text-base font-bold text-[hsl(var(--text-primary))] truncate" title={node.title}>
                                        {node.title}
                                    </h2>
                                    <div className="flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))] font-medium">
                                        <span>{node.subtitle}</span>
                                        {Boolean(node.budget) && (
                                            <span className="font-semibold text-[hsl(var(--text-primary))] flex items-center">
                                                <DollarSign size={10} className="inline" />
                                                {node.budget?.toLocaleString('es-CO')}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        }

                        // Level 2: Component Node (EDT / WBS)
                        if (node.level === 2) {
                            return (
                                <div
                                    key={node.id}
                                    data-testid={`workflow-node-${node.id}`}
                                    className="absolute p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.75)] backdrop-blur shadow-sm flex flex-col justify-between"
                                    style={{
                                        left: node.x,
                                        top: node.y,
                                        width: node.width,
                                        height: node.height,
                                    }}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))]">
                                            <Layers size={13} style={{ color: node.color }} />
                                            <span className="px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] font-mono text-3xs font-extrabold" style={{ color: node.color }}>
                                                {node.code}
                                            </span>
                                        </span>
                                        <span className="text-3xs font-semibold px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]">
                                            Nivel 2 · Componente
                                        </span>
                                    </div>
                                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate" title={node.title}>
                                        {node.title}
                                    </h3>
                                    <div className="flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))]">
                                        <span>{node.subtitle}</span>
                                        {Boolean(node.budget) && (
                                            <span className="font-medium text-[hsl(var(--text-primary))] flex items-center">
                                                <DollarSign size={10} className="inline" />
                                                {node.budget?.toLocaleString('es-CO')}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        }

                        // Level 3, 4, 5 ... N: Recursive Task / Activity Nodes
                        const isSubtask = node.level >= 4;
                        return (
                            <div
                                key={node.id}
                                data-testid={`workflow-node-${node.id}`}
                                data-interactive="true"
                                role="button"
                                tabIndex={0}
                                aria-label={`${node.levelLabel}: ${node.title}`}
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
                                <div className="flex items-center justify-between gap-1.5">
                                    <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                        {node.levelLabel}
                                    </span>
                                    <AvatarInitial name={node.assigneeName || 'CCF'} size="sm" />
                                </div>

                                <span className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate my-1" title={node.title}>
                                    {node.title}
                                </span>

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

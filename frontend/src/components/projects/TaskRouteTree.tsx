"use client";

import { useMemo, useState, ElementType } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronRight, ChevronDown, FolderOpen,
    Target, FileText, CheckSquare, Home, ArrowRight,
    Search, ShieldCheck, Layers,
} from 'lucide-react';
import clsx from 'clsx';

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export interface RouteNode {
    id: string;
    label: string;
    type: 'workspace' | 'portfolio' | 'project' | 'section' | 'task';
    href?: string;
    active?: boolean;
    children?: RouteNode[];
}

interface TaskRouteTreeProps {
    /** La ruta activa desde raíz hasta la tarea actual */
    breadcrumb: Array<{ label: string; type: RouteNode['type'] }>;
    /** Árbol completo de nodos (portfolio → projects → tasks) */
    tree: RouteNode[];
    /** ID del nodo activo (la tarea abierta) */
    activeId?: string;
    onNavigate?: (node: RouteNode) => void;
}

// ─────────────────────────────────────────────────────────────────
// NODE ICONS
// ─────────────────────────────────────────────────────────────────
const TYPE_ICON: Record<RouteNode['type'], ElementType> = {
    workspace: Home,
    portfolio: Target,
    project:   FolderOpen,
    section:   FileText,
    task:      CheckSquare,
};

const TYPE_COLOR: Record<RouteNode['type'], string> = {
    workspace: 'text-[hsl(var(--text-secondary))]',
    portfolio: 'text-[hsl(var(--primary))]',
    project:   'text-[hsl(var(--primary))]',
    section:   'text-[hsl(var(--warning))]',
    task:      'text-[hsl(var(--success))]',
};

function computeWbsTreeStats(
    nodes: RouteNode[],
    currentDepth = 1
): { totalNodes: number; maxDepth: number; leafPackagesCount: number } {
    if (!nodes || nodes.length === 0) {
        return { totalNodes: 0, maxDepth: 0, leafPackagesCount: 0 };
    }
    let totalNodes = 0;
    let maxDepth = currentDepth;
    let leafPackagesCount = 0;

    for (const node of nodes) {
        totalNodes += 1;
        const children = node.children ?? [];
        if (children.length === 0) {
            if (node.type === 'task') {
                leafPackagesCount += 1;
            }
        } else {
            const childStats = computeWbsTreeStats(children, currentDepth + 1);
            totalNodes += childStats.totalNodes;
            if (childStats.maxDepth > maxDepth) {
                maxDepth = childStats.maxDepth;
            }
            leafPackagesCount += childStats.leafPackagesCount;
        }
    }

    return { totalNodes, maxDepth, leafPackagesCount };
}

function filterWbsTree(
    nodes: RouteNode[],
    query: string,
    onlyLeafPackages: boolean
): RouteNode[] {
    const q = query.trim().toLowerCase();
    if (!q && !onlyLeafPackages) {
        return nodes;
    }

    const result: RouteNode[] = [];
    for (const node of nodes) {
        const rawChildren = node.children ?? [];
        const filteredChildren = filterWbsTree(rawChildren, query, onlyLeafPackages);
        const matchesQuery = !q || node.label.toLowerCase().includes(q);
        const isLeafTask = node.type === 'task' && rawChildren.length === 0;

        if (onlyLeafPackages) {
            if ((isLeafTask && matchesQuery) || filteredChildren.length > 0) {
                result.push({
                    ...node,
                    children: filteredChildren,
                });
            }
        } else if (matchesQuery || filteredChildren.length > 0) {
            result.push({
                ...node,
                children: filteredChildren,
            });
        }
    }
    return result;
}

// ─────────────────────────────────────────────────────────────────
// RECURSIVE TREE NODE
// ─────────────────────────────────────────────────────────────────
function TreeNode({
    node,
    depth = 0,
    activeId,
    forceExpand = false,
    onNavigate,
}: {
    node: RouteNode;
    depth?: number;
    activeId?: string;
    forceExpand?: boolean;
    onNavigate?: (n: RouteNode) => void;
}) {
    const [open, setOpen] = useState(node.active || node.children?.some(c => c.active || c.id === activeId) || false);
    const hasChildren = (node.children?.length ?? 0) > 0;
    const isExpanded = forceExpand || open;
    const isActive = node.id === activeId || node.active;
    const Icon = TYPE_ICON[node.type] ?? FileText;

    return (
        <div>
            <div
                onClick={() => {
                    if (hasChildren) setOpen(v => !v);
                    onNavigate?.(node);
                }}
                className={clsx(
                    'group relative flex items-center gap-1.5 py-1.5 px-2 rounded-lg cursor-pointer transition-all select-none',
                    isActive
                        ? 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                        : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]',
                )}
                style={{ paddingLeft: depth * 16 + 8 }}
            >
                {/* Guide line */}
                {depth > 0 && (
                    <div
                        className="absolute top-0 bottom-0 w-px bg-[hsl(var(--border))]"
                        style={{ left: depth * 16 - 4 }}
                    />
                )}

                {/* Expand arrow */}
                <span className={clsx('shrink-0 transition-transform', !hasChildren && 'opacity-0 pointer-events-none')}>
                    {isExpanded
                        ? <ChevronDown size={11} />
                        : <ChevronRight size={11} />
                    }
                </span>

                {/* Node icon */}
                <span className={clsx('shrink-0', TYPE_COLOR[node.type])}>
                    <Icon size={12} />
                </span>

                {/* Label */}
                <span className={clsx(
                    'flex-1 text-sm truncate',
                    isActive ? 'font-bold' : 'font-medium'
                )}>
                    {node.label}
                </span>

                {/* Active indicator */}
                {isActive && (
                    <span className="font-semibold px-1.5 py-0.5 bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] rounded">
                        actual
                    </span>
                )}

                {/* Navigate arrow on hover */}
                {!isActive && node.href && (
                    <ArrowRight size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                )}
            </div>

            {/* Children */}
            <AnimatePresence initial={false}>
                {isExpanded && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.16 }}
                        className="overflow-hidden"
                    >
                        {node.children!.map(child => (
                            <TreeNode
                                key={child.id}
                                node={child}
                                depth={depth + 1}
                                activeId={activeId}
                                forceExpand={forceExpand}
                                onNavigate={onNavigate}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────
// MAIN: TASK ROUTE TREE
// ─────────────────────────────────────────────────────────────────
export default function TaskRouteTree({
    breadcrumb,
    tree,
    activeId,
    onNavigate,
}: TaskRouteTreeProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [onlyLeafPackages, setOnlyLeafPackages] = useState(false);

    const wbsStats = useMemo(() => computeWbsTreeStats(tree), [tree]);
    const filteredTree = useMemo(
        () => filterWbsTree(tree, searchQuery, onlyLeafPackages),
        [tree, searchQuery, onlyLeafPackages]
    );
    const isFiltering = Boolean(searchQuery.trim() || onlyLeafPackages);

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-2">Ruta de la actividad</p>

                {/* Breadcrumb path */}
                <div className="flex flex-col gap-1">
                    {breadcrumb.map((crumb, i) => {
                        const CrumbIcon = TYPE_ICON[crumb.type] ?? FileText;
                        const isLast = i === breadcrumb.length - 1;
                        return (
                            <div key={i} className="flex items-center gap-2" style={{ paddingLeft: i * 12 }}>
                                {/* Connector line */}
                                {i > 0 && (
                                    <div className="w-px h-4 bg-[hsl(var(--border))] shrink-0 -ml-px" />
                                )}
                                <div className={clsx(
                                    'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs',
                                    isLast
                                        ? 'font-bold text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]'
                                        : 'font-medium text-[hsl(var(--muted-foreground))]'
                                )}>
                                    <CrumbIcon size={11} className={TYPE_COLOR[crumb.type]} />
                                    {crumb.label}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Resumen de Jerarquía WBS PMI */}
            <div
                data-testid="task-route-pmi-summary"
                className="px-4 py-2.5 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2"
            >
                <div className="flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    <ShieldCheck size={12} className="text-[hsl(var(--primary))]" />
                    <span>Diagnóstico de Jerarquía WBS (PMI §5.4)</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Nodos Totales
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {wbsStats.totalNodes}
                        </p>
                    </div>
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Profundidad WBS
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {wbsStats.maxDepth} niveles
                        </p>
                    </div>
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Paquetes Hoja (WP)
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--success))] mt-0.5">
                            {wbsStats.leafPackagesCount}
                        </p>
                    </div>
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Nivel WBS Actual
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--primary))] mt-0.5">
                            Nivel {breadcrumb.length}
                        </p>
                    </div>
                </div>
            </div>

            {/* Barra de Búsqueda y Filtro WBS */}
            <div
                data-testid="task-route-filter-bar"
                className="px-4 py-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex items-center gap-2 flex-wrap"
            >
                <div className="relative flex-1 min-w-[160px]">
                    <Search
                        size={12}
                        className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
                    />
                    <input
                        type="text"
                        data-testid="task-route-search-input"
                        aria-label="Filtrar nodo WBS"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Filtrar nodo WBS..."
                        className="w-full pl-7 pr-2.5 py-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none focus:border-[hsl(var(--primary))]"
                    />
                </div>
                <button
                    type="button"
                    data-testid="task-route-leaf-toggle"
                    onClick={() => setOnlyLeafPackages((prev) => !prev)}
                    className={clsx(
                        'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-2xs font-bold uppercase tracking-wider transition-all border',
                        onlyLeafPackages
                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:text-[hsl(var(--foreground))]'
                    )}
                >
                    <Layers size={11} />
                    Solo Paquetes Hoja (WP)
                </button>
            </div>

            {/* Legend */}
            <div className="px-4 py-2 border-b border-[hsl(var(--border))]">
                <div className="flex flex-wrap gap-2">
                    {(Object.entries(TYPE_COLOR) as [RouteNode['type'], string][]).map(([type, color]) => {
                        const Icon = TYPE_ICON[type];
                        return (
                            <span key={type} className={clsx('flex items-center gap-1 text-2xs font-medium', color)}>
                                <Icon size={10} />
                                <span className="text-[hsl(var(--muted-foreground))] capitalize">{type}</span>
                            </span>
                        );
                    })}
                </div>
            </div>

            {/* Tree */}
            <div className="flex-1 overflow-y-auto py-2 px-2">
                {filteredTree.length === 0 ? (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] text-center py-2">
                        No hay datos de ruta disponibles.
                    </p>
                ) : (
                    filteredTree.map(node => (
                        <TreeNode
                            key={node.id}
                            node={node}
                            depth={0}
                            activeId={activeId}
                            forceExpand={isFiltering}
                            onNavigate={onNavigate}
                        />
                    ))
                )}
            </div>
        </div>
    );
}

"use client";

import { useState, ElementType } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronRight, ChevronDown, FolderOpen,
    Target, FileText, CheckSquare, Home, ArrowRight
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

// ─────────────────────────────────────────────────────────────────
// RECURSIVE TREE NODE
// ─────────────────────────────────────────────────────────────────
function TreeNode({
    node,
    depth = 0,
    activeId,
    onNavigate,
}: {
    node: RouteNode;
    depth?: number;
    activeId?: string;
    onNavigate?: (n: RouteNode) => void;
}) {
    const [open, setOpen] = useState(node.active || node.children?.some(c => c.active || c.id === activeId) || false);
    const hasChildren = (node.children?.length ?? 0) > 0;
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
                        ? 'bg-info-soft dark:bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]'
                        : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]',
                )}
                style={{ paddingLeft: depth * 16 + 8 }}
            >
                {/* Guide line */}
                {depth > 0 && (
                    <div
                        className="absolute top-0 bottom-0 w-px bg-[hsl(var(--surface-3))]/60 dark:bg-white/[0.06]"
                        style={{ left: depth * 16 - 4 }}
                    />
                )}

                {/* Expand arrow */}
                <span className={clsx('shrink-0 transition-transform', !hasChildren && 'opacity-0 pointer-events-none')}>
                    {open
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
                    'flex-1 text-[12px] truncate',
                    isActive ? 'font-bold' : 'font-medium'
                )}>
                    {node.label}
                </span>

                {/* Active indicator */}
                {isActive && (
                    <span className="font-semibold px-1.5 py-0.5 bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded">
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
                {open && hasChildren && (
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
    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.06]">
                <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Ruta de la tarea</p>

                {/* Breadcrumb path */}
                <div className="flex flex-col gap-1">
                    {breadcrumb.map((crumb, i) => {
                        const CrumbIcon = TYPE_ICON[crumb.type] ?? FileText;
                        const isLast = i === breadcrumb.length - 1;
                        return (
                            <div key={i} className="flex items-center gap-2" style={{ paddingLeft: i * 12 }}>
                                {/* Connector line */}
                                {i > 0 && (
                                    <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/[0.08] shrink-0 -ml-px" />
                                )}
                                <div className={clsx(
                                    'flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px]',
                                    isLast
                                        ? 'font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/10'
                                        : 'font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                                )}>
                                    <CrumbIcon size={11} className={TYPE_COLOR[crumb.type]} />
                                    {crumb.label}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Legend */}
            <div className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
                <div className="flex flex-wrap gap-2">
                    {(Object.entries(TYPE_COLOR) as [RouteNode['type'], string][]).map(([type, color]) => {
                        const Icon = TYPE_ICON[type];
                        return (
                            <span key={type} className={clsx('flex items-center gap-1 text-[10px] font-medium', color)}>
                                <Icon size={10} />
                                <span className="text-[hsl(var(--text-secondary))] capitalize">{type}</span>
                            </span>
                        );
                    })}
                </div>
            </div>

            {/* Tree */}
            <div className="flex-1 overflow-y-auto py-2 px-2">
                {tree.length === 0 ? (
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] text-center py-2">
                        No hay datos de ruta disponibles.
                    </p>
                ) : (
                    tree.map(node => (
                        <TreeNode
                            key={node.id}
                            node={node}
                            depth={0}
                            activeId={activeId}
                            onNavigate={onNavigate}
                        />
                    ))
                )}
            </div>
        </div>
    );
}

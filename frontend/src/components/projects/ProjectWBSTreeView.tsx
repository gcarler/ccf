"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectWBSTreeResponse, WBSNode } from '@/types/projects';
import {
    Activity,
    AlertCircle,
    ChevronDown,
    ChevronRight,
    Clock,
    DollarSign,
    Folder,
    FolderOpen,
    Layers,
    ListTree,
    Maximize2,
    Minimize2,
    RefreshCw,
    Search,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

interface ProjectWBSTreeViewProps {
    projectId: string;
    projectTitle?: string;
    onSelectNode?: (node: WBSNode) => void;
}

export function ProjectWBSTreeView({
    projectId,
    projectTitle: _projectTitle = 'Proyecto',
    onSelectNode,
}: ProjectWBSTreeViewProps) {
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [treeData, setTreeData] = useState<ProjectWBSTreeResponse | null>(null);
    const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
    const [searchTerm, setSearchTerm] = useState('');
    const [typeFilter, setTypeFilter] = useState<'all' | 'component' | 'task'>('all');

    const loadTree = useCallback(async () => {
        if (!projectId || !token) return;
        setLoading(true);
        setError(null);
        try {
            const res = await apiFetch<ProjectWBSTreeResponse>(
                `/projects/${projectId}/wbs-tree`,
                { token }
            );
            setTreeData(res);

            // Auto-expandir raíz y componentes inicialmente
            const initialMap: Record<string, boolean> = { [res.root.id]: true };
            if (res.root.children) {
                res.root.children.forEach(c => {
                    initialMap[c.id] = true;
                });
            }
            setExpandedMap(initialMap);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al cargar Organigrama WBS';
            setError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, [projectId, token]);

    useEffect(() => {
        void loadTree();
    }, [loadTree]);

    const toggleExpand = (id: string) => {
        setExpandedMap(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const expandAll = () => {
        if (!treeData) return;
        const newMap: Record<string, boolean> = {};
        const traverse = (node: WBSNode) => {
            newMap[node.id] = true;
            if (node.children) node.children.forEach(traverse);
        };
        traverse(treeData.root);
        setExpandedMap(newMap);
    };

    const collapseAll = () => {
        setExpandedMap({});
    };

    // Render recursivo de un nodo del árbol
    const renderNode = (node: WBSNode, depth = 0) => {
        const isExpanded = !!expandedMap[node.id];
        const hasChildren = node.children && node.children.length > 0;

        // Filtro de búsqueda y tipo
        const termLower = searchTerm.toLowerCase();
        const matchesSearch =
            !searchTerm ||
            node.title.toLowerCase().includes(termLower) ||
            node.wbs_code.includes(termLower);

        const matchesType = typeFilter === 'all' || node.type === typeFilter || depth === 0;

        // Si los hijos coinciden con la búsqueda, debemos mostrar este nodo
        const hasMatchingChild = (n: WBSNode): boolean => {
            if (!searchTerm) return true;
            if (n.title.toLowerCase().includes(termLower) || n.wbs_code.includes(termLower)) return true;
            return n.children?.some(hasMatchingChild) ?? false;
        };

        const shouldRender = (matchesSearch || hasMatchingChild(node)) && matchesType;
        if (!shouldRender) return null;

        return (
            <div key={node.id} className="space-y-1" data-testid={`wbs-node-${node.wbs_code}`}>
                <div
                    onClick={() => {
                        if (hasChildren) toggleExpand(node.id);
                        if (onSelectNode) onSelectNode(node);
                    }}
                    style={{ paddingLeft: `${Math.max(depth * 18, 8)}px` }}
                    className={clsx(
                        "group flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-all",
                        "hover:bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary)/0.35)]",
                        depth === 0 && "bg-[hsl(var(--surface-2)/0.6)] border-[hsl(var(--border))] font-bold",
                        depth === 1 && "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]",
                        depth >= 2 && "bg-[hsl(var(--surface-1)/0.7)] border-[hsl(var(--border)/0.6)]"
                    )}
                >
                    <div className="flex items-center gap-2 min-w-0">
                        {/* Botón de colapso/expansión */}
                        {hasChildren ? (
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    toggleExpand(node.id);
                                }}
                                className="p-0.5 rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            >
                                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </button>
                        ) : (
                            <span className="w-3.5 inline-block" />
                        )}

                        {/* Badge de Código WBS */}
                        <span
                            className={clsx(
                                "px-1.5 py-0.5 rounded font-mono font-bold text-[10px] shrink-0 border",
                                node.type === 'project' && "bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.3)]",
                                node.type === 'component' && "bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] border-[hsl(var(--border))]",
                                node.type === 'task' && "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]"
                            )}
                        >
                            {node.wbs_code}
                        </span>

                        {/* Ícono de tipo */}
                        {node.type === 'project' && <Layers size={14} className="text-[hsl(var(--primary))] shrink-0" />}
                        {node.type === 'component' && (
                            isExpanded ? (
                                <FolderOpen size={14} className="text-[hsl(var(--primary))] shrink-0" />
                            ) : (
                                <Folder size={14} className="text-[hsl(var(--muted-foreground))] shrink-0" />
                            )
                        )}
                        {node.type === 'task' && <Activity size={13} className="text-[hsl(var(--muted-foreground))] shrink-0" />}

                        {/* Título del nodo */}
                        <span className="truncate font-semibold text-[hsl(var(--foreground))]">
                            {node.title}
                        </span>
                    </div>

                    {/* Métricas del nodo */}
                    <div className="flex items-center gap-3 shrink-0 text-[11px]">
                        {/* Horas estimadas y reales */}
                        {(node.estimated_hours > 0 || node.actual_hours > 0) && (
                            <div className="hidden sm:flex items-center gap-1 font-mono text-[hsl(var(--muted-foreground))]">
                                <Clock size={12} />
                                <span>{node.actual_hours}h / {node.estimated_hours}h</span>
                            </div>
                        )}

                        {/* Costo imputado */}
                        {node.cost > 0 && (
                            <div className="hidden md:flex items-center gap-1 font-mono font-medium text-[hsl(var(--muted-foreground))]">
                                <DollarSign size={12} />
                                <span>${node.cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                            </div>
                        )}

                        {/* Barra de progreso continuo */}
                        <div className="flex items-center gap-1.5 w-24">
                            <div className="h-1.5 flex-1 rounded-full bg-[hsl(var(--surface-2))] overflow-hidden border border-[hsl(var(--border))]">
                                <div
                                    className={clsx(
                                        "h-full rounded-full transition-all duration-300",
                                        node.progress_pct >= 100
                                            ? "bg-[hsl(var(--success))]"
                                            : node.progress_pct > 0
                                            ? "bg-[hsl(var(--primary))]"
                                            : "bg-transparent"
                                    )}
                                    style={{ width: `${Math.min(100, node.progress_pct)}%` }}
                                />
                            </div>
                            <span className="font-mono font-bold text-[10px] w-9 text-right text-[hsl(var(--foreground))]">
                                {node.progress_pct.toFixed(0)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Hijos colapsables */}
                {hasChildren && isExpanded && (
                    <div className="space-y-1">
                        {node.children.map(child => renderNode(child, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-4" data-testid="project-wbs-tree-view">
            {/* Cabecera y controles */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-3">
                <div className="flex items-center gap-2">
                    <ListTree size={18} className="text-[hsl(var(--primary))]" />
                    <div>
                        <h3 className="text-sm font-bold tracking-tight text-[hsl(var(--foreground))]">
                            Organigrama y Estructura de Desglose del Trabajo (EDT / WBS)
                        </h3>
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                            Codificación jerárquica recursiva estándar PMI (1.1, 1.1.1...)
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={expandAll}
                        className="px-2 py-1 text-xs font-semibold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] inline-flex items-center gap-1 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                        title="Expandir todo"
                    >
                        <Maximize2 size={12} />
                        Expandir
                    </button>
                    <button
                        type="button"
                        onClick={collapseAll}
                        className="px-2 py-1 text-xs font-semibold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] inline-flex items-center gap-1 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                        title="Colapsar todo"
                    >
                        <Minimize2 size={12} />
                        Colapsar
                    </button>
                    <button
                        type="button"
                        onClick={() => void loadTree()}
                        disabled={loading}
                        className="p-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                        title="Actualizar"
                    >
                        <RefreshCw size={13} className={clsx(loading && 'animate-spin')} />
                    </button>
                </div>
            </div>

            {/* Barra de búsqueda y filtros */}
            <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1 min-w-[180px]">
                    <Search size={14} className="absolute left-2.5 top-2.5 text-[hsl(var(--muted-foreground))]" />
                    <input
                        type="text"
                        placeholder="Buscar por código (ej: 1.1) o título..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-hidden focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                </div>

                <div className="flex rounded-lg p-0.5 border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs">
                    {(['all', 'component', 'task'] as const).map(type => (
                        <button
                            key={type}
                            type="button"
                            onClick={() => setTypeFilter(type)}
                            className={clsx(
                                "px-2 py-1 font-semibold rounded-md transition-all",
                                typeFilter === type
                                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] shadow-xs"
                                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            )}
                        >
                            {type === 'all' && 'Todos'}
                            {type === 'component' && 'Componentes'}
                            {type === 'task' && 'Tareas'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Estados de carga o error */}
            {loading && !treeData && (
                <div className="space-y-2 animate-pulse py-4">
                    <div className="h-10 rounded-lg bg-[hsl(var(--surface-2))]" />
                    <div className="h-10 rounded-lg bg-[hsl(var(--surface-2))] ml-6" />
                    <div className="h-10 rounded-lg bg-[hsl(var(--surface-2))] ml-12" />
                </div>
            )}

            {error && !treeData && (
                <div className="p-4 rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] text-center space-y-2">
                    <AlertCircle className="mx-auto text-[hsl(var(--destructive))]" size={20} />
                    <p className="text-xs font-semibold text-[hsl(var(--destructive))]">{error}</p>
                </div>
            )}

            {/* Árbol renderizado */}
            {treeData && (
                <div className="space-y-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-[hsl(var(--muted-foreground))] px-2 pb-1 border-b border-[hsl(var(--border)/0.5)]">
                        <span>Total Nodos: {treeData.total_nodes} • Profundidad: {treeData.max_depth}</span>
                        <span>Avance Físico Continuo</span>
                    </div>

                    <div className="space-y-1 pt-1 max-h-[500px] overflow-y-auto">
                        {renderNode(treeData.root, 0)}
                    </div>
                </div>
            )}
        </div>
    );
}

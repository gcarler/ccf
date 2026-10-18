"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import RightPanel from '@/components/ui/RightPanel';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectWBSTreeResponse, WBSNode } from '@/types/projects';
import clsx from 'clsx';
import { toast } from 'sonner';
import { AlertCircle, BookOpen, CheckCircle2, CircleHelp, ListTree, Search } from 'lucide-react';

interface ProjectWBSDrawerProps {
    projectId: string;
    projectTitle?: string;
    isOpen: boolean;
    onClose: () => void;
    onSelectNode?: (node: WBSNode) => void;
}

interface CodedWBSNode {
    node: WBSNode;
    code: string;
    depth: number;
    localWeight: number;
    technicalWeight: number;
    children: CodedWBSNode[];
}

type TreeFilter = 'all' | 'leaves';

const amountForWeight = (node: WBSNode, parent: CodedWBSNode | null): number => {
    if (parent === null || parent.node.type === 'project') {
        return Math.max(0, node.budget_allocated ?? 0);
    }
    return Math.max(0, node.estimated_hours ?? 0);
};

function codeTree(node: WBSNode, code: string, depth: number): CodedWBSNode {
    const children = (node.children ?? []).map((child, index) =>
        codeTree(child, depth === 0 ? `1.${index + 1}` : `${code}.${index + 1}`, depth + 1)
    );
    return { node, code, depth, localWeight: 0, technicalWeight: 0, children };
}

function assignWeights(branch: CodedWBSNode, parent: CodedWBSNode | null = null): void {
    if (parent === null) {
        branch.localWeight = 100;
        branch.technicalWeight = 100;
    } else {
        const siblings = parent.children;
        const total = siblings.reduce((sum, sibling) => sum + amountForWeight(sibling.node, parent), 0);
        const own = amountForWeight(branch.node, parent);
        branch.localWeight = total > 0 ? (own / total) * 100 : 0;
        branch.technicalWeight = parent.technicalWeight * branch.localWeight / 100;
    }
    branch.children.forEach(child => assignWeights(child, branch));
}

function flattenTree(branch: CodedWBSNode): CodedWBSNode[] {
    return [branch, ...branch.children.flatMap(flattenTree)];
}

function nodeKind(branch: CodedWBSNode): string {
    if (branch.node.type === 'project') return 'Proyecto';
    if (branch.node.type === 'component') return 'Cuenta de Control';
    if (branch.children.length > 0) return 'Paquete de Planificación';
    return 'Paquete de Trabajo Hoja';
}

function isWorkPackageLeaf(branch: CodedWBSNode): boolean {
    return branch.node.type === 'task' && branch.children.length === 0;
}

function formatMoney(value: number | null | undefined): string {
    if (value === null || value === undefined) return 'No asignado';
    return `$${value.toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;
}

export function ProjectWBSDrawer({
    projectId,
    projectTitle = 'Proyecto',
    isOpen,
    onClose,
    onSelectNode,
}: ProjectWBSDrawerProps) {
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [treeData, setTreeData] = useState<ProjectWBSTreeResponse | null>(null);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState<TreeFilter>('all');
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const loadTree = useCallback(async () => {
        if (!projectId || !token) return;
        setLoading(true);
        setError(null);
        try {
            const response = await apiFetch<ProjectWBSTreeResponse>(`/projects/${projectId}/wbs-tree`, { token });
            setTreeData(response);
        } catch (loadError: unknown) {
            const message = loadError instanceof Error ? loadError.message : 'No se pudo cargar la EDT';
            setError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [projectId, token]);

    useEffect(() => {
        if (isOpen) void loadTree();
    }, [isOpen, loadTree]);

    const codedRoot = useMemo(() => {
        if (!treeData) return null;
        const root = codeTree(treeData.root, '1.0', 0);
        assignWeights(root);
        return root;
    }, [treeData]);
    const allNodes = useMemo(() => codedRoot ? flattenTree(codedRoot) : [], [codedRoot]);
    const selected = allNodes.find(branch => branch.node.id === selectedId) ?? allNodes.find(branch => branch.node.type !== 'project') ?? codedRoot;

    const componentWeights = codedRoot?.children ?? [];
    const componentWeightSum = componentWeights.reduce((sum, branch) => sum + branch.technicalWeight, 0);
    const componentBudgets = componentWeights.reduce((sum, branch) => sum + (branch.node.budget_allocated ?? 0), 0);
    const projectBudget = codedRoot?.node.budget_allocated ?? null;
    const budgetDifference = projectBudget === null ? null : componentBudgets - projectBudget;
    const budgetBalanced = budgetDifference !== null && Math.abs(budgetDifference) <= 0.01;
    const lowerLevelRules = componentWeights.map(branch => {
        const taskBranches = branch.children;
        const activityWeight = taskBranches.reduce((sum, task) => sum + task.localWeight, 0);
        const hasHours = taskBranches.some(task => task.node.estimated_hours > 0);
        return { branch, activityWeight, valid: taskBranches.length > 0 && hasHours && Math.abs(activityWeight - 100) <= 0.01 };
    });

    const searchText = search.trim().toLocaleLowerCase();
    const hasVisibleMatch = (branch: CodedWBSNode): boolean => {
        const ownMatches = !searchText || `${branch.code} ${branch.node.title}`.toLocaleLowerCase().includes(searchText);
        const leafMatches = filter === 'all' || isWorkPackageLeaf(branch);
        return (ownMatches && leafMatches) || branch.children.some(hasVisibleMatch);
    };

    const renderBranch = (branch: CodedWBSNode): React.ReactNode => {
        if (!hasVisibleMatch(branch)) return null;
        const matchesSearch = !searchText || `${branch.code} ${branch.node.title}`.toLocaleLowerCase().includes(searchText);
        const isLeafFilter = filter === 'leaves';
        const showSelf = matchesSearch && (!isLeafFilter || isWorkPackageLeaf(branch));
        return (
            <React.Fragment key={branch.node.id}>
                {showSelf && (
                    <button
                        type="button"
                        data-testid={`wbs-node-${branch.code}`}
                        onClick={() => {
                            setSelectedId(branch.node.id);
                            onSelectNode?.(branch.node);
                        }}
                        className={clsx(
                            'flex w-full items-center justify-between gap-3 rounded-lg border p-2.5 text-left transition-colors',
                            selected?.node.id === branch.node.id
                                ? 'border-[hsl(var(--primary)/0.5)] bg-[hsl(var(--surface-2))]'
                                : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))]'
                        )}
                        style={{ marginLeft: `${branch.depth * 14}px`, width: `calc(100% - ${branch.depth * 14}px)` }}
                    >
                        <span className="flex min-w-0 items-center gap-2">
                            <span className="shrink-0 rounded border border-[hsl(var(--border))] px-1.5 py-0.5 font-mono text-[10px] font-bold text-[hsl(var(--primary))]">{branch.code}</span>
                            <span className="truncate text-xs font-semibold text-[hsl(var(--text-primary))]">{branch.node.title}</span>
                        </span>
                        <span className="shrink-0 text-[10px] text-[hsl(var(--text-secondary))]">{nodeKind(branch)}</span>
                    </button>
                )}
                {branch.children.map(renderBranch)}
            </React.Fragment>
        );
    };

    return (
        <RightPanel
            isOpen={isOpen}
            onClose={onClose}
            title={<div className="flex items-center gap-2"><ListTree className="text-[hsl(var(--primary))]" size={18} /><span className="font-bold text-sm uppercase tracking-tight">EDT / WBS y Diccionario</span></div>}
            subtitle={<span className="text-xs text-[hsl(var(--text-secondary))]">Jerarquía PMI, Regla del 100% y Cuentas de Control • {projectTitle}</span>}
            width="w-full sm:max-w-4xl xl:max-w-6xl"
        >
            <div className="space-y-4 p-4 sm:p-6" data-testid="project-wbs-drawer">
                {loading && !treeData && <div role="status" className="space-y-2 animate-pulse"><div className="h-10 rounded-lg bg-[hsl(var(--surface-2))]" /><div className="h-10 rounded-lg bg-[hsl(var(--surface-2))]" /><div className="h-24 rounded-lg bg-[hsl(var(--surface-2))]" /></div>}
                {error && !treeData && <div role="alert" className="flex items-center gap-2 rounded-lg border border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.08)] p-3 text-sm text-[hsl(var(--destructive))]"><AlertCircle size={17} />{error}</div>}
                {treeData && codedRoot && (
                    <>
                        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
                            <section className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3" aria-label="Árbol WBS">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <h3 className="flex items-center gap-2 text-sm font-bold text-[hsl(var(--text-primary))]"><ListTree size={16} />Estructura jerárquica</h3>
                                    <label className="flex min-w-[180px] flex-1 items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 lg:max-w-xs">
                                        <Search size={14} className="text-[hsl(var(--text-secondary))]" />
                                        <input aria-label="Buscar por código WBS o nombre" value={search} onChange={event => setSearch(event.target.value)} placeholder="Código WBS o nombre" className="w-full bg-transparent text-xs text-[hsl(var(--text-primary))] outline-none placeholder:text-[hsl(var(--text-secondary))]" />
                                    </label>
                                </div>
                                <div className="flex gap-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-1 text-xs">
                                    <button type="button" onClick={() => setFilter('all')} aria-pressed={filter === 'all'} className={clsx('rounded-md px-2 py-1 font-semibold', filter === 'all' ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]' : 'text-[hsl(var(--text-secondary))]')}>Árbol Completo</button>
                                    <button type="button" onClick={() => setFilter('leaves')} aria-pressed={filter === 'leaves'} className={clsx('rounded-md px-2 py-1 font-semibold', filter === 'leaves' ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]' : 'text-[hsl(var(--text-secondary))]')}>Solo Paquetes de Trabajo Hoja</button>
                                </div>
                                <div className="max-h-[420px] space-y-1 overflow-y-auto" data-testid="wbs-tree">
                                    {renderBranch(codedRoot)}
                                    {!allNodes.some(branch => hasVisibleMatch(branch)) && <p className="p-4 text-center text-xs text-[hsl(var(--text-secondary))]">No hay nodos que coincidan con el filtro.</p>}
                                </div>
                            </section>

                            <section className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4" aria-label="Diccionario de la EDT">
                                <h3 className="flex items-center gap-2 text-sm font-bold text-[hsl(var(--text-primary))]"><BookOpen size={16} />Diccionario de la EDT</h3>
                                {selected ? (
                                    <div className="space-y-3 text-xs" data-testid="wbs-dictionary-entry">
                                        <div><p className="text-[hsl(var(--text-secondary))]">Entregable</p><p className="font-semibold text-[hsl(var(--text-primary))]">{selected.node.title}</p></div>
                                        <dl className="grid grid-cols-2 gap-x-3 gap-y-2">
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Código WBS</dt><dd className="font-mono font-bold">{selected.code}</dd></div>
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Tipo de nodo</dt><dd>{nodeKind(selected)}</dd></div>
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Peso técnico</dt><dd>{selected.technicalWeight.toFixed(1)}%</dd></div>
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Presupuesto asignado</dt><dd>{formatMoney(selected.node.budget_allocated)}</dd></div>
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Avance físico ponderado</dt><dd>{((selected.node.progress_pct * selected.technicalWeight) / 100).toFixed(1)}%</dd></div>
                                            <div><dt className="text-[hsl(var(--text-secondary))]">Horas estimadas / reales</dt><dd>{selected.node.estimated_hours.toFixed(1)}h / {selected.node.actual_hours.toFixed(1)}h</dd></div>
                                        </dl>
                                        <div><p className="text-[hsl(var(--text-secondary))]">Descripción del trabajo</p><p>{selected.node.description?.trim() || 'Sin descripción registrada.'}</p></div>
                                        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
                                            <p className="flex items-center gap-1 font-semibold text-[hsl(var(--text-primary))]"><CircleHelp size={13} />Criterio de aceptación</p>
                                            <p className="mt-1 text-[hsl(var(--text-secondary))]">No registrado en el modelo actual.</p>
                                        </div>
                                    </div>
                                ) : <p className="text-xs text-[hsl(var(--text-secondary))]">Selecciona un nodo para inspeccionar su ficha.</p>}
                            </section>
                        </div>

                        <section className="space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4" aria-label="Validación de la Regla del 100%">
                            <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">Validador en vivo • Regla del 100%</h3>
                            <div className="grid gap-2 md:grid-cols-2">
                                <ValidationResult label="Peso técnico de componentes" value={`${componentWeightSum.toFixed(1)}%`} valid={componentWeights.length > 0 && componentWeightSum >= 99.99 && componentWeightSum <= 100.01} />
                                <ValidationResult label="Presupuesto de componentes vs BAC del proyecto" value={`${formatMoney(componentBudgets)} / ${formatMoney(projectBudget)}`} valid={budgetBalanced} detail={budgetDifference === null ? 'BAC del proyecto no disponible' : `Diferencia: ${formatMoney(budgetDifference)}`} />
                                {lowerLevelRules.map(({ branch, activityWeight, valid }) => <ValidationResult key={branch.node.id} label={`Peso de actividades • ${branch.code} ${branch.node.title}`} value={`${activityWeight.toFixed(1)}%`} valid={valid} />)}
                            </div>
                        </section>
                    </>
                )}
                {!loading && !error && !treeData && <p className="rounded-lg border border-[hsl(var(--border))] p-4 text-center text-sm text-[hsl(var(--text-secondary))]">No hay estructura WBS disponible.</p>}
            </div>
        </RightPanel>
    );
}

function ValidationResult({ label, value, valid, detail }: { label: string; value: string; valid: boolean; detail?: string }) {
    return (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
            <div><p className="text-xs font-semibold text-[hsl(var(--text-primary))]">{label}</p><p className="text-xs text-[hsl(var(--text-secondary))]">{value}{detail ? ` • ${detail}` : ''}</p></div>
            <span className={clsx('flex shrink-0 items-center gap-1 text-[10px] font-bold', valid ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--destructive))]')}>
                <CheckCircle2 size={13} />{valid ? 'Cumple' : 'Revisar'}
            </span>
        </div>
    );
}

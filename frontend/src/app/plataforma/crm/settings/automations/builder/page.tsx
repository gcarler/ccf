"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    Connection,
    Edge,
    Node,
    Panel,
    MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
    Zap, Plus, Trash2, Save, ArrowLeft,
    Clock, Settings, AlertTriangle, Play,
    MessageSquare, CheckSquare, Send, Bell, Heart, GitBranch
} from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import Skeleton from '@/components/ui/Skeleton';

// ─── Constants ───────────────────────────────────────────
const TRIGGERS = [
    { value: 'new_persona', label: 'Nuevo Persona' },
    { value: 'birthday', label: 'Cumpleaños' },
    { value: 'inactivity', label: 'Inactividad (30 días)' },
    { value: 'low_attendance', label: 'Baja Asistencia' },
    { value: 'anniversary', label: 'Aniversario Espiritual' },
    { value: 'stage_change', label: 'Cambio de Etapa Pipeline' },
];

const ACTIONS = [
    { value: 'send_whatsapp', label: 'Enviar WhatsApp' },
    { value: 'send_sms', label: 'Enviar SMS' },
    { value: 'create_task', label: 'Crear Tarea de Consolidación' },
    { value: 'send_email', label: 'Enviar Email' },
];

const CONDITION_TYPES = [
    { value: 'always', label: 'Siempre (Siempre Verdadero)' },
    { value: 'equals', label: 'Igual a (==)' },
    { value: 'ne', label: 'Diferente de (!=)' },
    { value: 'contains', label: 'Contiene' },
    { value: 'starts_with', label: 'Comienza con' },
    { value: 'in', label: 'En (lista separada por comas)' },
    { value: 'gt', label: 'Mayor que (>)' },
    { value: 'lt', label: 'Menor que (<)' },
];

interface AutomationData {
    id?: string;
    name: string;
    trigger_event: string;
    action_type: string;
    action_payload: any;
    delay_minutes: number;
    is_active: boolean;
    ui_graph_state?: any;
}

interface EdgeData {
    condition_type?: string;
    condition_key?: string | null;
    condition_value?: string | null;
    [key: string]: any;
}

type CustomNode = Node<{
    label: string;
    automation: AutomationData;
}>;

type CustomEdge = Edge<EdgeData>;

export default function AutomationBuilderPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [nodes, setNodes, onNodesChange] = useNodesState<CustomNode>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<CustomEdge>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Sidebar state
    const [selectedNode, setSelectedNode] = useState<CustomNode | null>(null);
    const [selectedEdge, setSelectedEdge] = useState<CustomEdge | null>(null);

    // Raw loaded data to track deletions
    const [originalEdges, setOriginalEdges] = useState<any[]>([]);

    // Fetch automations and edges
    const loadGraphData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const automations = await apiFetch<any[]>('/api/crm/resources/automations', { token });
            const serverEdges = await apiFetch<any[]>('/api/crm/resources/automations/edges', { token });

            setOriginalEdges(serverEdges);

            // Convert automations to React Flow Nodes
            const rfNodes: CustomNode[] = automations.map((aut, idx) => {
                const uiPos = aut.ui_graph_state?.position || { x: 100 + (idx * 250), y: 150 };
                return {
                    id: aut.id,
                    type: 'default',
                    position: uiPos,
                    data: {
                        label: aut.name,
                        automation: aut
                    },
                    style: {
                        background: aut.is_active ? 'var(--card-bg, #ffffff)' : '#f3f4f6',
                        color: 'var(--text-primary, #111827)',
                        border: '2px solid ' + (aut.is_active ? '#3b82f6' : '#d1d5db'),
                        borderRadius: '8px',
                        padding: '12px',
                        width: 200,
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                    }
                };
            });

            // Convert server edges to React Flow Edges
            const rfEdges: CustomEdge[] = serverEdges.map(e => ({
                id: e.id,
                source: e.source_id,
                target: e.target_id,
                label: e.condition_type !== 'always' && e.condition_type ? `${e.condition_key} ${e.condition_type}` : 'Siempre',
                data: e,
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: '#3b82f6'
                },
                style: {
                    stroke: '#3b82f6',
                    strokeWidth: 2
                }
            }));

            setNodes(rfNodes);
            setEdges(rfEdges);
        } catch (err) {
            console.error(err);
            addToast('Error al cargar el flujo de automatizaciones', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast, setNodes, setEdges]);

    useEffect(() => {
        loadGraphData();
    }, [loadGraphData]);

    // Handle flow connections
    const onConnect = useCallback((connection: Connection) => {
        const newEdge: CustomEdge = {
            id: `temp_${Date.now()}`,
            source: connection.source!,
            target: connection.target!,
            label: 'Siempre',
            data: {
                condition_type: 'always',
                condition_key: '',
                condition_value: ''
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#3b82f6'
            },
            style: {
                stroke: '#3b82f6',
                strokeWidth: 2
            }
        };
        setEdges(eds => addEdge(newEdge, eds));
    }, [setEdges]);

    // Handle selection changes
    const onSelectionChange = useCallback(({ nodes: selectedNodes, edges: selectedEdges }: any) => {
        if (selectedNodes.length > 0) {
            setSelectedNode(selectedNodes[0]);
            setSelectedEdge(null);
        } else if (selectedEdges.length > 0) {
            setSelectedEdge(selectedEdges[0]);
            setSelectedNode(null);
        } else {
            setSelectedNode(null);
            setSelectedEdge(null);
        }
    }, []);

    // Create a new automation node
    const handleAddNode = async () => {
        if (!token) return;
        try {
            const defaultPayload = {
                name: `Nueva Automatización ${nodes.length + 1}`,
                trigger_event: 'new_persona',
                action_type: 'send_whatsapp',
                action_payload: { message: 'Hola, bienvenido!' },
                delay_minutes: 0,
                is_active: true,
                ui_graph_state: { position: { x: 150, y: 150 } }
            };

            const created = await apiFetch<any>('/api/crm/resources/automations', {
                method: 'POST',
                token,
                body: defaultPayload
            });

            const newNode: CustomNode = {
                id: created.id,
                type: 'default',
                position: defaultPayload.ui_graph_state.position,
                data: {
                    label: created.name,
                    automation: created
                },
                style: {
                    background: '#ffffff',
                    color: '#111827',
                    border: '2px solid #3b82f6',
                    borderRadius: '8px',
                    padding: '12px',
                    width: 200,
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                }
            };

            setNodes(nds => [...nds, newNode]);
            setSelectedNode(newNode);
            addToast('Nodo de automatización creado', 'success');
        } catch {
            addToast('Error al crear el nodo', 'error');
        }
    };

    // Update node details (local state)
    const handleUpdateNodeField = (field: string, value: any) => {
        if (!selectedNode) return;
        setNodes(nds => nds.map(node => {
            if (node.id === selectedNode.id) {
                const updatedAut = { ...node.data.automation, [field]: value };
                const updatedNode = {
                    ...node,
                    data: {
                        ...node.data,
                        label: field === 'name' ? value : node.data.label,
                        automation: updatedAut
                    }
                };
                setSelectedNode(updatedNode);
                return updatedNode;
            }
            return node;
        }));
    };

    // Update node action payload (local state)
    const handleUpdateNodePayload = (key: string, value: any) => {
        if (!selectedNode) return;
        const currentPayload = selectedNode.data.automation.action_payload || {};
        const newPayload = { ...currentPayload, [key]: value };
        handleUpdateNodeField('action_payload', newPayload);
    };

    // Delete node
    const handleDeleteNode = async () => {
        if (!selectedNode || !token) return;
        if (!confirm('¿Estás seguro de que deseas eliminar esta automatización? Esto eliminará también sus conexiones.')) return;

        try {
            await apiFetch(`/api/crm/resources/automations/${selectedNode.id}`, {
                method: 'DELETE',
                token
            });

            setNodes(nds => nds.filter(n => n.id !== selectedNode.id));
            setEdges(eds => eds.filter(e => e.source !== selectedNode.id && e.target !== selectedNode.id));
            setSelectedNode(null);
            addToast('Automatización eliminada', 'success');
        } catch {
            addToast('Error al eliminar la automatización', 'error');
        }
    };

    // Update edge details (local state)
    const handleUpdateEdgeField = (field: string, value: any) => {
        if (!selectedEdge) return;
        setEdges(eds => eds.map(e => {
            if (e.id === selectedEdge.id) {
                const updatedData = { ...e.data, [field]: value };
                let newLabel = 'Siempre';
                if (updatedData.condition_type !== 'always' && updatedData.condition_type) {
                    newLabel = `${updatedData.condition_key || 'var'} ${updatedData.condition_type}`;
                }
                const updatedEdge = {
                    ...e,
                    label: newLabel,
                    data: updatedData
                };
                setSelectedEdge(updatedEdge);
                return updatedEdge;
            }
            return e;
        }));
    };

    // Save entire graph
    const handleSaveGraph = async () => {
        if (!token) return;
        setSaving(true);
        try {
            // 1. Save positions & node updates
            for (const node of nodes) {
                const aut = node.data.automation;
                const body = {
                    name: aut.name,
                    trigger_event: aut.trigger_event,
                    action_type: aut.action_type,
                    action_payload: aut.action_payload,
                    delay_minutes: aut.delay_minutes,
                    is_active: aut.is_active,
                    ui_graph_state: {
                        position: node.position
                    }
                };
                await apiFetch(`/api/crm/resources/automations/${node.id}`, {
                    method: 'PATCH',
                    token,
                    body
                });
            }

            // 2. Identify edges to create/delete
            // Find edges deleted locally
            const localEdgeIds = new Set(edges.map(e => e.id));
            const deletedEdges = originalEdges.filter(oe => !localEdgeIds.has(oe.id));

            for (const de of deletedEdges) {
                await apiFetch(`/api/crm/resources/automations/edges/${de.id}`, {
                    method: 'DELETE',
                    token
                });
            }

            // Find new edges (have temp ids) or edited edges
            for (const edge of edges) {
                const isNew = edge.id.startsWith('temp_');
                const edgeBody = {
                    source_id: edge.source,
                    target_id: edge.target,
                    condition_type: edge.data?.condition_type || 'always',
                    condition_key: edge.data?.condition_key || null,
                    condition_value: edge.data?.condition_value || null,
                };

                if (isNew) {
                    await apiFetch('/api/crm/resources/automations/edges', {
                        method: 'POST',
                        token,
                        body: edgeBody
                    });
                } else {
                    // Update existing edge if changed
                    const orig = originalEdges.find(oe => oe.id === edge.id);
                    const hasChanged = orig && (
                        orig.condition_type !== edgeBody.condition_type ||
                        orig.condition_key !== edgeBody.condition_key ||
                        orig.condition_value !== edgeBody.condition_value
                    );
                    if (hasChanged) {
                        // Check if delete & recreate is needed or patch endpoint is supported.
                        // Let's delete and recreate to be robust.
                        await apiFetch(`/api/crm/resources/automations/edges/${edge.id}`, {
                            method: 'DELETE',
                            token
                        });
                        await apiFetch('/api/crm/resources/automations/edges', {
                            method: 'POST',
                            token,
                            body: edgeBody
                        });
                    }
                }
            }

            addToast('Flujo guardado con éxito', 'success');
            await loadGraphData();
        } catch (err) {
            console.error(err);
            addToast('Error al guardar el flujo', 'error');
        } finally {
            setSaving(false);
        }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Zap },
                { label: 'Automatizaciones', icon: Settings },
                { label: 'Constructor Visual', icon: GitBranch }
            ]}
            rightActions={
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => router.push('/plataforma/crm/messaging/automations')}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold uppercase hover:bg-slate-50 dark:hover:bg-white/5 transition-all text-slate-700 dark:text-slate-200"
                    >
                        <ArrowLeft size={12} /> Volver
                    </button>
                    <button
                        onClick={handleSaveGraph}
                        disabled={saving}
                        className="flex items-center gap-1.5 bg-blue-600 text-white px-4 py-1.5 rounded-md text-[11px] font-bold uppercase hover:bg-blue-700 shadow-lg shadow-blue-500/20 transition-all disabled:opacity-50"
                    >
                        {saving ? 'Guardando...' : <Save size={12} />}
                        Guardar Flujo
                    </button>
                </div>
            }
        >
            <div className="flex-1 flex overflow-hidden h-[calc(100vh-120px)]">
                {/* Visual Area */}
                <div className="flex-1 relative h-full bg-slate-50 dark:bg-slate-900">
                    {loading ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                            <Skeleton className="h-10 w-48 rounded-md" />
                            <div className="flex gap-4">
                                <Skeleton className="h-32 w-56 rounded-md" />
                                <Skeleton className="h-32 w-56 rounded-md" />
                            </div>
                        </div>
                    ) : (
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onSelectionChange={onSelectionChange}
                            fitView
                        >
                            <Background color="#ccc" gap={16} />
                            <Controls />
                            <MiniMap />
                            <Panel position="top-left">
                                <button
                                    onClick={handleAddNode}
                                    className="flex items-center gap-1 bg-white dark:bg-slate-800 text-slate-800 dark:text-white px-3 py-2 border border-slate-200 dark:border-white/10 rounded-md shadow text-xs font-bold uppercase tracking-wide hover:bg-slate-50 dark:hover:bg-slate-700 transition-all"
                                >
                                    <Plus size={14} /> Añadir Paso
                                </button>
                            </Panel>
                        </ReactFlow>
                    )}
                </div>

                {/* Right Properties Panel */}
                <div className="w-80 border-l border-slate-200 dark:border-white/10 bg-white dark:bg-slate-950 flex flex-col overflow-y-auto">
                    <div className="p-4 border-b border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50">
                        <h3 className="font-bold text-xs uppercase tracking-wider text-slate-500">Propiedades del Elemento</h3>
                    </div>

                    <div className="p-4 flex-1 space-y-4">
                        {selectedNode ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-slate-800 dark:text-white font-bold text-sm">
                                    <Settings size={16} className="text-blue-500" />
                                    <span>Configurar Paso</span>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Nombre del paso</label>
                                    <input
                                        type="text"
                                        value={selectedNode.data.automation.name}
                                        onChange={e => handleUpdateNodeField('name', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                    />
                                </div>

                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Disparador (Trigger)</label>
                                    <select
                                        value={selectedNode.data.automation.trigger_event}
                                        onChange={e => handleUpdateNodeField('trigger_event', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                    >
                                        {TRIGGERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                                    </select>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Acción a realizar</label>
                                    <select
                                        value={selectedNode.data.automation.action_type}
                                        onChange={e => handleUpdateNodeField('action_type', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                    >
                                        {ACTIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                                    </select>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1">
                                        <Clock size={12} />
                                        Retardo de ejecución (minutos)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={selectedNode.data.automation.delay_minutes || 0}
                                        onChange={e => handleUpdateNodeField('delay_minutes', parseInt(e.target.value) || 0)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                    />
                                </div>

                                {selectedNode.data.automation.action_type === 'create_task' ? (
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Título de Tarea Pastoral</label>
                                        <input
                                            type="text"
                                            value={selectedNode.data.automation.action_payload?.task_title || ''}
                                            onChange={e => handleUpdateNodePayload('task_title', e.target.value)}
                                            placeholder="Visitar al nuevo contacto"
                                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                        />
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Mensaje de Notificación</label>
                                        <textarea
                                            value={selectedNode.data.automation.action_payload?.message || ''}
                                            onChange={e => handleUpdateNodePayload('message', e.target.value)}
                                            placeholder="Hola {nombre}, ¡bienvenido a nuestra comunidad!"
                                            rows={4}
                                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold resize-none"
                                        />
                                    </div>
                                )}

                                <div className="flex items-center gap-3 pt-2">
                                    <label className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={selectedNode.data.automation.is_active}
                                            onChange={e => handleUpdateNodeField('is_active', e.target.checked)}
                                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 size-4"
                                        />
                                        Activo / En funcionamiento
                                    </label>
                                </div>

                                <div className="border-t border-slate-200 dark:border-white/10 pt-4 mt-4">
                                    <button
                                        onClick={handleDeleteNode}
                                        className="w-full flex items-center justify-center gap-2 py-2 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/20 text-rose-600 dark:text-rose-400 hover:bg-rose-100 rounded-md text-xs font-bold uppercase transition-all"
                                    >
                                        <Trash2 size={14} />
                                        Eliminar Paso
                                    </button>
                                </div>
                            </div>
                        ) : selectedEdge ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-slate-800 dark:text-white font-bold text-sm">
                                    <GitBranch size={16} className="text-blue-500" />
                                    <span>Configurar Conexión</span>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Tipo de Condición</label>
                                    <select
                                        value={selectedEdge.data?.condition_type || 'always'}
                                        onChange={e => handleUpdateEdgeField('condition_type', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                    >
                                        {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                                    </select>
                                </div>

                                {selectedEdge.data?.condition_type !== 'always' && (
                                    <>
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Variable / Campo a evaluar</label>
                                            <input
                                                type="text"
                                                value={selectedEdge.data?.condition_key || ''}
                                                onChange={e => handleUpdateEdgeField('condition_key', e.target.value)}
                                                placeholder="Ej: stage, delivery_status"
                                                className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Valor Esperado</label>
                                            <input
                                                type="text"
                                                value={selectedEdge.data?.condition_value || ''}
                                                onChange={e => handleUpdateEdgeField('condition_value', e.target.value)}
                                                placeholder="Ej: read, active"
                                                className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-900/50 outline-none text-xs text-slate-800 dark:text-white font-bold"
                                            />
                                        </div>
                                    </>
                                )}

                                <div className="border-t border-slate-200 dark:border-white/10 pt-4 mt-4">
                                    <button
                                        onClick={() => {
                                            setEdges(eds => eds.filter(e => e.id !== selectedEdge.id));
                                            setSelectedEdge(null);
                                            addToast('Conexión eliminada', 'info');
                                        }}
                                        className="w-full flex items-center justify-center gap-2 py-2 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/20 text-rose-600 dark:text-rose-400 hover:bg-rose-100 rounded-md text-xs font-bold uppercase transition-all"
                                    >
                                        <Trash2 size={14} />
                                        Eliminar Conexión
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center text-center text-slate-400 py-12 px-4">
                                <AlertTriangle size={32} className="mb-2 opacity-55 text-slate-400" />
                                <p className="text-xs font-bold">Ningún elemento seleccionado</p>
                                <p className="text-[11px] mt-1 text-slate-500">Selecciona un paso o una línea de conexión para editar sus configuraciones específicas.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

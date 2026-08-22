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
    Zap, Trash2, Save, ArrowLeft,
    Clock, Settings, AlertTriangle, GitBranch,
    CheckCircle2, PlayCircle, ShieldCheck,
    Sparkles
} from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { DSSkeleton } from '@/design';
import {
    automationNodeTypes,
    wouldCreateCycle,
    validateGraphDAG,
    validateFlowWithServer,
    AutomationNodeData
} from '@/components/automations';
import type { CrmAutomationEdgeRecord, CrmAutomationRecord } from '@/types/crm';

const AUTOMATION_EDGES_API = '/crm/resources/automation-edges';

// ─── Constants ───────────────────────────────────────────
const TRIGGERS = [
    { value: 'new_persona', label: 'Nuevo Persona (Registro)' },
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

const CONDITION_VARIABLES = [
    { value: 'nombre', label: 'Nombre del Contacto' },
    { value: 'email', label: 'Correo Electrónico' },
    { value: 'telefono', label: 'Teléfono' },
    { value: 'etapa_actual_id', label: 'Etapa Actual del Pipeline' },
    { value: 'sort_order', label: 'Orden de Clasificación' },
    { value: 'is_active', label: 'Contacto Activo' },
    { value: 'status', label: 'Estado Espiritual' },
];

type CustomNode = Node<AutomationNodeData>;

interface EdgeData {
    condition_type?: string;
    condition_key?: string | null;
    condition_value?: string | null;
    [key: string]: unknown;
}

type CustomEdge = Edge<EdgeData>;

function readPayloadText(payload: Record<string, unknown> | undefined, key: string): string {
    const value = payload?.[key];
    return typeof value === 'string' ? value : '';
}

export default function AutomationBuilderPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [nodes, setNodes, onNodesChange] = useNodesState<CustomNode>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<CustomEdge>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [validating, setValidating] = useState(false);
    const [dagStatus, setDagStatus] = useState<{ valid: boolean; message?: string } | null>(null);

    // Sidebar state
    const [selectedNode, setSelectedNode] = useState<CustomNode | null>(null);
    const [selectedEdge, setSelectedEdge] = useState<CustomEdge | null>(null);

    // Raw loaded data to track deletions
    const [originalEdges, setOriginalEdges] = useState<CrmAutomationEdgeRecord[]>([]);

    // Fetch automations and edges
    const loadGraphData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const automations = await apiFetch<CrmAutomationRecord[]>('/crm/resources/automations', { token });
            const serverEdges = await apiFetch<CrmAutomationEdgeRecord[]>(AUTOMATION_EDGES_API, { token });

            setOriginalEdges(serverEdges);

            // Convert automations to React Flow Nodes
            const rfNodes: CustomNode[] = automations.map((aut, idx) => {
                const uiPos = aut.ui_graph_state?.position || { x: 100 + (idx * 280), y: 150 };
                
                // Determine node type: trigger, condition, or action
                let nodeType: 'trigger' | 'condition' | 'action' = 'trigger';
                if (aut.trigger_event === 'condition' || aut.action_type === 'condition' || aut.name?.toLowerCase().includes('condición')) {
                    nodeType = 'condition';
                } else if (idx > 0 && aut.action_type) {
                    nodeType = 'action';
                }

                return {
                    id: aut.id,
                    type: nodeType,
                    position: uiPos,
                    data: {
                        label: aut.name,
                        nodeType,
                        automation: aut,
                        condition_config: {
                            field: typeof aut.action_payload?.condition_key === 'string' ? aut.action_payload.condition_key : 'etapa_actual_id',
                            operator: typeof aut.action_payload?.condition_type === 'string' ? aut.action_payload.condition_type : 'equals',
                            value: typeof aut.action_payload?.condition_value === 'string' ? aut.action_payload.condition_value : 'bautismo',
                        }
                    }
                };
            });

            // Convert server edges to React Flow Edges
            const rfEdges: CustomEdge[] = serverEdges.map(e => ({
                id: e.id,
                source: e.source_id,
                target: e.target_id,
                label: e.condition_type !== 'always' && e.condition_type ? `${e.condition_key || 'cond'} ${e.condition_type}` : 'Siempre',
                data: {
                    condition_type: e.condition_type ?? undefined,
                    condition_key: e.condition_key ?? undefined,
                    condition_value: e.condition_value ?? undefined,
                    source_node_id: e.source_node_id ?? undefined,
                    target_node_id: e.target_node_id ?? undefined,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: 'hsl(var(--primary))'
                },
                style: {
                    stroke: 'hsl(var(--primary))',
                    strokeWidth: 2
                }
            }));

            setNodes(rfNodes);
            setEdges(rfEdges);
        } catch (err) {
            addToast('Error al cargar el flujo de automatizaciones', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast, setNodes, setEdges]);

    useEffect(() => {
        loadGraphData();
    }, [loadGraphData]);

    // Handle flow connections with DAG Cycle Detection
    const onConnect = useCallback(async (connection: Connection) => {
        if (!connection.source || !connection.target) return;

        // 1. Client-Side DAG Cycle Detection
        const cycleCheck = wouldCreateCycle(connection.source, connection.target, edges);
        if (cycleCheck.hasCycle) {
            addToast(cycleCheck.error || 'Conexión inválida: Se detectó un ciclo en el flujo (violación de DAG).', 'error');
            setDagStatus({ valid: false, message: cycleCheck.error });
            return;
        }

        // 2. Proactively test full DAG with new edge
        const newEdge: CustomEdge = {
            id: `temp_${Date.now()}`,
            source: connection.source,
            target: connection.target,
            label: 'Siempre',
            data: {
                condition_type: 'always',
                condition_key: '',
                condition_value: ''
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: 'hsl(var(--primary))'
            },
            style: {
                stroke: 'hsl(var(--primary))',
                strokeWidth: 2
            }
        };

        const simulatedEdges = [...edges, newEdge];
        const fullDagCheck = validateGraphDAG(nodes, simulatedEdges);
        if (fullDagCheck.hasCycle) {
            addToast(fullDagCheck.error || 'Conexión rechazada: Crearía un ciclo cerrado.', 'error');
            setDagStatus({ valid: false, message: fullDagCheck.error });
            return;
        }

        // 3. Server-side cycle validation if token is present
        if (token) {
            const serverCheck = await validateFlowWithServer(nodes, simulatedEdges, token);
            if (!serverCheck.valid) {
                addToast(serverCheck.error || 'El servidor rechazó la conexión por violación de ciclo.', 'error');
                setDagStatus({ valid: false, message: serverCheck.error });
                return;
            }
        }

        setEdges(eds => addEdge(newEdge, eds));
        setDagStatus({ valid: true, message: 'DAG válido sin ciclos' });
        addToast('Paso conectado correctamente (DAG validado)', 'success');
    }, [edges, nodes, token, addToast, setEdges]);

    // Handle selection changes
    const onSelectionChange = useCallback(({ nodes: selectedNodes, edges: selectedEdges }: { nodes: CustomNode[]; edges: CustomEdge[] }) => {
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

    // Create a new automation node with specific type
    const handleAddNode = async (nodeType: 'trigger' | 'condition' | 'action' = 'trigger') => {
        if (!token) return;
        try {
            let defaultName = `Nuevo Disparador ${nodes.length + 1}`;
            let triggerEvent = 'new_persona';
            let actionType = 'send_whatsapp';
            let actionPayload: Record<string, unknown> = { message: 'Hola, ¡bienvenido a nuestra comunidad!' };

            if (nodeType === 'condition') {
                defaultName = `Condición ${nodes.length + 1}`;
                triggerEvent = 'stage_change';
                actionType = 'send_whatsapp';
                actionPayload = { condition_key: 'etapa_actual_id', condition_type: 'equals', condition_value: 'bautismo' };
            } else if (nodeType === 'action') {
                defaultName = `Acción ${nodes.length + 1}`;
                triggerEvent = 'new_persona';
                actionType = 'send_whatsapp';
                actionPayload = { message: '¡Nos alegra tenerte con nosotros!' };
            }

            const defaultPayload = {
                name: defaultName,
                trigger_event: triggerEvent,
                action_type: actionType,
                action_payload: actionPayload,
                delay_minutes: 0,
                is_active: true,
                ui_graph_state: {
                    position: {
                        x: 100 + (nodes.length % 4) * 280,
                        y: 120 + Math.floor(nodes.length / 4) * 160
                    }
                }
            };

            const created = await apiFetch<CrmAutomationRecord>('/crm/resources/automations', {
                method: 'POST',
                token,
                body: defaultPayload
            });

            const newNode: CustomNode = {
                id: created.id,
                type: nodeType,
                position: defaultPayload.ui_graph_state.position,
                data: {
                    label: created.name,
                    nodeType,
                    automation: created,
                    condition_config: {
                        field: 'etapa_actual_id',
                        operator: 'equals',
                        value: 'bautismo'
                    }
                }
            };

            setNodes(nds => [...nds, newNode]);
            setSelectedNode(newNode);
            addToast(`Nodo ${nodeType.toUpperCase()} creado con éxito`, 'success');
        } catch {
            addToast('Error al crear el nodo', 'error');
        }
    };

    // Update node details (local state)
    const handleUpdateNodeField = (field: string, value: unknown) => {
        if (!selectedNode) return;
        setNodes(nds => nds.map(node => {
            if (node.id === selectedNode.id) {
                const updatedAut = { ...node.data.automation, [field]: value };
                const updatedNode: CustomNode = {
                    ...node,
                    type: field === 'nodeType' ? (value as any) : node.type,
                    data: {
                        ...node.data,
                        nodeType: field === 'nodeType' ? (value as any) : node.data.nodeType,
                        label: field === 'name' ? String(value) : node.data.label,
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
    const handleUpdateNodePayload = (key: string, value: unknown) => {
        if (!selectedNode) return;
        const currentPayload = selectedNode.data.automation.action_payload || {};
        const newPayload = { ...currentPayload, [key]: value };
        handleUpdateNodeField('action_payload', newPayload);
    };

    // Update condition config for condition nodes
    const handleUpdateConditionConfig = (key: 'field' | 'operator' | 'value', value: string) => {
        if (!selectedNode) return;
        setNodes(nds => nds.map(node => {
            if (node.id === selectedNode.id) {
                const currentConfig = node.data.condition_config || {};
                const newConfig = { ...currentConfig, [key]: value };
                const updatedNode: CustomNode = {
                    ...node,
                    data: {
                        ...node.data,
                        condition_config: newConfig
                    }
                };
                setSelectedNode(updatedNode);
                return updatedNode;
            }
            return node;
        }));
        handleUpdateNodePayload(`condition_${key}`, value);
    };

    // Delete node
    const handleDeleteNode = async () => {
        if (!selectedNode || !token) return;
        if (!confirm('¿Estás seguro de que deseas eliminar este nodo? Esto eliminará también sus conexiones.')) return;

        try {
            await apiFetch(`/crm/resources/automations/${selectedNode.id}`, {
                method: 'DELETE',
                token
            });

            setNodes(nds => nds.filter(n => n.id !== selectedNode.id));
            setEdges(eds => eds.filter(e => e.source !== selectedNode.id && e.target !== selectedNode.id));
            setSelectedNode(null);
            addToast('Nodo eliminado con éxito', 'success');
        } catch {
            addToast('Error al eliminar el nodo', 'error');
        }
    };

    // Update edge details (local state)
    const handleUpdateEdgeField = (field: string, value: unknown) => {
        if (!selectedEdge) return;
        setEdges(eds => eds.map(e => {
            if (e.id === selectedEdge.id) {
                const updatedData = { ...e.data, [field]: value };
                let newLabel = 'Siempre';
                if (updatedData.condition_type !== 'always' && updatedData.condition_type) {
                    newLabel = `${updatedData.condition_key || 'var'} ${updatedData.condition_type}`;
                }
                const updatedEdge: CustomEdge = {
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

    // Validate DAG Flow on demand
    const handleValidateFlow = async () => {
        setValidating(true);
        try {
            // Client side check
            const clientCheck = validateGraphDAG(nodes, edges);
            if (clientCheck.hasCycle) {
                setDagStatus({ valid: false, message: clientCheck.error });
                addToast(clientCheck.error || 'Error: Se detectaron ciclos en el flujo.', 'error');
                return;
            }

            // Server side check
            if (token) {
                const serverCheck = await validateFlowWithServer(nodes, edges, token);
                if (!serverCheck.valid) {
                    setDagStatus({ valid: false, message: serverCheck.error });
                    addToast(serverCheck.error || 'El servidor detectó un ciclo.', 'error');
                    return;
                }
            }

            setDagStatus({ valid: true, message: 'Flujo verificado: DAG acíclico válido.' });
            addToast('✅ Flujo verificado con éxito: Grafo Acíclico Dirigido (DAG) 100% válido.', 'success');
        } catch (err: any) {
            setDagStatus({ valid: false, message: err?.message || 'Error en validación' });
            addToast('Error al validar el flujo', 'error');
        } finally {
            setValidating(false);
        }
    };

    // Save entire graph and persist positions
    const handleSaveGraph = async () => {
        if (!token) return;
        setSaving(true);
        try {
            // 1. Verify DAG validity first
            const dagCheck = validateGraphDAG(nodes, edges);
            if (dagCheck.hasCycle) {
                addToast(dagCheck.error || 'No se puede guardar un flujo con ciclos.', 'error');
                setSaving(false);
                return;
            }

            // 2. Save positions & node updates
            for (const node of nodes) {
                const aut = node.data.automation;
                const body = {
                    name: aut.name,
                    trigger_event: aut.trigger_event,
                    action_type: aut.action_type,
                    action_payload: {
                        ...aut.action_payload,
                        ...(node.data.condition_config ? {
                            condition_key: node.data.condition_config.field,
                            condition_type: node.data.condition_config.operator,
                            condition_value: node.data.condition_config.value
                        } : {})
                    },
                    delay_minutes: aut.delay_minutes,
                    is_active: aut.is_active,
                    ui_graph_state: {
                        position: node.position
                    }
                };
                await apiFetch(`/crm/resources/automations/${node.id}`, {
                    method: 'PATCH',
                    token,
                    body
                });
            }

            // 3. Identify edges to create/delete
            const localEdgeIds = new Set(edges.map(e => e.id));
            const deletedEdges = originalEdges.filter(oe => !localEdgeIds.has(oe.id));

            for (const de of deletedEdges) {
                await apiFetch(`${AUTOMATION_EDGES_API}/${de.id}`, {
                    method: 'DELETE',
                    token
                });
            }

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
                    await apiFetch(AUTOMATION_EDGES_API, {
                        method: 'POST',
                        token,
                        body: edgeBody
                    });
                } else {
                    const orig = originalEdges.find(oe => oe.id === edge.id);
                    const hasChanged = orig && (
                        orig.condition_type !== edgeBody.condition_type ||
                        orig.condition_key !== edgeBody.condition_key ||
                        orig.condition_value !== edgeBody.condition_value
                    );
                    if (hasChanged) {
                        await apiFetch(`${AUTOMATION_EDGES_API}/${edge.id}`, {
                            method: 'DELETE',
                            token
                        });
                        await apiFetch(AUTOMATION_EDGES_API, {
                            method: 'POST',
                            token,
                            body: edgeBody
                        });
                    }
                }
            }

            addToast('Flujo y posiciones guardados con éxito', 'success');
            await loadGraphData();
        } catch (err) {
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
                { label: 'Constructor Visual 2.0', icon: GitBranch }
            ]}
            rightActions={
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => router.push('/plataforma/crm/messaging/automations')}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-xs font-bold uppercase hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all text-[hsl(var(--text-secondary))]"
                    >
                        <ArrowLeft size={12} /> Volver
                    </button>
                    <button
                        onClick={handleValidateFlow}
                        disabled={validating}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-blue-500/30 text-blue-600 dark:text-blue-400 bg-blue-500/10 rounded-md text-xs font-bold uppercase hover:bg-blue-500/20 transition-all"
                    >
                        <ShieldCheck size={13} />
                        {validating ? 'Validando...' : 'Validar DAG'}
                    </button>
                    <button
                        onClick={handleSaveGraph}
                        disabled={saving}
                        className="flex items-center gap-1.5 bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-md text-xs font-bold uppercase hover:opacity-90 shadow-lg shadow-[hsl(var(--primary)/0.2)] transition-all disabled:opacity-50"
                    >
                        {saving ? 'Guardando...' : <Save size={12} />}
                        Guardar Flujo
                    </button>
                </div>
            }
        >
            <div className="flex-1 flex overflow-hidden h-[calc(100vh-120px)]">
                {/* Visual Canvas Area */}
                <div className="flex-1 relative h-full bg-[hsl(var(--surface-1))] dark:bg-[#101114]">
                    {loading ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                            <DSSkeleton className="h-10 w-48 rounded-md" />
                            <div className="flex gap-4">
                                <DSSkeleton className="h-32 w-56 rounded-md" />
                                <DSSkeleton className="h-32 w-56 rounded-md" />
                            </div>
                        </div>
                    ) : (
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            nodeTypes={automationNodeTypes}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onSelectionChange={onSelectionChange}
                            fitView
                        >
                            <Background color="#888" gap={20} size={1} />
                            <Controls />
                            <MiniMap
                                nodeStrokeWidth={3}
                                zoomable
                                pannable
                                className="!bg-[hsl(var(--bg-primary))] !border-[hsl(var(--border))] !rounded-lg !shadow-lg"
                            />

                            {/* Node Creation Palette */}
                            <Panel position="top-left" className="flex items-center gap-2 bg-[hsl(var(--bg-primary))]/90 dark:bg-[#18191c]/90 backdrop-blur-md p-1.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 shadow-lg">
                                <span className="text-[10px] font-extrabold uppercase tracking-wider text-[hsl(var(--text-secondary))] px-2">
                                    Añadir:
                                </span>
                                <button
                                    onClick={() => handleAddNode('trigger')}
                                    className="flex items-center gap-1.5 bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30 px-2.5 py-1.5 rounded-lg text-xs font-bold uppercase hover:bg-blue-500/20 transition-all"
                                >
                                    <Zap size={13} /> Disparador
                                </button>
                                <button
                                    onClick={() => handleAddNode('condition')}
                                    className="flex items-center gap-1.5 bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30 px-2.5 py-1.5 rounded-lg text-xs font-bold uppercase hover:bg-blue-500/20 transition-all"
                                >
                                    <GitBranch size={13} /> Condición
                                </button>
                                <button
                                    onClick={() => handleAddNode('action')}
                                    className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 px-2.5 py-1.5 rounded-lg text-xs font-bold uppercase hover:bg-emerald-500/20 transition-all"
                                >
                                    <PlayCircle size={13} /> Acción
                                </button>
                            </Panel>

                            {/* Status Indicator Panel */}
                            {dagStatus && (
                                <Panel position="bottom-center" className="bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] border border-[hsl(var(--border))] dark:border-white/10 px-4 py-2 rounded-full shadow-xl flex items-center gap-2">
                                    {dagStatus.valid ? (
                                        <CheckCircle2 size={15} className="text-emerald-500" />
                                    ) : (
                                        <AlertTriangle size={15} className="text-rose-500" />
                                    )}
                                    <span className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                        {dagStatus.message}
                                    </span>
                                </Panel>
                            )}
                        </ReactFlow>
                    )}
                </div>

                {/* Right Properties Panel / Drawer */}
                <div className="w-84 border-l border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#141517] flex flex-col overflow-y-auto">
                    <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-between">
                        <h3 className="font-extrabold text-xs uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                            Propiedades del Elemento
                        </h3>
                        {selectedNode && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                                {selectedNode.type || 'Nodo'}
                            </span>
                        )}
                    </div>

                    <div className="p-4 flex-1 space-y-4">
                        {selectedNode ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-[hsl(var(--text-primary))] dark:text-white font-bold text-sm">
                                    <Settings size={16} className="text-[hsl(var(--primary))]" />
                                    <span>Configurar Nodo</span>
                                </div>

                                {/* Node Type Switcher */}
                                <div className="space-y-1">
                                    <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                        Tipo de Componente
                                    </label>
                                    <select
                                        value={selectedNode.type || 'trigger'}
                                        onChange={e => handleUpdateNodeField('nodeType', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                    >
                                        <option value="trigger">Disparador (Trigger)</option>
                                        <option value="condition">Condición / Bifurcación (Condition)</option>
                                        <option value="action">Acción Ejecutable (Action)</option>
                                    </select>
                                </div>

                                {/* Name Field */}
                                <div className="space-y-1">
                                    <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                        Nombre identificador
                                    </label>
                                    <input
                                        type="text"
                                        value={selectedNode.data.automation.name}
                                        onChange={e => handleUpdateNodeField('name', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                    />
                                </div>

                                {/* Trigger configuration */}
                                {selectedNode.type === 'trigger' && (
                                    <div className="space-y-3 p-3 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/50 dark:border-blue-800/30">
                                        <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400 font-bold text-xs">
                                            <Zap size={13} />
                                            <span>Configuración del Disparador</span>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Evento Disparador
                                            </label>
                                            <select
                                                value={selectedNode.data.automation.trigger_event}
                                                onChange={e => handleUpdateNodeField('trigger_event', e.target.value)}
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            >
                                                {TRIGGERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                )}

                                {/* Condition configuration */}
                                {selectedNode.type === 'condition' && (
                                    <div className="space-y-3 p-3 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/50 dark:border-blue-800/30">
                                        <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400 font-bold text-xs">
                                            <GitBranch size={13} />
                                            <span>Regla de Evaluación</span>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Variable / Campo
                                            </label>
                                            <select
                                                value={selectedNode.data.condition_config?.field || 'etapa_actual_id'}
                                                onChange={e => handleUpdateConditionConfig('field', e.target.value)}
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            >
                                                {CONDITION_VARIABLES.map(v => <option key={v.value} value={v.value}>{v.label} ({v.value})</option>)}
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Operador
                                            </label>
                                            <select
                                                value={selectedNode.data.condition_config?.operator || 'equals'}
                                                onChange={e => handleUpdateConditionConfig('operator', e.target.value)}
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            >
                                                {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Valor Esperado
                                            </label>
                                            <input
                                                type="text"
                                                value={selectedNode.data.condition_config?.value || ''}
                                                onChange={e => handleUpdateConditionConfig('value', e.target.value)}
                                                placeholder="Ej: bautismo, 1, activo"
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            />
                                        </div>
                                    </div>
                                )}

                                {/* Action configuration */}
                                {selectedNode.type === 'action' && (
                                    <div className="space-y-3 p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-800/30">
                                        <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                                            <PlayCircle size={13} />
                                            <span>Configuración de la Acción</span>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Tipo de Acción
                                            </label>
                                            <select
                                                value={selectedNode.data.automation.action_type}
                                                onChange={e => handleUpdateNodeField('action_type', e.target.value)}
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            >
                                                {ACTIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                                            </select>
                                        </div>

                                        {selectedNode.data.automation.action_type === 'create_task' ? (
                                            <div className="space-y-1">
                                                <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                    Título de Tarea Pastoral
                                                </label>
                                                <input
                                                    type="text"
                                                    value={readPayloadText(selectedNode.data.automation.action_payload, 'task_title')}
                                                    onChange={e => handleUpdateNodePayload('task_title', e.target.value)}
                                                    placeholder="Ej: Visita pastoral y oración"
                                                    className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                                />
                                            </div>
                                        ) : (
                                            <div className="space-y-1">
                                                <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                    Mensaje de Notificación
                                                </label>
                                                <textarea
                                                    value={readPayloadText(selectedNode.data.automation.action_payload, 'message')}
                                                    onChange={e => handleUpdateNodePayload('message', e.target.value)}
                                                    placeholder="Hola {nombre}, ¡bienvenido a nuestra comunidad!"
                                                    rows={4}
                                                    className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold resize-none"
                                                />
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Delay field */}
                                <div className="space-y-1">
                                    <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1">
                                        <Clock size={12} />
                                        Retardo de ejecución (minutos)
                                    </label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={selectedNode.data.automation.delay_minutes || 0}
                                        onChange={e => handleUpdateNodeField('delay_minutes', parseInt(e.target.value) || 0)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                    />
                                </div>

                                {/* Active toggle */}
                                <div className="flex items-center gap-3 pt-2">
                                    <label className="flex items-center gap-2 text-xs font-bold text-[hsl(var(--text-secondary))] cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={selectedNode.data.automation.is_active}
                                            onChange={e => handleUpdateNodeField('is_active', e.target.checked)}
                                            className="rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))] size-4"
                                        />
                                        Activo / En ejecución continua
                                    </label>
                                </div>

                                {/* Delete node */}
                                <div className="border-t border-[hsl(var(--border))] dark:border-white/10 pt-4 mt-4">
                                    <button
                                        onClick={handleDeleteNode}
                                        className="w-full flex items-center justify-center gap-2 py-2 bg-[hsl(var(--destructive)/0.08)] dark:bg-[hsl(var(--destructive)/0.2)] border border-[hsl(var(--destructive)/0.2)] text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.15)] rounded-md text-xs font-bold uppercase transition-all"
                                    >
                                        <Trash2 size={14} />
                                        Eliminar Nodo
                                    </button>
                                </div>
                            </div>
                        ) : selectedEdge ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-[hsl(var(--text-primary))] dark:text-white font-bold text-sm">
                                    <GitBranch size={16} className="text-[hsl(var(--primary))]" />
                                    <span>Configurar Conexión</span>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                        Tipo de Condición
                                    </label>
                                    <select
                                        value={selectedEdge.data?.condition_type || 'always'}
                                        onChange={e => handleUpdateEdgeField('condition_type', e.target.value)}
                                        className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                    >
                                        {CONDITION_TYPES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                                    </select>
                                </div>

                                {selectedEdge.data?.condition_type !== 'always' && (
                                    <>
                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Variable a evaluar
                                            </label>
                                            <input
                                                type="text"
                                                value={selectedEdge.data?.condition_key || ''}
                                                onChange={e => handleUpdateEdgeField('condition_key', e.target.value)}
                                                placeholder="Ej: stage, delivery_status"
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                                Valor Esperado
                                            </label>
                                            <input
                                                type="text"
                                                value={selectedEdge.data?.condition_value || ''}
                                                onChange={e => handleUpdateEdgeField('condition_value', e.target.value)}
                                                placeholder="Ej: read, activo, bautismo"
                                                className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 outline-none text-xs text-[hsl(var(--text-primary))] dark:text-white font-bold"
                                            />
                                        </div>
                                    </>
                                )}

                                <div className="border-t border-[hsl(var(--border))] dark:border-white/10 pt-4 mt-4">
                                    <button
                                        onClick={() => {
                                            setEdges(eds => eds.filter(e => e.id !== selectedEdge.id));
                                            setSelectedEdge(null);
                                            addToast('Conexión eliminada', 'info');
                                        }}
                                        className="w-full flex items-center justify-center gap-2 py-2 bg-[hsl(var(--destructive)/0.08)] dark:bg-[hsl(var(--destructive)/0.2)] border border-[hsl(var(--destructive)/0.2)] text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.15)] rounded-md text-xs font-bold uppercase transition-all"
                                    >
                                        <Trash2 size={14} />
                                        Eliminar Conexión
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center text-center text-[hsl(var(--text-secondary))] py-12 px-4 space-y-2">
                                <Sparkles size={32} className="opacity-40 text-[hsl(var(--primary))]" />
                                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                    Canvas No-Code 2.0
                                </p>
                                <p className="text-xs text-[hsl(var(--text-secondary))]">
                                    Haz clic en un nodo de Disparador, Condición o Acción para configurar sus propiedades, o arrastra entre los conectores para crear bifurcaciones acíclicas.
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

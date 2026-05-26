"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    Bot,
    Users,
    MessageSquare,
    Settings,
    Shield,
    Zap,
    Eye,
    Activity,
    Clock,
    Search,
    Plus,
    RefreshCw,
    BrainCircuit,
    MessageCircle,
    Database,
    Send,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';

// Types
interface Agent {
    id: number;
    code: string;
    first_name: string;
    last_name: string;
    email: string | null;
    phone: string | null;
    spiritual_stage: string;
    is_active: boolean;
    created_at: string;
}

interface Tool {
    name: string;
    description: string;
    module: string;
    parameters: any[];
}

interface Conversation {
    id: number;
    title: string;
    agent_name: string;
    created_at: string;
    updated_at: string;
    message_count: number;
}

const STAGE_LABELS: Record<string, string> = {
    visitor: 'Visitante',
    believer: 'Creiente',
    disciple: 'Discípulo',
    servant: 'Siervo',
    leader: 'Líder',
    pastor: 'Pastor',
};

export default function AgentsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState<'agents' | 'tools' | 'conversations' | 'chat'>('agents');
    const [agents, setAgents] = useState<Agent[]>([]);
    const [tools, setTools] = useState<Tool[]>([]);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([]);
    const [chatInput, setChatInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const [activeConversation, setActiveConversation] = useState<number | null>(null);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [agentsRes, convRes] = await Promise.all([
                apiFetch('/agents/search?q=', { token }).catch(() => [] as Agent[]),
                apiFetch('/agents/conversations', { token }).catch(() => [] as Conversation[]),
            ]);
            setAgents(Array.isArray(agentsRes) ? agentsRes : []);
            setConversations(Array.isArray(convRes) ? convRes : []);
        } catch (err) {
            addToast('Error al cargar datos', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const fetchTools = async () => {
        try {
            const res = await apiFetch('/agents/tools', { token }).catch(() => null);
            if (res && Array.isArray(res)) setTools(res);
        } catch {
            // Tools endpoint may not exist yet
        }
    };

    useEffect(() => {
        if (activeTab === 'tools') fetchTools();
    }, [activeTab, token]);

    const sendChat = async () => {
        if (!chatInput.trim() || !token) return;
        setChatLoading(true);
        const userMsg = { role: 'user', content: chatInput };
        setChatMessages(prev => [...prev, userMsg]);
        setChatInput('');

        try {
            const res = await apiFetch('/agents/ask', {
                token,
                method: 'POST',
                body: JSON.stringify({ query: chatInput, conversation_id: activeConversation }),
            }) as any;
            if (res?.answer) {
                setChatMessages(prev => [...prev, { role: 'assistant', content: res.answer }]);
                if (res.conversation_id) setActiveConversation(res.conversation_id);
            }
        } catch {
            setChatMessages(prev => [...prev, { role: 'assistant', content: 'Error al procesar la consulta.' }]);
        } finally {
            setChatLoading(false);
        }
    };

    const createConversation = async () => {
        if (!token) return;
        try {
            const res = await apiFetch('/agents/conversations', {
                token,
                method: 'POST',
                body: JSON.stringify({ agent_name: 'Optimus' }),
            }) as any;
            if (res?.id) {
                setActiveConversation(res.id);
                setChatMessages([]);
                addToast('Nueva conversación creada', 'success');
                fetchData();
            }
        } catch {
            addToast('Error al crear conversación', 'error');
        }
    };

    const rebuildKB = async () => {
        if (!token) return;
        try {
            await apiFetch('/agents/kb/rebuild', { token, method: 'POST' });
            addToast('Knowledge Base reconstruida', 'success');
        } catch {
            addToast('Error al reconstruir KB', 'error');
        }
    };

    const filteredAgents = agents.filter(a =>
        `${a.first_name} ${a.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
        a.email?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <BrainCircuit className="w-8 h-8 text-blue-600" />
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                            Sistema Multiagente CCF
                        </h1>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400">
                        Optimus Neural MESH — Agentes inteligentes para gestión ministerial
                    </p>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700">
                    {[
                        { id: 'agents', label: 'Agentes', icon: Bot },
                        { id: 'tools', label: 'Herramientas', icon: Zap },
                        { id: 'conversations', label: 'Conversaciones', icon: MessageSquare },
                        { id: 'chat', label: 'Chat Optimus', icon: MessageCircle },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
                                activeTab === tab.id
                                    ? 'bg-white dark:bg-gray-800 border-b-2 border-blue-600 text-blue-600 font-medium'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                            }`}
                        >
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Agents Tab */}
                {activeTab === 'agents' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <div className="relative flex-1 max-w-md">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Buscar agentes..."
                                    value={searchTerm}
                                    onChange={e => setSearchTerm(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                                />
                            </div>
                            <button
                                onClick={fetchData}
                                className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Actualizar
                            </button>
                        </div>

                        {loading ? (
                            <div className="text-center py-12 text-gray-500">Cargando agentes...</div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {filteredAgents.map(agent => (
                                    <div
                                        key={agent.id}
                                        className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700"
                                    >
                                        <div className="flex items-center gap-3 mb-3">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                                agent.is_active ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
                                            }`}>
                                                <Bot className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <h3 className="font-medium text-gray-900 dark:text-white">
                                                    {agent.first_name} {agent.last_name}
                                                </h3>
                                                <p className="text-sm text-gray-500">{agent.code}</p>
                                            </div>
                                        </div>
                                        <div className="space-y-1 text-sm">
                                            {agent.email && (
                                                <p className="text-gray-600 dark:text-gray-400">{agent.email}</p>
                                            )}
                                            <div className="flex items-center gap-2">
                                                <Shield className="w-4 h-4 text-blue-500" />
                                                <span className="text-gray-700 dark:text-gray-300">
                                                    {STAGE_LABELS[agent.spiritual_stage] || agent.spiritual_stage}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Activity className={`w-4 h-4 ${agent.is_active ? 'text-green-500' : 'text-gray-400'}`} />
                                                <span className={agent.is_active ? 'text-green-600' : 'text-gray-400'}>
                                                    {agent.is_active ? 'Activo' : 'Inactivo'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Tools Tab */}
                {activeTab === 'tools' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                Herramientas Registradas
                            </h2>
                            <button
                                onClick={rebuildKB}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                                <Database className="w-4 h-4" />
                                Reconstruir KB
                            </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {tools.length === 0 ? (
                                <div className="col-span-full text-center py-12 text-gray-500">
                                    Las herramientas se registran automáticamente al iniciar el backend.
                                    <br />
                                    <span className="text-sm">8 herramientas disponibles: CRM, Academy, Projects, Analytics</span>
                                </div>
                            ) : (
                                tools.map((tool, i) => (
                                    <div
                                        key={i}
                                        className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <Zap className="w-5 h-5 text-yellow-500" />
                                            <h3 className="font-medium text-gray-900 dark:text-white">{tool.name}</h3>
                                        </div>
                                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{tool.description}</p>
                                        <span className="inline-block px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs rounded">
                                            {tool.module}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Conversations Tab */}
                {activeTab === 'conversations' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                Conversaciones
                            </h2>
                            <button
                                onClick={createConversation}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                                <Plus className="w-4 h-4" />
                                Nueva Conversación
                            </button>
                        </div>
                        {conversations.length === 0 ? (
                            <div className="text-center py-12 text-gray-500">
                                No hay conversaciones aún. Crea una nueva para empezar.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {conversations.map(conv => (
                                    <button
                                        key={conv.id}
                                        onClick={() => {
                                            setActiveConversation(conv.id);
                                            setActiveTab('chat');
                                            setChatMessages([]);
                                        }}
                                        className="w-full bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 text-left hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <MessageCircle className="w-5 h-5 text-blue-500" />
                                                <div>
                                                    <h3 className="font-medium text-gray-900 dark:text-white">
                                                        {conv.title || 'Sin título'}
                                                    </h3>
                                                    <p className="text-sm text-gray-500">
                                                        {conv.message_count} mensajes · {conv.agent_name}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 text-sm text-gray-500">
                                                <Clock className="w-4 h-4" />
                                                {new Date(conv.updated_at).toLocaleDateString('es-ES')}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Chat Tab */}
                {activeTab === 'chat' && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <Bot className="w-6 h-6 text-blue-600" />
                                <div>
                                    <h3 className="font-medium text-gray-900 dark:text-white">Chat con Optimus</h3>
                                    <p className="text-sm text-green-600 flex items-center gap-1">
                                        <span className="w-2 h-2 bg-green-500 rounded-full inline-block"></span>
                                        En línea
                                    </p>
                                </div>
                            </div>
                            {activeConversation && (
                                <span className="text-sm text-gray-500">
                                    Conversación #{activeConversation}
                                </span>
                            )}
                        </div>

                        {/* Messages */}
                        <div className="h-96 overflow-y-auto p-4 space-y-4">
                            {chatMessages.length === 0 ? (
                                <div className="text-center py-12 text-gray-500">
                                    <BrainCircuit className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                                    <p>Haz una pregunta a Optimus</p>
                                    <p className="text-sm">Puede buscar miembros, cursos, proyectos y más</p>
                                </div>
                            ) : (
                                chatMessages.map((msg, i) => (
                                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[80%] rounded-lg p-3 ${
                                            msg.role === 'user'
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                                        }`}>
                                            {msg.role === 'assistant' && <Bot className="w-4 h-4 mb-1 text-blue-500" />}
                                            <p className="whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                            {chatLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3">
                                        <div className="flex gap-1">
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input */}
                        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={chatInput}
                                    onChange={e => setChatInput(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && sendChat()}
                                    placeholder="Pregunta algo a Optimus..."
                                    className="flex-1 px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                />
                                <button
                                    onClick={sendChat}
                                    disabled={chatLoading || !chatInput.trim()}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                >
                                    <Send className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

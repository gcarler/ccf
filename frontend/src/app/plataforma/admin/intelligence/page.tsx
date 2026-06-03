"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Bot, 
    Zap, 
    BrainCircuit, 
    Activity, 
    Send, 
    Layers, 
    BarChart3, 
    Sparkles, 
    Settings,
    MoreHorizontal,
    ChevronRight,
    Terminal,
    Cpu,
    ShieldCheck
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function IntelligenceConsole() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [insights, setInsights] = useState<any[]>([]);
    const [tasks, setTasks] = useState<any[]>([]);
    const [query, setQuery] = useState('');
    const [aiResponse, setAiResponse] = useState<any>(null);
    const [isAsking, setIsAsking] = useState(false);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);
    const [acknowledgingAll, setAcknowledgingAll] = useState(false);
    const [showTaskComposer, setShowTaskComposer] = useState(false);
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const [newTaskPriority, setNewTaskPriority] = useState('medium');
    const [creatingTask, setCreatingTask] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        setLoadError(null);
        try {
            const [insightsData, tasksData] = await Promise.all([
                apiFetch('/agents/insights', { token }),
                apiFetch('/agents/tasks', { token })
            ]);
            setInsights(Array.isArray(insightsData) ? insightsData : []);
            setTasks(Array.isArray(tasksData) ? tasksData : []);
        } catch (err) {
            console.error(err);
            setInsights([]);
            setTasks([]);
            setLoadError('No se pudo sincronizar la consola de inteligencia.');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { if (isAuthenticated) fetchData(); }, [isAuthenticated, fetchData]);

    const handleAskOptimus = async () => {
        if (!query.trim() || !token) return;
        setIsAsking(true);
        try {
            const res = await apiFetch('/agents/ask', {
                method: 'POST',
                token,
                body: { query }
            });
            setAiResponse(res);
        } catch (err) {
            addToast('Error al consultar a Optimus', 'error');
        } finally {
            setIsAsking(false);
        }
    };

    const handleTrainModel = async () => {
        await fetchData();
        addToast('Modelo sincronizado con los datos más recientes', 'success');
    };

    const handleAcknowledgeInsight = async (insightId: number) => {
        if (!token) return;
        setAcknowledgingId(insightId);
        try {
            await apiFetch(`/agents/insights/${insightId}/ack`, {
                method: 'POST',
                token,
            });
            setInsights((items) => items.map((item) => item.id === insightId ? { ...item, acknowledged: true } : item));
            addToast('Insight reconocido', 'success');
        } catch (err) {
            console.error(err);
            addToast('No se pudo reconocer el insight', 'error');
        } finally {
            setAcknowledgingId(null);
        }
    };

    const handleAcknowledgeAll = async () => {
        if (!token) return;
        const pending = insights.filter((insight) => !insight.acknowledged);
        if (pending.length === 0) return;

        setAcknowledgingAll(true);
        try {
            await Promise.all(pending.map((insight) => apiFetch(`/agents/insights/${insight.id}/ack`, {
                method: 'POST',
                token,
            })));
            setInsights((items) => items.map((item) => ({ ...item, acknowledged: true })));
            addToast('Todos los insights fueron reconocidos', 'success');
        } catch (err) {
            console.error(err);
            addToast('No se pudieron reconocer todos los insights', 'error');
        } finally {
            setAcknowledgingAll(false);
        }
    };

    const handleCreateTask = async () => {
        if (!token || !newTaskTitle.trim()) return;
        setCreatingTask(true);
        try {
            const created = await apiFetch('/agents/tasks', {
                method: 'POST',
                token,
                body: {
                    title: newTaskTitle.trim(),
                    priority: newTaskPriority,
                    source: 'manual_console',
                },
            });
            setTasks((items) => [created, ...items]);
            setNewTaskTitle('');
            setNewTaskPriority('medium');
            setShowTaskComposer(false);
            addToast('Tarea manual asignada', 'success');
        } catch (err) {
            console.error(err);
            addToast('No se pudo crear la tarea manual', 'error');
        } finally {
            setCreatingTask(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Gestión Central', icon: Settings },
                { label: 'Inteligencia de Negocios', icon: BrainCircuit }
            ]}
        >
            <AdminHero
                eyebrow="AI Command Center"
                title="Consola de Comando Optimus"
                description="Supervisa la red de agentes autónomos y procesa los hallazgos generados por Optimus Brain. La IA está analizando patrones operativos en tiempo real."
                tags={['Optimus v2.1', 'Neural Core', 'Active']}
                watchers={['Tech Lead', 'Dirección Académica']}
                primaryAction={{ label: 'Entrenar Modelo', icon: Zap, onClick: handleTrainModel }}
                secondaryAction={{ label: 'Ver Logs', icon: Terminal, onClick: () => router.push('/plataforma/admin/audit') }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 pb-4">
                {/* Main AI Stats */}
                <div className="lg:col-span-8 space-y-3">
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <StatusCard label="Salud del Core" value={loadError ? 'DEGRADADA' : 'ÓPTIMA'} status={loadError ? 'degraded' : 'online'} icon={Cpu} color="blue" />
                        <StatusCard label="Insights Activos" value={insights.length.toString()} status="ready" icon={Sparkles} color="purple" />
                        <StatusCard label="Tareas en Cola" value={tasks.length.toString()} status="processing" icon={Layers} color="amber" />
                    </section>

                    {/* Ask Optimus Interface */}
                    <section className="bg-slate-900 rounded-lg p-4 text-white shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-10 bg-blue-600/20 rounded-full blur-[80px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10 space-y-3">
                            <div className="flex items-center gap-4">
                                <div className="size-7 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center shadow-lg shadow-blue-500/20"><Bot size={28} /></div>
                                <div>
                                    <h3 className="text-lg font-bold tracking-tight leading-none mb-1 uppercase">Consultar Base de Conocimientos</h3>
                                    <p className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide">Query el Cerebro Central de CCF</p>
                                </div>
                            </div>

                            <div className="relative">
                                <input 
                                    value={query} onChange={(e) => setQuery(e.target.value)}
                                    placeholder="¿Cuál es la tendencia de crecimiento en el curso de liderazgo?"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg py-2 px-4 pr-16 text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500/50 transition-all placeholder:text-slate-500"
                                />
                                <button 
                                    onClick={handleAskOptimus} disabled={isAsking}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 size-7 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] rounded-md flex items-center justify-center transition-all active:scale-90"
                                >
                                    {isAsking ? <Activity size={20} className="animate-spin" /> : <Send size={20} />}
                                </button>
                            </div>

                            <AnimatePresence>
                                {aiResponse && (
                                    <motion.div 
                                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                        className="p-4 bg-white/5 border border-white/10 rounded-lg space-y-4"
                                    >
                                        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-emerald-400"><ShieldCheck size={14} /> Respuesta Certificada</div>
                                        <p className="text-slate-300 leading-relaxed text-sm font-medium">{aiResponse.answer}</p>
                                        <div className="pt-4 border-t border-white/5 flex gap-3 flex-wrap">
                                            {aiResponse.sources?.map((s: string, i: number) => (
                                                <span key={i} className="px-3 py-1 bg-white/5 rounded-full font-semibold text-slate-500 uppercase">{s}</span>
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </section>

                    {/* Insights Wall */}
                    <section className="space-y-3">
                        <div className="flex justify-between items-center px-4">
                            <h3 className="text-lg font-bold tracking-tight uppercase tracking-wide">Intelligent Insights</h3>
                            <button
                                onClick={() => void handleAcknowledgeAll()}
                                disabled={acknowledgingAll || insights.every((insight) => insight.acknowledged)}
                                className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide hover:underline disabled:opacity-40 disabled:no-underline"
                            >
                                {acknowledgingAll ? 'Procesando...' : 'Reconocer Todo'}
                            </button>
                        </div>
                        {loadError && (
                            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-600">
                                {loadError}
                            </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {insights.map((insight) => (
                                <div key={insight.id} className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg shadow-sm hover:shadow-xl transition-all group relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-3 opacity-5 group-hover:opacity-10 transition-opacity"><Zap size={48} className="text-[hsl(var(--primary))]" /></div>
                                    <div className="relative z-10 space-y-4">
                                        <div className="flex justify-between items-start">
                                            <div className="size-10 rounded-lg bg-slate-100 dark:bg-white/10 flex items-center justify-center text-[hsl(var(--primary))]"><BrainCircuit size={20} /></div>
                                            {!insight.acknowledged && <div className="px-2 py-0.5 bg-blue-100 text-[hsl(var(--primary))] rounded text-[8px] font-semibold uppercase tracking-wide">NUEVO</div>}
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-1 uppercase tracking-tight">{insight.title}</h4>
                                            <p className="text-[12px] font-medium text-slate-500 leading-tight">{insight.payload}</p>
                                        </div>
                                        {!insight.acknowledged ? (
                                            <button
                                                onClick={() => void handleAcknowledgeInsight(insight.id)}
                                                disabled={acknowledgingId === insight.id}
                                                className="flex items-center gap-2 font-semibold text-[hsl(var(--primary))] uppercase tracking-wide group-hover:gap-3 transition-all disabled:opacity-40"
                                            >
                                                {acknowledgingId === insight.id ? 'Procesando...' : 'Reconocer'} <ChevronRight size={14} />
                                            </button>
                                        ) : (
                                            <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">Reconocido</span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                        {!loading && insights.length === 0 && (
                            <div className="rounded-lg border border-dashed border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 p-4 text-sm font-semibold text-slate-500">
                                No hay insights disponibles.
                            </div>
                        )}
                    </section>
                </div>

                {/* Sidebar: Agents Status & Tasks */}
                <aside className="lg:col-span-4 space-y-3">
                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3">
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Estado de la Red</h4>
                                <BarChart3 size={18} className="text-slate-300" />
                            </div>
                            <div className="space-y-3">
                                <AgentState label="Optimus Analysis" load={65} status="Online" color="bg-[hsl(var(--primary))]" />
                                <AgentState label="Crawler Doctrinal" load={12} status="Idle" color="bg-slate-400" />
                                <AgentState label="Messenger Bot" load={94} status="Busy" color="bg-amber-500" />
                            </div>
                        </div>

                        <div className="pt-10 border-t border-slate-100 dark:border-white/5">
                            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Cola de Procesos</h4>
                            <div className="space-y-4">
                                {tasks.map((task) => (
                                    <div key={task.id} className="p-3 bg-slate-50 dark:bg-white/5 rounded-lg flex items-center justify-between group">
                                        <div className="flex items-center gap-4">
                                            <div className={clsx("size-3 rounded-full animate-pulse", task.status === 'running' ? 'bg-[hsl(var(--primary))]' : 'bg-slate-300')} />
                                            <div>
                                                <p className="font-semibold text-slate-800 dark:text-white uppercase leading-none mb-1">{task.title}</p>
                                                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{task.status}</p>
                                            </div>
                                        </div>
                                        <button className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity"><MoreHorizontal size={16} /></button>
                                    </div>
                                ))}
                                {!loading && tasks.length === 0 && (
                                    <div className="rounded-lg border border-dashed border-slate-200 dark:border-white/10 p-3 text-[11px] font-bold uppercase tracking-wide text-slate-400">
                                        Sin tareas en cola
                                    </div>
                                )}
                            </div>
                        </div>

                        {showTaskComposer ? (
                            <div className="space-y-3 rounded-lg border border-slate-200 dark:border-white/10 p-4">
                                <input
                                    value={newTaskTitle}
                                    onChange={(event) => setNewTaskTitle(event.target.value)}
                                    placeholder="Título de la tarea"
                                    className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none"
                                />
                                <select
                                    value={newTaskPriority}
                                    onChange={(event) => setNewTaskPriority(event.target.value)}
                                    className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none"
                                >
                                    <option value="low">Baja</option>
                                    <option value="medium">Media</option>
                                    <option value="high">Alta</option>
                                </select>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => void handleCreateTask()}
                                        disabled={creatingTask || !newTaskTitle.trim()}
                                        className="flex-1 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-40"
                                    >
                                        {creatingTask ? 'Guardando...' : 'Crear'}
                                    </button>
                                    <button
                                        onClick={() => setShowTaskComposer(false)}
                                        className="rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={() => setShowTaskComposer(true)}
                                className="w-full py-2 bg-slate-900 dark:bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl transition-all active:scale-95"
                            >
                                Asignar Tarea Manual
                            </button>
                        )}
                    </section>

                    <section className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-500/20">
                        <div className="flex items-center gap-3 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] mb-4">
                            <Activity size={18} />
                            <h5 className="text-[11px] font-semibold uppercase tracking-wide">Uptime del Cerebro</h5>
                        </div>
                        <div className="h-2 w-full bg-blue-200 dark:bg-white/10 rounded-full overflow-hidden mb-2">
                            <div className="h-full bg-[hsl(var(--primary))] w-[99.9%]" />
                        </div>
                        <p className="font-semibold text-[hsl(var(--primary))] uppercase tracking-wide text-right">99.98% Anual</p>
                    </section>
                </aside>
            </div>
        </AdminShell>
    );
}

function StatusCard({ label, value, status, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-900/20',
        purple: 'text-sky-600 bg-sky-50 dark:bg-sky-900/20',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20'
    };
    const statusTone = status === 'degraded'
        ? 'bg-rose-50 dark:bg-rose-900/20 text-rose-600'
        : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600';
    return (
        <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg shadow-sm flex flex-col gap-3 group hover:shadow-xl transition-all relative overflow-hidden">
            <div className="flex justify-between items-start">
                <div className={clsx("size-7 rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                    <Icon size={28} />
                </div>
                <div className={clsx("flex items-center gap-1.5 px-2 py-1 rounded-lg", statusTone)}>
                    <div className={clsx("size-1.5 rounded-full animate-pulse", status === 'degraded' ? 'bg-rose-500' : 'bg-emerald-500')} />
                    <span className="text-[8px] font-semibold uppercase">{status}</span>
                </div>
            </div>
            <div>
                <p className="font-semibold text-slate-400 uppercase tracking-wide mb-1">{label}</p>
                <h4 className="text-xl font-bold text-slate-900 dark:text-white tracking-tighter uppercase">{value}</h4>
            </div>
        </div>
    );
}

function AgentState({ label, load, status, color }: any) {
    return (
        <div className="space-y-3">
            <div className="flex justify-between items-end">
                <p className="font-semibold text-slate-800 dark:text-white uppercase leading-none">{label}</p>
                <span className="text-[9px] font-bold text-slate-400 uppercase">{status}</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                <div className={clsx("h-full transition-all duration-1000", color)} style={{ width: `${load}%` }} />
            </div>
        </div>
    );
}


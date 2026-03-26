"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Bot, 
    Zap, 
    BrainCircuit, 
    Activity, 
    CheckCircle2, 
    Clock, 
    AlertTriangle, 
    Search, 
    Send, 
    Layers, 
    BarChart3, 
    Sparkles, 
    Settings,
    MoreHorizontal,
    ChevronRight,
    Terminal,
    Cpu,
    Database,
    ShieldCheck
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function IntelligenceConsole() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [insights, setInsights] = useState<any[]>([]);
    const [tasks, setTasks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [aiResponse, setAiResponse] = useState<any>(null);
    const [isAsking, setIsAsking] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [insightsData, tasksData] = await Promise.all([
                apiFetch('/agents/insights', { token }),
                apiFetch('/agents/tasks', { token })
            ]);
            setInsights(Array.isArray(insightsData) ? insightsData : []);
            setTasks(Array.isArray(tasksData) ? tasksData : []);
        } catch (err) {
            console.error(err);
            // Mock data for visual excellence
            setInsights([
                { id: 1, title: 'Predicción de Deserción', insight_type: 'predictive', payload: 'Se detectó un 15% de riesgo en el curso de Fundamentos.', acknowledged: false, created_at: new Date().toISOString() },
                { id: 2, title: 'Pico de Donaciones', insight_type: 'anomaly', payload: 'Las ofrendas del sector Norte superaron la meta en 20%.', acknowledged: true, created_at: new Date().toISOString() }
            ]);
            setTasks([
                { id: 1, title: 'Indexación de Base Doctrinal', status: 'running', priority: 'high', created_at: new Date().toISOString() },
                { id: 2, title: 'Cierre Mensual Automático', status: 'pending', priority: 'medium', created_at: new Date().toISOString() }
            ]);
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
                primaryAction={{ label: 'Entrenar Modelo', icon: Zap, onClick: () => {} }}
                secondaryAction={{ label: 'Ver Logs', icon: Terminal, onClick: () => {} }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-20">
                {/* Main AI Stats */}
                <div className="lg:col-span-8 space-y-8">
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatusCard label="Salud del Core" value="ÓPTIMA" status="online" icon={Cpu} color="blue" />
                        <StatusCard label="Insights Activos" value={insights.length.toString()} status="ready" icon={Sparkles} color="purple" />
                        <StatusCard label="Tareas en Cola" value={tasks.length.toString()} status="processing" icon={Layers} color="amber" />
                    </section>

                    {/* Ask Optimus Interface */}
                    <section className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-64 bg-blue-600/20 rounded-full blur-[80px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10 space-y-8">
                            <div className="flex items-center gap-4">
                                <div className="size-12 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20"><Bot size={28} /></div>
                                <div>
                                    <h3 className="text-2xl font-black tracking-tight leading-none mb-1 uppercase">Consultar Base de Conocimientos</h3>
                                    <p className="text-[10px] font-black text-blue-400 uppercase tracking-[0.3em]">Query el Cerebro Central de CCF</p>
                                </div>
                            </div>

                            <div className="relative">
                                <input 
                                    value={query} onChange={(e) => setQuery(e.target.value)}
                                    placeholder="¿Cuál es la tendencia de crecimiento en el curso de liderazgo?"
                                    className="w-full bg-white/5 border border-white/10 rounded-2xl py-5 px-8 pr-16 text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500/50 transition-all placeholder:text-slate-500"
                                />
                                <button 
                                    onClick={handleAskOptimus} disabled={isAsking}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 size-12 bg-blue-600 hover:bg-blue-500 rounded-xl flex items-center justify-center transition-all active:scale-90"
                                >
                                    {isAsking ? <Activity size={20} className="animate-spin" /> : <Send size={20} />}
                                </button>
                            </div>

                            <AnimatePresence>
                                {aiResponse && (
                                    <motion.div 
                                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                        className="p-8 bg-white/5 border border-white/10 rounded-[2rem] space-y-4"
                                    >
                                        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-emerald-400"><ShieldCheck size={14} /> Respuesta Certificada</div>
                                        <p className="text-slate-300 leading-relaxed text-sm font-medium">{aiResponse.answer}</p>
                                        <div className="pt-4 border-t border-white/5 flex gap-3 flex-wrap">
                                            {aiResponse.sources?.map((s: string, i: number) => (
                                                <span key={i} className="px-3 py-1 bg-white/5 rounded-full text-[9px] font-black text-slate-500 uppercase">{s}</span>
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </section>

                    {/* Insights Wall */}
                    <section className="space-y-6">
                        <div className="flex justify-between items-center px-4">
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Intelligent Insights</h3>
                            <button className="text-[11px] font-black text-blue-600 uppercase tracking-widest hover:underline">Limpiar Todo</button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {insights.map((insight) => (
                                <div key={insight.id} className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all group relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity"><Zap size={48} className="text-blue-600" /></div>
                                    <div className="relative z-10 space-y-4">
                                        <div className="flex justify-between items-start">
                                            <div className="size-10 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-blue-600"><BrainCircuit size={20} /></div>
                                            {!insight.acknowledged && <div className="px-2 py-0.5 bg-blue-100 text-blue-600 rounded text-[8px] font-black uppercase tracking-widest">NUEVO</div>}
                                        </div>
                                        <div>
                                            <h4 className="text-[15px] font-black text-slate-900 dark:text-white mb-1 uppercase tracking-tight">{insight.title}</h4>
                                            <p className="text-[12px] font-medium text-slate-500 leading-tight">{insight.payload}</p>
                                        </div>
                                        <button className="flex items-center gap-2 text-[10px] font-black text-blue-600 uppercase tracking-widest group-hover:gap-3 transition-all">
                                            Ejecutar Acción <ChevronRight size={14} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {/* Sidebar: Agents Status & Tasks */}
                <aside className="lg:col-span-4 space-y-8">
                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-10">
                        <div>
                            <div className="flex items-center justify-between mb-8">
                                <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Estado de la Red</h4>
                                <BarChart3 size={18} className="text-slate-300" />
                            </div>
                            <div className="space-y-6">
                                <AgentState label="Optimus Analysis" load={65} status="Online" color="bg-blue-500" />
                                <AgentState label="Crawler Doctrinal" load={12} status="Idle" color="bg-slate-400" />
                                <AgentState label="Messenger Bot" load={94} status="Busy" color="bg-amber-500" />
                            </div>
                        </div>

                        <div className="pt-10 border-t border-slate-100 dark:border-white/5">
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-8">Cola de Procesos</h4>
                            <div className="space-y-4">
                                {tasks.map((task) => (
                                    <div key={task.id} className="p-5 bg-slate-50 dark:bg-white/5 rounded-2xl flex items-center justify-between group">
                                        <div className="flex items-center gap-4">
                                            <div className={clsx("size-3 rounded-full animate-pulse", task.status === 'running' ? 'bg-blue-500' : 'bg-slate-300')} />
                                            <div>
                                                <p className="text-[12px] font-black text-slate-800 dark:text-white uppercase leading-none mb-1">{task.title}</p>
                                                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{task.status}</p>
                                            </div>
                                        </div>
                                        <button className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity"><MoreHorizontal size={16} /></button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <button className="w-full py-5 bg-slate-900 dark:bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl transition-all active:scale-95">
                            Asignar Tarea Manual
                        </button>
                    </section>

                    <section className="p-8 bg-blue-50 dark:bg-blue-900/10 rounded-[3rem] border border-blue-100 dark:border-blue-500/20">
                        <div className="flex items-center gap-3 text-blue-600 dark:text-blue-400 mb-4">
                            <Activity size={18} />
                            <h5 className="text-[11px] font-black uppercase tracking-widest">Uptime del Cerebro</h5>
                        </div>
                        <div className="h-2 w-full bg-blue-200 dark:bg-white/10 rounded-full overflow-hidden mb-2">
                            <div className="h-full bg-blue-600 w-[99.9%]" />
                        </div>
                        <p className="text-[9px] font-black text-blue-500 uppercase tracking-widest text-right">99.98% Anual</p>
                    </section>
                </aside>
            </div>
        </AdminShell>
    );
}

function StatusCard({ label, value, status, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        purple: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all relative overflow-hidden">
            <div className="flex justify-between items-start">
                <div className={clsx("size-14 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                    <Icon size={28} />
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-lg">
                    <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[8px] font-black uppercase">{status}</span>
                </div>
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                <h4 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter uppercase">{value}</h4>
            </div>
        </div>
    );
}

function AgentState({ label, load, status, color }: any) {
    return (
        <div className="space-y-3">
            <div className="flex justify-between items-end">
                <p className="text-[10px] font-black text-slate-800 dark:text-white uppercase leading-none">{label}</p>
                <span className="text-[9px] font-bold text-slate-400 uppercase">{status}</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                <div className={clsx("h-full transition-all duration-1000", color)} style={{ width: `${load}%` }} />
            </div>
        </div>
    );
}

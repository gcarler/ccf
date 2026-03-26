"use client";

import React, { useEffect, useState } from "react";
import { 
    Check, Clock, Shield, X, Loader2, ArrowUpRight, FileText, CheckCircle2, TrendingUp, Users, Calendar, CheckSquare, 
    MessageSquare, ChevronRight, Search, Filter, MoreHorizontal, Plus, Bot, Sparkles, Layout, BarChart3, History, Target,
    DollarSign, Activity, AlertTriangle, Zap, Globe
} from "lucide-react";
import clsx from "clsx";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import Link from 'next/link';
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import { ViewType } from "@/components/ViewSwitcher";
import MetricCard from "@/components/ui/MetricCard";
import Skeleton from "@/components/ui/Skeleton";
import { motion, AnimatePresence } from 'framer-motion';

export default function AdminDashboardPage() {
  const { token, user } = useAuth();
  const [viewType, setViewType] = useState<ViewType>('grid');
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [testimonials, setTestimonials] = useState<any[]>([]);
  const [agentTasks, setAgentTasks] = useState<any[]>([]);
  const [agentInsights, setAgentInsights] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      setLoading(true);
      try {
        const [testRes, taskRes, insightRes, analyticsRes] = await Promise.all([
          apiFetch<any[]>("/admin/testimonials", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/tasks", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/insights", { token, cache: 'no-store' }),
          apiFetch<any>("/analytics/summary", { token, cache: 'no-store' })
        ]);

        setTestimonials(Array.isArray(testRes) ? testRes : []);
        setAgentTasks(Array.isArray(taskRes) ? taskRes : []);
        setAgentInsights(Array.isArray(insightRes) ? insightRes : []);
        setAnalytics(analyticsRes);
      } catch (e) {
        console.error("Error fetching admin data", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleOpenTask = (task: any) => {
    setSelectedTask(task);
    setIsDrawerOpen(true);
  };

  const pendingTestimonials = testimonials.filter(t => !t.is_approved).length;

  if (loading) {
      return (
          <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
              <WorkspaceToolbar breadcrumbs={[{ label: 'Gestión Central', icon: Shield }]} viewType="grid" setViewType={() => {}} />
              <div className="p-8 space-y-8">
                  <div className="grid grid-cols-4 gap-4"><Skeleton className="h-40 col-span-2 rounded-3xl" /><Skeleton className="h-40 rounded-3xl" /><Skeleton className="h-40 rounded-3xl" /></div>
                  <div className="grid grid-cols-3 gap-8"><div className="col-span-2 space-y-4"><Skeleton className="h-12 w-full rounded-xl" /><Skeleton className="h-64 w-full rounded-3xl" /></div><Skeleton className="h-80 w-full rounded-3xl" /></div>
              </div>
          </div>
      );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display">
        <WorkspaceToolbar 
            breadcrumbs={[{ label: 'Gestión Central', icon: Shield }, { label: 'Dashboard Operativo', icon: Layout }]}
            viewType={viewType} setViewType={setViewType} availableViews={['grid']}
            rightActions={
                <button className="flex items-center gap-2 px-4 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all">
                    Reporte Global <ArrowUpRight size={14} />
                </button>
            }
        />

        <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
            {/* Background Aesthetic Shimmer */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

            <div className="max-w-[1600px] mx-auto space-y-10 relative z-10">
                
                {/* 1. High Impact Financial & Stats Grid */}
                <section className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                    <div className="xl:col-span-2 relative overflow-hidden rounded-[3rem] bg-slate-900 dark:bg-blue-600 p-10 text-white shadow-2xl shadow-blue-500/20 group">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2 group-hover:scale-110 transition-transform duration-1000" />
                        <div className="relative z-10 h-full flex flex-col justify-between">
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-white/40">
                                    <Globe size={14} /> Tesorería Consolidada <span className="text-white/10">|</span> 2026
                                </div>
                                <div className="flex items-end gap-6">
                                    <h3 className="text-5xl lg:text-6xl font-black tracking-tighter">$12,450.00</h3>
                                    <div className="mb-2 px-3 py-1 bg-emerald-500 text-white rounded-full text-[10px] font-black flex items-center gap-1 shadow-lg shadow-emerald-500/20">
                                         <TrendingUp size={12} /> +15.2%
                                    </div>
                                </div>
                            </div>
                            <div className="mt-10 flex gap-10">
                                <div className="space-y-1"><p className="text-[9px] font-black text-white/30 uppercase tracking-widest">Diezmos</p><p className="text-xl font-bold">$8,200</p></div>
                                <div className="space-y-1"><p className="text-[9px] font-black text-white/30 uppercase tracking-widest">Ofrendas</p><p className="text-xl font-bold">$4,250</p></div>
                                <div className="flex-1" />
                                <div className="h-12 w-32 bg-white/5 rounded-xl border border-white/10 flex items-center justify-center backdrop-blur-md group-hover:bg-white/10 transition-all cursor-pointer">
                                    <span className="text-[10px] font-black uppercase tracking-widest">Detalles</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <MetricCard title="Miembros Activos" value="1,240" trend="+42" icon={Users} tone="blue" />
                    <MetricCard title="Asistencia Promedio" value="85%" trend="Óptimo" icon={Calendar} tone="emerald" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* 2. Operations Center (Left) */}
                    <div className="lg:col-span-8 space-y-8">
                        <div className="flex items-center justify-between px-4">
                            <h2 className="text-[12px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                <div className="size-2 rounded-full bg-rose-500 animate-pulse shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                                Comandos de Control Interno
                            </h2>
                            <div className="flex items-center gap-4">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{agentTasks.length} Activos</span>
                                <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all text-slate-400"><Filter size={16} /></button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            {agentTasks.map((task: any, idx: number) => (
                                <AdminTaskRow key={task.id} task={task} onOpen={handleOpenTask} index={idx} />
                            ))}
                            {pendingTestimonials > 0 && (
                                <AdminTaskRow 
                                    task={{ title: 'Moderador de Testimonios', description: `Hay ${pendingTestimonials} nuevos milagros esperando aprobación.`, priority: 'medium', status: 'Pendiente', is_special: true }}
                                    onOpen={() => window.location.href = '/admin/cms'}
                                />
                            )}
                            <button className="w-full h-14 border-2 border-dashed border-slate-100 dark:border-white/5 rounded-[1.5rem] flex items-center justify-center gap-3 text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all font-black uppercase text-[11px] tracking-widest mt-4">
                                <Plus size={18} /> Iniciar Nueva Operación
                            </button>
                        </div>
                    </div>

                    {/* 3. AI Intelligence & Logs (Right) */}
                    <aside className="lg:col-span-4 space-y-10">
                        
                        {/* Optimus Neural Widget */}
                        <div className="p-8 rounded-[3rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-2xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-100 transition-opacity rotate-12 group-hover:rotate-0 duration-500">
                                <Bot size={64} className="text-purple-600" />
                            </div>
                            <div className="space-y-6 relative z-10">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-black tracking-tight flex items-center gap-2">
                                        <Sparkles size={20} className="text-purple-500 animate-pulse" /> Optimus Neural
                                    </h3>
                                    <div className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[8px] font-black uppercase rounded-lg">Online</div>
                                </div>
                                
                                <div className="space-y-4">
                                    {agentInsights.slice(0, 2).map((insight: any) => (
                                        <div key={insight.id} className="p-4 bg-slate-50 dark:bg-black/40 rounded-2xl border border-slate-100 dark:border-white/5 space-y-2 group/insight cursor-pointer hover:border-purple-500/30 transition-all">
                                            <p className="text-[13px] font-bold text-slate-700 dark:text-slate-200 leading-tight">{insight.title}</p>
                                            <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 italic font-medium">&ldquo;{insight.payload}&rdquo;</p>
                                        </div>
                                    ))}
                                </div>

                                <button className="w-full py-4 bg-purple-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-lg shadow-purple-500/20 active:scale-95 transition-all">
                                    Intervenir con IA
                                </button>
                            </div>
                        </div>

                        {/* Recent Activity Log */}
                        <div className="space-y-6">
                            <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] px-4 flex items-center justify-between">
                                Actividad del Staff <History size={14} />
                            </h3>
                            <div className="space-y-6 relative before:absolute before:left-[23px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100 dark:before:bg-white/5">
                                <LogItem icon={Zap} title="Migración DB" user="Alex L." time="Hace 10m" color="bg-blue-500" />
                                <LogItem icon={CheckCircle2} title="Aprobación Curso" user="Pedro M." time="Hace 1h" color="bg-emerald-500" />
                                <LogItem icon={AlertTriangle} title="Fallo en Pasarela" user="System" time="Hace 3h" color="bg-rose-500" />
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        </main>

        <WorkspaceDrawer 
            isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
            title={selectedTask?.title || 'Detalles Operativos'} subtitle="Administración Central"
            actions={<><button className="px-4 py-2 text-[11px] font-bold text-slate-500">Descartar</button><button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20">Ejecutar Acción</button></>}
        >
            <div className="space-y-8 animate-fade-in">
                <section className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Estado</p>
                        <p className="text-sm font-black text-slate-800 dark:text-white uppercase tracking-tight">{selectedTask?.status}</p>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5">
                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Prioridad</p>
                        <p className="text-sm font-black text-rose-500 uppercase tracking-tight">{selectedTask?.priority}</p>
                    </div>
                </section>
                <section className="space-y-4">
                    <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><FileText size={14} /> Descripción Técnica</h4>
                    <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] text-[14px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                        {selectedTask?.description || selectedTask?.payload || 'Cargando detalles de la operación...'}
                    </div>
                </section>
            </div>
        </WorkspaceDrawer>
    </div>
  );
}

function AdminTaskRow({ task, onOpen, index }: any) {
    return (
        <motion.div 
            initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.03 }}
            onClick={() => onOpen(task)}
            className={clsx(
                "px-6 py-3 rounded-2xl bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/40 hover:shadow-xl transition-all cursor-pointer h-16 relative overflow-hidden",
                task.is_special && "border-l-4 border-l-amber-400"
            )}
        >
            <div className="flex items-center gap-5 flex-1 truncate">
                <div className={clsx(
                    "size-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm transition-transform group-hover:scale-110",
                    task.priority === 'high' ? "bg-rose-50 dark:bg-rose-900/30 text-rose-500" : "bg-slate-50 dark:bg-white/5 text-slate-400"
                )}>
                    {task.priority === 'high' ? <Shield size={20} /> : <CheckSquare size={20} />}
                </div>
                <div className="truncate">
                    <h4 className="text-[15px] font-black text-slate-800 dark:text-slate-100 tracking-tight truncate">{task.title}</h4>
                    <p className="text-[12px] text-slate-500 dark:text-slate-400 truncate font-medium">{task.description || 'Haz clic para intervenir en esta operación'}</p>
                </div>
            </div>
            <div className="flex items-center gap-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Intervenir</span>
                <ChevronRight size={18} className="text-slate-300" />
            </div>
            <div className="absolute right-0 top-0 bottom-0 w-1 bg-blue-600 opacity-0 group-hover:opacity-100 transition-opacity" />
        </motion.div>
    );
}

function LogItem({ icon: Icon, title, user, time, color }: any) {
    return (
        <div className="flex gap-4 relative z-10 group cursor-default">
            <div className={clsx("size-12 rounded-[1.2rem] flex items-center justify-center text-white shadow-lg shrink-0 transition-transform group-hover:scale-110", color)}>
                <Icon size={20} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-0.5">
                    <h5 className="text-[13px] font-bold text-slate-800 dark:text-slate-100 truncate tracking-tight">{title}</h5>
                    <span className="text-[10px] font-black text-slate-400 whitespace-nowrap">{time}</span>
                </div>
                <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium">Por <span className="text-blue-600 dark:text-blue-400">{user}</span></p>
            </div>
        </div>
    );
}

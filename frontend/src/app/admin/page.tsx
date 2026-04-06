"use client";

import React, { useEffect, useState } from "react";
import { 
    Check, Clock, Shield, X, Loader2, ArrowUpRight, ArrowRight, FileText, CheckCircle2, TrendingUp, Users, Calendar, CheckSquare, 
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
        const [testRes, taskRes, insightRes, analyticsRes] = await Promise.allSettled([
          apiFetch<any[]>("/admin/testimonials", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/tasks", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/insights", { token, cache: 'no-store' }),
          apiFetch<any>("/analytics/summary", { token, cache: 'no-store' })
        ]);

        setTestimonials(testRes.status === 'fulfilled' && Array.isArray(testRes.value) ? testRes.value : []);
        setAgentTasks(taskRes.status === 'fulfilled' && Array.isArray(taskRes.value) ? taskRes.value : []);
        setAgentInsights(insightRes.status === 'fulfilled' && Array.isArray(insightRes.value) ? insightRes.value : []);
        setAnalytics(analyticsRes.status === 'fulfilled' ? analyticsRes.value : null);
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
          <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden items-center justify-center space-y-4">
              <div className="relative">
                  <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                  <Shield className="w-8 h-8 animate-pulse text-blue-600 relative z-10" />
              </div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Verificando Sistemas...</p>
          </div>
      );
  }

  const containerVariants = {
      hidden: { opacity: 0 },
      show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
      hidden: { opacity: 0, y: 20 },
      show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
  };

  return (
    <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden font-sans relative">
        <WorkspaceToolbar 
            breadcrumbs={[{ label: 'Ecosistema', icon: Globe }, { label: 'Gestión Central', icon: Shield }]}
            viewType={viewType} setViewType={setViewType} availableViews={['grid']}
            rightActions={
                <button className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-slate-900/10 active:scale-95 transition-all">
                    Reporte Global <ArrowUpRight size={14} strokeWidth={3} />
                </button>
            }
        />

        {/* Ambient Background */}
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-600/5 rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-purple-600/5 rounded-full blur-[120px] pointer-events-none" />

        <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative z-10">
            <motion.div 
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="max-w-[1600px] mx-auto space-y-10"
            >
                
                {/* 1. High Impact Financial & Stats Grid */}
                <motion.section variants={itemVariants} className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                    <div className="xl:col-span-2 relative overflow-hidden rounded-[3rem] bg-[#001b48] p-10 lg:p-12 text-white shadow-2xl group border border-blue-500/20">
                        <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-[0.05] mix-blend-overlay" />
                        <div className="absolute top-[-50%] right-[-10%] w-[80%] h-[200%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#018abd]/30 via-[#004581]/10 to-transparent blur-3xl transition-transform duration-1000 group-hover:scale-110 pointer-events-none" />
                        
                        <div className="relative z-10 h-full flex flex-col justify-between">
                            <div className="space-y-4">
                                <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-[0.3em] text-blue-100 border border-white/20 shadow-inner">
                                    <Globe size={14} /> Tesorería Consolidada <span className="text-white/20">|</span> 2026
                                </div>
                                <div className="flex flex-col md:flex-row md:items-end gap-6 pt-2">
                                    <h3 className="text-5xl lg:text-7xl font-black tracking-tighter leading-none">$12,450<span className="text-3xl text-blue-300">.00</span></h3>
                                    <div className="mb-2 px-4 py-1.5 bg-emerald-500 text-white rounded-full text-[11px] font-black flex items-center gap-1.5 shadow-lg shadow-emerald-500/20 w-fit">
                                         <TrendingUp size={14} strokeWidth={3} /> +15.2%
                                    </div>
                                </div>
                            </div>
                            <div className="mt-12 flex flex-wrap gap-8 lg:gap-12 items-center">
                                <div className="space-y-1"><p className="text-[10px] font-black text-blue-200/50 uppercase tracking-widest">Diezmos</p><p className="text-2xl font-black">$8,200</p></div>
                                <div className="space-y-1"><p className="text-[10px] font-black text-blue-200/50 uppercase tracking-widest">Ofrendas</p><p className="text-2xl font-black">$4,250</p></div>
                                <div className="flex-1 hidden md:block" />
                                <button className="h-14 px-8 bg-white text-[#001b48] rounded-[2rem] font-black text-[11px] uppercase tracking-widest shadow-xl hover:scale-105 active:scale-95 transition-all w-full md:w-auto">
                                    Desglosar
                                </button>
                            </div>
                        </div>
                    </div>
                    <KpiCard title="Miembros Activos" value="1,240" trend="+42 nuevas personas" icon={Users} color="text-blue-500" />
                    <KpiCard title="Asistencia Global" value="85%" trend="Indicador Óptimo" icon={Calendar} color="text-emerald-500" />
                </motion.section>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* 2. Operations Center (Left) */}
                    <div className="lg:col-span-8 space-y-8">
                        <motion.div variants={itemVariants} className="flex items-center justify-between px-4">
                            <h2 className="text-[12px] font-black text-slate-800 dark:text-white uppercase tracking-[0.3em] flex items-center gap-3">
                                <div className="size-2 rounded-full bg-rose-500 animate-pulse shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                                Comandos de Control Interno
                            </h2>
                            <div className="flex items-center gap-4">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{agentTasks.length} Activos</span>
                                <button className="p-2 hover:bg-white dark:hover:bg-white/5 rounded-xl transition-all text-slate-400 bg-slate-50 dark:bg-black/20"><Filter size={16} /></button>
                            </div>
                        </motion.div>

                        <motion.div variants={itemVariants} className="space-y-4">
                            {agentTasks.map((task: any, idx: number) => (
                                <AdminTaskRow key={task.id} task={task} onOpen={handleOpenTask} index={idx} />
                            ))}
                            {pendingTestimonials > 0 && (
                                <AdminTaskRow 
                                    task={{ title: 'Moderador de Testimonios', description: `Hay ${pendingTestimonials} nuevos milagros esperando aprobación.`, priority: 'medium', status: 'Pendiente', is_special: true }}
                                    onOpen={() => window.location.href = '/admin/cms'}
                                    index={100}
                                />
                            )}
                            <button className="w-full h-16 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[2rem] flex items-center justify-center gap-3 text-slate-400 hover:text-blue-600 hover:border-blue-500/30 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all font-black uppercase text-[11px] tracking-widest mt-6 group">
                                <Plus size={18} className="group-hover:scale-125 transition-transform" /> Iniciar Nueva Operación
                            </button>
                        </motion.div>
                    </div>

                    {/* 3. AI Intelligence & Logs (Right) */}
                    <aside className="lg:col-span-4 space-y-10">
                        
                        {/* Optimus Neural Widget */}
                        <motion.div variants={itemVariants} className="p-8 rounded-[3rem] bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/20 dark:shadow-none relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity duration-500 pointer-events-none">
                                <Bot size={120} className="text-purple-600" />
                            </div>
                            <div className="space-y-6 relative z-10">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-black tracking-tight text-slate-800 dark:text-white flex items-center gap-2">
                                        <Sparkles size={20} className="text-purple-500" /> MESH AI Neural
                                    </h3>
                                    <div className="px-3 py-1 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[9px] font-black uppercase tracking-widest rounded-lg flex items-center gap-1.5">
                                        <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" /> Online
                                    </div>
                                </div>
                                
                                <div className="space-y-4">
                                    {agentInsights.length > 0 ? (
                                        agentInsights.slice(0, 3).map((insight: any) => (
                                            <div key={insight.id} className="p-5 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 space-y-2 group/insight cursor-pointer hover:border-purple-500/30 hover:shadow-md transition-all">
                                                <div className="flex items-center justify-between">
                                                    <p className="text-[13px] font-bold text-slate-800 dark:text-slate-200 leading-tight group-hover/insight:text-purple-600 transition-colors">{insight.title}</p>
                                                    <span className="text-[8px] font-black px-1.5 py-0.5 bg-purple-50 dark:bg-purple-500/10 text-purple-600 rounded-md uppercase tracking-widest">{insight.insight_type.split('_')[0]}</span>
                                                </div>
                                                <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed italic font-medium">&ldquo;{insight.payload}&rdquo;</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="p-5 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 space-y-2">
                                            <p className="text-[13px] font-bold text-slate-800 dark:text-slate-200 leading-tight">Análisis de Sistema</p>
                                            <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed italic font-medium">&ldquo;Todos los sistemas operan dentro de los parámetros normales. No se requiere intervención inmediata.&rdquo;</p>
                                        </div>
                                    )}
                                </div>

                                <button className="w-full py-5 bg-purple-600 text-white rounded-2xl font-black text-[11px] uppercase tracking-[0.2em] shadow-xl shadow-purple-500/20 active:scale-95 transition-all flex items-center justify-center gap-2">
                                    Intervenir con IA <ArrowRight size={16} />
                                </button>
                            </div>
                        </motion.div>

                        {/* Recent Activity Log */}
                        <motion.div variants={itemVariants} className="space-y-6 bg-white dark:bg-[#15171c] p-8 rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-sm">
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2 mb-6">
                                <History size={14} /> Actividad del Staff
                            </h3>
                            <div className="space-y-6 relative before:absolute before:left-[23px] before:top-4 before:bottom-4 before:w-[2px] before:bg-slate-100 dark:before:bg-white/5">
                                <LogItem icon={Zap} title="Migración DB completada" user="Alex L." time="Hace 10m" color="text-blue-500" bg="bg-blue-50 dark:bg-blue-500/10" />
                                <LogItem icon={CheckCircle2} title="Aprobación Curso Teología" user="Pedro M." time="Hace 1h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                                <LogItem icon={AlertTriangle} title="Fallo en Pasarela Resuelto" user="System" time="Hace 3h" color="text-rose-500" bg="bg-rose-50 dark:bg-rose-500/10" />
                            </div>
                            <button className="w-full mt-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] hover:text-slate-600 transition-colors">Ver bitácora completa</button>
                        </motion.div>
                    </aside>
                </div>
            </motion.div>
        </main>

        <WorkspaceDrawer 
            isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
            title={selectedTask?.title || 'Detalles Operativos'} subtitle="Administración Central"
            actions={
                <>
                    <button className="px-5 py-2.5 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors" onClick={() => setIsDrawerOpen(false)}>Descartar</button>
                    <button className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">Ejecutar Acción</button>
                </>
            }
        >
            <div className="space-y-8 animate-fade-in p-2">
                <section className="grid grid-cols-2 gap-4">
                    <div className="p-5 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-sm">
                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] mb-2">Estado</p>
                        <p className="text-[15px] font-black text-slate-800 dark:text-white uppercase">{selectedTask?.status}</p>
                    </div>
                    <div className="p-5 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-sm">
                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] mb-2">Prioridad</p>
                        <p className="text-[15px] font-black text-rose-500 uppercase">{selectedTask?.priority}</p>
                    </div>
                </section>
                <section className="space-y-4">
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2"><FileText size={14} className="text-blue-500"/> Descripción Técnica</h4>
                    <div className="p-6 bg-slate-50 dark:bg-[#15171c] rounded-[2.5rem] text-[14px] text-slate-600 dark:text-slate-300 leading-relaxed font-medium shadow-inner">
                        {selectedTask?.description || selectedTask?.payload || 'Cargando detalles de la operación...'}
                    </div>
                </section>
            </div>
        </WorkspaceDrawer>
    </div>
  );
}

function KpiCard({ title, value, trend, icon: Icon, color }: any) {
    return (
        <div className="p-8 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none relative overflow-hidden group hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-slate-100 dark:from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-bl-[100px] pointer-events-none" />
            <div className="flex items-center justify-between mb-6 relative z-10">
                <div className={clsx("size-14 rounded-2xl flex items-center justify-center bg-slate-50 dark:bg-black/20 shadow-inner group-hover:scale-110 transition-transform", color)}>
                    <Icon size={24} strokeWidth={2.5} />
                </div>
                <button className="text-slate-300 hover:text-slate-500 transition-colors bg-slate-50 dark:bg-white/5 p-2 rounded-xl"><MoreHorizontal size={18} /></button>
            </div>
            <div className="relative z-10">
                <p className="text-[2.5rem] font-black text-slate-800 dark:text-white tracking-tighter leading-none mb-3">{value}</p>
                <div className="flex flex-col gap-2">
                    <p className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em]">{title}</p>
                    <span className="text-[10px] font-bold px-2.5 py-1 bg-slate-50 dark:bg-white/5 text-slate-500 rounded-lg flex items-center gap-1.5 w-fit">
                        <ArrowUpRight size={12} strokeWidth={3} /> {trend}
                    </span>
                </div>
            </div>
        </div>
    );
}

function AdminTaskRow({ task, onOpen, index }: any) {
    return (
        <motion.div 
            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05, type: 'spring', stiffness: 300, damping: 24 }}
            onClick={() => onOpen(task)}
            className={clsx(
                "p-4 rounded-[2rem] bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/40 hover:shadow-xl shadow-sm transition-all cursor-pointer relative overflow-hidden",
                task.is_special && "border-l-4 border-l-amber-400"
            )}
        >
            <div className="flex items-center gap-5 flex-1 min-w-0">
                <div className={clsx(
                    "size-12 rounded-2xl flex items-center justify-center shrink-0 shadow-inner transition-transform duration-300 group-hover:scale-110",
                    task.priority === 'high' ? "bg-rose-50 dark:bg-rose-500/10 text-rose-500" : "bg-slate-50 dark:bg-black/20 text-slate-400"
                )}>
                    {task.priority === 'high' ? <Shield size={20} strokeWidth={2.5} /> : <CheckSquare size={20} strokeWidth={2.5} />}
                </div>
                <div className="min-w-0 pr-4">
                    <h4 className="text-[15px] font-black text-slate-800 dark:text-white tracking-tight truncate group-hover:text-blue-600 transition-colors">{task.title}</h4>
                    <p className="text-[12px] text-slate-500 dark:text-slate-400 truncate font-medium mt-0.5">{task.description || 'Haz clic para intervenir en esta operación'}</p>
                </div>
            </div>
            <div className="flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-all transform translate-x-4 group-hover:translate-x-0 bg-blue-50 dark:bg-blue-500/10 px-4 py-2 rounded-xl">
                <span className="text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest hidden sm:inline">Intervenir</span>
                <ChevronRight size={16} className="text-blue-600 dark:text-blue-400" strokeWidth={3} />
            </div>
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity" />
        </motion.div>
    );
}

function LogItem({ icon: Icon, title, user, time, color, bg }: any) {
    return (
        <div className="flex gap-5 relative z-10 group cursor-default">
            <div className={clsx("size-12 rounded-2xl flex items-center justify-center shadow-inner shrink-0 transition-transform duration-300 group-hover:scale-110", bg, color)}>
                <Icon size={20} strokeWidth={2.5} />
            </div>
            <div className="flex-1 min-w-0 border-b border-slate-50 dark:border-white/5 pb-5 group-last:border-0 group-last:pb-0">
                <div className="flex justify-between items-center mb-1 gap-2">
                    <h5 className="text-[13px] font-bold text-slate-800 dark:text-white truncate tracking-tight">{title}</h5>
                    <span className="text-[9px] font-black text-slate-400 whitespace-nowrap bg-slate-50 dark:bg-black/20 px-2 py-1 rounded-md uppercase tracking-widest">{time}</span>
                </div>
                <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium">Por <span className="text-slate-700 dark:text-slate-200 font-bold">{user}</span></p>
            </div>
        </div>
    );
}

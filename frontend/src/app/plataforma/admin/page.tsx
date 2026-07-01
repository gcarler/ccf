"use client";

import { ViewType } from "@/components/ViewSwitcher";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import clsx from "clsx";
import { motion } from 'framer-motion';
import {
AlertTriangle,
ArrowRight,
ArrowUpRight,
Bot,
Calendar,
CheckCircle2,
CheckSquare,
ChevronRight,
FileText,
Filter,
Globe,
History,
MoreHorizontal,Plus,
Shield,
Sparkles,
TrendingUp,Users,
Zap
} from "lucide-react";
import { useEffect,useState } from "react";

export default function AdminDashboardPage() {
  const { token } = useAuth();
  const [viewType, setViewType] = useState<ViewType>('grid');
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [testimonials, setTestimonials] = useState<any[]>([]);
  const [agentTasks, setAgentTasks] = useState<any[]>([]);
  const [agentInsights, setAgentInsights] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      setLoading(true);
      try {
        const [testRes, taskRes, insightRes] = await Promise.allSettled([
          apiFetch<any[]>("/admin/testimonials", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/tasks", { token, cache: 'no-store' }),
          apiFetch<any[]>("/agents/insights", { token, cache: 'no-store' }),
        ]);

        setTestimonials(testRes.status === 'fulfilled' && Array.isArray(testRes.value) ? testRes.value : []);
        setAgentTasks(taskRes.status === 'fulfilled' && Array.isArray(taskRes.value) ? taskRes.value : []);
        setAgentInsights(insightRes.status === 'fulfilled' && Array.isArray(insightRes.value) ? insightRes.value : []);
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
          <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden items-center justify-center space-y-3">
              <div className="relative">
                  <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                  <Shield className="w-8 h-8 animate-pulse text-[hsl(var(--primary))] relative z-10" />
              </div>
              <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando Sistemas...</p>
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
                <button className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-md hover:scale-105 active:scale-95 transition-all">
                    Reporte Global <ArrowUpRight size={10} strokeWidth={3} />
                </button>
            }
        />

        {/* Ambient Background */}
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-600/5 rounded-full blur-[150px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-sky-600/5 rounded-full blur-[120px] pointer-events-none" />

        <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative z-10">
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="w-full mx-auto space-y-3"
            >

                {/* 1. High Impact Financial & Stats Grid */}
                <motion.section variants={itemVariants} className="grid grid-cols-1 xl:grid-cols-4 gap-3">
                    <div className="xl:col-span-2 relative overflow-hidden rounded-lg bg-[#001b48] p-4 text-white shadow-lg group border border-blue-500/20 flex flex-col justify-between">
                        <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-[0.05] mix-blend-overlay" />
                        <div className="absolute top-[-50%] right-[-10%] w-[80%] h-[200%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#018abd]/30 via-[#004581]/10 to-transparent blur-3xl transition-transform duration-1000 group-hover:scale-110 pointer-events-none" />

                        <div className="relative z-10 flex items-center justify-between mb-3">
                            <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-white/10 backdrop-blur-md rounded-lg text-[9px] font-bold uppercase tracking-wide text-blue-100 border border-white/20">
                                <Globe size={10} /> Tesorería Consolidada <span className="text-white/20">|</span> 2026
                            </div>
                            <button className="px-3 py-1 bg-white/10 hover:bg-[hsl(var(--bg-primary))] text-white hover:text-[#001b48] rounded-lg font-bold text-[9px] uppercase tracking-wide transition-all">
                                Desglosar
                            </button>
                        </div>

                        <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-3">
                            <div className="flex items-end gap-3">
                                <h3 className="text-xl lg:text-xl font-bold tracking-tighter leading-none">$12,450<span className="text-lg text-blue-300">.00</span></h3>
                                <div className="mb-1.5 px-2 py-0.5 bg-emerald-500 text-white rounded-md text-[9px] font-bold flex items-center gap-1 shadow-sm">
                                     <TrendingUp size={10} strokeWidth={3} /> +15.2%
                                </div>
                            </div>
                            <div className="flex gap-3 items-center">
                                <div className="space-y-0.5"><p className="text-[9px] font-bold text-blue-200/60 uppercase tracking-wide">Diezmos</p><p className="text-lg font-bold leading-none">$8,200</p></div>
                                <div className="space-y-0.5"><p className="text-[9px] font-bold text-blue-200/60 uppercase tracking-wide">Ofrendas</p><p className="text-lg font-bold leading-none">$4,250</p></div>
                            </div>
                        </div>
                    </div>
                    <KpiCard title="Personas" value="1,240" trend="+42 nuevas" icon={Users} color="text-[hsl(var(--primary))]" />
                    <KpiCard title="Asistencia" value="85%" trend="Óptimo" icon={Calendar} color="text-emerald-500" />
                </motion.section>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">

                    {/* 2. Operations Center (Left) */}
                    <div className="lg:col-span-8 space-y-3">
                        <motion.div variants={itemVariants} className="flex items-center justify-between px-2">
                            <h2 className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-rose-500 animate-pulse shadow-[0_0_6px_rgba(244,63,94,0.5)]" />
                                Comandos de Control Interno
                            </h2>
                            <div className="flex items-center gap-3">
                                <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{agentTasks.length} Activos</span>
                                <button className="p-1.5 hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 rounded-lg transition-all text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-black/20"><Filter size={10} /></button>
                            </div>
                        </motion.div>

                        <motion.div variants={itemVariants} className="space-y-2">
                            {agentTasks.map((task: any, idx: number) => (
                                <AdminTaskRow key={task.id} task={task} onOpen={handleOpenTask} index={idx} />
                            ))}
                            {pendingTestimonials > 0 && (
                                <AdminTaskRow
                                    task={{ title: 'Moderador de Testimonios', description: `Hay ${pendingTestimonials} nuevos milagros esperando aprobación.`, priority: 'medium', status: 'Pendiente', is_special: true }}
                                    onOpen={() => window.location.href = '/plataforma/admin/cms'}
                                    index={100}
                                />
                            )}
                            <button className="w-full py-3 border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-md flex items-center justify-center gap-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-blue-500/30 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all font-bold uppercase text-[10px] tracking-wide mt-2 group">
                                <Plus size={10} className="group-hover:scale-125 transition-transform" /> Iniciar Nueva Operación
                            </button>
                        </motion.div>
                    </div>

                    {/* 3. AI Intelligence & Logs (Right) */}
                    <aside className="lg:col-span-4 space-y-3">

                        {/* Optimus Neural Widget */}
                        <motion.div variants={itemVariants} className="p-4 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] border border-[hsl(var(--border))] dark:border-white/5 shadow-sm relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500 pointer-events-none">
                                <Bot size={10} className="text-sky-600" />
                            </div>
                            <div className="space-y-3 relative z-10">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white flex items-center gap-1.5">
                                        <Sparkles size={10} className="text-sky-500" /> MESH AI Neural
                                    </h3>
                                    <div className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[8px] font-bold uppercase tracking-wide rounded flex items-center gap-1">
                                        <div className="size-1 rounded-full bg-emerald-500 animate-pulse" /> Online
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    {agentInsights.length > 0 ? (
                                        agentInsights.slice(0, 3).map((insight: any) => (
                                            <div key={insight.id} className="p-3 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 space-y-1 group/insight cursor-pointer hover:border-sky-500/30 hover:shadow-sm transition-all">
                                                <div className="flex items-center justify-between">
                                                    <p className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-none group-hover/insight:text-sky-600 transition-colors truncate">{insight.title}</p>
                                                    <span className="text-[7px] font-bold px-1.5 py-0.5 bg-sky-50 dark:bg-sky-500/10 text-sky-600 rounded uppercase tracking-wide shrink-0">{insight.insight_type.split('_')[0]}</span>
                                                </div>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-tight italic font-medium line-clamp-2">&ldquo;{insight.payload}&rdquo;</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="p-3 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 space-y-1">
                                            <p className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-none">Análisis de Sistema</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-tight italic font-medium">&ldquo;Todos los sistemas operan dentro de los parámetros normales. No se requiere intervención inmediata.&rdquo;</p>
                                        </div>
                                    )}
                                </div>

                                <button className="w-full py-2.5 bg-sky-600 text-white rounded-lg font-bold text-[10px] uppercase tracking-wider shadow-sm active:scale-95 transition-all flex items-center justify-center gap-1.5">
                                    Intervenir con IA <ArrowRight size={10} />
                                </button>
                            </div>
                        </motion.div>

                        {/* Recent Activity Log */}
                        <motion.div variants={itemVariants} className="space-y-3 bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] p-4 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                            <h3 className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1.5 mb-3">
                                <History size={10} /> Actividad del Staff
                            </h3>
                            <div className="space-y-3 relative before:absolute before:left-[15px] before:top-2 before:bottom-2 before:w-[2px] before:bg-[hsl(var(--surface-2))] dark:before:bg-white/5">
                                <LogItem icon={Zap} title="Migración DB completada" user="Alex L." time="10m" color="text-[hsl(var(--primary))]" bg="bg-blue-50 dark:bg-blue-500/10" />
                                <LogItem icon={CheckCircle2} title="Aprobación Curso Teología" user="Pedro M." time="1h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                                <LogItem icon={AlertTriangle} title="Fallo en Pasarela Resuelto" user="System" time="3h" color="text-rose-500" bg="bg-rose-50 dark:bg-rose-500/10" />
                            </div>
                            <button className="w-full mt-2 py-2 text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider hover:text-[hsl(var(--text-secondary))] transition-colors">Ver bitácora completa</button>
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
                    <button className="px-3 py-2 text-[10px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors" onClick={() => setIsDrawerOpen(false)}>Descartar</button>
                    <button className="px-3 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-md active:scale-95 transition-all">Ejecutar Acción</button>
                </>
            }
        >
            <div className="space-y-3 animate-fade-in p-2">
                <section className="grid grid-cols-2 gap-3">
                    <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                        <p className="text-[8px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Estado</p>
                        <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase">{selectedTask?.status}</p>
                    </div>
                    <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5 shadow-sm">
                        <p className="text-[8px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1">Prioridad</p>
                        <p className="text-[13px] font-bold text-rose-500 uppercase">{selectedTask?.priority}</p>
                    </div>
                </section>
                <section className="space-y-3">
                    <h4 className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide flex items-center gap-1.5"><FileText size={10} className="text-[hsl(var(--primary))]"/> Descripción Técnica</h4>
                    <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-md text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium shadow-inner">
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
        <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm relative overflow-hidden group hover:-translate-y-0.5 hover:shadow-md transition-all duration-300 flex flex-col justify-between">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[hsl(var(--surface-2))] dark:from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-bl-full pointer-events-none" />
            <div className="flex items-center justify-between mb-2 relative z-10">
                <div className={clsx("size-10 rounded-md flex items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-black/20 shadow-inner group-hover:scale-105 transition-transform", color)}>
                    <Icon size={10} strokeWidth={2.5} />
                </div>
                <button className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors p-1 rounded-lg"><MoreHorizontal size={10} /></button>
            </div>
            <div className="relative z-10 flex flex-col gap-1">
                <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">{value}</p>
                <div className="flex items-center justify-between">
                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide truncate mr-2">{title}</p>
                    <span className="text-[8px] font-bold px-1.5 py-0.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded flex items-center gap-0.5 shrink-0">
                        <ArrowUpRight size={10} strokeWidth={3} /> {trend}
                    </span>
                </div>
            </div>
        </div>
    );
}

function AdminTaskRow({ task, onOpen, index }: any) {
    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.03, type: 'spring', stiffness: 300, damping: 24 }}
            onClick={() => onOpen(task)}
            className={clsx(
                "p-2.5 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between group hover:border-blue-500/40 hover:shadow-sm shadow-sm transition-all cursor-pointer relative overflow-hidden",
                task.is_special && "border-l-2 border-l-amber-400"
            )}
        >
            <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className={clsx(
                    "size-8 rounded-lg flex items-center justify-center shrink-0 shadow-inner transition-transform duration-300 group-hover:scale-105",
                    task.priority === 'high' ? "bg-rose-50 dark:bg-rose-500/10 text-rose-500" : "bg-[hsl(var(--surface-1))] dark:bg-black/20 text-[hsl(var(--text-secondary))]"
                )}>
                    {task.priority === 'high' ? <Shield size={10} strokeWidth={2.5} /> : <CheckSquare size={10} strokeWidth={2.5} />}
                </div>
                <div className="min-w-0 pr-2">
                    <h4 className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight truncate group-hover:text-[hsl(var(--primary))] transition-colors leading-tight">{task.title}</h4>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] truncate font-medium mt-0.5 leading-tight">{task.description || 'Haz clic para intervenir'}</p>
                </div>
            </div>
            <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-all transform translate-x-2 group-hover:translate-x-0 bg-blue-50 dark:bg-blue-500/10 px-2.5 py-1 rounded-lg">
                <span className="text-[8px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide hidden sm:inline">Revisar</span>
                <ChevronRight size={10} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" strokeWidth={3} />
            </div>
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500 to-sky-600 opacity-0 group-hover:opacity-100 transition-opacity" />
        </motion.div>
    );
}

function LogItem({ icon: Icon, title, user, time, color, bg }: any) {
    return (
        <div className="flex gap-3 relative z-10 group cursor-default">
            <div className={clsx("size-8 rounded-lg flex items-center justify-center shadow-inner shrink-0 transition-transform duration-300 group-hover:scale-105", bg, color)}>
                <Icon size={10} strokeWidth={2.5} />
            </div>
            <div className="flex-1 min-w-0 border-b border-[hsl(var(--border))] dark:border-white/5 pb-3 group-last:border-0 group-last:pb-0">
                <div className="flex justify-between items-center gap-2">
                    <h5 className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate tracking-tight leading-tight">{title}</h5>
                    <span className="text-[8px] font-bold text-[hsl(var(--text-secondary))] whitespace-nowrap bg-[hsl(var(--surface-1))] dark:bg-black/20 px-1.5 py-0.5 rounded uppercase tracking-wide">{time}</span>
                </div>
                <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium leading-tight mt-0.5"><span className="text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] font-bold">{user}</span></p>
            </div>
        </div>
    );
}

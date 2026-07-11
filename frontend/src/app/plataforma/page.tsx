"use client";

import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import {
Activity,
ArrowRight,
ArrowUpRight,
Bell,
BookOpen,
Bot,
Calendar,
CheckCircle2,
ChevronRight,
Clock,
FolderKanban,
MessageSquare,
PlayCircle,
Sparkles,
Star,
Target,
TrendingUp,
Users,
Zap
} from 'lucide-react';
import Link from 'next/link';
import { useEffect,useState } from 'react';

const DASHBOARD_SECTIONS = [
    {
        title: 'Favoritos',
        items: [
            { id: 'dash-home',     label: 'Inicio',        href: '/plataforma',         icon: Sparkles },
            { id: 'dash-tasks',    label: 'Mis Tareas',    href: '/plataforma/tasks',    icon: Target },
            { id: 'dash-calendar', label: 'Calendario',    href: '/plataforma/calendar', icon: Calendar },
        ],
    },
    {
        title: 'Módulos',
        items: [
            { id: 'dash-crm',      label: 'CRM Pastoral', href: '/plataforma/crm',      icon: Users },
            { id: 'dash-academy',  label: 'Academia',      href: '/plataforma/academy',  icon: BookOpen },
            { id: 'dash-projects', label: 'Proyectos',     href: '/plataforma/projects', icon: FolderKanban },
            { id: 'dash-inbox',    label: 'Bandeja',       href: '/plataforma/inbox',    icon: Bell },
        ],
    },
];

export default function PlataformaHome() {
    const { user, token } = useAuth();
    return (
        <WorkspaceLayout sidebarTitle="Panel Principal" sidebarSections={DASHBOARD_SECTIONS}>
            <CommandCenterHome user={user} token={token} />
        </WorkspaceLayout>
    );
}

function CommandCenterHome({ user, token }: any) {
    const [stats, setStats] = useState<any>(null);
    const [tasks, setTasks] = useState<any[]>([]);
    const [insights, setInsights] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                await new Promise(r => setTimeout(r, 400));
                const [metrics, taskData, insightRes] = await Promise.all([
                    apiFetch('/analytics/summary', { token }).catch(() => ({})),
                    apiFetch('/projects/tasks', { token }).catch(() => []),
                    apiFetch<any[]>('/agents/insights', { token }).catch(() => [])
                ]);

                setInsights(Array.isArray(insightRes) ? insightRes : []);

                setStats((metrics as any)?.cards?.length ? metrics : {
                    cards: [
                        { title: 'Personas', value: String((metrics as any)?.total_personas ?? '0'), trend: 'Resumen operativo' },
                        { title: 'Proyectos', value: String((metrics as any)?.total_projects ?? '0'), trend: 'Resumen operativo' },
                        { title: 'Pendientes', value: String((metrics as any)?.pending_agent_tasks ?? '0'), trend: 'Resumen operativo' },
                        { title: 'Testimonios', value: String((metrics as any)?.pending_testimonials ?? '0'), trend: 'Resumen operativo' }
                    ]
                });

                setTasks(Array.isArray(taskData) && taskData.length ? taskData.slice(0, 4) : [
                    { id: 1, title: 'Revisar lección de Fundamentos I', priority: 'high', project: 'Academia' },
                    { id: 2, title: 'Actualizar pipeline de consolidación', priority: 'medium', project: 'CRM' },
                    { id: 3, title: 'Preparar diapositivas de domingo', priority: 'low', project: 'Media' },
                ]);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchDashboardData();
    }, [token]);

    const [greeting, setGreeting] = useState('Hola');

    useEffect(() => {
        const hour = new Date().getHours();
        if (hour < 12) setGreeting('Buenos días');
        else if (hour < 18) setGreeting('Buenas tardes');
        else setGreeting('Buenas noches');
    }, []);

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username || 'Persona';

    const containerVariants = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] dark:bg-transparent overflow-y-auto scrollbar-thin p-3 p-4 font-sans relative">
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="w-full space-y-3 relative z-10"
            >
                {/* 1. Header & Greeting */}
                <motion.header variants={itemVariants} className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">
                            {greeting}, {displayName}
                        </h1>
                        <p className="text-[13px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium mt-1">
                            Este es tu centro de comando. Resumen de actividad reciente.
                        </p>
                    </div>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-lg text-[10px] font-bold uppercase tracking-wide">
                        <Sparkles size={12} /> MESH OS v2.1
                    </div>
                </motion.header>

                {/* 2. Key Metrics */}
                <motion.section variants={itemVariants} className="grid grid-cols-1 md:grid-cols-4 gap-3">
                    {loading ? (
                        [1,2,3,4].map(i => <div key={i} className="h-28 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 animate-pulse" />)
                    ) : (
                        (stats?.cards || []).map((card: any, idx: number) => (
                            <div key={idx} className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-3 shadow-sm hover:shadow-md hover:border-[hsl(var(--border))] dark:hover:border-white/10 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99]">
                                <div className={clsx(
                                    "absolute top-0 left-0 right-0 h-[3px]",
                                    idx === 0 ? "bg-gradient-to-r from-emerald-400 to-emerald-500" :
                                    idx === 1 ? "bg-gradient-to-r from-blue-400 to-blue-500" :
                                    idx === 2 ? "bg-gradient-to-r from-blue-400 to-blue-500" :
                                    "bg-gradient-to-r from-amber-400 to-amber-500"
                                )} />
                                <div className="flex items-center justify-between mb-3 mt-1">
                                    <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{card.title}</p>
                                    <div className="text-[hsl(var(--text-secondary))]">
                                        {idx === 0 && <TrendingUp size={14} />}
                                        {idx === 1 && <FolderKanban size={14} />}
                                        {idx === 2 && <Bell size={14} />}
                                        {idx === 3 && <Zap size={14} />}
                                    </div>
                                </div>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">{card.value}</span>
                                    <span className={clsx(
                                        "text-[10px] font-bold px-1.5 py-0.5 rounded-md flex items-center gap-0.5",
                                        (card.trend || '').includes('-')
                                            ? "bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                            : "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                    )}>
                                        <ArrowUpRight size={10} strokeWidth={3} className={(card.trend || '').includes('-') ? "rotate-90" : ""} /> {card.trend}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </motion.section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    {/* 3. Main Content: Tasks */}
                    <div className="lg:col-span-2 space-y-3">

                        {/* Focus / Tasks */}
                        <motion.div variants={itemVariants} className="space-y-3">
                            <div className="flex items-center justify-between">
                                <h2 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-2">
                                    <Target size={16} className="text-[hsl(var(--primary))]" /> Foco de Hoy
                                </h2>
                                <Link href="/plataforma/projects" className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors flex items-center gap-1">
                                    Ver Agenda <ChevronRight size={12} />
                                </Link>
                            </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {loading ? (
                                    [1,2].map(i => <div key={i} className="h-32 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 animate-pulse" />)
                                ) : tasks.length > 0 ? (
                                    tasks.map((task) => (
                                        <div key={task.id} className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))]/70 dark:border-white/5 rounded-lg shadow-sm hover:shadow-md hover:border-[hsl(var(--border))] dark:hover:border-white/10 transition-all group cursor-pointer flex flex-col justify-between min-h-[140px] active:scale-[0.99]">
                                            <div className="space-y-2.5">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="px-2 py-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded flex text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-fit">
                                                        {task.project || 'General'}
                                                    </div>
                                                    {task.priority === 'high' && (
                                                        <div className="size-5 rounded bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
                                                            <Activity size={10} strokeWidth={3} />
                                                        </div>
                                                    )}
                                                </div>
                                                <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-snug group-hover:text-[hsl(var(--primary))] dark:group-hover:text-[hsl(var(--primary))] transition-colors line-clamp-2">
                                                    {task.title}
                                                </h3>
                                            </div>
                                            <div className="flex items-center justify-between pt-3 mt-3 border-t border-[hsl(var(--border))] dark:border-white/5">
                                                <div className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                                    <Clock size={12} />
                                                    <span className="text-[11px] font-medium">Vence pronto</span>
                                                </div>
                                                <div className="size-6 rounded bg-blue-100 dark:bg-blue-500/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] flex items-center justify-center font-semibold">
                                                    {user?.username ? user.username.substring(0, 2).toUpperCase() : 'ME'}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="col-span-full py-1.5 text-center bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                                        <div className="size-10 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg flex items-center justify-center mx-auto mb-3">
                                            <CheckCircle2 size={16} className="text-emerald-500" />
                                        </div>
                                        <p className="text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] font-semibold text-[13px] mb-1">Todo al día</p>
                                        <p className="text-[hsl(var(--text-secondary))] font-medium text-[12px]">No tienes tareas urgentes pendientes.</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>

                        {/* Academy Progress Banner */}
                        <motion.div variants={itemVariants} className="p-4 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))]/70 dark:border-white/5 shadow-sm relative overflow-hidden flex flex-col sm:flex-row items-center gap-3">
                            <div className="absolute top-0 left-0 w-1.5 h-full bg-[hsl(var(--primary))]" />
                            <div className="flex-1 space-y-3">
                                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 dark:bg-blue-500/10 rounded text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                    <BookOpen size={12} /> Academia
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Fundamentos de la Fe I</h3>
                                    <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-0.5">Módulo 3: La Gracia · 2 lecciones restantes</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="h-1.5 flex-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: '65%' }}
                                            transition={{ duration: 1, delay: 0.2 }}
                                            className="h-full bg-[hsl(var(--primary))] rounded-full"
                                        />
                                    </div>
                                    <span className="font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">65%</span>
                                </div>
                            </div>
                            <Link href="/plataforma/academy" className="shrink-0 px-4 py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg text-[11px] font-bold hover:bg-[hsl(var(--surface-2))] dark:hover:bg-[hsl(var(--surface-2))] active:scale-95 transition-all flex items-center gap-2">
                                Continuar <PlayCircle size={14} />
                            </Link>
                        </motion.div>
                    </div>

                    {/* 4. Right Panel: Intelligence & Activity */}
                    <div className="space-y-3">

                        {/* MESH AI Widget */}
                        <motion.div variants={itemVariants} className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))]/70 dark:border-white/5 rounded-lg shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-2">
                                    <Bot size={16} className="text-[hsl(var(--primary))]" /> MESH AI
                                </h3>
                                <div className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded text-[9px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">
                                    <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                    En línea
                                </div>
                            </div>

                            <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 space-y-2 mb-4">
                                <div className="flex items-center gap-1.5">
                                    <Sparkles size={12} className="text-[hsl(var(--primary))]" />
                                    <span className="text-[9px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide">
                                        {insights.length > 0 ? insights[0].title : 'Insight del día'}
                                    </span>
                                </div>
                                <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium italic">
                                    {insights.length > 0
                                        ? `"${insights[0].payload}"`
                                        : 'Has mantenido un buen ritmo de estudio esta semana. Si dedicas 20 minutos hoy, podrías terminar el módulo.'}
                                </p>
                            </div>

                            <button className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-sky-600 text-white rounded-lg text-[11px] font-bold hover:opacity-90 active:scale-95 transition-all">
                                Consultar <ArrowRight size={12} />
                            </button>
                        </motion.div>

                        {/* Recent Activity */}
                        <motion.div variants={itemVariants} className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))]/70 dark:border-white/5 rounded-lg shadow-sm">
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-4 flex items-center gap-2">
                                <Activity size={12} /> Actividad Reciente
                            </h3>
                            <div className="space-y-4">
                                <ActivityItem icon={CheckCircle2} title="Lección Finalizada" desc="Completaste 'La Naturaleza de Dios'." time="2h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                                <ActivityItem icon={MessageSquare} title="Comentario en Tarea" desc="El líder respondió a tu reporte." time="5h" color="text-[hsl(var(--primary))]" bg="bg-blue-50 dark:bg-blue-500/10" />
                                <ActivityItem icon={Star} title="Nueva Insignia" desc="Alcanzaste 1,000 XP." time="Ayer" color="text-amber-500" bg="bg-amber-50 dark:bg-amber-500/10" />
                            </div>
                        </motion.div>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}

function ActivityItem({ icon: Icon, title, desc, time, color, bg }: any) {
    return (
        <div className="flex gap-4 group cursor-pointer">
            <div className={clsx("size-10 shrink-0 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3", bg, color)}>
                <Icon size={18} strokeWidth={2.5} />
            </div>
            <div className="space-y-0.5 min-w-0 flex-1 border-b border-[hsl(var(--border))] dark:border-white/5 pb-4 group-last:border-0 group-last:pb-0">
                <div className="flex items-center justify-between gap-2">
                    <h4 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{title}</h4>
                    <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] whitespace-nowrap uppercase tracking-wide">{time}</span>
                </div>
                <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] truncate font-medium">{desc}</p>
            </div>
        </div>
    );
}

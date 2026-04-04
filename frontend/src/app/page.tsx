"use client";

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import {
  PlayCircle,
  ChevronRight,
  MessageCircle,
  Users,
  BookOpen,
  Calendar,
  Sparkles,
  ArrowRight,
  Shield,
  Heart,
  Loader2,
  Video,
  ImageIcon,
  CheckCircle2,
  Clock,
  Layout,
  FolderKanban,
  Target,
  Bell,
  Star,
  Zap,
  Bot,
  Feather,
  MessageSquare,
  TrendingUp,
  Activity,
  ArrowUpRight
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Navbar from '@/components/Navbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import Skeleton from '@/components/ui/Skeleton';

const DASHBOARD_SECTIONS = [
    {
        title: 'Favoritos',
        items: [
            { id: 'dash-home',     label: 'Inicio',        href: '/',         icon: Sparkles },
            { id: 'dash-tasks',    label: 'Mis Tareas',    href: '/tasks',    icon: Target },
            { id: 'dash-calendar', label: 'Calendario',    href: '/calendar', icon: Calendar },
        ],
    },
    {
        title: 'Módulos',
        items: [
            { id: 'dash-crm',      label: 'CRM Pastoral', href: '/crm',      icon: Users },
            { id: 'dash-academy',  label: 'Academia',      href: '/academy',  icon: BookOpen },
            { id: 'dash-projects', label: 'Proyectos',     href: '/projects', icon: FolderKanban },
            { id: 'dash-inbox',    label: 'Bandeja',       href: '/inbox',    icon: Bell },
        ],
    },
];

export default function HomeRoot() {
    const { isAuthenticated, user, token } = useAuth();
    const [loading, setLoading] = useState(true);
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
        const t = setTimeout(() => setLoading(false), 600);
        return () => clearTimeout(t);
    }, []);

    // Prevent hydration mismatch: render nothing until client mounts
    if (!isMounted) {
        return <div className="h-screen w-full bg-[#f8fafc] dark:bg-[#0b0d11]" />;
    }

    if (loading && isAuthenticated) {
        return (
            <div className="h-screen w-full bg-[#f8fafc] dark:bg-[#0b0d11] flex flex-col items-center justify-center gap-4">
                <div className="relative">
                    <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                    <Loader2 className="w-8 h-8 animate-spin text-blue-600 relative z-10" />
                </div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Iniciando Ecosistema...</p>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <PublicLandingPage />;
    }

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
                    apiFetch('/dashboard/metrics', { token }).catch(() => ({ cards: [] })),
                    apiFetch('/projects/1/tasks', { token }).catch(() => []),
                    apiFetch<any[]>('/agents/insights', { token }).catch(() => [])
                ]);
                
                setInsights(Array.isArray(insightRes) ? insightRes : []);
                
                setStats((metrics as any)?.cards?.length ? metrics : {
                    cards: [
                        { title: 'Progreso Académico', value: '78%', trend: '+12% este mes' },
                        { title: 'Tareas Activas', value: '14', trend: '3 vencen hoy' },
                        { title: 'Menciones', value: '5', trend: 'Sin leer' },
                        { title: 'Puntos MESH', value: '2,450', trend: '+150 hoy' }
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
        // Client-only: avoids hydration mismatch con new Date()
        const hour = new Date().getHours();
        if (hour < 12) setGreeting('Buenos días');
        else if (hour < 18) setGreeting('Buenas tardes');
        else setGreeting('Buenas noches');
    }, []);

    // Friendly display name: part before @ in username (full_name not in User type)
    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username || 'Miembro';

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
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-y-auto scrollbar-thin p-6 lg:p-10 font-sans relative">
            {/* Ambient Background */}
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-600/5 rounded-full blur-[100px] pointer-events-none" />

            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="max-w-[1600px] mx-auto w-full space-y-10 relative z-10"
            >
                {/* 1. Header & Greeting */}
                <motion.header variants={itemVariants} className="space-y-3">
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-full text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.3em] shadow-sm">
                        <Sparkles size={12} className="animate-pulse" /> MESH OS v2.1
                    </div>
                    <h1 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter">
                        {greeting}, <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">{displayName}</span>.
                    </h1>
                    <p className="text-base text-slate-500 dark:text-slate-400 font-medium max-w-2xl">
                        Este es tu centro de comando. Hemos organizado lo más importante para tu crecimiento y servicio hoy.
                    </p>
                </motion.header>

                {/* 2. Key Metrics - Premium Grid */}
                <motion.section variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                    {loading ? (
                        [1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-200 dark:bg-white/5 rounded-3xl animate-pulse" />)
                    ) : (
                        (stats?.cards || []).map((card: any, idx: number) => (
                            <div key={idx} className="p-6 bg-white dark:bg-[#15171c] rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none group hover:-translate-y-1 hover:shadow-2xl hover:border-blue-500/30 transition-all duration-300 cursor-pointer relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-bl-full" />
                                <div className="flex items-center justify-between mb-4 relative z-10">
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{card.title}</p>
                                    <div className="size-8 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-blue-500 group-hover:bg-blue-50 dark:group-hover:bg-blue-500/10 transition-colors">
                                        {idx === 0 && <TrendingUp size={16} />}
                                        {idx === 1 && <FolderKanban size={16} />}
                                        {idx === 2 && <Bell size={16} />}
                                        {idx === 3 && <Zap size={16} />}
                                    </div>
                                </div>
                                <div className="flex items-end justify-between relative z-10">
                                    <span className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter">{card.value}</span>
                                    <span className="text-[10px] font-bold px-2 py-1 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-lg flex items-center gap-1">
                                        <ArrowUpRight size={10} strokeWidth={3} /> {card.trend}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </motion.section>

                <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                    {/* 3. Main Content: Tasks & Academy */}
                    <div className="xl:col-span-8 space-y-8">
                        
                        {/* Tasks LineUp */}
                        <motion.div variants={itemVariants} className="space-y-5">
                            <div className="flex items-center justify-between px-2">
                                <h2 className="text-lg font-black tracking-tight text-slate-800 dark:text-white flex items-center gap-2">
                                    <Target size={20} className="text-blue-600" /> Foco de Hoy
                                </h2>
                                <Link href="/projects" className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-blue-600 transition-colors flex items-center gap-1 group">
                                    Ver Agenda <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                                </Link>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                {loading ? (
                                    [1,2].map(i => <div key={i} className="h-44 bg-slate-200 dark:bg-white/5 rounded-[2.5rem] animate-pulse" />)
                                ) : tasks.length > 0 ? (
                                    tasks.map((task, i) => (
                                        <div key={task.id} className="p-6 bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 rounded-[2.5rem] shadow-lg shadow-slate-200/20 dark:shadow-none hover:border-blue-500/30 hover:shadow-xl transition-all group cursor-pointer flex flex-col justify-between min-h-[160px]">
                                            <div className="space-y-3">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="px-2.5 py-1 bg-slate-100 dark:bg-white/5 rounded-lg text-[9px] font-black uppercase tracking-widest text-slate-500">
                                                        {task.project || 'General'}
                                                    </div>
                                                    {task.priority === 'high' && (
                                                        <div className="size-6 rounded-full bg-rose-50 dark:bg-rose-500/10 text-rose-500 flex items-center justify-center shrink-0">
                                                            <Activity size={12} strokeWidth={3} />
                                                        </div>
                                                    )}
                                                </div>
                                                <h3 className="text-[15px] font-bold text-slate-800 dark:text-white leading-snug group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                    {task.title}
                                                </h3>
                                            </div>
                                            <div className="flex items-center justify-between pt-4 mt-2 border-t border-slate-100 dark:border-white/5">
                                                <div className="flex items-center gap-1.5 text-slate-400">
                                                    <Clock size={14} />
                                                    <span className="text-[11px] font-bold">Vence pronto</span>
                                                </div>
                                                <div className="flex items-center">
                                                    <div className="size-7 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-[9px] font-black text-white shadow-md border-2 border-white dark:border-[#15171c]">
                                                        {user?.username ? user.username.substring(0, 2).toUpperCase() : 'ME'}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="col-span-full p-12 text-center bg-white dark:bg-[#15171c] border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[2.5rem]">
                                        <div className="size-16 bg-slate-50 dark:bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <CheckCircle2 size={24} className="text-emerald-500" />
                                        </div>
                                        <p className="text-slate-800 dark:text-white font-bold text-sm mb-1">Todo al día</p>
                                        <p className="text-slate-400 font-medium text-xs">No tienes tareas urgentes pendientes.</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>

                        {/* Academy Progress Banner */}
                        <motion.div variants={itemVariants} className="p-8 md:p-10 rounded-[3rem] bg-[#001b48] border border-[#018abd]/30 text-white relative overflow-hidden group shadow-2xl">
                            <div className="absolute top-[-20%] right-[-10%] w-[80%] h-[150%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#018abd]/40 via-[#004581]/10 to-transparent blur-2xl transition-transform duration-700 group-hover:scale-110" />
                            <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-10 mix-blend-overlay" />
                            
                            <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
                                <div className="space-y-5 flex-1 w-full">
                                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-md rounded-xl text-[10px] font-black uppercase tracking-[0.2em] text-blue-200 border border-white/10">
                                        <BookOpen size={14} /> Academia Digital
                                    </div>
                                    <div>
                                        <h3 className="text-3xl md:text-4xl font-black tracking-tight mb-2">Fundamentos de la Fe I</h3>
                                        <p className="text-blue-200/70 text-sm font-medium">Módulo 3: La Gracia · 2 lecciones restantes</p>
                                    </div>
                                    <div className="flex items-center gap-4 w-full max-w-md">
                                        <div className="h-2 flex-1 bg-white/10 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: '65%' }}
                                                transition={{ duration: 1.5, delay: 0.5, ease: "easeOut" }}
                                                className="h-full bg-gradient-to-r from-blue-400 to-[#018abd] shadow-[0_0_15px_rgba(1,138,189,0.8)]"
                                            />
                                        </div>
                                        <span className="text-sm font-black tracking-widest text-blue-100">65%</span>
                                    </div>
                                </div>
                                <Link href="/academy" className="shrink-0 px-8 py-5 bg-white text-[#001b48] rounded-[1.5rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-blue-50 active:scale-95 transition-all shadow-xl shadow-black/20 flex items-center gap-3">
                                    Continuar <PlayCircle size={18} className="fill-[#001b48] text-white" />
                                </Link>
                            </div>
                        </motion.div>
                    </div>

                    {/* 4. Right Panel: Intelligence & Activity */}
                    <motion.aside variants={itemVariants} className="xl:col-span-4 space-y-6">
                        
                        {/* Optimus Brain AI Widget */}
                        <div className="p-8 bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 rounded-[2.5rem] shadow-xl shadow-slate-200/20 dark:shadow-none relative overflow-hidden group">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-bl-[100px] transition-transform duration-500 group-hover:scale-125" />
                            
                            <div className="relative z-10 space-y-6">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-black tracking-tight text-slate-800 dark:text-white flex items-center gap-2">
                                        <Bot size={20} className="text-purple-500" /> MESH AI
                                    </h3>
                                    <div className="flex items-center gap-2 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-1 rounded-lg">
                                        <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                        <span className="text-[8px] font-black text-emerald-600 uppercase tracking-widest">En línea</span>
                                    </div>
                                </div>
                                
                                <div className="p-5 bg-slate-50 dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5 space-y-3">
                                    <div className="flex items-center gap-2">
                                        <Sparkles size={12} className="text-purple-500" />
                                        <span className="text-[9px] font-black text-purple-600 dark:text-purple-400 uppercase tracking-[0.2em]">
                                            {insights.length > 0 ? insights[0].title : 'Insight del día'}
                                        </span>
                                    </div>
                                    <p className="text-[13px] text-slate-600 dark:text-slate-300 font-medium leading-relaxed italic">
                                        {insights.length > 0
                                            ? `"${insights[0].payload}"`
                                            : 'Has mantenido un buen ritmo de estudio esta semana. Si dedicas 20 minutos hoy, podrías terminar el módulo actual antes del fin de semana.'}
                                    </p>
                                </div>

                                <button className="w-full py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] hover:bg-slate-800 dark:hover:bg-slate-100 active:scale-95 transition-all flex items-center justify-center gap-2">
                                    Preguntar a MESH <ArrowRight size={14} />
                                </button>
                            </div>
                        </div>

                        {/* Recent Activity */}
                        <div className="bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 rounded-[2.5rem] p-8 shadow-sm">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 mb-6 flex items-center gap-2">
                                <Activity size={14} /> Feed de Actividad
                            </h3>
                            <div className="space-y-5">
                                <ActivityItem icon={CheckCircle2} title="Lección Finalizada" desc="Completaste 'La Naturaleza de Dios'." time="Hace 2h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                                <ActivityItem icon={MessageSquare} title="Comentario en Tarea" desc="El líder respondió a tu reporte." time="Hace 5h" color="text-blue-500" bg="bg-blue-50 dark:bg-blue-500/10" />
                                <ActivityItem icon={Star} title="Nueva Insignia" desc="Alcanzaste 1,000 XP acumulados." time="Ayer" color="text-amber-500" bg="bg-amber-50 dark:bg-amber-500/10" />
                            </div>
                        </div>
                    </motion.aside>
                </div>
            </motion.div>
        </div>
    );
}

function ActivityItem({ icon: Icon, title, desc, time, color, bg }: any) {
    return (
        <div className="flex gap-4 group cursor-pointer">
            <div className={clsx("size-10 shrink-0 rounded-2xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3", bg, color)}>
                <Icon size={18} strokeWidth={2.5} />
            </div>
            <div className="space-y-0.5 min-w-0 flex-1 border-b border-slate-50 dark:border-white/5 pb-4 group-last:border-0 group-last:pb-0">
                <div className="flex items-center justify-between gap-2">
                    <h4 className="text-[13px] font-bold text-slate-800 dark:text-white truncate">{title}</h4>
                    <span className="text-[9px] font-black text-slate-400 whitespace-nowrap uppercase tracking-widest">{time}</span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate font-medium">{desc}</p>
            </div>
        </div>
    );
}

// Keep the PublicLandingPage component for unauthenticated users
function PublicLandingPage() {
    const linkCards = [
        {
            title: 'Página Web',
            description: 'Explora la experiencia pública y descubre testimonios, eventos y convocatorias.',
            href: '/faro',
            label: 'Ir al sitio',
            icon: Layout
        },
        {
            title: 'CMS de Contenido',
            description: 'Administra landing, hero y testimonios con un hub curado para comunicación.',
            href: '/cms',
            label: 'Entrar al CMS',
            icon: Feather
        },
        {
            title: 'Plataforma Pastoral',
            description: 'Accede a CRM, Academia y módulos operativos de la comunidad.',
            href: '/login',
            label: 'Ir a la plataforma',
            icon: Shield
        }
    ];

    return (
        <div className="min-h-screen bg-[#020617] text-slate-200 flex flex-col items-center p-6 lg:p-10 gap-10 font-sans relative overflow-hidden">
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/10 blur-[120px] animate-pulse-soft"></div>
            </div>
            <Navbar />
            <div className="max-w-4xl w-full space-y-8 text-center relative z-10 mt-10">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-full text-[10px] font-black uppercase tracking-[0.3em] mx-auto shadow-lg shadow-blue-500/5">
                    <Shield size={14} /> MESH Ecosystem v2.1
                </div>
                <h1 className="text-5xl lg:text-7xl font-black text-white tracking-tighter leading-[1.1]">
                    Identidad Digital <br /> <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">Ministerial.</span>
                </h1>
                <p className="text-lg text-slate-400 font-medium max-w-2xl mx-auto">El centro operativo para la formación teológica, gestión pastoral y colaboración de equipos.</p>
                <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
                    <Link href="/login" className="px-10 py-5 bg-blue-600 text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-blue-600/20 hover:bg-blue-500 active:scale-95 transition-all flex items-center justify-center gap-2">
                        Acceso Interno <ArrowRight size={16} />
                    </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 text-left">
                    {linkCards.map((card) => (
                        <Link
                            key={card.href}
                            href={card.href}
                            className="p-8 rounded-[2rem] bg-white/5 border border-white/10 hover:border-blue-500/50 hover:bg-white/10 transition-all group"
                        >
                            <div className="size-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-400 mb-6 group-hover:scale-110 transition-transform">
                                <card.icon size={24} />
                            </div>
                            <h3 className="text-xl font-black text-white mb-2">{card.title}</h3>
                            <p className="text-sm text-slate-400 leading-relaxed mb-6">{card.description}</p>
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-blue-400">
                                {card.label} <ChevronRight size={14} />
                            </div>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}

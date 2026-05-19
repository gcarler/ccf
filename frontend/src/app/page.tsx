"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  PlayCircle,
  ChevronRight,
  Users,
  BookOpen,
  Calendar,
  Sparkles,
  ArrowRight,
  Shield,
  Loader2,
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
import { motion } from 'framer-motion';
import clsx from 'clsx';
import Navbar from '@/components/Navbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';


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
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
        const t = setTimeout(() => setLoading(false), 600);
        return () => clearTimeout(t);
    }, []);

    useEffect(() => {
        if (!isMounted) return;
        if (isAuthenticated) {
            router.replace('/mi-vista');
        }
    }, [isAuthenticated, isMounted, router]);

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

    if (isAuthenticated) {
        return (
            <div className="h-screen w-full bg-[#f8fafc] dark:bg-[#0b0d11] flex flex-col items-center justify-center gap-4">
                <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
                <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">Abriendo Mi Vista...</p>
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
                const [taskData, insightRes] = await Promise.all([
                    apiFetch('/projects/tasks', { token }).catch(() => []),
                    apiFetch<any[]>('/agents/insights', { token }).catch(() => [])
                ]);
                
                setInsights(Array.isArray(insightRes) ? insightRes : []);
                setStats(null);
                setTasks(Array.isArray(taskData) ? taskData.slice(0, 4) : []);
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
        <div className="flex flex-col h-full bg-slate-50 dark:bg-transparent overflow-y-auto scrollbar-thin p-6 lg:p-8 font-sans relative">
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="show"
                className="max-w-[1600px] w-full space-y-8 relative z-10"
            >
                {/* 1. Header & Greeting */}
                <motion.header variants={itemVariants} className="flex items-start justify-between gap-4">
                    <div>
                        <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
                            {greeting}, {displayName}
                        </h1>
                        <p className="text-[13px] text-slate-500 dark:text-slate-400 font-medium mt-1">
                            Este es tu centro de comando. Resumen de actividad reciente.
                        </p>
                    </div>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-lg text-[10px] font-black uppercase tracking-widest">
                        <Sparkles size={12} /> MESH OS v2.1
                    </div>
                </motion.header>

                {/* 2. Key Metrics */}
                <motion.section variants={itemVariants} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {loading ? (
                        [1,2,3,4].map(i => <div key={i} className="h-28 bg-white dark:bg-[#252528] rounded-2xl border border-slate-100 dark:border-white/5 animate-pulse" />)
                    ) : !(stats?.cards?.length) ? (
                        <div className="md:col-span-4 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 bg-white dark:bg-[#252528] p-6 text-center">
                            <p className="text-xs font-black uppercase tracking-widest text-slate-400">Sin metricas disponibles</p>
                        </div>
                    ) : (
                        (stats?.cards || []).map((card: any, idx: number) => (
                            <div key={idx} className="group relative bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-5 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-white/10 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99]">
                                {/* Top accent bar */}
                                <div className={clsx(
                                    "absolute top-0 left-0 right-0 h-[3px]",
                                    idx === 0 ? "bg-gradient-to-r from-emerald-400 to-emerald-500" :
                                    idx === 1 ? "bg-gradient-to-r from-blue-400 to-blue-500" :
                                    idx === 2 ? "bg-gradient-to-r from-blue-400 to-blue-500" :
                                    "bg-gradient-to-r from-amber-400 to-amber-500"
                                )} />
                                <div className="flex items-center justify-between mb-3 mt-1">
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.15em]">{card.title}</p>
                                    <div className="text-slate-400">
                                        {idx === 0 && <TrendingUp size={14} />}
                                        {idx === 1 && <FolderKanban size={14} />}
                                        {idx === 2 && <Bell size={14} />}
                                        {idx === 3 && <Zap size={14} />}
                                    </div>
                                </div>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-2xl font-bold text-slate-900 dark:text-white tracking-tighter">{card.value}</span>
                                    <span className={clsx(
                                        "text-[10px] font-bold px-1.5 py-0.5 rounded-md flex items-center gap-0.5",
                                        card.trend.includes('-') 
                                            ? "bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400"
                                            : "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                    )}>
                                        <ArrowUpRight size={10} strokeWidth={3} className={card.trend.includes('-') ? "rotate-90" : ""} /> {card.trend}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </motion.section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* 3. Main Content: Tasks */}
                    <div className="lg:col-span-2 space-y-6">
                        
                        {/* Focus / Tasks */}
                        <motion.div variants={itemVariants} className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-[13px] font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                                    <Target size={16} className="text-blue-500" /> Foco de Hoy
                                </h2>
                                <Link href="/projects" className="text-[10px] font-black uppercase tracking-[0.15em] text-blue-600 hover:text-blue-700 transition-colors flex items-center gap-1">
                                    Ver proyectos <ChevronRight size={12} />
                                </Link>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {loading ? (
                                    [1,2].map(i => <div key={i} className="h-32 bg-white dark:bg-[#252528] rounded-2xl border border-slate-100 dark:border-white/5 animate-pulse" />)
                                ) : tasks.length > 0 ? (
                                    tasks.map((task) => (
                                        <div key={task.id} className="p-5 bg-white dark:bg-[#252528] border border-slate-200/70 dark:border-white/5 rounded-2xl shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-white/10 transition-all group cursor-pointer flex flex-col justify-between min-h-[140px] active:scale-[0.99]">
                                            <div className="space-y-2.5">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="px-2 py-0.5 bg-slate-100 dark:bg-white/5 rounded flex text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400 max-w-fit">
                                                        {task.project || 'General'}
                                                    </div>
                                                    {task.priority === 'high' && (
                                                        <div className="size-5 rounded bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
                                                            <Activity size={10} strokeWidth={3} />
                                                        </div>
                                                    )}
                                                </div>
                                                <h3 className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 leading-snug group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
                                                    {task.title}
                                                </h3>
                                            </div>
                                            <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100 dark:border-white/5">
                                                <div className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500">
                                                    <Clock size={12} />
                                                    <span className="text-[11px] font-medium">Vence pronto</span>
                                                </div>
                                                <div className="size-6 rounded bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 flex items-center justify-center text-[9px] font-black">
                                                    {user?.username ? user.username.substring(0, 2).toUpperCase() : 'ME'}
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="col-span-full py-10 text-center bg-white dark:bg-[#252528] border border-dashed border-slate-200 dark:border-white/10 rounded-2xl">
                                        <div className="size-10 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                                            <CheckCircle2 size={16} className="text-emerald-500" />
                                        </div>
                                        <p className="text-slate-800 dark:text-slate-200 font-semibold text-[13px] mb-1">Sin tareas disponibles</p>
                                        <p className="text-slate-400 font-medium text-[12px]">Aen no hay tareas cargadas desde el backend.</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>

                        {/* Academy Progress Banner */}
                        <motion.div variants={itemVariants} className="p-6 rounded-2xl bg-white dark:bg-[#252528] border border-slate-200/70 dark:border-white/5 shadow-sm relative overflow-hidden flex flex-col sm:flex-row items-center gap-6">
                            <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500" />
                            <div className="flex-1 space-y-3">
                                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 dark:bg-blue-500/10 rounded text-[10px] font-black uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400">
                                    <BookOpen size={12} /> Academia
                                </div>
                                <div>
                                    <h3 className="text-[15px] font-bold text-slate-800 dark:text-white">Fundamentos de la Fe I</h3>
                                    <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-0.5">Módulo 3: La Gracia · 2 lecciones restantes</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="h-1.5 flex-1 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: '65%' }}
                                            transition={{ duration: 1, delay: 0.2 }}
                                            className="h-full bg-blue-500 rounded-full"
                                        />
                                    </div>
                                    <span className="text-[11px] font-black text-slate-600 dark:text-slate-300">65%</span>
                                </div>
                            </div>
                            <Link href="/academy" className="shrink-0 px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg text-[11px] font-bold hover:bg-slate-800 dark:hover:bg-slate-100 active:scale-95 transition-all flex items-center gap-2">
                                Continuar <PlayCircle size={14} />
                            </Link>
                        </motion.div>
                    </div>

                    {/* 4. Right Panel: Intelligence & Activity */}
                    <div className="space-y-6">
                        
                        {/* MESH AI Widget */}
                        <motion.div variants={itemVariants} className="p-5 bg-white dark:bg-[#252528] border border-slate-200/70 dark:border-white/5 rounded-2xl shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-[13px] font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                                    <Bot size={16} className="text-blue-500" /> MESH AI
                                </h3>
                                <div className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">
                                    <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                    En línea
                                </div>
                            </div>
                            
                            <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-xl border border-slate-100 dark:border-white/5 space-y-2 mb-4">
                                <div className="flex items-center gap-1.5">
                                    <Sparkles size={12} className="text-blue-500" />
                                    <span className="text-[9px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.15em]">
                                        {insights.length > 0 ? insights[0].title : 'Insight del día'}
                                    </span>
                                </div>
                                <p className="text-[12px] text-slate-600 dark:text-slate-300 font-medium italic">
                                    {insights.length > 0
                                        ? `"${insights[0].payload}"`
                                        : 'Has mantenido un buen ritmo de estudio esta semana. Si dedicas 20 minutos hoy, podrías terminar el módulo.'}
                                </p>
                            </div>

                            <button className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg text-[11px] font-bold hover:opacity-90 active:scale-95 transition-all">
                                Consultar <ArrowRight size={12} />
                            </button>
                        </motion.div>

                        {/* Recent Activity */}
                        <motion.div variants={itemVariants} className="p-5 bg-white dark:bg-[#252528] border border-slate-200/70 dark:border-white/5 rounded-2xl shadow-sm">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 dark:text-slate-500 mb-4 flex items-center gap-2">
                                <Activity size={12} /> Actividad Reciente
                            </h3>
                            <div className="space-y-4">
                                <ActivityItem icon={CheckCircle2} title="Lección Finalizada" desc="Completaste 'La Naturaleza de Dios'." time="2h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                                <ActivityItem icon={MessageSquare} title="Comentario en Tarea" desc="El líder respondió a tu reporte." time="5h" color="text-blue-500" bg="bg-blue-50 dark:bg-blue-500/10" />
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
            description: 'Explora la experiencia pública y descubre testimonios, eventos y ministerios.',
            href: '/faro',
            label: 'Ir al sitio',
            icon: Layout,
            color: 'text-blue-600 dark:text-blue-400',
            bg: 'bg-blue-50 dark:bg-blue-500/10'
        },
        {
            title: 'CMS de Contenido',
            description: 'Administra landing, hero y testimonios con un hub curado para comunicación.',
            href: '/cms',
            label: 'Entrar al CMS',
            icon: Feather,
            color: 'text-blue-600 dark:text-blue-400',
            bg: 'bg-blue-50 dark:bg-blue-500/10'
        },
        {
            title: 'Plataforma Pastoral',
            description: 'Accede a CRM, Academia y módulos operativos de la comunidad.',
            href: '/login',
            label: 'Ir a la plataforma',
            icon: Shield,
            color: 'text-emerald-600 dark:text-emerald-400',
            bg: 'bg-emerald-50 dark:bg-emerald-500/10'
        }
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-[#1E1F21] flex flex-col items-center justify-center p-6 lg:p-10 gap-10 font-sans relative overflow-hidden transition-colors duration-300">
            {/* Background elements (Clean Productivity style) */}
            <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
                <div className="absolute top-[-10%] right-[-5%] w-[40%] h-[40%] rounded-full bg-blue-500/5 dark:bg-blue-500/10 blur-[100px]"></div>
                <div className="absolute bottom-[-10%] left-[-5%] w-[40%] h-[40%] rounded-full bg-blue-500/5 dark:bg-blue-500/10 blur-[100px]"></div>
            </div>
            
            <Navbar />
            
            <div className="max-w-5xl w-full space-y-10 text-center relative z-10 mt-16 md:mt-10">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="space-y-6"
                >
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-black uppercase tracking-widest mx-auto shadow-sm">
                        <Sparkles size={12} /> MESH Ecosystem v2.1
                    </div>
                    
                    <h1 className="text-4xl md:text-6xl lg:text-7xl font-black text-slate-900 dark:text-white tracking-tighter leading-[1.1] max-w-4xl mx-auto">
                        Identidad Digital <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                            Ministerial.
                        </span>
                    </h1>
                    
                    <p className="text-base md:text-lg text-slate-500 dark:text-slate-400 font-medium max-w-2xl mx-auto leading-relaxed">
                        El centro operativo para la formación teológica, gestión pastoral y colaboración de equipos.
                    </p>
                </motion.div>

                <motion.div 
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-10 text-left"
                >
                    {linkCards.map((card) => (
                        <Link
                            key={card.href}
                            href={card.href}
                            className="group relative bg-white dark:bg-[#252528] rounded-3xl border border-slate-200/70 dark:border-white/5 p-8 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden flex flex-col"
                        >
                            <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-slate-200 to-slate-100 dark:from-white/10 dark:to-transparent group-hover:from-blue-500 group-hover:to-indigo-500 transition-colors" />
                            
                            <div className={`size-14 rounded-2xl ${card.bg} flex items-center justify-center ${card.color} mb-8 group-hover:scale-110 group-hover:-rotate-3 transition-transform duration-300`}>
                                <card.icon size={26} strokeWidth={2.5} />
                            </div>
                            
                            <h3 className="text-xl font-black text-slate-900 dark:text-white mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                {card.title}
                            </h3>
                            
                            <p className="text-[13px] text-slate-500 dark:text-slate-400 leading-relaxed font-medium flex-1 mb-8">
                                {card.description}
                            </p>
                            
                            <div className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors mt-auto">
                                {card.label} <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                            </div>
                        </Link>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}



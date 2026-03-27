"use client";

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
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
  MessageSquare } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Navbar from '@/components/Navbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import Skeleton from '@/components/ui/Skeleton';

export default function HomeRoot() {
    const { isAuthenticated, user, token } = useAuth();
    const [loading, setLoading] = useState(true);

    if (loading && isAuthenticated) {
        // Simple loading check to avoid flicker
        setTimeout(() => setLoading(false), 500);
        return <div className="h-screen bg-[#1e1f21] flex items-center justify-center"><Loader2 className="animate-spin text-blue-500" /></div>;
    }

    if (!isAuthenticated) {
        return <PublicLandingPage />;
    }

    return (
        <WorkspaceLayout sidebarTitle="Mi Panel / Inicio">
            <CommandCenterHome user={user} token={token} />
        </WorkspaceLayout>
    );
}

function CommandCenterHome({ user, token }: any) {
    const [stats, setStats] = useState<any>(null);
    const [tasks, setTasks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                const [metrics, taskData] = await Promise.all([
                    apiFetch('/dashboard/metrics', { token }),
                    apiFetch('/projects/1/tasks', { token }) // Using project 1 as default
                ]);
                setStats(metrics);
                setTasks(Array.isArray(taskData) ? taskData.slice(0, 4) : []);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchDashboardData();
    }, [token]);

    const greeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return "Buenos días";
        if (hour < 18) return "Buenas tardes";
        return "Buenas noches";
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-y-auto scrollbar-thin p-6 lg:p-10 space-y-10 animate-fade-in">
            {/* 1. Header & Greeting */}
            <header className="space-y-2">
                <div className="flex items-center gap-2 text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.3em]">
                    <Sparkles size={14} /> Centro de Comando CCF 3.0
                </div>
                <h1 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter">
                    {greeting()}, <span className="text-blue-600">{user?.username}</span>.
                </h1>
                <p className="text-lg text-slate-500 dark:text-slate-400 font-medium">Aquí tienes un resumen de lo que requiere tu atención hoy.</p>
            </header>

            {/* 2. Key Metrics - High Impact Grid */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {loading ? (
                    [1,2,3,4].map(i => <Skeleton key={i} className="h-28 rounded-[2rem]" />)
                ) : (
                    (stats?.cards || []).map((card: any, idx: number) => (
                        <div key={idx} className="p-6 bg-slate-50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/5 shadow-sm group hover:shadow-xl transition-all cursor-pointer">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">{card.title}</p>
                            <div className="flex items-end justify-between">
                                <span className="text-3xl font-black text-slate-800 dark:text-white tracking-tighter">{card.value}</span>
                                <span className="text-[10px] font-black px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 rounded-lg">{card.trend}</span>
                            </div>
                        </div>
                    ))
                )}
            </section>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                {/* 3. LineUp - Priority Tasks */}
                <div className="xl:col-span-8 space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-xl font-black tracking-tight flex items-center gap-2">
                            <FolderKanban size={20} className="text-blue-600" /> Mi Agenda
                        </h2>
                        <Link href="/projects" className="text-[11px] font-black uppercase text-blue-600 hover:underline">Ver todo</Link>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {loading ? (
                            [1,2].map(i => <Skeleton key={i} className="h-40 rounded-[2.5rem]" />)
                        ) : tasks.length > 0 ? (
                            tasks.map(task => (
                                <div key={task.id} className="p-6 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-2xl hover:border-blue-500/30 transition-all group relative overflow-hidden">
                                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2" />
                                    <div className="relative z-10 space-y-4">
                                        <div className="flex items-center justify-between">
                                            <div className="px-2 py-0.5 bg-slate-100 dark:bg-white/10 rounded text-[8px] font-black uppercase tracking-widest text-slate-500">PROYECTO 1</div>
                                            {task.priority === 'high' && <div className="p-1 rounded-md bg-rose-50 text-rose-500"><Target size={14} /></div>}
                                        </div>
                                        <h3 className="text-lg font-bold text-slate-800 dark:text-white leading-tight line-clamp-2">{task.title}</h3>
                                        <div className="flex items-center justify-between pt-4 border-t border-slate-50 dark:border-white/5">
                                            <div className="flex items-center gap-2 text-slate-400">
                                                <Clock size={12} />
                                                <span className="text-[10px] font-bold">Mañana</span>
                                            </div>
                                            <div className="size-6 rounded-full bg-blue-600 flex items-center justify-center text-[8px] font-black text-white uppercase">JD</div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="col-span-full p-12 text-center border-2 border-dashed border-slate-100 dark:border-white/5 rounded-[2.5rem]">
                                <p className="text-slate-400 font-bold uppercase text-[10px] tracking-widest">No tienes tareas pendientes.</p>
                            </div>
                        )}
                    </div>

                    {/* 4. Academy Progress */}
                    <div className="p-8 rounded-[3rem] bg-gradient-to-br from-slate-900 to-[#1e1f21] border border-white/5 text-white relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-[100px] transition-transform group-hover:scale-110" />
                        <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                            <div className="space-y-4">
                                <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest text-blue-400">
                                    <BookOpen size={14} /> Sigue aprendiendo
                                </div>
                                <h3 className="text-3xl font-black tracking-tight">Fundamentos de la Fe I</h3>
                                <div className="flex items-center gap-4">
                                    <div className="w-48 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                        <div className="h-full w-[65%] bg-blue-500 shadow-[0_0_15px_rgba(37,99,235,0.5)]" />
                                    </div>
                                    <span className="text-sm font-black tracking-widest">65%</span>
                                </div>
                            </div>
                            <Link href="/academy" className="px-8 py-4 bg-white text-slate-900 rounded-2xl font-black text-xs uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-xl">
                                Continuar Clase
                            </Link>
                        </div>
                    </div>
                </div>

                {/* 5. Right Panel: Activity & AI */}
                <aside className="xl:col-span-4 space-y-8">
                    <div className="p-8 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[2.5rem] space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-black tracking-tight flex items-center gap-2">
                                <Bot size={20} className="text-purple-500" /> Optimus Brain
                            </h3>
                            <div className="animate-pulse size-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                        </div>
                        <div className="p-5 bg-white dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                            <div className="px-2 py-0.5 bg-purple-50 dark:bg-purple-900/30 text-purple-600 text-[8px] font-black uppercase rounded w-fit">Insight Académico</div>
                            <p className="text-sm text-slate-600 dark:text-slate-300 italic font-medium leading-relaxed">
                                &ldquo;Has completado el 80% de tus tareas esta semana. ¡Vas por buen camino para certificar Fundamentos I!&rdquo;
                            </p>
                        </div>
                        <button className="w-full py-4 bg-purple-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-lg shadow-purple-500/20 active:scale-95 transition-all">
                            Consultar con la IA
                        </button>
                    </div>

                    <div className="space-y-6">
                        <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 px-2 flex items-center justify-between">
                            Actividad Reciente <History size={14} />
                        </h3>
                        <div className="space-y-4">
                            <ActivityItem icon={CheckCircle2} title="Tarea Completada" desc="Finalizaste 'Diseño UI' en Proyectos." time="Hace 2h" color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-900/20" />
                            <ActivityItem icon={MessageSquare} title="Nueva Mención" desc="Juan te mencionó en un comentario." time="Hace 5h" color="text-blue-500" bg="bg-blue-50 dark:bg-blue-900/20" />
                            <ActivityItem icon={Star} title="Logro Obtenido" desc="5 días seguidos en la Academia." time="Ayer" color="text-amber-500" bg="bg-amber-50 dark:bg-amber-900/20" />
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}

function ActivityItem({ icon: Icon, title, desc, time, color, bg }: any) {
    return (
        <div className="flex gap-4 group cursor-pointer">
            <div className={clsx("size-10 shrink-0 rounded-xl flex items-center justify-center transition-all group-hover:scale-110", bg, color)}>
                <Icon size={18} />
            </div>
            <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-2">
                    <h4 className="text-[13px] font-bold text-slate-700 dark:text-white truncate">{title}</h4>
                    <span className="text-[9px] font-black text-slate-400 whitespace-nowrap">{time}</span>
                </div>
                <p className="text-[12px] text-slate-500 dark:text-slate-400 truncate font-medium">{desc}</p>
            </div>
        </div>
    );
}

function History({ size, className }: any) { return <Clock size={size} className={className} />; }

function PublicLandingPage() {
    const linkCards = [
        {
            title: 'Página Web',
            description: 'Explora la experiencia pública y descubre testimonios, eventos y convocatorias.',
            href: '/',
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
        <div className="min-h-screen bg-[#07090d] text-slate-200 flex flex-col items-center p-10 gap-10">
            <Navbar />
            <div className="max-w-4xl w-full space-y-8 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-primary/10 text-primary rounded-full text-xs font-black uppercase tracking-widest animate-pulse mx-auto">
                    <Shield size={16} /> Plataforma Oficial CCF
                </div>
                <h1 className="text-6xl lg:text-7xl font-black text-white tracking-tight leading-[0.9]">Transformando vidas con propósito.</h1>
                <p className="text-xl text-slate-400 font-medium">Únete a nuestra academia teológica y gestiona tu crecimiento espiritual en un solo lugar.</p>
                <div className="flex justify-center gap-4 pt-2">
                    <Link href="/login" className="px-10 py-5 bg-primary text-white rounded-2xl font-black uppercase tracking-widest shadow-2xl shadow-primary/40 hover:scale-105 active:scale-95 transition-all">Ingresar al Portal</Link>
                    <Link href="/register" className="px-10 py-5 bg-white/5 border border-white/10 text-white rounded-2xl font-black uppercase tracking-widest hover:bg-white/10 transition-all">Crear Cuenta</Link>
                </div>
            </div>

            <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-4">
                {linkCards.map(({ title, description, href, label, icon: Icon }) => (
                    <Link
                        key={title}
                        href={href}
                        className="rounded-[2rem] border border-white/10 bg-white/5 hover:bg-primary/10 transition-all p-6 text-left space-y-4"
                    >
                        <div className="flex items-center gap-3 text-primary">
                            <div className="size-10 rounded-xl bg-primary/20 flex items-center justify-center">
                                <Icon size={20} />
                            </div>
                            <span className="text-xs font-black uppercase tracking-[0.35em]">Acceso</span>
                        </div>
                        <h3 className="text-xl font-black text-white">{title}</h3>
                        <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
                        <span className="inline-flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-[0.35em]">
                            {label} <ArrowRight size={14} />
                        </span>
                    </Link>
                ))}
            </div>
        </div>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import CourseCatalog from '@/components/CourseCatalog';
import MyEnrollments from '@/components/MyEnrollments';
import {
    Sparkles, BookOpen, Target, ArrowRight, Search, Filter,
    BarChart3, Star, Flame, Calendar, Rocket, ShieldCheck, ChevronRight, Award, PlayCircle, GraduationCap
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useContentBlocks } from '@/hooks/useContent';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { DSToolbarChip, DSSectionHeader } from '@/design';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { useRouter } from 'next/navigation';
import { useGraphInsights } from '@/hooks/useGraphInsights';

interface AcademyClientProps {
    initialCourses: any[];
    initialEnrollments: any[];
}

export default function AcademyClient({ initialCourses, initialEnrollments }: AcademyClientProps) {
    const { user, token, isAuthenticated } = useAuth();
    const router = useRouter();
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [enrolledCourseIds, setEnrolledCourseIds] = useState<number[]>(() => (initialEnrollments || []).map((e: any) => e.course?.id).filter(Boolean));
    const [loading, setLoading] = useState(initialEnrollments.length === 0);
    const [aiInsights, setAiInsights] = useState<any[]>([]);
    const { data: pageContents } = useContentBlocks(['academy_hero', 'academy_welcome_sub']);
    const { insights: graphInsights } = useGraphInsights({ types: ['course'], limit: 4, enabled: isAuthenticated });

    useEffect(() => {
        const fetchData = async () => {
            if (!isAuthenticated || !user) return;
            try {
                // Slight delay for smooth animation
                await new Promise(r => setTimeout(r, 400));
                const [enrRes, aiRes] = await Promise.all([
                    apiFetch(`/academy/users/${user.id}/enrollments`, { token, cache: 'no-store' }),
                    apiFetch<any[]>('/agents/insights', { token }).catch(() => [])
                ]);
                
                if (Array.isArray(enrRes)) setEnrolledCourseIds(enrRes.map((e: any) => e.course.id));
                setAiInsights(Array.isArray(aiRes) ? aiRes.filter(i => i.insight_type === 'academy_insight') : []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        if (!initialEnrollments.length) {
            fetchData();
        } else {
            // Still fetch AI insights even if enrollments are initial
            apiFetch<any[]>('/agents/insights', { token })
                .then(res => setAiInsights(Array.isArray(res) ? res.filter(i => i.insight_type === 'academy_insight') : []))
                .catch(() => {});
            setLoading(false);
        }
    }, [user, token, isAuthenticated, initialEnrollments.length]);

    useRegisterCommands('academy-dashboard', [
        { id: 'academy-curriculum', label: 'Abrir plan de estudio', description: 'Explora tu ruta curricular', group: 'Academia', action: () => router.push('/academy/curriculum') },
        { id: 'academy-certificates', label: 'Ver certificados', description: 'Diplomas y reconocimientos', group: 'Academia', action: () => router.push('/academy/certificates') },
    ]);

    if (!isAuthenticated) return null;

    if (loading && enrolledCourseIds.length === 0) {
        return (
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden items-center justify-center space-y-4">
                <div className="relative">
                    <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse" />
                    <BookOpen className="w-8 h-8 animate-pulse text-blue-600 relative z-10" />
                </div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Cargando Academia...</p>
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
                breadcrumbs={[{ label: 'Academia Digital', icon: GraduationCap }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'table']}
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
                    {/* Hero Section Premium */}
                    <motion.section variants={itemVariants} className="relative w-full rounded-[3.5rem] shadow-2xl group border border-white/10 overflow-hidden bg-[#001b48]">
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.05] mix-blend-overlay" />
                        <div className="absolute top-[-50%] right-[-10%] w-[80%] h-[200%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#018abd]/30 via-[#004581]/10 to-transparent blur-3xl transition-transform duration-1000 group-hover:scale-110 pointer-events-none" />
                        
                        <div className="relative h-full flex flex-col md:flex-row items-center justify-between p-12 lg:p-16 gap-10">
                            <div className="space-y-6 max-w-2xl">
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                                    className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl rounded-full text-[10px] font-black uppercase tracking-[0.3em] text-blue-100 border border-white/20 shadow-inner"
                                >
                                    <Sparkles size={14} className="text-amber-400" /> {pageContents.academy_welcome_sub?.title || 'Ruta de Crecimiento Espiritual'}
                                </motion.div>
                                
                                <div>
                                    <h2 className="text-5xl lg:text-7xl font-black text-white tracking-tighter leading-[0.95] mb-4">
                                        Forjando <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-300 to-[#018abd]">Carácter.</span>
                                    </h2>
                                    <p className="text-blue-100/70 text-lg font-medium leading-relaxed">
                                        {pageContents.academy_hero?.content || `Hola, ${user?.username}. Estás a un paso de completar tu próximo nivel. Continúa aprendiendo y descubre el propósito que Dios tiene para ti.`}
                                    </p>
                                </div>

                                <div className="flex items-center gap-4 pt-4">
                                    <button className="px-8 py-5 bg-white text-[#001b48] rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-blue-50 active:scale-95 transition-all shadow-xl flex items-center gap-3">
                                        Ir al curso actual <PlayCircle size={18} className="fill-[#001b48] text-white" />
                                    </button>
                                    <button className="px-8 py-5 bg-white/10 text-white border border-white/20 rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] hover:bg-white/20 active:scale-95 transition-all">
                                        Ver Pénsum
                                    </button>
                                </div>
                            </div>

                            {/* Hero Stats */}
                            <div className="hidden lg:flex flex-col gap-4">
                                <HeroStat label="Puntos MESH" value="2,450" icon={Star} color="text-amber-400" bg="bg-amber-400/20" />
                                <HeroStat label="Racha Actual" value="12 Días" icon={Flame} color="text-rose-400" bg="bg-rose-400/20" />
                            </div>
                        </div>
                    </motion.section>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        {/* Main Content Area */}
                        <div className="lg:col-span-8 space-y-10">
                            
                            {/* Enrollments Section */}
                            <motion.section variants={itemVariants} className="space-y-6">
                                <DSSectionHeader
                                    eyebrow="Tus Estudios"
                                    title="Cursos Activos"
                                    description="Retoma tus lecciones donde las dejaste."
                                    actions={
                                        <div className="flex gap-2">
                                            {['Recientes', 'Completados'].map((chip) => (
                                                <DSToolbarChip key={chip} label={chip} size="sm" active={chip === 'Recientes'} />
                                            ))}
                                        </div>
                                    }
                                />
                                <div className="bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 p-4 shadow-xl shadow-slate-200/20 dark:shadow-none">
                                    <MyEnrollments
                                        userId={user?.id || 0}
                                        token={token || ''}
                                        initialEnrollments={initialEnrollments}
                                    />
                                </div>
                            </motion.section>

                            {/* Catalog Section */}
                            <motion.section variants={itemVariants} className="bg-slate-50/50 dark:bg-white/5 rounded-[3.5rem] border border-slate-100 dark:border-white/10 p-8 md:p-12 shadow-inner relative overflow-hidden group">
                                <DSSectionHeader
                                    title="Catálogo Formativo"
                                    description="Explora nuevas rutas y profundiza en la Palabra."
                                    actions={
                                        <div className="flex items-center gap-2 bg-white dark:bg-[#15171c] p-2 rounded-[1.5rem] border border-slate-200 dark:border-white/10 shadow-sm">
                                            <div className="relative">
                                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                                                <input type="text" placeholder="Buscar diplomados..." className="bg-transparent pl-11 pr-4 py-2.5 text-[13px] font-bold outline-none text-slate-800 dark:text-white placeholder:text-slate-400" />
                                            </div>
                                            <button className="p-3 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all"><Filter size={18} className="text-slate-500" /></button>
                                        </div>
                                    }
                                />
                                <div className="mt-8">
                                    <CourseCatalog
                                        userId={user?.id || 0}
                                        token={token || ''}
                                        enrolledCourseIds={enrolledCourseIds}
                                        initialCourses={initialCourses}
                                    />
                                </div>
                            </motion.section>
                        </div>

                        {/* Sidebar / Intelligence Panel */}
                        <aside className="lg:col-span-4 space-y-8">
                            
                            {/* Weekly Goal Chart */}
                            <motion.div variants={itemVariants} className="p-8 rounded-[3rem] bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-[0.08] transition-opacity"><BarChart3 size={80} className="text-blue-600" /></div>
                                <div className="space-y-8 relative z-10">
                                    <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                        <Target size={16} className="text-blue-600" /> Meta de Estudio Semanal
                                    </h4>
                                    <div className="flex items-end justify-between gap-3 h-40">
                                        {[40, 70, 55, 90, 60, 85, 45].map((h, i) => (
                                            <div key={i} className="flex-1 bg-slate-100 dark:bg-white/5 rounded-t-2xl relative group/bar hover:bg-blue-600 dark:hover:bg-blue-500 transition-all duration-300 cursor-pointer" style={{ height: `${h}%` }}>
                                                <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[10px] font-black px-3 py-1.5 rounded-xl opacity-0 group-hover/bar:opacity-100 transition-all shadow-xl z-20 whitespace-nowrap pointer-events-none translate-y-2 group-hover/bar:translate-y-0">{h} min</div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="flex justify-between px-1">
                                        {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map((d, i) => (
                                            <span key={i} className={clsx("text-[11px] font-black", i === 3 ? "text-blue-600" : "text-slate-400")}>{d}</span>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>

                            {/* Achievements */}
                            <motion.div variants={itemVariants} className="p-8 rounded-[3rem] bg-slate-50/80 dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm space-y-6">
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Vitrina de Logros</h4>
                                <div className="space-y-4">
                                    <AchievementItem icon={Award} title="Fundamentos I Aprobado" date="Hace 2 días" color="text-amber-500" bg="bg-white dark:bg-[#15171c] shadow-sm" />
                                    <AchievementItem icon={ShieldCheck} title="Identidad Verificada" date="Mes pasado" color="text-blue-500" bg="bg-white dark:bg-[#15171c] shadow-sm" />
                                    <AchievementItem icon={Flame} title="Racha: 10 Días Seguidos" date="Activo" color="text-rose-500" bg="bg-white dark:bg-[#15171c] shadow-sm border-rose-500/20" />
                                </div>
                                <button className="w-full mt-6 py-5 border-2 border-slate-200 dark:border-white/10 bg-transparent rounded-[2rem] text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 hover:bg-white dark:hover:bg-white/5 hover:text-slate-800 dark:hover:text-white transition-all active:scale-95">Ver Perfil Completo</button>
                            </motion.div>

                            {/* MESH Intelligence */}
                            <motion.div variants={itemVariants} className="p-8 rounded-[3rem] bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/5 shadow-xl space-y-5">
                                <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                    <Rocket size={14} className="text-purple-500" /> Sugerencias MESH
                                </h4>
                                <div className="space-y-4">
                                    {aiInsights.length > 0 ? (
                                        aiInsights.slice(0, 2).map((item: any, idx: number) => (
                                            <div key={item.id || idx} className="rounded-2xl border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20 p-4 group hover:bg-purple-50 dark:hover:bg-purple-500/10 transition-colors cursor-default">
                                                <p className="text-[9px] font-black uppercase tracking-widest text-purple-500 transition-colors">{item.title}</p>
                                                <p className="text-[13px] font-medium text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">“{item.payload}”</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="grid grid-cols-2 gap-4">
                                            {graphInsights.slice(0, 4).map((item: any, idx: number) => (
                                                <div key={item.id || idx} className="rounded-2xl border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20 p-4 group hover:bg-purple-50 dark:hover:bg-purple-500/10 transition-colors cursor-default">
                                                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 group-hover:text-purple-500 transition-colors">{item.label}</p>
                                                    <p className="text-2xl font-black text-slate-800 dark:text-white mt-1 tracking-tighter">{item.value}</p>
                                                </div>
                                            ))}
                                            {graphInsights.length === 0 && (
                                                <>
                                                    <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20 p-4"><p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Lecciones</p><p className="text-2xl font-black text-slate-800 dark:text-white mt-1">12</p></div>
                                                    <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20 p-4"><p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Horas</p><p className="text-2xl font-black text-slate-800 dark:text-white mt-1">4.5</p></div>
                                                </>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </motion.div>

                        </aside>
                    </div>
                </motion.div>
            </main>
        </div>
    );
}

function HeroStat({ label, value, icon: Icon, color, bg }: any) {
    return (
        <div className="px-6 py-5 bg-white/5 backdrop-blur-2xl rounded-[2.5rem] border border-white/10 flex items-center gap-5 shadow-2xl group hover:scale-105 transition-all duration-300 hover:bg-white/10">
            <div className={clsx('size-12 rounded-2xl flex items-center justify-center shadow-inner', bg, color)}>
                <Icon size={24} strokeWidth={2.5} />
            </div>
            <div>
                <p className="text-[10px] font-black text-blue-200/50 uppercase tracking-[0.2em] leading-none mb-2">{label}</p>
                <p className="text-2xl font-black text-white tracking-tighter leading-none">{value}</p>
            </div>
        </div>
    );
}

function AchievementItem({ icon: Icon, title, date, color, bg }: any) {
    return (
        <div className={clsx("flex items-center gap-4 p-4 rounded-3xl border border-slate-100 dark:border-white/5 group cursor-pointer transition-all hover:border-slate-300 dark:hover:border-white/20 hover:shadow-md", bg)}>
            <div className={clsx('size-12 rounded-2xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-3 shadow-inner shrink-0', color, bg.replace('bg-white', 'bg-slate-50').replace('bg-[#15171c]', 'bg-black/20'))}>
                <Icon size={22} strokeWidth={2.5} />
            </div>
            <div className="flex-1 min-w-0">
                <h5 className="text-[13px] font-bold text-slate-800 dark:text-white leading-tight truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{title}</h5>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mt-1">{date}</p>
            </div>
            <ChevronRight size={18} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1" />
        </div>
    );
}

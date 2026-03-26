"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import CourseCatalog from '@/components/CourseCatalog';
import MyEnrollments from '@/components/MyEnrollments';
import { 
    Sparkles, Trophy, BookOpen, Clock, Target, ArrowRight, Search, Filter, 
    MoreHorizontal, Layout, Award, FileCheck, GraduationCap, BarChart3, Star,
    Zap, Rocket, ShieldCheck, Flame, ChevronRight
, Calendar } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useContentBlocks } from '@/hooks/useContent';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';

export default function AcademyPage() {
    const { user, token, isAuthenticated } = useAuth();
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [enrolledCourseIds, setEnrolledCourseIds] = useState<number[]>([]);
    const [loading, setLoading] = useState(true);
    const { data: pageContents } = useContentBlocks(['academy_hero', 'academy_welcome_sub']);

    useEffect(() => {
        const fetchData = async () => {
            if (!isAuthenticated || !user) return;
            try {
                const enrRes = await apiFetch(`/users/${user.id}/enrollments`, { token, cache: 'no-store' });
                if (Array.isArray(enrRes)) setEnrolledCourseIds(enrRes.map((e: any) => e.course.id));
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchData();
    }, [user, token, isAuthenticated]);

    if (loading && enrolledCourseIds.length === 0) {
        return (
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden">
                <WorkspaceToolbar breadcrumbs={[{ label: 'Academia Faro', icon: GraduationCap }]} viewType={viewType} setViewType={setViewType} />
                <div className="p-8 space-y-8 animate-fade-in"><Skeleton className="h-64 w-full rounded-[3rem]" /><div className="grid grid-cols-12 gap-8"><div className="col-span-8 space-y-6"><Skeleton className="h-48 w-full rounded-3xl" /><div className="grid grid-cols-2 gap-6"><Skeleton className="h-64 rounded-3xl" /><Skeleton className="h-64 rounded-3xl" /></div></div><div className="col-span-4 space-y-6"><Skeleton className="h-80 w-full rounded-3xl" /></div></div></div>
            </div>
        );
    }

    const heroTags = ['Formación', 'IA Coach', 'Gamificación'];
    const heroWatchers = ['Academia Faro', 'Optimus Brain'];

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF', icon: Layout }, { label: 'Academia Faro', icon: GraduationCap }]}
                viewType={viewType} setViewType={setViewType} availableViews={['grid', 'table']} onAdd={() => {}}
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                {/* AI Shimmer Backdrop */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f008_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1600px] mx-auto space-y-10 relative z-10">
                    <AdminHero
                        eyebrow="Academia"
                        title={pageContents.academy_hero?.title || 'Continúa tu propósito.'}
                        description={pageContents.academy_hero?.content || `Hola, ${user?.username ?? 'estudiante'}. Tienes 2 cursos pendientes esta semana.`}
                        tags={heroTags}
                        watchers={heroWatchers}
                        primaryAction={{ label: 'Explorar rutas', icon: ArrowRight, onClick: () => setViewType('grid') }}
                        secondaryAction={{ label: 'Ver horario', icon: Calendar, onClick: () => {} }}
                        commandBar={{
                            title: 'Coach IA',
                            description: 'Pide al coach que adapte tu plan de estudio en segundos.',
                            ctaLabel: '/coach',
                            shortcuts: [
                                { label: 'Recordatorios', command: '/coach recordatorios' },
                                { label: 'Mentorías', command: '/coach mentorias' },
                                { label: 'Plan semanal', command: '/coach plan-semana' }
                            ]
                        }}
                    />

                    {/* 1. Cinematic Hero Section */}
                    <section className="relative h-[280px] w-full overflow-hidden rounded-[3.5rem] shadow-2xl group border border-white/10">
                        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800" />
                        <div className="absolute top-0 right-0 w-1/2 h-full bg-[radial-gradient(circle_at_center,_white_0%,_transparent_70%)] opacity-10 animate-pulse" />
                        
                        <div className="relative h-full flex flex-col justify-center px-12 lg:px-20 space-y-6">
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl rounded-full text-[10px] font-black uppercase tracking-[0.3em] text-white border border-white/20"
                            >
                                <Rocket size={14} className="animate-bounce" /> {pageContents.academy_welcome_sub?.title || "Tu Ruta de Formación"}
                            </motion.div>
                            <div className="max-w-2xl">
                                <h2 className="text-4xl lg:text-6xl font-black text-white tracking-tighter leading-none mb-4">
                                    Continúa tu <span className="text-blue-200 italic">propósito.</span>
                                </h2>
                                <p className="text-blue-100/80 text-lg font-medium leading-relaxed max-w-lg">
                                    {pageContents.academy_hero?.content || `Hola, ${user?.username}. Tienes 2 cursos pendientes por terminar esta semana.`}
                                </p>
                            </div>
                        </div>

                        {/* Floating Stats over Hero */}
                        <div className="absolute bottom-8 right-12 hidden lg:flex gap-4">
                            <HeroStat label="Puntos" value="1,240" icon={Star} color="text-amber-400" />
                            <HeroStat label="Racha" value="5 Días" icon={Flame} color="text-rose-400" />
                        </div>
                    </section>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                        
                        {/* 2. Main Learning Area */}
                        <div className="lg:col-span-8 space-y-10">
                            
                            {/* Active Learning Grid */}
                            <section className="space-y-6">
                                    <div className="flex items-center justify-between px-4">
                                        <h3 className="text-[12px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                            <div className="size-2 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                                            Mis Cursos Activos
                                        </h3>
                                        <div className="flex gap-2">
                                            {['Semana', 'Mes', 'Todo'].map((chip) => (
                                                <CommunityToolbarChip key={chip} label={chip} size="sm" />
                                            ))}
                                        </div>
                                    </div>
                                <div className="bg-slate-50/50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 p-2">
                                    <MyEnrollments userId={user?.id || 0} token={token || ''} refreshToken={0} />
                                </div>
                            </section>

                            {/* Catalog Exploration */}
                            <section className="bg-white dark:bg-black/20 rounded-[3rem] border border-slate-100 dark:border-white/5 p-10 shadow-sm relative overflow-hidden group">
                                <div className="flex items-center justify-between mb-12">
                                    <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">Explorar Nuevos Caminos</h3>
                                    <div className="flex items-center gap-2 bg-slate-100 dark:bg-black/40 p-1.5 rounded-2xl border border-slate-200 dark:border-white/5">
                                        <div className="relative">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                                            <input type="text" placeholder="Buscar formación..." className="bg-transparent pl-9 pr-4 py-2 text-[12px] font-bold outline-none" />
                                        </div>
                                        <button className="p-2 hover:bg-white dark:hover:bg-white/10 rounded-xl transition-all shadow-sm"><Filter size={16} /></button>
                                    </div>
                                </div>
                                <CourseCatalog userId={user?.id || 0} token={token || ''} enrolledCourseIds={enrolledCourseIds} />
                            </section>
                        </div>

                        {/* 3. Progress Sidebar: Gamified & Premium */}
                        <aside className="lg:col-span-4 space-y-8">
                            
                            {/* Weekly Goal Card */}
                            <div className="p-8 rounded-[2.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-xl relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-100 transition-opacity"><BarChart3 size={48} className="text-blue-600" /></div>
                                <div className="space-y-6">
                                    <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                        <Target size={16} className="text-blue-600" /> Meta Semanal
                                    </h4>
                                    <div className="flex items-end justify-between gap-2 h-32 px-2">
                                        {[40, 70, 55, 90, 60, 85, 45].map((h, i) => (
                                            <div key={i} className="flex-1 bg-blue-100 dark:bg-white/5 rounded-t-xl relative group/bar hover:bg-blue-600 transition-all cursor-pointer" style={{ height: `${h}%` }}>
                                                <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] font-black px-2 py-1 rounded-lg opacity-0 group-hover/bar:opacity-100 transition-all shadow-xl z-20 whitespace-nowrap">{h} min</div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="flex justify-between px-2">
                                        {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map(d => <span key={d} className="text-[10px] font-black text-slate-400">{d}</span>)}
                                    </div>
                                </div>
                            </div>

                            {/* Recent Achievements */}
                            <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-black/40 border border-slate-100 dark:border-white/5 shadow-sm space-y-6">
                                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em]">Logros Recientes</h4>
                                <div className="space-y-4">
                                    <AchievementItem icon={Award} title="Fundamentos I" date="Hace 2h" color="text-amber-500" bg="bg-amber-50 dark:bg-amber-900/20" />
                                    <AchievementItem icon={ShieldCheck} title="Perfil Verificado" date="8 Mar" color="text-blue-500" bg="bg-blue-50 dark:bg-blue-900/20" />
                                    <AchievementItem icon={Flame} title="Racha 5 Días" date="Hoy" color="text-rose-500" bg="bg-rose-50 dark:bg-rose-900/20" />
                                </div>
                                <button className="w-full mt-4 py-4 border-2 border-white dark:border-white/5 bg-white/50 dark:bg-white/5 rounded-[2rem] text-[11px] font-black uppercase tracking-widest text-slate-500 hover:shadow-lg transition-all active:scale-95">Ver mi vitrina</button>
                            </div>

                            {/* AI Academic Coach Widget */}
                            <div className="p-8 rounded-[2.5rem] bg-gradient-to-br from-purple-600 to-indigo-800 text-white shadow-2xl relative overflow-hidden group">
                                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10" />
                                <div className="relative z-10 space-y-6">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center shadow-inner"><Sparkles size={20} /></div>
                                        <h4 className="text-lg font-black tracking-tight leading-none">Coach Académico</h4>
                                    </div>
                                    <p className="text-sm font-medium text-purple-100 leading-relaxed italic">&ldquo;Matias, si terminas la lección de hoy, habrás superado tu meta semanal en un 15%. ¡Tú puedes!&rdquo;</p>
                                    <button className="w-full py-4 bg-white text-indigo-900 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-xl hover:scale-[1.02] active:scale-95 transition-all">Pedir ayuda con IA</button>
                                </div>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}

function HeroStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="px-6 py-4 bg-white/10 backdrop-blur-2xl rounded-[2rem] border border-white/20 flex items-center gap-4 shadow-2xl group hover:scale-105 transition-all">
            <div className={clsx("size-10 rounded-xl bg-white/10 flex items-center justify-center shadow-inner", color)}>
                <Icon size={20} strokeWidth={2.5} />
            </div>
            <div>
                <p className="text-[10px] font-black text-white/50 uppercase tracking-widest leading-none mb-1">{label}</p>
                <p className="text-xl font-black text-white tracking-tighter leading-none">{value}</p>
            </div>
        </div>
    );
}

function AchievementItem({ icon: Icon, title, date, color, bg }: any) {
    return (
        <div className="flex items-center gap-4 group cursor-pointer transition-all">
            <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-all group-hover:scale-110 shadow-sm shrink-0", bg, color)}>
                <Icon size={24} />
            </div>
            <div className="flex-1 min-w-0">
                <h5 className="text-[14px] font-bold text-slate-800 dark:text-slate-100 leading-tight truncate">{title}</h5>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-0.5">{date}</p>
            </div>
            <ChevronRight size={16} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1" />
        </div>
    );
}

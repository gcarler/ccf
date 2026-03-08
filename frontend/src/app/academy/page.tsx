"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import CourseCatalog from '@/components/CourseCatalog';
import MyEnrollments from '@/components/MyEnrollments';
import { Sparkles, Trophy, BookOpen, Clock, Target, ArrowRight } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface PageContent {
    page_key: string;
    title?: string;
    content?: string;
}

export default function AcademyPage() {
    const { user, token, isAuthenticated } = useAuth();
    const [refreshKey, setRefreshKey] = useState(0);
    const [enrolledCourseIds, setEnrolledCourseIds] = useState<number[]>([]);
    const [pageContents, setPageContents] = useState<Record<string, PageContent>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated || !user) return;

        const fetchData = async () => {
            setLoading(true);
            try {
                // Fetch enrollments
                const enrRes = await fetch(apiUrl(`/users/${user.id}/enrollments`), {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (enrRes.ok) {
                    const data = await enrRes.json();
                    setEnrolledCourseIds(data.map((e: any) => e.course.id));
                }

                // Fetch page content
                const keys = ["academy_hero", "academy_welcome_sub"];
                const fetchedContents: Record<string, PageContent> = {};

                await Promise.all(keys.map(async (key) => {
                    const res = await fetch(apiUrl(`/content/${key}`));
                    if (res.ok) fetchedContents[key] = await res.json();
                }));
                setPageContents(fetchedContents);

            } catch (err) {
                console.error("Error fetching data:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [user, token, isAuthenticated, refreshKey]);

    return (
        <div className="space-y-10 animate-in fade-in duration-700">
            {/* Desktop Welcome Banner */}
            <section className="relative overflow-hidden rounded-[3rem] bg-navy-dark p-12 text-white border border-white/5 shadow-2xl">
                <div className="absolute top-0 right-0 w-1/2 h-full opacity-20 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary via-transparent to-transparent"></div>
                <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div>
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/20 text-primary border border-primary/20 rounded-full text-[10px] font-black uppercase tracking-widest mb-6">
                            <Sparkles size={14} /> {pageContents.academy_welcome_sub?.title || "Portal Estudiantil"}
                        </div>
                        <h1 className="text-5xl font-black tracking-tight mb-4">
                            {pageContents.academy_hero?.title || "Continúa tu Formación"}
                        </h1>
                        <p className="text-slate-400 text-lg font-medium max-w-lg leading-relaxed mb-8">
                            {pageContents.academy_hero?.content || `Bienvenido de nuevo, ${user?.username || 'Estudiante'}. Tienes cursos pendientes que requieren tu atención hoy.`}
                        </p>
                        <div className="flex gap-4">
                            <div className="px-6 py-4 rounded-2xl bg-white/5 border border-white/5 flex items-center gap-4">
                                <Trophy className="text-amber-400" size={24} />
                                <div>
                                    <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Puntos</p>
                                    <p className="text-xl font-bold">1,240</p>
                                </div>
                            </div>
                            <div className="px-6 py-4 rounded-2xl bg-white/5 border border-white/5 flex items-center gap-4">
                                <Target className="text-primary" size={24} />
                                <div>
                                    <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Nivel</p>
                                    <p className="text-xl font-bold">Intermedio</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="hidden lg:block">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="aspect-square rounded-3xl overflow-hidden shadow-2xl border border-white/10 rotate-3">
                                <img className="w-full h-full object-cover opacity-60" src="https://images.unsplash.com/photo-1504052434569-70ad5836ab65?auto=format&fit=crop&q=80" alt="Study" />
                            </div>
                            <div className="aspect-square rounded-3xl overflow-hidden shadow-2xl border border-white/10 -rotate-6 translate-y-12">
                                <img className="w-full h-full object-cover opacity-60" src="https://images.unsplash.com/photo-1490730141103-6ca3ef7a2c4d?auto=format&fit=crop&q=80" alt="Study" />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Desktop Dashboard Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">

                {/* Main Content: Enrollments (Col 8) */}
                <div className="xl:col-span-8 space-y-8">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-3xl font-black tracking-tighter">Mis Cursos Activos</h2>
                        <button className="text-primary text-xs font-black uppercase tracking-widest hover:underline flex items-center gap-2">
                            Ver todo el historial <ArrowRight size={16} />
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Enrollments component will now map into a grid if we adjust its internal CSS, 
                            but for now let's keep the list style inside the wide column */}
                        <div className="md:col-span-2">
                            <MyEnrollments
                                userId={user?.id || 0}
                                token={token || ''}
                                refreshToken={refreshKey}
                            />
                        </div>
                    </div>
                </div>

                {/* Sidebar: Course Catalog & Progress (Col 4) */}
                <div className="xl:col-span-4 space-y-10">

                    {/* Catalog Mini View */}
                    <div className="glass-card dark:glass-card-dark rounded-[3rem] p-8 border-white/10 shadow-2xl overflow-hidden relative border-t-4 border-t-primary">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl"></div>
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-8">
                                <div className="p-3 bg-primary/10 rounded-2xl text-primary">
                                    <BookOpen size={24} />
                                </div>
                                <h3 className="text-xl font-black tracking-tighter">Explorar Catálogo</h3>
                            </div>

                            <CourseCatalog
                                userId={user?.id || 0}
                                token={token || ''}
                                enrolledCourseIds={enrolledCourseIds}
                            />
                        </div>
                    </div>

                    {/* Progress Chart Placeholder */}
                    <div className="bg-white dark:bg-slate-800/40 rounded-[2.5rem] p-8 border border-white/5 shadow-xl">
                        <h3 className="text-lg font-black tracking-tighter mb-6 flex items-center gap-2">
                            <Clock size={18} className="text-primary" /> Tiempo de Estudio
                        </h3>
                        <div className="h-48 w-full flex items-end justify-between gap-2 px-2">
                            {[40, 70, 55, 90, 60, 85, 45].map((h, i) => (
                                <div key={i} className="flex-1 bg-primary/10 rounded-t-lg relative group transition-all hover:bg-primary/30 cursor-pointer" style={{ height: `${h}%` }}>
                                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-primary text-white text-[8px] font-black py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                                        {h}m
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className="flex justify-between mt-4 px-1">
                            {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map(d => (
                                <span key={d} className="text-[10px] font-black text-slate-500">{d}</span>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

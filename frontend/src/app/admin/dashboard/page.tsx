"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import {
    LayoutDashboard,
    Users,
    Activity,
    TrendingUp,
    Bell,
    UserPlus,
    Heart,
    Zap,
    Target,
    Layers,
    Calendar,
    PieChart,
    ChevronRight,
    Sparkles
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

type AdminStats = {
    users: number;
    donations: number;
    attendance: number;
};

type AcademyMetrics = {
    active_students: number;
    completion_rate: number;
    certificates_issued: number;
    formal_stats: { total: number, completed: number, rate: number, avg_grade: number };
    no_formal_stats: { total: number, completed: number, rate: number, avg_grade: number };
    top_courses: Array<{ title: string, count: number }>;
};

export default function AdminDashboard() {
    const { isAuthenticated, token } = useAuth();
    const router = useRouter();
    const [stats, setStats] = useState<AdminStats>({ users: 0, donations: 0, attendance: 24 });
    const [academy, setAcademy] = useState<AcademyMetrics | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        if (!token) return;
        try {
            const [statsData, academyData] = await Promise.all([
                apiFetch<AdminStats>('/auth/stats/summary', { token }),
                apiFetch<AcademyMetrics>('/academy/dashboard/metrics', { token })
            ]);
            
            setStats({
                users: statsData?.users ?? 0,
                donations: statsData?.donations ?? 0,
                attendance: statsData?.attendance ?? 0
            });
            setAcademy(academyData);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { if (isAuthenticated) fetchData(); }, [isAuthenticated, fetchData]);

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Gestión Central', icon: Bell },
                { label: 'Dashboard Ejecutivo', icon: LayoutDashboard }
            ]}
        >
            <AdminHero
                eyebrow="Resumen de Operación"
                title="Consola de Control Central"
                description="Monitorea el crecimiento espiritual y académico de la comunidad en tiempo real. Optimus Brain está analizando las tendencias de participación."
                tags={['Dashboard', 'Real-time', 'BI']}
                watchers={['Admin Team', 'Optimus Brain']}
                primaryAction={{ label: 'Nueva Campaña', icon: Zap, onClick: () => router.push('/admin/announcements/new') }}
                secondaryAction={{ label: 'Ver Reportes', icon: TrendingUp, onClick: () => router.push('/admin/reports') }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 pb-4">
                {/* Main Stats Area */}
                <div className="lg:col-span-8 space-y-3">
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <StatCard 
                            label="Usuarios Totales" value={loading ? '...' : stats.users.toLocaleString()} 
                            icon={Users} trend="+12.5%" color="blue" 
                        />
                        <StatCard 
                            label="Ofrendas del Mes" value={`$${loading ? '...' : stats.donations.toLocaleString()}`} 
                            icon={Heart} trend="+8.2%" color="rose" 
                        />
                        <StatCard 
                            label="Asistencia Promedio" value={`${loading ? '...' : stats.attendance}%`} 
                            icon={Activity} trend="-2.1%" color="emerald" 
                        />
                    </section>

                    {/* Interactive Chart Section */}
                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3 group">
                        <div className="flex justify-between items-center">
                            <div>
                                <h3 className="text-xl font-bold tracking-tight mb-1">Tendencia de Crecimiento</h3>
                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">Participación Semanal</p>
                            </div>
                            <div className="flex items-center gap-2 bg-slate-100 dark:bg-white/5 p-1 rounded-md border border-slate-200 dark:border-white/10">
                                {['7D', '30D', '90D'].map(p => (
                                    <button key={p} className={clsx("px-4 py-1.5 rounded-lg font-semibold transition-all", p === '7D' ? "bg-white dark:bg-blue-600 text-blue-600 dark:text-white shadow-sm" : "text-slate-500")}>{p}</button>
                                ))}
                            </div>
                        </div>
                        <div className="h-48 flex items-end gap-3 lg:gap-5 pt-10">
                            {[40, 65, 30, 85, 70, 55, 100].map((h, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center gap-4 group/bar">
                                    <motion.div 
                                        initial={{ height: 0 }} animate={{ height: `${h}%` }}
                                        className={clsx(
                                            "w-full rounded-t-2xl transition-all duration-700 relative",
                                            i === 6 ? "bg-blue-600 shadow-[0_0_20px_rgba(37,99,235,0.4)]" : "bg-slate-200 dark:bg-white/10 opacity-60 group-hover/bar:opacity-100"
                                        )}
                                    >
                                        <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover/bar:opacity-100 transition-opacity bg-slate-900 text-white px-2 py-1 rounded font-semibold">
                                            {h}%
                                        </div>
                                    </motion.div>
                                    <span className="font-semibold text-slate-400 uppercase tracking-wide">{['L','M','M','J','V','S','D'][i]}</span>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Recent Activity List */}
                    <section className="space-y-6">
                        <div className="flex justify-between items-center px-4">
                            <h3 className="text-lg font-bold tracking-tight uppercase tracking-wide">Actividad Reciente</h3>
                            <button className="font-semibold text-blue-600 uppercase tracking-wide hover:underline">Ver Todo</button>
                        </div>
                        <div className="space-y-4">
                            {[
                                { title: 'Nueva Inscripción', desc: 'Ricardo Mendez se unió a "Fundamentos de la Fe"', time: 'Hace 5 min', icon: UserPlus, color: 'text-blue-500', bg: 'bg-blue-50' },
                                { title: 'Donación Recibida', desc: 'Ofrenda especial pro-construcción confirmada', time: 'Hace 12 min', icon: Heart, color: 'text-rose-500', bg: 'bg-rose-50' },
                                { title: 'Examen Completado', desc: 'Elena Rodriguez aprobó "Historia de la Iglesia"', time: 'Hace 45 min', icon: Target, color: 'text-emerald-500', bg: 'bg-emerald-50' },
                            ].map((item, idx) => (
                                <div key={idx} className="flex items-center gap-3 p-3 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg hover:border-blue-500/20 transition-all group cursor-pointer shadow-sm hover:shadow-md">
                                    <div className={clsx("size-7 rounded-lg flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform", item.bg, "dark:bg-white/10", item.color)}>
                                        <item.icon size={28} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white truncate">{item.title}</h4>
                                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wide mt-1 truncate">{item.desc}</p>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="font-semibold text-slate-400 uppercase tracking-wide mb-1">{item.time}</p>
                                        <ChevronRight size={18} className="text-slate-300 group-hover:text-blue-600 transition-colors inline-block" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* ACADEMY PERFORMANCE SECTION - MVP-006 */}
                    <section className="pt-10 space-y-3">
                         <div className="flex items-center gap-4 px-4">
                            <div className="size-10 rounded-md bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                                <Target size={20} />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold tracking-tight uppercase tracking-wide">Rendimiento Académico</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Desglose por Modalidad</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                             <ModalityCard 
                                title="Ruta Formal" 
                                stats={academy?.formal_stats} 
                                icon={Layers}
                                color="blue"
                             />
                             <ModalityCard 
                                title="No Formal / Abierta" 
                                stats={academy?.no_formal_stats} 
                                icon={Zap}
                                color="amber"
                             />
                        </div>

                        {/* Top Courses List */}
                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4">
                             <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-3 px-2">Cursos más Populares</h4>
                             <div className="space-y-4">
                                {academy?.top_courses.map((course, i) => (
                                    <div key={i} className="flex items-center justify-between p-4 bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 group hover:border-blue-500/20 transition-all">
                                        <div className="flex items-center gap-4">
                                            <span className="font-semibold text-slate-300">0{i+1}</span>
                                            <span className="text-sm font-semibold group-hover:text-blue-600 transition-colors">{course.title}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold">{course.count}</span>
                                            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">Estudiantes</span>
                                        </div>
                                    </div>
                                ))}
                             </div>
                        </div>
                    </section>
                </div>

                {/* Sidebar Contextual BI */}
                <aside className="lg:col-span-4 space-y-3">
                    <div className="bg-slate-900 rounded-lg p-4 text-white shadow-2xl space-y-3 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-20 -mt-20 size-10 bg-blue-600/20 rounded-full blur-[80px] group-hover:bg-blue-600/30 transition-all duration-1000" />
                        
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-3">
                                <PieChart size={20} className="text-blue-400" />
                                <h4 className="text-[11px] font-semibold uppercase tracking-wide text-blue-400">Distribución de Impacto</h4>
                            </div>
                            <div className="relative size-56 mx-auto mb-3">
                                <svg className="size-full -rotate-90 drop-shadow-2xl" viewBox="0 0 36 36">
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#2563eb" strokeWidth="4.5" strokeDasharray="75 100" />
                                    <circle cx="18" cy="18" r="15.9" fill="transparent" stroke="#334155" strokeWidth="4.5" strokeDasharray="25 100" strokeDashoffset="-75" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-lg font-bold tracking-tighter">75%</span>
                                    <span className="font-semibold text-slate-500 uppercase tracking-wide">Crecimiento</span>
                                </div>
                            </div>
                            <div className="space-y-4">
                                <ProgressItem label="Inscripciones" value="75%" color="bg-blue-600" />
                                <ProgressItem label="Graduaciones" value="25%" color="bg-slate-700" />
                            </div>
                        </div>

                        <div className="relative z-10 pt-10 border-t border-white/5">
                            <div className="p-3 bg-white/5 rounded-lg border border-white/10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <Sparkles size={18} className="text-blue-400" />
                                    <h5 className="text-[10px] font-semibold uppercase tracking-wide">IA Insights</h5>
                                </div>
                                <p className="text-[11px] font-bold text-slate-400 leading-relaxed uppercase tracking-wider">
                                    &quot;La participación ha subido un 15% en los cursos no formales. Se recomienda potenciar la ruta formal para el próximo trimestre.&quot;
                                </p>
                            </div>
                        </div>

                        <button className="relative z-10 w-full py-2 bg-white text-slate-900 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl hover:scale-[1.02] transition-all active:scale-95">
                            Generar Auditoría
                        </button>
                    </div>

                    <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Próximos Eventos</h4>
                            <Calendar size={18} className="text-slate-300" />
                        </div>
                        <div className="space-y-6">
                            {[
                                { day: '15', month: 'MAR', title: 'Cierre de Actas Cohorte B', time: '09:00 AM' },
                                { day: '22', month: 'MAR', title: 'Asamblea de Líderes', time: '06:30 PM' },
                            ].map((event, i) => (
                                <div key={i} className="flex gap-3 items-center group cursor-pointer">
                                    <div className="flex flex-col items-center justify-center size-7 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 group-hover:bg-blue-600 group-hover:text-white transition-all">
                                        <span className="text-lg font-bold leading-none">{event.day}</span>
                                        <span className="text-[8px] font-semibold uppercase">{event.month}</span>
                                    </div>
                                    <div>
                                        <h5 className="font-semibold text-slate-800 dark:text-white group-hover:text-blue-600 transition-colors">{event.title}</h5>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mt-0.5">{event.time}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </aside>
            </div>
        </AdminShell>
    );
}

function ModalityCard({ title, stats, icon: Icon, color }: any) {
    if (!stats) return <div className="h-48 bg-slate-50 dark:bg-white/5 rounded-lg animate-pulse" />;
    
    const colorMap: any = {
        blue: { text: 'text-blue-600', bg: 'bg-blue-50', bar: 'bg-blue-600', border: 'border-blue-100' },
        amber: { text: 'text-amber-600', bg: 'bg-amber-50', bar: 'bg-amber-600', border: 'border-amber-100' }
    };
    const c = colorMap[color];

    return (
        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 space-y-6 shadow-sm group hover:shadow-xl transition-all">
            <div className="flex justify-between items-start">
                <div className={clsx("size-7 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110", c.bg, "dark:bg-white/10", c.text)}>
                    <Icon size={24} />
                </div>
                <div className="text-right">
                    <span className="font-semibold text-slate-400 uppercase tracking-wide">Éxito</span>
                    <h5 className={clsx("text-xl font-bold tracking-tight", c.text)}>{stats.rate}%</h5>
                </div>
            </div>
            
            <div>
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-wider">{title}</h4>
                <div className="flex items-center gap-2 mt-1">
                    <div className="size-1.5 rounded-full bg-emerald-500" />
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">{stats.completed} de {stats.total} finalizados</p>
                </div>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-white/5 grid grid-cols-2 gap-4">
                <div>
                    <span className="font-semibold text-slate-400 uppercase tracking-wide block mb-1">Promedio</span>
                    <p className="text-lg font-bold tracking-tighter">{stats.avg_grade}</p>
                </div>
                <div className="text-right">
                    <span className="font-semibold text-slate-400 uppercase tracking-wide block mb-1">Inscritos</span>
                    <p className="text-lg font-bold tracking-tighter">{stats.total}</p>
                </div>
            </div>
            
            <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }} 
                    animate={{ width: `${stats.rate}%` }} 
                    className={clsx("h-full", c.bar)} 
                />
            </div>
        </div>
    );
}

function StatCard({ label, value, icon: Icon, trend, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20'
    };
    return (
        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 shadow-sm hover:shadow-xl transition-all group overflow-hidden relative">
            <div className="absolute top-0 right-0 -mr-6 -mt-3 size-10 bg-slate-50 dark:bg-white/5 rounded-full scale-0 group-hover:scale-100 transition-transform duration-700" />
            <div className="relative z-10 space-y-6">
                <div className="flex justify-between items-center">
                    <div className={clsx("size-7 rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                        <Icon size={28} />
                    </div>
                    <div className={clsx("font-semibold px-2 py-0.5 rounded-lg border", 
                        trend.startsWith('+') ? "text-emerald-500 bg-emerald-50 border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-500/20" : "text-rose-500 bg-rose-50 border-rose-100 dark:bg-rose-900/20 dark:border-rose-500/20"
                    )}>
                        {trend}
                    </div>
                </div>
                <div>
                    <p className="font-semibold text-slate-400 uppercase tracking-wide mb-1">{label}</p>
                    <h4 className="text-xl font-bold text-slate-900 dark:text-white tracking-tighter leading-none">{value}</h4>
                </div>
            </div>
        </div>
    );
}

function ProgressItem({ label, value, color }: any) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <span>{label}</span>
                <span className="text-white">{value}</span>
            </div>
            <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: value }} className={clsx("h-full", color)} />
            </div>
        </div>
    );
}


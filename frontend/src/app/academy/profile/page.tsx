"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { 
    Award, 
    BookOpen, 
    CheckCircle2, 
    Clock, 
    Download, 
    Edit3, 
    GraduationCap, 
    Heart, 
    ShieldCheck, 
    Sparkles, 
    Star, 
    TrendingUp, 
    Zap,
    MapPin,
    Calendar,
    ChevronRight,
    Target
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { AcademyStudentProfile, CertificateRecord, EnrollmentRecord } from '@/types/academy';
import Skeleton from '@/components/ui/Skeleton';
import { toast } from 'sonner';

export default function StudentProfilePage() {
    const { user, token } = useAuth();
    const [profile, setProfile] = useState<AcademyStudentProfile | null>(null);
    const [certificates, setCertificates] = useState<CertificateRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const fetchData = async () => {
            if (!token || !user?.id) return;
            try {
                setLoading(true);
                setError(null);
                const [profileData, certsData] = await Promise.all([
                    apiFetch<AcademyStudentProfile>(`/academy/me/profile`, { token, cache: 'no-store' }),
                    apiFetch<CertificateRecord[]>(`/academy/me/certificates`, { token, cache: 'no-store' })
                ]);
                setProfile(profileData);
                setCertificates(Array.isArray(certsData) ? certsData : []);
            } catch (err) {
                console.error(err);
                setError('No pudimos cargar tu perfil académico');
                toast.error('Perfil académico no disponible temporalmente');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [token, user]);

    const activeCourses = useMemo(() => profile?.active_courses ?? [], [profile]);
    const totalCertificates = certificates.length || profile?.certificates_count || 0;

    if (!user) return null;

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#0a0f16] overflow-hidden font-display">
                <WorkspaceToolbar 
                    breadcrumbs={[
                        { label: 'Academia', icon: GraduationCap },
                        { label: 'Mi Perfil Pastoral', icon: ShieldCheck }
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={['grid', 'list', 'table']}
                />
                <div className="flex-1 p-10 space-y-8">
                    <Skeleton className="h-72 rounded-[3rem]" />
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <Skeleton className="h-48 rounded-[2rem]" />
                        <Skeleton className="h-48 rounded-[2rem]" />
                        <Skeleton className="h-48 rounded-[2rem]" />
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#0a0f16] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Mi Perfil Pastoral', icon: ShieldCheck }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-white dark:bg-white/5 hover:bg-slate-50 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all border border-slate-200 dark:border-white/10 shadow-sm active:scale-95">
                        <Edit3 size={14} /> Editar Perfil
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-blue-500/5 via-transparent to-transparent pointer-events-none" />
                
                {error && (
                    <div className="mb-6 text-rose-500 text-sm font-semibold bg-rose-500/10 border border-rose-500/20 rounded-2xl px-4 py-3 relative z-10">
                        {error}
                    </div>
                )}
                
                {viewType === 'list' && (
                    <div className="relative z-10 mx-auto max-w-5xl space-y-5">
                        {activeCourses.map((enrollment) => (
                            <article key={enrollment.id} className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-white/10 dark:bg-white/5">
                                <h3 className="text-lg font-black text-slate-900 dark:text-white">{enrollment.course.title}</h3>
                                <p className="mt-2 text-sm text-slate-500">Progreso {Math.round(enrollment.progress_percent)}% · Asistencia {Math.round(enrollment.attendance_percent)}%</p>
                            </article>
                        ))}
                        {certificates.map((certificate, index) => (
                            <article key={`${certificate.course_title}-${index}`} className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-white/10 dark:bg-white/5">
                                <h3 className="text-lg font-black text-slate-900 dark:text-white">{certificate.course_title || certificate.certificate_type || 'Certificado'}</h3>
                                <p className="mt-2 text-sm text-slate-500">Expedido {new Date(certificate.issued_at).toLocaleDateString()}</p>
                            </article>
                        ))}
                    </div>
                )}

                {viewType === 'table' && (
                    <div className="relative z-10 mx-auto max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                <tr><th className="px-6 py-4">Tipo</th><th className="px-6 py-4">Nombre</th><th className="px-6 py-4">Progreso</th><th className="px-6 py-4">Detalle</th></tr>
                            </thead>
                            <tbody>
                                {activeCourses.map((enrollment) => (
                                    <tr key={enrollment.id} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-6 py-4 font-bold text-blue-600">Curso</td>
                                        <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">{enrollment.course.title}</td>
                                        <td className="px-6 py-4 text-slate-500">{Math.round(enrollment.progress_percent)}%</td>
                                        <td className="px-6 py-4 text-slate-500">Asistencia {Math.round(enrollment.attendance_percent)}%</td>
                                    </tr>
                                ))}
                                {certificates.map((certificate, index) => (
                                    <tr key={`${certificate.course_title}-${index}`} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-6 py-4 font-bold text-emerald-600">Certificado</td>
                                        <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">{certificate.course_title || certificate.certificate_type || 'Certificado'}</td>
                                        <td className="px-6 py-4 text-slate-500">100%</td>
                                        <td className="px-6 py-4 text-slate-500">{new Date(certificate.issued_at).toLocaleDateString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {viewType === 'grid' && (
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 relative z-10">
                    
                    {/* Left Column: Identity Card */}
                    <aside className="lg:col-span-4 space-y-8">
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-12 -mt-12 size-40 bg-blue-600/10 rounded-full blur-3xl group-hover:bg-blue-600/20 transition-all duration-1000" />
                            
                            <div className="relative z-10 flex flex-col items-center text-center space-y-6">
                                <div className="relative">
                                    <div className="size-32 rounded-[2.5rem] bg-gradient-to-tr from-blue-600 to-indigo-600 p-1 shadow-2xl">
                                        <div className="size-full rounded-[2.2rem] bg-white dark:bg-[#0a0f16] flex items-center justify-center text-4xl font-black text-blue-600 uppercase border-4 border-white dark:border-[#0a0f16]">
                                            {user.username?.charAt(0)}
                                        </div>
                                    </div>
                                    <div className="absolute -bottom-2 -right-2 size-10 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 text-white flex items-center justify-center shadow-lg border-4 border-white dark:border-[#0a0f16]">
                                        <Zap size={18} fill="currentColor" />
                                    </div>
                                </div>

                                <div>
                                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white leading-none mb-2 uppercase">{user.username}</h2>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">{user.role} • Ruta de Liderazgo</p>
                                </div>

                                <div className="flex items-center gap-4 text-slate-500">
                                    <div className="flex items-center gap-1.5"><MapPin size={12} /><span className="text-[11px] font-bold">Sede Central</span></div>
                                    <div className="size-1 rounded-full bg-slate-200 dark:bg-slate-700" />
                                    <div className="flex items-center gap-1.5"><Calendar size={12} /><span className="text-[11px] font-bold">Unido en 2024</span></div>
                                </div>

                                 <div className="w-full pt-8 border-t border-slate-100 dark:border-white/5 space-y-6">
                                     <div className="flex justify-between items-end">
                                         <div className="text-left">
                                             <p className="text-[10px] font-black text-blue-600 uppercase tracking-widest mb-1">Nivel Actual</p>
                                             <h4 className="text-xl font-black dark:text-white">{profile?.active_courses.length ? 'Discípulo Maduro' : 'Nuevo estudiante'}</h4>
                                         </div>
                                         <span className="text-[11px] font-black text-slate-400 uppercase">Progreso total: {profile?.total_progress ?? 0}%</span>
                                     </div>
                                     <div className="h-3 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner p-0.5">
                                         <motion.div initial={{ width: 0 }} animate={{ width: `${profile?.total_progress ?? 0}%` }} className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full shadow-[0_0_10px_rgba(37,99,235,0.4)]" />
                                     </div>
                                 </div>
                            </div>
                        </section>

                        {/* GAMIFICATION 3D BADGES SECTION */}
                        <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8 relative overflow-hidden">
                            <div className="absolute -right-10 -bottom-10 opacity-5"><Sparkles size={160} /></div>
                            <div className="relative z-10">
                                <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] mb-8">Vitrina de Logros MESH</h3>
                                <div className="grid grid-cols-3 gap-6">
                                    {[
                                        { icon: Star, color: 'from-amber-400 to-orange-500', locked: false, title: 'Excelencia' },
                                        { icon: BookOpen, color: 'from-blue-400 to-indigo-600', locked: false, title: 'Sabiduría' },
                                        { icon: Heart, color: 'from-rose-400 to-pink-600', locked: false, title: 'Servicio' },
                                        { icon: Zap, color: 'from-indigo-400 to-sky-600', locked: false, title: 'Poder' },
                                        { icon: ShieldCheck, color: 'from-emerald-400 to-teal-600', locked: false, title: 'Fidelidad' },
                                        { icon: Target, color: 'from-slate-400 to-slate-600', locked: true, title: 'Misiones' },
                                    ].map((badge, i) => (
                                        <div key={i} className="flex flex-col items-center gap-3">
                                            <div className={clsx(
                                                "aspect-square w-full rounded-2xl flex items-center justify-center relative badge-3d group cursor-crosshair",
                                                badge.locked ? "bg-slate-100 dark:bg-white/5 opacity-50 grayscale" : `bg-gradient-to-br ${badge.color} inner-glow`
                                            )}>
                                                <badge.icon size={28} fill={badge.locked ? "none" : "rgba(255,255,255,0.5)"} className={clsx(badge.locked ? "text-slate-400" : "text-white")} />
                                                {badge.locked && <div className="absolute inset-0 flex items-center justify-center"><Clock size={16} className="text-slate-600" /></div>}
                                                
                                                {/* Tooltip on hover */}
                                                <div className="absolute -top-10 scale-0 group-hover:scale-100 transition-transform bg-slate-900 text-white text-[10px] font-black px-3 py-1.5 rounded-lg whitespace-nowrap z-50">
                                                    {badge.title}
                                                </div>
                                            </div>
                                            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">{badge.title}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </section>
                    </aside>

                    {/* Right Column: Content & Progress */}
                    <div className="lg:col-span-8 space-y-10 pb-20">
                        {/* Quick Stats Grid */}
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                             <StatBox icon={BookOpen} label="Cursos Activos" value={activeCourses.length} color="blue" />
                             <StatBox icon={CheckCircle2} label="Certificados" value={totalCertificates} color="emerald" />
                             <StatBox icon={TrendingUp} label="Progreso Promedio" value={`${profile?.total_progress ?? 0}%`} color="amber" />
                         </section>

                         {/* Growth Path (Visual Timeline) */}
                         <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                            <div className="flex items-center gap-3">
                                <Sparkles size={20} className="text-blue-600" />
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest dark:text-white">Ruta de Crecimiento CCF</h3>
                            </div>
                            <div className="relative flex justify-between items-start pt-4">
                                <div className="absolute top-10 left-0 right-0 h-1 bg-slate-100 dark:bg-white/5 z-0" />
                                {[
                                    { label: 'Aspirante', done: true },
                                    { label: 'Discípulo', done: true, active: true },
                                    { label: 'Líder', done: false },
                                    { label: 'Pastor', done: false },
                                ].map((step, i) => (
                                    <div key={i} className="relative z-10 flex flex-col items-center gap-4 group cursor-pointer">
                                        <div className={clsx(
                                            "size-12 rounded-2xl flex items-center justify-center transition-all border-4 border-white dark:border-[#0a0f16]",
                                            step.done ? "bg-blue-600 text-white shadow-xl shadow-blue-500/20" : "bg-slate-100 dark:bg-white/5 text-slate-400 group-hover:bg-blue-100",
                                            step.active && "ring-4 ring-blue-500/20 scale-110"
                                        )}>
                                            {step.done ? <CheckCircle2 size={20} /> : <span className="text-[11px] font-black">{i+1}</span>}
                                        </div>
                                        <span className={clsx("text-[10px] font-black uppercase tracking-widest", step.done ? "text-slate-900 dark:text-white" : "text-slate-400")}>{step.label}</span>
                                    </div>
                                ))}
                            </div>
                        </section>

                         {/* Active Courses Breakdown */}
                        {activeCourses.length > 0 && (
                            <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-8 shadow-xl space-y-6">
                                <div className="flex items-center justify-between px-2">
                                    <h3 className="text-lg font-black tracking-tight uppercase tracking-widest dark:text-white">Cursos activos</h3>
                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{activeCourses.length} programas</span>
                                </div>
                                <div className="space-y-4">
                                    {activeCourses.map((enrollment: EnrollmentRecord) => (
                                        <article key={enrollment.id} className="flex flex-col lg:flex-row lg:items-center gap-6 rounded-[2rem] border border-slate-100 dark:border-white/5 bg-slate-50/60 dark:bg-white/5 p-5 hover:border-blue-500/30 transition-colors">
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-blue-500 mb-1">{enrollment.course.modality === 'formal' ? 'Formal' : 'No formal'}</p>
                                                <h4 className="text-base font-bold text-slate-900 dark:text-white mb-1 leading-tight truncate">{enrollment.course.title}</h4>
                                                <p className="text-[12px] text-slate-500 font-medium">Asistencia {Math.round(enrollment.attendance_percent)}% • Nota {enrollment.final_grade ?? 'N/A'}</p>
                                            </div>
                                            <div className="w-full lg:w-auto lg:min-w-[220px] flex flex-col gap-3">
                                                <ProgressPill label="Progreso" value={enrollment.progress_percent} tone="primary" />
                                                <ProgressPill label="Asistencia" value={enrollment.attendance_percent} tone="emerald" />
                                            </div>
                                        </article>
                                    ))}
                                </div>
                            </section>
                        )}

                         {/* Certificates Gallery */}
                        <section className="space-y-6">
                            <div className="flex justify-between items-center px-4">
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest dark:text-white">Certificados Verificables</h3>
                                <button className="text-[11px] font-black text-blue-600 uppercase tracking-widest flex items-center gap-2 hover:underline">Ver Galería <ChevronRight size={14} /></button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                 {certificates.length === 0 ? (
                                     <div className="col-span-2 p-12 bg-slate-50 dark:bg-white/5 rounded-[2.5rem] border-2 border-dashed border-slate-200 dark:border-white/10 text-center text-slate-400 font-medium italic">
                                         Aún no has obtenido certificados oficiales. ¡Sigue aprendiendo!
                                     </div>
                                 ) : (
                                     certificates.map((cert, i) => (
                                         <div key={i} className="group p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] hover:border-blue-500/30 transition-all shadow-sm hover:shadow-xl flex flex-col justify-between h-[200px]">
                                             <div className="flex justify-between items-start">
                                                 <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform"><Award size={24} /></div>
                                                 <button className="p-3 bg-slate-50 dark:bg-white/10 rounded-xl text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"><Download size={18} /></button>
                                             </div>
                                             <div>
                                                 <h4 className="text-[13px] font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none mb-2 line-clamp-2">{cert.course_title || cert.certificate_type || 'Certificado'}</h4>
                                                 <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Expedido: {new Date(cert.issued_at).toLocaleDateString()}</p>
                                             </div>
                                         </div>
                                     ))
                                 )}
                            </div>
                        </section>
                    </div>
                </div>
                )}
            </main>
        </div>
    );
}

function StatBox({ icon: Icon, label, value, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20'
    };
    return (
        <div className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 shadow-sm hover:shadow-xl transition-all group flex items-center gap-6">
            <div className={clsx("size-14 rounded-2xl flex items-center justify-center shrink-0 group-hover:rotate-12 transition-transform", colors[color])}>
                <Icon size={28} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 leading-none">{label}</p>
                <h4 className="text-3xl font-black text-slate-900 dark:text-white leading-none tracking-tighter">{value}</h4>
            </div>
        </div>
    );
}

function ProgressPill({ label, value, tone }: { label: string; value: number; tone: 'primary' | 'emerald' }) {
    const bg = tone === 'primary' ? 'from-blue-500 to-indigo-500 shadow-[0_0_10px_rgba(37,99,235,0.4)]' : 'from-emerald-500 to-teal-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]';
    return (
        <div className="w-full">
            <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                <span>{label}</span>
                <span className={clsx(tone === 'primary' ? "text-blue-600" : "text-emerald-600")}>{Math.round(value)}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                <div className={`h-full bg-gradient-to-r ${bg} transition-all duration-1000`} style={{ width: `${Math.min(100, Math.round(value))}%` }} />
            </div>
        </div>
    );
}


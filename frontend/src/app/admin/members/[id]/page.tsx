"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import MemberDetailSidebar from '@/components/crm/MemberDetailSidebar';
import {
    User, Phone, Mail, MapPin, LayoutDashboard, Briefcase, Zap,
    PencilLine, GraduationCap, Heart, Users,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

function InfoRow({ icon: Icon, label, value, color = 'text-blue-600' }: { icon: any; label: string; value?: string; color?: string }) {
    if (!value) return null;
    return (
        <div className="flex items-center gap-4">
            <div className={clsx("size-10 rounded-2xl flex items-center justify-center flex-shrink-0", "bg-slate-50 dark:bg-white/5", color)}>
                <Icon size={18} />
            </div>
            <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.15em]">{label}</p>
                <p className="text-sm font-bold text-slate-800 dark:text-white">{value}</p>
            </div>
        </div>
    );
}

function Badge({ label, color = 'blue' }: { label: string; color?: string }) {
    const styles: Record<string, string> = {
        blue:   'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-200/50 dark:border-blue-500/20',
        violet: 'bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-200/50 dark:border-violet-500/20',
        emerald:'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/50 dark:border-emerald-500/20',
        rose:   'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200/50 dark:border-rose-500/20',
    };
    return (
        <span className={clsx("inline-flex items-center px-3 py-1 rounded-xl border text-[9px] font-black uppercase tracking-[0.15em]", styles[color] ?? styles.blue)}>
            {label}
        </span>
    );
}

export default function MemberDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();

    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const loadMember = async () => {
        if (!token || !id) return;
        try {
            setLoading(true);
            const data = await apiFetch<any>(`/crm/members/${id}`, { token });
            setMember(data);
        } catch {
            toast.error('Error al cargar expediente de miembro');
        } finally {
            setLoading(false);
        }
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadMember(); }, [id, token]);

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] items-center justify-center gap-3">
                <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center">
                    <User className="text-blue-600 animate-pulse" size={24} />
                </div>
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 animate-pulse">Cargando expediente...</p>
            </div>
        );
    }

    if (!member) return null;

    const initials = `${member.first_name?.charAt(0) ?? ''}${member.last_name?.charAt(0) ?? ''}`.toUpperCase();

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/admin' },
                    { label: 'Membresía', icon: User, href: '/admin/members' },
                    { label: `${member.first_name} ${member.last_name}`, icon: User },
                ]}
                rightActions={
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <PencilLine size={14} /> Editar Expediente
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10">
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    className="max-w-5xl mx-auto space-y-8">

                    {/* Hero */}
                    <header className="bg-white dark:bg-[#15171c] rounded-3xl border border-slate-200 dark:border-white/5 p-6 lg:p-10 shadow-sm flex flex-col md:flex-row md:items-center gap-8 relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-6 opacity-[0.03] pointer-events-none text-blue-600">
                            <User size={180} />
                        </div>
                        <motion.div whileHover={{ scale: 1.04 }}
                            className="size-28 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-black text-4xl shadow-2xl shadow-blue-500/25 border-4 border-white dark:border-[#1e1f21] flex-shrink-0 relative z-10">
                            {initials || <User size={48} />}
                        </motion.div>
                        <div className="relative z-10 space-y-3">
                            <h1 className="text-3xl lg:text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                                {member.first_name} <span className="text-blue-600">{member.last_name}</span>
                            </h1>
                            <div className="flex flex-wrap items-center gap-2">
                                {member.church_role && <Badge label={member.church_role.toUpperCase()} color="violet" />}
                                {member.spiritual_status && <Badge label={member.spiritual_status.toUpperCase()} color="emerald" />}
                                {member.is_baptized && <Badge label="BAUTIZADO" color="blue" />}
                            </div>
                            {member.joined_date && (
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                    Miembro desde {new Date(member.joined_date).toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                                </p>
                            )}
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Contacto */}
                        <div className="lg:col-span-2 space-y-6">
                            <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm space-y-5">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Canales de Comunicación</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                    <InfoRow icon={Phone} label="Teléfono Móvil" value={member.phone} />
                                    <InfoRow icon={Mail} label="Correo Electrónico" value={member.email} />
                                    <InfoRow icon={MapPin} label="Dirección" value={member.address} color="text-rose-500" />
                                    <InfoRow icon={Briefcase} label="Ocupación" value={member.occupation} color="text-violet-600" />
                                </div>
                            </div>

                            {/* Stats rápidos */}
                            <div className="grid grid-cols-3 gap-3">
                                {[
                                    { label: 'Salud Esp.', value: member.spiritual_health ? `${Math.round(member.spiritual_health * 100)}%` : '—', icon: Heart, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
                                    { label: 'Progreso', value: member.academy_progress ? `${Math.round(member.academy_progress)}%` : '—', icon: GraduationCap, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-500/10' },
                                    { label: 'Familia', value: member.family_id ? `#${member.family_id}` : '—', icon: Users, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-500/10' },
                                ].map(s => {
                                    const Icon = s.icon;
                                    return (
                                        <div key={s.label} className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-4 shadow-sm flex flex-col gap-3">
                                            <div className={clsx("size-9 rounded-xl flex items-center justify-center", s.bg, s.color)}>
                                                <Icon size={16} />
                                            </div>
                                            <div>
                                                <p className="text-xl font-black text-slate-900 dark:text-white tracking-tighter">{s.value}</p>
                                                <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">{s.label}</p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Info ministerial */}
                        <aside className="space-y-6">
                            <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm space-y-5">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Posición Ministerial</p>
                                <div className="space-y-4">
                                    {member.ministry_id && (
                                        <div className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-black/20 rounded-xl">
                                            <div className="size-8 rounded-xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600"><Briefcase size={15} /></div>
                                            <div>
                                                <p className="text-[9px] text-slate-400 font-black uppercase">Ministerio</p>
                                                <p className="text-xs font-black text-slate-800 dark:text-white">#{member.ministry_id}</p>
                                            </div>
                                        </div>
                                    )}
                                    {member.joined_date && (
                                        <div className="flex items-center gap-3 p-3 bg-emerald-50 dark:bg-emerald-500/5 rounded-xl border border-emerald-100 dark:border-emerald-500/20">
                                            <div className="size-8 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600"><Zap size={15} fill="currentColor" /></div>
                                            <div>
                                                <p className="text-[9px] text-emerald-600 font-black uppercase">Ingreso a CCF</p>
                                                <p className="text-xs font-black text-slate-800 dark:text-white">{new Date(member.joined_date).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Notas pastorales (preview) */}
                            {member.pastoral_notes && (
                                <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Notas Pastorales</p>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic line-clamp-4">
                                        &ldquo;{member.pastoral_notes}&rdquo;
                                    </p>
                                    <button onClick={() => setSidebarOpen(true)}
                                        className="mt-3 text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline">
                                        Ver completo →
                                    </button>
                                </div>
                            )}
                        </aside>
                    </div>
                </motion.div>
            </main>

            {/* Sidebar de edición */}
            <AnimatePresence>
                {sidebarOpen && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setSidebarOpen(false)} />
                        <motion.aside
                            initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: '100%', opacity: 0 }}
                            transition={{ type: 'spring', damping: 26, stiffness: 260 }}
                            className="fixed top-0 right-0 h-screen z-[100] w-full max-w-[460px] shadow-2xl rounded-l-[2.5rem] overflow-hidden">
                            <MemberDetailSidebar
                                member={member}
                                onClose={() => setSidebarOpen(false)}
                                onUpdate={() => { loadMember(); setSidebarOpen(false); }}
                            />
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

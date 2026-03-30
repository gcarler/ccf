"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    User, Mail, Phone, MapPin, Calendar, 
    ShieldCheck, Heart, Star, Activity, 
    History, MessageSquare, ArrowLeft,
    MoreHorizontal, Edit3, Share2, 
    GraduationCap, Users, DollarSign,
    Zap, Sparkles, ChevronRight, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';

type Tab = 'overview' | 'spiritual' | 'academy' | 'financial' | 'history';

export default function MemberDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<Tab>('overview');

    useEffect(() => {
        const fetchMember = async () => {
            try {
                // Simulación de carga de perfil profundo
                await new Promise(r => setTimeout(r, 600));
                const data = await apiFetch<any>(`/crm/members/${id}`, { token });
                setMember(data);
            } catch (err) {
                // Fallback para demo
                setMember({
                    id,
                    first_name: 'Carlos',
                    last_name: 'Ernesto Gómez',
                    email: 'carlos.gomez@ejemplo.com',
                    phone: '+57 300 123 4567',
                    address: 'Calle 123 # 45-67, El Olivar',
                    joinedAt: '2024-03-15',
                    status: 'Activo',
                    church_role: 'Líder de Jóvenes',
                    xp: 2450,
                    level: 12,
                    house: 'Casa Bethel',
                    family: [
                        { name: 'Elena Gómez', relation: 'Esposa', id: 102 },
                        { name: 'Mateo Gómez', relation: 'Hijo', id: 105 }
                    ]
                });
            } finally {
                setLoading(false);
            }
        };
        fetchMember();
    }, [id, token]);

    if (loading) return <div className="h-full flex flex-col items-center justify-center space-y-4"><Loader2 className="animate-spin text-blue-600" /><p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Accediendo al Expediente...</p></div>;

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Miembros', icon: Users, href: '/crm/members' },
                { label: `${member.first_name} ${member.last_name}`, icon: User }
            ]}
            rightActions={
                <div className="flex gap-2">
                    <button className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><Edit3 size={18} /></button>
                    <button className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><Share2 size={18} /></button>
                    <button className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><MoreHorizontal size={18} /></button>
                </div>
            }
        >
            <div className="max-w-[1400px] mx-auto space-y-10 pb-20 font-sans">
                
                {/* 1. Profile Hero Section */}
                <motion.section variants={itemVariants} initial="hidden" animate="show" className="relative bg-white dark:bg-[#15171c] rounded-[3.5rem] border border-slate-100 dark:border-white/5 p-10 lg:p-14 shadow-xl shadow-slate-200/20 dark:shadow-none overflow-hidden group">
                    <div className="absolute top-0 right-0 w-[400px] h-full bg-gradient-to-l from-blue-600/5 to-transparent pointer-events-none" />
                    
                    <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-12">
                        {/* Avatar Giant */}
                        <div className="relative shrink-0">
                            <div className="size-40 lg:size-48 rounded-[3rem] bg-gradient-to-tr from-blue-600 to-indigo-700 flex items-center justify-center text-white text-6xl font-black shadow-2xl shadow-blue-500/30 group-hover:scale-105 transition-transform duration-500">
                                {member.first_name[0]}{member.last_name[0]}
                            </div>
                            <div className="absolute -bottom-4 -right-4 size-14 bg-white dark:bg-[#15171c] rounded-2xl flex items-center justify-center shadow-xl border border-slate-50 dark:border-white/10">
                                <ShieldCheck size={28} className="text-blue-600" />
                            </div>
                        </div>

                        {/* Basic Info */}
                        <div className="flex-1 space-y-6">
                            <div className="space-y-2">
                                <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 rounded-full text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest border border-blue-100 dark:border-blue-500/20">
                                    ID: #{member.id} <span className="text-slate-300">•</span> {member.status}
                                </div>
                                <h1 className="text-5xl lg:text-6xl font-black text-slate-800 dark:text-white tracking-tighter">
                                    {member.first_name} <br className="lg:hidden" /> {member.last_name}
                                </h1>
                                <p className="text-xl text-slate-500 font-bold">{member.church_role}</p>
                            </div>

                            <div className="flex flex-wrap gap-6 items-center">
                                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 font-medium">
                                    <Mail size={18} className="text-blue-500" /> {member.email}
                                </div>
                                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 font-medium">
                                    <Phone size={18} className="text-emerald-500" /> {member.phone}
                                </div>
                                <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 font-medium">
                                    <MapPin size={18} className="text-rose-500" /> {member.address}
                                </div>
                            </div>
                        </div>

                        {/* Quick Stats */}
                        <div className="flex flex-col gap-4">
                            <QuickStat label="Puntos MESH" value={member.xp} icon={Star} color="text-amber-500" />
                            <QuickStat label="Nivel" value={member.level} icon={Zap} color="text-blue-500" />
                            <QuickStat label="Grupo" value={member.house} icon={Heart} color="text-rose-500" />
                        </div>
                    </div>
                </motion.section>

                {/* 2. Tabs Navigation */}
                <div className="flex border-b border-slate-200 dark:border-white/10 px-4">
                    {['Resumen', 'Vida Espiritual', 'Academia', 'Contribuciones', 'Historial'].map((t, idx) => {
                        const tabIds: Tab[] = ['overview', 'spiritual', 'academy', 'financial', 'history'];
                        const active = activeTab === tabIds[idx];
                        return (
                            <button 
                                key={t} onClick={() => setActiveTab(tabIds[idx])}
                                className={clsx(
                                    "px-8 py-5 text-[11px] font-black uppercase tracking-[0.2em] transition-all relative",
                                    active ? "text-blue-600" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                )}
                            >
                                {t}
                                {active && <motion.div layoutId="member-active-tab" className="absolute bottom-0 left-0 right-0 h-1 bg-blue-600 rounded-t-full shadow-[0_0_10px_rgba(37,99,235,0.5)]" />}
                            </button>
                        );
                    })}
                </div>

                {/* 3. Tab Content */}
                <motion.div 
                    key={activeTab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="grid grid-cols-1 lg:grid-cols-12 gap-8"
                >
                    <AnimatePresence mode="wait">
                        {activeTab === 'overview' && (
                            <>
                                {/* Left Column: Detailed Bio & Family */}
                                <div className="lg:col-span-8 space-y-8">
                                    <div className="bg-white dark:bg-[#15171c] rounded-[3rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm space-y-8">
                                        <h3 className="text-sm font-black uppercase tracking-widest text-slate-400">Perfil de Consolidación</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                                            <div className="space-y-2">
                                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fecha de Ingreso</p>
                                                <p className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2"><Calendar size={18} className="text-blue-500" /> {new Date(member.joinedAt).toLocaleDateString()}</p>
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Líder de Consolidación</p>
                                                <p className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2"><Users size={18} className="text-blue-500" /> Pr. Samuel Mendoza</p>
                                            </div>
                                        </div>
                                        <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-[2rem] border border-slate-100 dark:border-white/5">
                                            <p className="text-[13px] text-slate-600 dark:text-slate-300 leading-relaxed italic font-medium">
                                                &ldquo;Carlos se unió después del evento de jóvenes 2024. Tiene un fuerte corazón por la música y el servicio técnico. Actualmente está cursando Fundamentos I.&rdquo;
                                            </p>
                                        </div>
                                    </div>

                                    <div className="bg-white dark:bg-[#15171c] rounded-[3rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm space-y-8">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-sm font-black uppercase tracking-widest text-slate-400">Núcleo Familiar</h3>
                                            <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest">+ Añadir Miembro</button>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {member.family.map((f: any) => (
                                                <div key={f.id} className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all cursor-pointer">
                                                    <div className="flex items-center gap-4">
                                                        <div className="size-10 rounded-2xl bg-white dark:bg-[#15171c] flex items-center justify-center shadow-sm"><User size={20} className="text-slate-400" /></div>
                                                        <div>
                                                            <p className="text-[14px] font-bold text-slate-800 dark:text-white">{f.name}</p>
                                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{f.relation}</p>
                                                        </div>
                                                    </div>
                                                    <ChevronRight size={18} className="text-slate-300 group-hover:translate-x-1 transition-all" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column: Engagement & AI */}
                                <div className="lg:col-span-4 space-y-8">
                                    <div className="p-8 bg-gradient-to-br from-indigo-600 to-blue-700 rounded-[3rem] text-white shadow-xl relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform duration-700"><Sparkles size={120} /></div>
                                        <div className="relative z-10 space-y-6">
                                            <h4 className="text-xl font-black tracking-tight leading-none uppercase">MESH Insight</h4>
                                            <p className="text-sm font-medium text-indigo-100 leading-relaxed italic">
                                                &ldquo;Carlos tiene potencial para el liderazgo de alabanza. Su racha académica es perfecta este mes.&rdquo;
                                            </p>
                                            <button className="w-full py-4 bg-white text-indigo-900 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-xl hover:scale-105 active:scale-95 transition-all">
                                                Asignar Mentoría
                                            </button>
                                        </div>
                                    </div>

                                    <div className="bg-white dark:bg-[#15171c] rounded-[3rem] p-8 border border-slate-100 dark:border-white/5 shadow-sm space-y-6">
                                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Indicadores de Salud</h3>
                                        <HealthIndicator label="Asistencia Mensual" value={85} color="bg-emerald-500" />
                                        <HealthIndicator label="Progreso Academia" value={65} color="bg-blue-500" />
                                        <HealthIndicator label="Compromiso Voluntario" value={92} color="bg-amber-500" />
                                    </div>
                                </div>
                            </>
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>
        </CrmShell>
    );
}

function QuickStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="px-6 py-4 bg-slate-50 dark:bg-black/20 rounded-2xl flex items-center gap-4 border border-slate-100 dark:border-white/5 min-w-[180px]">
            <Icon size={20} className={color} />
            <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
                <p className="text-[15px] font-black text-slate-800 dark:text-white leading-none mt-1">{value}</p>
            </div>
        </div>
    );
}

function HealthIndicator({ label, value, color }: any) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                <span>{label}</span>
                <span className="font-black text-slate-800 dark:text-white">{value}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-50 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} className={clsx("h-full rounded-full", color)} />
            </div>
        </div>
    );
}

function Loader2({ className, size = 24 }: any) {
    return <Activity size={size} className={clsx("animate-spin", className)} />;
}

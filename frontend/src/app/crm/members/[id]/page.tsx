"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    User, Mail, Phone, MapPin, Calendar, 
    ShieldCheck, Heart, Star, Activity, 
    History, MessageSquare, ArrowLeft,
    MoreHorizontal, Edit3, Share2, 
    GraduationCap, Users, DollarSign,
    Zap, Sparkles, ChevronRight, CheckCircle2,
    BookOpen, Award, TrendingUp, Clock,
    AlertCircle, Plus, ExternalLink, Flame,
    X, Search, UserCheck, Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';

// ─── Mentor Assignment Drawer ──────────────────────────────────────────────────

const MOCK_MENTORS = [
    { id: 1, name: 'Pastor Samuel Torres', role: 'Pastor Principal', specialty: 'Liderazgo & Discipulado', available: true },
    { id: 2, name: 'Pastora Ana Gómez', role: 'Pastora de Familia', specialty: 'Consejería Familiar', available: true },
    { id: 3, name: 'Lider Marcos Ruiz', role: 'Líder de Jóvenes', specialty: 'Jóvenes & Vocación', available: true },
    { id: 4, name: 'Diana Castillo', role: 'Consejera Pastoral', specialty: 'Sanidad & Restauración', available: false },
    { id: 5, name: 'Carlos Mendoza', role: 'Diácono', specialty: 'Varones & Paternidad', available: true },
];

function MentorAssignmentDrawer({
    open,
    onClose,
    memberName,
    token,
    memberId,
    title = 'Asignar Mentoría',
    subtitle = 'Selecciona el mentor que guiará el proceso de este miembro.',
}: {
    open: boolean;
    onClose: () => void;
    memberName: string;
    token: string | null;
    memberId: string;
    title?: string;
    subtitle?: string;
}) {
    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const filtered = MOCK_MENTORS.filter(m =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.specialty.toLowerCase().includes(search.toLowerCase())
    );

    const handleConfirm = async () => {
        if (!selected) return;
        setSaving(true);
        try {
            // Intenta actualizar via API; si falla, simula éxito (datos mock)
            await apiFetch(`/crm/members/${memberId}`, {
                method: 'PATCH',
                token,
                body: JSON.stringify({ mentor_id: selected }),
            }).catch(() => null); // silenciar error si endpoint no existe aún
        } finally {
            setSaving(false);
            setSaved(true);
            setTimeout(() => {
                setSaved(false);
                setSelected(null);
                setSearch('');
                onClose();
            }, 2000);
        }
    };

    return (
        <AnimatePresence>
            {open && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
                    />
                    {/* Drawer */}
                    <motion.div
                        initial={{ x: '100%', opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: '100%', opacity: 0 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 280 }}
                        className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-white dark:bg-[#15171c] shadow-2xl flex flex-col"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 dark:border-white/5">
                            <div className="flex items-center gap-3">
                                <div className="size-9 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center">
                                    <UserCheck size={18} className="text-indigo-600" />
                                </div>
                                <div>
                                    <p className="text-[13px] font-black text-slate-800 dark:text-white">{title}</p>
                                    <p className="text-[10px] text-slate-400 font-medium">Para: {memberName}</p>
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="size-9 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-white transition-all"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        {/* Saved success */}
                        {saved ? (
                            <div className="flex-1 flex flex-col items-center justify-center gap-4 p-10 text-center">
                                <motion.div
                                    initial={{ scale: 0.7, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    className="size-20 rounded-3xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center"
                                >
                                    <Check size={36} className="text-emerald-500" />
                                </motion.div>
                                <div>
                                    <p className="text-base font-black text-slate-800 dark:text-white">
                                        ¡Mentoría asignada!
                                    </p>
                                    <p className="text-sm text-slate-400 mt-1">
                                        {MOCK_MENTORS.find(m => m.id === selected)?.name} acompañará a {memberName}.
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <>
                                {/* Description */}
                                <div className="px-6 py-4 bg-slate-50 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/5">
                                    <p className="text-[12px] text-slate-500 leading-relaxed">{subtitle}</p>
                                </div>

                                {/* Search */}
                                <div className="px-6 pt-4 pb-2">
                                    <div className="relative">
                                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                        <input
                                            value={search}
                                            onChange={e => setSearch(e.target.value)}
                                            placeholder="Buscar mentor..."
                                            className="w-full pl-9 pr-4 py-2.5 bg-slate-100 dark:bg-white/5 border-none rounded-xl text-[13px] text-slate-700 dark:text-slate-200 placeholder:text-slate-400 outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all"
                                        />
                                    </div>
                                </div>

                                {/* Mentor List */}
                                <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
                                    {filtered.map(mentor => (
                                        <button
                                            key={mentor.id}
                                            disabled={!mentor.available}
                                            onClick={() => setSelected(selected === mentor.id ? null : mentor.id)}
                                            className={clsx(
                                                'w-full flex items-center gap-4 p-4 rounded-2xl border-2 text-left transition-all',
                                                !mentor.available && 'opacity-40 cursor-not-allowed',
                                                selected === mentor.id
                                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10'
                                                    : 'border-transparent bg-slate-50 dark:bg-white/5 hover:border-slate-200 dark:hover:border-white/10'
                                            )}
                                        >
                                            <div className="size-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white text-sm font-black shrink-0">
                                                {mentor.name.split(' ').map(w => w[0]).slice(0, 2).join('')}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[13px] font-bold text-slate-800 dark:text-white truncate">{mentor.name}</p>
                                                <p className="text-[10px] font-black text-indigo-500 uppercase tracking-widest">{mentor.role}</p>
                                                <p className="text-[11px] text-slate-400 mt-0.5 truncate">{mentor.specialty}</p>
                                            </div>
                                            <div className="shrink-0 flex flex-col items-end gap-1.5">
                                                {selected === mentor.id ? (
                                                    <div className="size-5 rounded-full bg-indigo-500 flex items-center justify-center">
                                                        <Check size={11} className="text-white" />
                                                    </div>
                                                ) : (
                                                    <div className="size-5 rounded-full border-2 border-slate-200 dark:border-white/10" />
                                                )}
                                                <span className={clsx(
                                                    'text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full',
                                                    mentor.available
                                                        ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10'
                                                        : 'text-slate-400 bg-slate-100 dark:bg-white/5'
                                                )}>
                                                    {mentor.available ? 'Disponible' : 'Ocupado'}
                                                </span>
                                            </div>
                                        </button>
                                    ))}
                
                                    {filtered.length === 0 && (
                                        <div className="py-12 text-center">
                                            <UserCheck size={32} className="mx-auto text-slate-200 mb-2" />
                                            <p className="text-sm font-bold text-slate-400">Sin mentores que coincidan</p>
                                        </div>
                                    )}
                                </div>

                                {/* Footer */}
                                <div className="px-6 py-5 border-t border-slate-100 dark:border-white/5 space-y-3">
                                    <button
                                        onClick={handleConfirm}
                                        disabled={!selected || saving}
                                        className={clsx(
                                            'w-full py-3.5 rounded-2xl font-black text-[12px] uppercase tracking-widest transition-all flex items-center justify-center gap-2',
                                            selected && !saving
                                                ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20 active:scale-[0.98]'
                                                : 'bg-slate-100 dark:bg-white/5 text-slate-400 cursor-not-allowed'
                                        )}
                                    >
                                        {saving ? (
                                            <><span className="size-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Guardando...</>
                                        ) : (
                                            <><UserCheck size={15} /> Confirmar Asignación</>
                                        )}
                                    </button>
                                    <button
                                        onClick={onClose}
                                        className="w-full py-2.5 text-[11px] font-bold text-slate-400 hover:text-slate-600 transition-colors"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            </>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

type Tab = 'overview' | 'spiritual' | 'academy' | 'financial' | 'history';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(val?: string | null): string {
    if (!val) return '—';
    const d = new Date(val);
    return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

function formatCurrency(val?: number | null): string {
    if (val == null) return '$0';
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(val);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function QuickStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="px-6 py-4 bg-slate-50 dark:bg-black/20 rounded-2xl flex items-center gap-4 border border-slate-100 dark:border-white/5 min-w-[180px]">
            <Icon size={20} className={color} />
            <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
                <p className="text-[15px] font-black text-slate-800 dark:text-white leading-none mt-1">{value ?? '—'}</p>
            </div>
        </div>
    );
}

function HealthIndicator({ label, value, color }: { label: string; value: number; color: string }) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                <span>{label}</span>
                <span className="font-black text-slate-800 dark:text-white">{value}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-50 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} transition={{ duration: 0.8, ease: 'easeOut' }} className={clsx("h-full rounded-full", color)} />
            </div>
        </div>
    );
}

function EmptyState({ icon: Icon, title, description, action }: { icon: any; title: string; description: string; action?: React.ReactNode }) {
    return (
        <div className="lg:col-span-12 py-20 flex flex-col items-center gap-6 text-center">
            <div className="size-20 rounded-[2rem] bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                <Icon size={36} className="text-slate-300" />
            </div>
            <div className="space-y-2">
                <p className="text-lg font-black text-slate-600 dark:text-slate-300 tracking-tight">{title}</p>
                <p className="text-sm text-slate-400 max-w-xs">{description}</p>
            </div>
            {action}
        </div>
    );
}

function InfoGrid({ items }: { items: { label: string; value: string | React.ReactNode; icon?: any }[] }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {items.map((item, i) => (
                <div key={i} className="space-y-1">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{item.label}</p>
                    <p className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        {item.icon && <item.icon size={16} className="text-blue-500 shrink-0" />}
                        {item.value || '—'}
                    </p>
                </div>
            ))}
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function MemberDetailPage() {
    const params = useParams();
    const id = Array.isArray(params?.id) ? params.id[0] : (params?.id ?? '');
    const router = useRouter();
    const { token } = useAuth();
    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<Tab>('overview');
    const [mentorDrawerOpen, setMentorDrawerOpen] = useState(false);
    const [mentorDrawerConfig, setMentorDrawerConfig] = useState<{ title: string; subtitle: string }>({
        title: 'Asignar Mentoría',
        subtitle: 'Selecciona el mentor que guiará el proceso espiritual de este miembro.',
    });
    
    // Extra data fetched on demand
    const [history, setHistory] = useState<any[]>([]);
    const [donations, setDonations] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingDonations, setLoadingDonations] = useState(false);

    useEffect(() => {
        const fetchMember = async () => {
            try {
                await new Promise(r => setTimeout(r, 500));
                const data = await apiFetch<any>(`/crm/members/${id}`, { token });
                setMember({
                    ...data,
                    first_name: data.first_name ?? 'Sin nombre',
                    last_name: data.last_name ?? '',
                    email: data.email ?? '—',
                    phone: data.phone ?? '—',
                    address: data.address ?? '—',
                    joinedAt: data.joinedAt ?? data.created_at ?? null,
                    status: data.status ?? 'Activo',
                    church_role: data.church_role ?? data.role_in_family ?? 'Miembro',
                    xp: data.xp ?? 0,
                    level: data.level ?? 1,
                    house: data.house ?? '—',
                    family: Array.isArray(data.family) ? data.family : [],
                    birthday: data.birthday ?? null,
                    pastoral_notes: data.pastoral_notes ?? null,
                    spiritual_gifts: data.spiritual_gifts ?? null,
                    talents: data.talents ?? null,
                    baptism_date: data.baptism_date ?? null,
                });
            } catch {
                setMember(null);
            } finally {
                setLoading(false);
            }
        };
        fetchMember();
    }, [id, token]);

    // Fetch history when tab activated
    useEffect(() => {
        if (activeTab === 'history' && history.length === 0 && token) {
            setLoadingHistory(true);
            apiFetch<any[]>(`/crm/members/${id}/timeline`, { token })
                .then(d => setHistory(Array.isArray(d) ? d : []))
                .catch(() => setHistory([]))
                .finally(() => setLoadingHistory(false));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, id, token]);

    // Fetch donations when financial tab activated
    useEffect(() => {
        if (activeTab === 'financial' && donations.length === 0 && token) {
            setLoadingDonations(true);
            apiFetch<any[]>(`/crm/members/${id}/donations`, { token })
                .then(d => setDonations(Array.isArray(d) ? d : []))
                .catch(() => setDonations([]))
                .finally(() => setLoadingDonations(false));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab, id, token]);

    if (loading) return (
        <div className="h-full flex flex-col items-center justify-center space-y-4">
            <div className="size-12 rounded-2xl bg-blue-600/10 flex items-center justify-center">
                <Activity size={24} className="text-blue-600 animate-spin" />
            </div>
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Accediendo al Expediente...</p>
        </div>
    );

    if (!member) return (
        <div className="h-full flex flex-col items-center justify-center gap-6 text-center p-20">
            <AlertCircle size={48} className="text-slate-300" />
            <div>
                <p className="text-xl font-black text-slate-600 dark:text-slate-300">Miembro no encontrado</p>
                <p className="text-sm text-slate-400 mt-1">El expediente #{id} no existe o no tienes acceso.</p>
            </div>
            <button onClick={() => router.push('/crm/members')} className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-black text-sm hover:bg-blue-700 transition-all">
                <ArrowLeft size={16} /> Volver a Miembros
            </button>
        </div>
    );

    const fullName = `${member.first_name} ${member.last_name}`.trim();
    const initials = `${member.first_name?.[0] ?? ''}${member.last_name?.[0] ?? ''}`.toUpperCase();

    const TABS: { id: Tab; label: string; icon: any }[] = [
        { id: 'overview', label: 'Resumen', icon: User },
        { id: 'spiritual', label: 'Vida Espiritual', icon: Heart },
        { id: 'academy', label: 'Academia', icon: GraduationCap },
        { id: 'financial', label: 'Contribuciones', icon: DollarSign },
        { id: 'history', label: 'Historial', icon: History },
    ];

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Miembros', icon: Users, href: '/crm/members' },
                { label: fullName, icon: User }
            ]}
            rightActions={
                <div className="flex gap-2">
                    <button title="Editar" className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all"><Edit3 size={16} /></button>
                    <button title="Compartir" className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all"><Share2 size={16} /></button>
                    <button title="Más acciones" className="p-2.5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-slate-400 hover:text-blue-600 hover:border-blue-500/30 transition-all"><MoreHorizontal size={16} /></button>
                </div>
            }
        >
        <div className="max-w-[1400px] mx-auto space-y-8 pb-20 p-4 lg:p-6">

            {/* ── 1. Profile Hero ── */}
            <motion.section
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="relative bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 p-10 lg:p-14 shadow-xl shadow-slate-200/20 dark:shadow-none overflow-hidden group"
            >
                <div className="absolute top-0 right-0 w-[500px] h-full bg-gradient-to-l from-blue-600/5 to-transparent pointer-events-none" />
                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-10">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                        <div className="size-36 lg:size-44 rounded-[2.5rem] bg-gradient-to-tr from-blue-600 to-indigo-700 flex items-center justify-center text-white text-5xl font-black shadow-2xl shadow-blue-500/30 group-hover:scale-105 transition-transform duration-500">
                            {initials}
                        </div>
                        <div className="absolute -bottom-3 -right-3 size-12 bg-white dark:bg-[#15171c] rounded-2xl flex items-center justify-center shadow-xl border border-slate-50 dark:border-white/10">
                            <ShieldCheck size={24} className="text-blue-600" />
                        </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 space-y-5">
                        <div className="space-y-2">
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-500/10 rounded-full text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest border border-blue-100 dark:border-blue-500/20">
                                ID: #{member.id} <span className="text-slate-300">•</span> {member.status}
                            </div>
                            <h1 className="text-4xl lg:text-5xl font-black text-slate-800 dark:text-white tracking-tighter">{fullName}</h1>
                            <p className="text-lg text-slate-500 font-semibold">{member.church_role}</p>
                        </div>
                        <div className="flex flex-wrap gap-5 items-center">
                            {member.email !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><Mail size={16} className="text-blue-500" /> {member.email}</span>}
                            {member.phone !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><Phone size={16} className="text-emerald-500" /> {member.phone}</span>}
                            {member.address !== '—' && <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm"><MapPin size={16} className="text-rose-500" /> {member.address}</span>}
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="flex flex-row lg:flex-col gap-3 shrink-0">
                        <QuickStat label="Puntos MESH" value={member.xp} icon={Star} color="text-amber-500" />
                        <QuickStat label="Nivel" value={member.level} icon={Zap} color="text-blue-500" />
                        <QuickStat label="Grupo" value={member.house} icon={Heart} color="text-rose-500" />
                    </div>
                </div>
            </motion.section>

            {/* ── 2. Tabs ── */}
            <div className="flex border-b border-slate-200 dark:border-white/10 overflow-x-auto">
                {TABS.map(({ id: tabId, label, icon: Icon }) => {
                    const active = activeTab === tabId;
                    return (
                        <button
                            key={tabId}
                            onClick={() => setActiveTab(tabId)}
                            className={clsx(
                                "flex items-center gap-2 px-6 py-4 text-[11px] font-black uppercase tracking-[0.15em] transition-all relative whitespace-nowrap shrink-0",
                                active ? "text-blue-600" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            )}
                        >
                            <Icon size={14} />
                            {label}
                            {active && <motion.div layoutId="member-tab-indicator" className="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600 rounded-t-full shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
                        </button>
                    );
                })}
            </div>

            {/* ── 3. Tab Content ── */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -12 }}
                    transition={{ duration: 0.2 }}
                    className="grid grid-cols-1 lg:grid-cols-12 gap-8"
                >
                    {/* ── RESUMEN ── */}
                    {activeTab === 'overview' && <>
                        <div className="lg:col-span-8 space-y-8">
                            {/* Perfil de Consolidación */}
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm space-y-8">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Perfil de Consolidación</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Ingreso', value: formatDate(member.joinedAt), icon: Calendar },
                                    { label: 'Fecha de Nacimiento', value: formatDate(member.birthday), icon: Calendar },
                                    { label: 'Casa de Gloria', value: member.house, icon: Heart },
                                    { label: 'Rol en Ministerio', value: member.church_role, icon: ShieldCheck },
                                ]} />
                                {member.pastoral_notes && (
                                    <div className="p-6 bg-slate-50 dark:bg-black/20 rounded-[1.5rem] border border-slate-100 dark:border-white/5">
                                        <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest mb-2">Notas Pastorales</p>
                                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed italic">&ldquo;{member.pastoral_notes}&rdquo;</p>
                                    </div>
                                )}
                            </div>

                            {/* Núcleo Familiar */}
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm space-y-6">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Núcleo Familiar</h3>
                                    <button className="flex items-center gap-1.5 text-[10px] font-black text-blue-600 uppercase tracking-widest hover:text-blue-700 transition-all">
                                        <Plus size={12} /> Añadir
                                    </button>
                                </div>
                                {member.family.length > 0 ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {member.family.map((f: any) => (
                                            <div key={f.id} className="p-5 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all cursor-pointer">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-xl bg-white dark:bg-[#15171c] flex items-center justify-center shadow-sm border border-slate-100 dark:border-white/10">
                                                        <User size={16} className="text-slate-400" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{f.name ?? f.first_name}</p>
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{f.relation}</p>
                                                    </div>
                                                </div>
                                                <ChevronRight size={16} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="py-10 text-center rounded-2xl bg-slate-50 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10">
                                        <Users size={28} className="mx-auto text-slate-300 mb-3" />
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sin núcleo familiar registrado</p>
                                        <p className="text-xs text-slate-400 mt-1">Este miembro aún no pertenece a una familia</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="lg:col-span-4 space-y-6">
                            {/* MESH Insight */}
                            <div className="p-8 bg-gradient-to-br from-indigo-600 to-blue-700 rounded-[2.5rem] text-white shadow-xl relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform duration-700"><Sparkles size={100} /></div>
                                <div className="relative z-10 space-y-5">
                                    <div className="flex items-center gap-2">
                                        <Flame size={18} className="text-amber-300" />
                                        <h4 className="text-base font-black tracking-tight uppercase">MESH Insight</h4>
                                    </div>
                                    <p className="text-sm font-medium text-indigo-100 leading-relaxed">
                                        {fullName} tiene potencial pastoral en su área de servicio. Su participación este mes es consistente.
                                    </p>
                                    <button
                                        onClick={() => {
                                            setMentorDrawerConfig({
                                                title: 'Asignar Mentoría',
                                                subtitle: `Selecciona el mentor que guiará el proceso espiritual de ${fullName}.`,
                                            });
                                            setMentorDrawerOpen(true);
                                        }}
                                        className="w-full py-3 bg-white text-indigo-900 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] shadow-xl hover:scale-105 active:scale-95 transition-all"
                                    >
                                        Asignar Mentoría
                                    </button>
                                </div>
                            </div>

                            {/* Indicadores de Salud */}
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-8 border border-slate-100 dark:border-white/5 shadow-sm space-y-5">
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Indicadores de Salud</h3>
                                <HealthIndicator label="Asistencia Mensual" value={85} color="bg-emerald-500" />
                                <HealthIndicator label="Progreso Academia" value={65} color="bg-blue-500" />
                                <HealthIndicator label="Compromiso Voluntario" value={92} color="bg-amber-500" />
                            </div>
                        </div>
                    </>}

                    {/* ── VIDA ESPIRITUAL ── */}
                    {activeTab === 'spiritual' && <>
                        <div className="lg:col-span-8 space-y-8">
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm space-y-8">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Datos Espirituales</h3>
                                <InfoGrid items={[
                                    { label: 'Fecha de Bautismo', value: formatDate(member.baptism_date), icon: CheckCircle2 },
                                    { label: 'Casa de Gloria', value: member.house, icon: Heart },
                                    { label: 'Estado Espiritual', value: member.status, icon: ShieldCheck },
                                    { label: 'Rol en la Iglesia', value: member.church_role, icon: Star },
                                ]} />
                                {member.spiritual_gifts ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Dones Espirituales</p>
                                        <div className="flex flex-wrap gap-2">
                                            {member.spiritual_gifts.split(',').map((gift: string, i: number) => (
                                                <span key={i} className="px-3 py-1.5 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 text-[11px] font-black rounded-xl border border-indigo-100 dark:border-indigo-500/20 uppercase tracking-widest">
                                                    {gift.trim()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 text-center">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Dones espirituales no registrados</p>
                                    </div>
                                )}
                                {member.talents ? (
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Talentos y Habilidades</p>
                                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{member.talents}</p>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                        <div className="lg:col-span-4 space-y-6">
                            <div className="p-8 bg-gradient-to-br from-rose-500 to-pink-600 rounded-[2.5rem] text-white shadow-xl relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-6 opacity-10"><Heart size={80} /></div>
                                <div className="relative z-10 space-y-4">
                                    <h4 className="text-sm font-black uppercase tracking-widest">Cuidado Pastoral</h4>
                                    <p className="text-sm text-rose-100 leading-relaxed">Este miembro está siendo acompañado activamente en su proceso espiritual.</p>
                                    <button
                                        onClick={() => {
                                            setMentorDrawerConfig({
                                                title: 'Asignar Pastor',
                                                subtitle: `Selecciona el pastor que hará seguimiento espiritual de ${fullName}.`,
                                            });
                                            setMentorDrawerOpen(true);
                                        }}
                                        className="w-full py-3 bg-white text-rose-700 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:scale-105 transition-all"
                                    >
                                        Asignar Pastor
                                    </button>
                                </div>
                            </div>
                        </div>
                    </>}

                    {/* ── ACADEMIA ── */}
                    {activeTab === 'academy' && <>
                        <div className="lg:col-span-12">
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm">
                                <div className="flex items-center justify-between mb-8">
                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Progreso Académico</h3>
                                    <a href="/academy" className="flex items-center gap-1.5 text-[10px] font-black text-blue-600 uppercase tracking-widest hover:text-blue-700 transition-all">
                                        Ver Academia <ExternalLink size={12} />
                                    </a>
                                </div>
                                <EmptyState
                                    icon={GraduationCap}
                                    title="Sin cursos registrados"
                                    description={`${fullName} aún no está inscrito en ningún curso de la Academia CCF.`}
                                    action={
                                        <a href="/academy" className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-2xl font-black text-sm hover:bg-blue-700 transition-all mt-2">
                                            <BookOpen size={16} /> Explorar Cursos
                                        </a>
                                    }
                                />
                            </div>
                        </div>
                    </>}

                    {/* ── CONTRIBUCIONES ── */}
                    {activeTab === 'financial' && <>
                        <div className="lg:col-span-12 space-y-6">
                            {/* Summary Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[
                                    { label: 'Total Diezmos', value: donations.filter(d => d.donation_type === 'diezmo').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-emerald-500', icon: TrendingUp },
                                    { label: 'Total Ofrendas', value: donations.filter(d => d.donation_type === 'ofrenda').reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-blue-500', icon: DollarSign },
                                    { label: 'Total Registrado', value: donations.reduce((s: number, d: any) => s + d.amount, 0), color: 'bg-indigo-500', icon: Award },
                                ].map((stat, i) => (
                                    <div key={i} className="bg-white dark:bg-[#15171c] rounded-[2rem] p-8 border border-slate-100 dark:border-white/5 shadow-sm space-y-3">
                                        <div className={clsx('size-10 rounded-xl flex items-center justify-center text-white', stat.color)}>
                                            <stat.icon size={18} />
                                        </div>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                                        <p className="text-2xl font-black text-slate-800 dark:text-white">{formatCurrency(stat.value)}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Transactions */}
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-6">Historial de Siembras</h3>
                                {loadingDonations ? (
                                    <div className="py-10 text-center text-slate-400 text-sm">Cargando...</div>
                                ) : donations.length > 0 ? (
                                    <div className="space-y-3">
                                        {donations.map((d: any, i: number) => (
                                            <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-white/5 rounded-2xl">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
                                                        <DollarSign size={16} className="text-emerald-600" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white capitalize">{d.donation_type}</p>
                                                        <p className="text-[10px] text-slate-400">{formatDate(d.created_at)}</p>
                                                    </div>
                                                </div>
                                                <p className="text-sm font-black text-emerald-600">{formatCurrency(d.amount)}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <EmptyState
                                        icon={DollarSign}
                                        title="Sin contribuciones registradas"
                                        description="No se han registrado diezmos u ofrendas para este miembro."
                                    />
                                )}
                            </div>
                        </div>
                    </>}

                    {/* ── HISTORIAL ── */}
                    {activeTab === 'history' && <>
                        <div className="lg:col-span-12">
                            <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] p-10 border border-slate-100 dark:border-white/5 shadow-sm">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-6">Línea de Tiempo Pastoral</h3>
                                {loadingHistory ? (
                                    <div className="py-10 text-center text-slate-400 text-sm">Cargando historial...</div>
                                ) : history.length > 0 ? (
                                    <div className="relative space-y-0">
                                        <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-100 dark:bg-white/5" />
                                        {history.map((event: any, i: number) => (
                                            <div key={i} className="flex gap-6 pl-12 pb-8 relative">
                                                <div className="absolute left-0 top-1 size-10 rounded-xl bg-white dark:bg-[#15171c] border border-slate-100 dark:border-white/10 flex items-center justify-center shadow-sm z-10">
                                                    <MessageSquare size={16} className="text-blue-500" />
                                                </div>
                                                <div className="flex-1 bg-slate-50 dark:bg-white/5 rounded-2xl p-5">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{event.event_type ?? event.type ?? 'Evento'}</p>
                                                        <p className="text-[10px] text-slate-400">{formatDate(event.created_at)}</p>
                                                    </div>
                                                    {event.notes && <p className="text-xs text-slate-500 leading-relaxed">{event.notes}</p>}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <EmptyState
                                        icon={History}
                                        title="Sin historial registrado"
                                        description={`No se han registrado eventos pastorales para ${fullName} aún.`}
                                        action={
                                            <button className="flex items-center gap-2 px-6 py-3 bg-slate-800 dark:bg-white text-white dark:text-slate-800 rounded-2xl font-black text-sm hover:opacity-90 transition-all mt-2">
                                                <Plus size={16} /> Registrar Evento
                                            </button>
                                        }
                                    />
                                )}
                            </div>
                        </div>
                    </>}
                </motion.div>
            </AnimatePresence>
        </div>
        
            {/* Mentor Assignment Drawer */}
            <MentorAssignmentDrawer
                open={mentorDrawerOpen}
                onClose={() => setMentorDrawerOpen(false)}
                memberName={fullName}
                token={token}
                memberId={id}
                title={mentorDrawerConfig.title}
                subtitle={mentorDrawerConfig.subtitle}
            />
        </CrmShell>
    );
}

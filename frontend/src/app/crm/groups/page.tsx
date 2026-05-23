"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { motion } from 'framer-motion';
import {
    Home,
    MapPin,
    MoreHorizontal,
    LayoutDashboard,
    Users,
    Search,
    TrendingUp,
    Star,
    ChevronRight,
    Calendar,
    Shield,
    UserPlus,
    Activity,
    Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

const ZONE_COLORS = ['from-blue-500 to-indigo-600', 'from-blue-500 to-sky-600', 'from-emerald-500 to-teal-600', 'from-orange-500 to-amber-600', 'from-rose-500 to-pink-600', 'from-sky-500 to-cyan-600'];

function getZoneColor(id: number) {
    return ZONE_COLORS[id % ZONE_COLORS.length];
}

interface GloryHouse {
    id: number;
    name: string;
    zone?: string;
    address?: string;
    leader_name?: string;
    members_count?: number;
    capacity?: number;
    schedule?: string;
    status?: string;
    created_at?: string;
    latitude?: number;
    longitude?: number;
    code?: string;
    leader_id?: number;
    assistant_id?: number;
    host_id?: number;
    day_of_week?: string;
    start_time?: string;
    end_time?: string;
    base_attendee_ids?: number[];
    base_attendees?: Array<{ member_id: number }>;
}

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    church_role?: string;
}


export default function CrmGroupsPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [groups, setGroups] = useState<GloryHouse[]>([]);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [members, setMembers] = useState<Member[]>([]);
    const [inviteGroup, setInviteGroup] = useState<GloryHouse | null>(null);
    const [memberQuery, setMemberQuery] = useState('');
    const [assigningMemberId, setAssigningMemberId] = useState<number | null>(null);

    const loadGroups = useCallback(async () => {
        if (!token) return;
        try {
            const data = await apiFetch<GloryHouse[]>('/crm/glory-houses', { token }).catch(() => []);
            setGroups(data);
        } catch {
            toast.error('Error al cargar Casas de Bendición');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadGroups();
    }, [loadGroups]);

    useEffect(() => {
        if (!token || !inviteGroup) return;
        apiFetch<Member[]>('/crm/members/', { token })
            .then(data => setMembers(Array.isArray(data) ? data : []))
            .catch(() => toast.error('No se pudo cargar la lista de miembros'));
    }, [inviteGroup, token]);

    const filtered = useMemo(() => {
        if (!query) return groups;
        const q = query.toLowerCase();
        return groups.filter(g =>
            g.name?.toLowerCase().includes(q) ||
            g.zone?.toLowerCase().includes(q) ||
            g.leader_name?.toLowerCase().includes(q)
        );
    }, [groups, query]);

    const stats = useMemo(() => {
        const total = groups.length;
        const totalMembers = groups.reduce((acc, g) => acc + (g.members_count || 0), 0);
        const active = groups.filter(g => g.status === 'Activo' || !g.status).length;
        const avgCapacity = total > 0 ? Math.round(groups.reduce((acc, g) => acc + ((g.members_count || 0) / (g.capacity || 20) * 100), 0) / total) : 0;
        return { total, totalMembers, active, avgCapacity };
    }, [groups]);

    const filteredMembers = useMemo(() => {
        const term = memberQuery.trim().toLowerCase();
        if (!term) return members;
        return members.filter(member =>
            `${member.first_name} ${member.last_name}`.toLowerCase().includes(term) ||
            member.church_role?.toLowerCase().includes(term)
        );
    }, [memberQuery, members]);

    const handleInviteMember = async (memberId: number) => {
        if (!token || !inviteGroup) return;
        setAssigningMemberId(memberId);
        try {
            const detail = await apiFetch<GloryHouse>(`/crm/glory-houses/${inviteGroup.id}`, { token });
            const current = new Set(detail.base_attendee_ids || detail.base_attendees?.map(member => member.member_id) || []);
            current.add(memberId);
            const updated = await apiFetch<GloryHouse>(`/crm/glory-houses/${inviteGroup.id}`, {
                method: 'PUT',
                token,
                body: {
                    code: detail.code,
                    name: detail.name,
                    zone: detail.zone,
                    address: detail.address,
                    leader_id: detail.leader_id,
                    assistant_id: detail.assistant_id,
                    host_id: detail.host_id,
                    capacity: detail.capacity,
                    day_of_week: detail.day_of_week,
                    start_time: detail.start_time,
                    end_time: detail.end_time,
                    status: detail.status,
                    base_attendee_ids: Array.from(current),
                },
            });
            setGroups(prev => prev.map(group => group.id === updated.id ? { ...group, ...updated } : group));
            setInviteGroup(updated);
            toast.success('Miembro agregado a la casa');
        } catch {
            toast.error('No se pudo agregar el miembro');
        } finally {
            setAssigningMemberId(null);
        }
    };


    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Casas de Bendición', icon: Home },
            ]}
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {/* Hero Header */}
                <div className="relative bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-700 px-3 py-2 overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_rgba(255,255,255,0.1)_0%,_transparent_60%)] pointer-events-none" />
                    <div className="absolute -top-4 -left-12 size-56 rounded-full bg-white/5 blur-3xl" />
                    <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div>
                            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-emerald-200 mb-2">Evangelismo · Faros en Casa</p>
                            <h1 className="text-lg font-bold text-white tracking-tight mb-1">Casas de Bendición</h1>
                            <p className="text-emerald-200 text-sm font-medium">Red de células y grupos de discipulado CCF</p>
                        </div>

                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-3 -mt-3 mb-3 relative z-10">
                    {[
                        { label: 'Total Casas', value: stats.total, icon: Home, bg: 'bg-emerald-500' },
                        { label: 'Miembros Activos', value: stats.totalMembers, icon: Users, bg: 'bg-blue-500' },
                        { label: 'Casas Activas', value: stats.active, icon: Activity, bg: 'bg-blue-500' },
                        { label: 'Ocup. Promedio', value: `${stats.avgCapacity}%`, icon: TrendingUp, bg: 'bg-amber-500' },
                    ].map(s => (
                        <div key={s.label} className="bg-white dark:bg-[#252528] rounded-lg border border-slate-200/70 dark:border-white/5 p-3 shadow-sm hover:shadow-lg transition-all duration-300">
                            <div className={`inline-flex size-8 rounded-xl ${s.bg} items-center justify-center text-white mb-3 shadow-md`}>
                                <s.icon size={18} />
                            </div>
                            <div className="text-xl font-bold text-slate-900 dark:text-white">{loading ? '—' : s.value}</div>
                            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mt-1">{s.label}</p>
                        </div>
                    ))}
                </div>

                <div className="px-3 space-y-3 pb-12">
                    {/* Search */}
                    <div className="relative max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            placeholder="Buscar por nombre, zona o líder..."
                            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-11 pr-4 text-xs font-medium outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 transition-all placeholder:text-slate-400"
                        />
                    </div>


                    {/* Loading */}
                    {loading && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                            {[...Array(6)].map((_, i) => <div key={i} className="bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse h-52" />)}
                        </div>
                    )}

                    {/* Empty */}
                    {!loading && filtered.length === 0 && (
                        <div className="py-4 text-center">
                            <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center mx-auto mb-3">
                                <Home size={36} className="text-slate-300 dark:text-slate-600" />
                            </div>
                            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide mb-2">Sin casas registradas</h3>
                            <p className="text-sm text-slate-400 font-medium mb-3">
                                {query ? `No se encontraron casas con "${query}"` : 'Registra la primera Casa de Bendición de la red.'}
                            </p>

                        </div>
                    )}

                    {/* Cards */}
                    {!loading && filtered.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                            {filtered.map((group, idx) => {
                                const occupancy = group.capacity ? Math.round((group.members_count || 0) / group.capacity * 100) : 0;
                                const isActive = !group.status || group.status === 'Activo';
                                return (
                                    <motion.div
                                        key={group.id}
                                        initial={{ opacity: 0, y: 16 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.04 }}
                                        onClick={() => router.push(`/crm/groups/${group.id}`)}
                                        className="group bg-white dark:bg-[#252528] rounded-lg border border-slate-200/70 dark:border-white/5 overflow-hidden shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 hover:-translate-y-1 transition-all duration-300 cursor-pointer"
                                    >
                                        {/* Card top accent */}
                                        <div className={`h-[3px] bg-gradient-to-r ${getZoneColor(group.id)}`} />

                                        <div className="p-4">
                                            <div className="flex items-start justify-between mb-4">
                                                <div className={`size-9 rounded-lg bg-gradient-to-br ${getZoneColor(group.id)} flex items-center justify-center text-white shadow-lg`}>
                                                    <Home size={22} />
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide ${isActive ? 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-white/5 text-slate-400'}`}>
                                                        {isActive ? 'Activo' : group.status}
                                                    </span>
                                                    <button onClick={e => { e.stopPropagation(); }} className="p-1.5 text-slate-300 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                                                        <MoreHorizontal size={16} />
                                                    </button>
                                                </div>
                                            </div>

                                            <h3 className="text-[15px] font-bold text-slate-900 dark:text-white mb-1 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                                                {group.name}
                                            </h3>

                                            <div className="space-y-1.5 mt-3 mb-4">
                                                {group.address && (
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <MapPin size={11} className="shrink-0" />
                                                        <span className="text-[11px] font-medium truncate">{group.address}</span>
                                                    </div>
                                                )}
                                                {group.zone && (
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <Star size={11} className="shrink-0" />
                                                        <span className="text-[11px] font-medium">Zona: {group.zone}</span>
                                                    </div>
                                                )}
                                                {group.leader_name && (
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <Shield size={11} className="shrink-0" />
                                                        <span className="text-[11px] font-medium">Líder: {group.leader_name}</span>
                                                    </div>
                                                )}
                                                {group.schedule && (
                                                    <div className="flex items-center gap-2 text-slate-400">
                                                        <Calendar size={11} className="shrink-0" />
                                                        <span className="text-[11px] font-medium">{group.schedule}</span>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Occupancy bar */}
                                            <div className="space-y-1.5">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Ocupación</span>
                                                    <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">
                                                        {group.members_count || 0}/{group.capacity || '—'}
                                                    </span>
                                                </div>
                                                <div className="h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                                    <motion.div
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${Math.min(occupancy, 100)}%` }}
                                                        transition={{ duration: 0.8, delay: idx * 0.04 + 0.2, ease: 'easeOut' }}
                                                        className={`h-full rounded-full bg-gradient-to-r ${getZoneColor(group.id)}`}
                                                    />
                                                </div>
                                            </div>

                                            <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100 dark:border-white/5">
                                                <div className="flex items-center gap-1.5 text-slate-400">
                                                    <Users size={13} />
                                                    <span className="text-[11px] font-bold">{group.members_count || 0} miembros</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button onClick={e => { e.stopPropagation(); setInviteGroup(group); }} className="p-2 text-slate-300 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-xl transition-colors">
                                                        <UserPlus size={14} />
                                                    </button>
                                                    <ChevronRight size={16} className="text-slate-200 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all" />
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </main>
            <WorkspaceDrawer
                isOpen={Boolean(inviteGroup)}
                onClose={() => {
                    setInviteGroup(null);
                    setMemberQuery('');
                }}
                title="Invitar persona"
                subtitle={inviteGroup ? `Agregar miembro a ${inviteGroup.name}` : undefined}
            >
                <div className="space-y-2">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            value={memberQuery}
                            onChange={event => setMemberQuery(event.target.value)}
                            placeholder="Buscar miembro..."
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-11 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-white/10 dark:bg-white/5 dark:text-white"
                        />
                    </div>
                    <div className="space-y-2">
                        {filteredMembers.map(member => (
                            <div key={member.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-4 dark:border-white/10">
                                <div>
                                    <p className="text-sm font-bold text-slate-900 dark:text-white">{member.first_name} {member.last_name}</p>
                                    <p className="text-[11px] text-slate-400">{member.church_role || 'Miembro'}</p>
                                </div>
                                <button
                                    onClick={() => handleInviteMember(member.id)}
                                    disabled={assigningMemberId === member.id}
                                    className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-[10px] font-bold uppercase tracking-wide text-white disabled:opacity-60"
                                >
                                    {assigningMemberId === member.id ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />}
                                    Agregar
                                </button>
                            </div>
                        ))}
                        {filteredMembers.length === 0 && (
                            <div className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-sm text-slate-400 dark:border-white/10">
                                No se encontraron miembros.
                            </div>
                        )}
                    </div>
                </div>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

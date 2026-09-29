"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { extractErrorMessage, apiFetch } from '@/lib/http';
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
import { Grupo } from '@/types/crm';

const ZONE_COLORS = ['from-[hsl(var(--info))] to-[hsl(var(--info))]', 'from-[hsl(var(--info))] to-[hsl(var(--info))]', 'from-[hsl(var(--success))] to-[hsl(var(--domain-teal))]', 'from-[hsl(var(--warning))] to-[hsl(var(--warning))]', 'from-[hsl(var(--danger))] to-[hsl(var(--domain-pink))]', 'from-[hsl(var(--info))] to-[hsl(var(--domain-cyan))]'];

function getZoneColor(id: string) {
    const n = parseInt(String(id).replace(/-/g, '').slice(-4), 16) || 0;
    return ZONE_COLORS[n % ZONE_COLORS.length];
}

interface Persona {
    id: string;
    nombre_completo?: string;
    first_name?: string;
    last_name?: string;
    church_role?: string;
}


export default function CrmGroupsPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [groups, setGroups] = useState<Grupo[]>([]);
    const [loading, setLoading] = useState(true);
    const [groupsError, setGroupsError] = useState<string | null>(null);
    const [query, setQuery] = useState('');
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [personasError, setPersonasError] = useState<string | null>(null);
    const [inviteGroup, setInviteGroup] = useState<Grupo | null>(null);
    const [personaQuery, setPersonaQuery] = useState('');
    const [assigningPersonaId, setAssigningPersonaId] = useState<string | null>(null);

    const loadGroups = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setGroupsError(null);
        try {
            const data = await apiFetch<Grupo[]>('/crm/grupos', { token });
            setGroups(data);
        } catch (err) {
            setGroups([]);
            const message = extractErrorMessage(err, 'Error al cargar grupos');
            setGroupsError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadGroups();
    }, [loadGroups]);

    useEffect(() => {
        if (!token || !inviteGroup) return;

        let cancelled = false;

        const loadPersonas = async () => {
            setPersonasError(null);
            try {
                const pageSize = 250;
                let skip = 0;
                const allPersonas: Persona[] = [];
                const MAX_PAGES = 50;
                let pageCount = 0;

                while (true) {
                    pageCount++;
                    if (pageCount > MAX_PAGES) break;
                    const data = await apiFetch<unknown>('/crm/personas/', {
                        token,
                        query: {
                            skip,
                            limit: pageSize,
                            sort_by: 'nombre_completo',
                            sort_dir: 'asc',
                        },
                    });

                    const page = Array.isArray(data)
                        ? data
                        : Array.isArray((data as { items?: Persona[] })?.items)
                            ? (data as { items: Persona[] }).items
                            : [];

                    allPersonas.push(...page);

                    if (page.length < pageSize) break;
                    skip += pageSize;
                }

                if (!cancelled) {
                    setPersonas(allPersonas);
                }
            } catch (err) {
                if (!cancelled) {
                    setPersonas([]);
                    const message = extractErrorMessage(err, 'Error al cargar grupos');
                    setPersonasError(message);
                    toast.error(message);
                }
            }
        };

        setPersonas([]);
        loadPersonas();

        return () => {
            cancelled = true;
        };
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
        const totalPersonas = groups.reduce((acc, g) => acc + (g.personas_count || 0), 0);
        const active = groups.filter(g => g.status === 'Activo' || !g.status).length;
        const avgCapacity = total > 0 ? Math.round(groups.reduce((acc, g) => acc + ((g.personas_count || 0) / (g.capacity || 20) * 100), 0) / total) : 0;
        return { total, totalPersonas, active, avgCapacity };
    }, [groups]);

    const filteredPersonas = useMemo(() => {
        const term = personaQuery.trim().toLowerCase();
        const base = [...personas].sort((a, b) => {
            const nameA = (a.nombre_completo || `${a.first_name ?? ''} ${a.last_name ?? ''}`.trim()).toLowerCase();
            const nameB = (b.nombre_completo || `${b.first_name ?? ''} ${b.last_name ?? ''}`.trim()).toLowerCase();
            return nameA.localeCompare(nameB, 'es');
        });

        if (!term) return base;
        return base.filter(persona =>
            (persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim()).toLowerCase().includes(term) ||
            persona.church_role?.toLowerCase().includes(term)
        );
    }, [personaQuery, personas]);

    const handleInvitePersona = async (personaId: string) => {
        if (!token || !inviteGroup) return;
        setAssigningPersonaId(personaId);
        try {
            const detail = await apiFetch<Grupo>(`/crm/grupos/${inviteGroup.id}`, { token });
            const leaderId = detail.lider_id ?? detail.leader_id ?? '';
            const assistantId = detail.asistente_id ?? detail.assistant_id ?? '';
            const hostId = detail.anfitrion_id ?? detail.host_id ?? '';
            const current = new Set(
                (detail.participante_ids || detail.participantes?.map(persona => persona.persona_id) || [])
                    .map(String)
            );
            current.add(personaId);
            const updated = await apiFetch<Grupo>(`/crm/grupos/${inviteGroup.id}`, {
                method: 'PUT',
                token,
                body: {
                    code: detail.code,
                    name: detail.name,
                    zone: detail.zone,
                    address: detail.address,
                    leader_id: leaderId,
                    assistant_id: assistantId,
                    host_id: hostId,
                    capacity: detail.capacity,
                    day_of_week: detail.day_of_week,
                    start_time: detail.start_time,
                    end_time: detail.end_time,
                    status: detail.status,
                    participante_ids: Array.from(current),
                },
            });
            setGroups(prev => prev.map(group => group.id === updated.id ? { ...group, ...updated } : group));
            setInviteGroup(updated);
            toast.success('Persona agregada al grupo');
        } catch {
            toast.error('No se pudo agregar el persona');
        } finally {
            setAssigningPersonaId(null);
        }
    };


    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                { label: 'Grupos', icon: Users },
            ]}
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {/* Header */}
                <div className="px-3 py-4 border-b border-[hsl(var(--border))] mb-4">
                    <h1 className="text-2xl font-bold text-[hsl(var(--foreground))] tracking-tight">Grupos</h1>
                </div>

                {groupsError && (
                    <div className="mx-3 mb-3 rounded-lg border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--warning))]">
                                No se pudo cargar la lista de grupos
                            </p>
                            <p className="text-sm text-[hsl(var(--warning))] mt-1 break-words">
                                {groupsError}
                            </p>
                        </div>
                        <button
                            onClick={loadGroups}
                            className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide shadow-sm hover:opacity-90 transition-all"
                        >
                            Reintentar
                        </button>
                    </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-3 -mt-3 mb-3 relative z-10">
                    {[
                        { label: 'Total Grupos', value: stats.total, icon: Users, bg: 'bg-[hsl(var(--success))]' },
                        { label: 'Integrantes Activos', value: stats.totalPersonas, icon: Users, bg: 'bg-[hsl(var(--primary))]' },
                        { label: 'Grupos Activos', value: stats.active, icon: Activity, bg: 'bg-[hsl(var(--primary))]' },
                        { label: 'Ocup. Promedio', value: `${stats.avgCapacity}%`, icon: TrendingUp, bg: 'bg-[hsl(var(--warning))]' },
                    ].map(s => (
                        <div key={s.label} className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm hover:shadow-md transition-all duration-300">
                            <div className={`inline-flex size-8 rounded-md ${s.bg} items-center justify-center text-[hsl(var(--primary-foreground))] mb-3 shadow-sm`}>
                                <s.icon size={18} />
                            </div>
                            <div className="text-xl font-bold text-[hsl(var(--foreground))]">{loading ? '—' : s.value}</div>
                            <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mt-1">{s.label}</p>
                        </div>
                    ))}
                </div>

                <div className="px-3 space-y-3 pb-12">
                    {/* Search */}
                    <div className="relative max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" size={16} />
                        <input
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            placeholder="Buscar por nombre, zona o líder..."
                            className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg py-1.5 pl-11 pr-4 text-xs font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] transition-all placeholder:text-[hsl(var(--muted-foreground))]"
                        />
                    </div>


                    {/* Loading */}
                    {loading && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {[...Array(6)].map((_, i) => <div key={i} className="bg-[hsl(var(--surface-2))] rounded-lg animate-pulse h-52" />)}
                        </div>
                    )}

                    {/* Empty */}
                    {!loading && !groupsError && filtered.length === 0 && (
                        <div className="py-1.5 text-center">
                            <div className="size-10 rounded-md bg-[hsl(var(--surface-2))] flex items-center justify-center mx-auto mb-3">
                                <Home size={36} className="text-[hsl(var(--muted-foreground))]" />
                            </div>
                            <h3 className="text-sm font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-2">Sin grupos registrados</h3>
                            <p className="text-sm text-[hsl(var(--muted-foreground))] font-medium mb-3">
                                {query ? `No se encontraron grupos con "${query}"` : 'Registra el primer grupo de la red.'}
                            </p>

                        </div>
                    )}

                    {/* Cards */}
                    {!loading && filtered.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {filtered.map((group, idx) => {
                                const occupancy = group.capacity ? Math.round((group.personas_count || 0) / group.capacity * 100) : 0;
                                const isActive = !group.status || group.status === 'Activo';
                                return (
                                    <motion.div
                                        key={group.id}
                                        initial={{ opacity: 0, y: 16 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.04 }}
                                        onClick={() => router.push(`/plataforma/crm/groups/${group.id}`)}
                                        className="group bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] overflow-hidden shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 cursor-pointer"
                                    >
                                        {/* Card top accent */}
                                        <div className={`h-[3px] bg-gradient-to-r ${getZoneColor(group.id)}`} />

                                        <div className="p-4">
                                            <div className="flex items-start justify-between mb-4">
                                                <div className={`size-9 rounded-lg bg-gradient-to-br ${getZoneColor(group.id)} flex items-center justify-center text-[hsl(var(--primary-foreground))] shadow-sm`}>
                                                    <Home size={22} />
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className={`px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wide ${isActive ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]' : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'}`}>
                                                        {isActive ? 'Activo' : group.status}
                                                    </span>
                                                    <button onClick={e => { e.stopPropagation(); }} className="p-1.5 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors" aria-label="Más opciones">
                                                        <MoreHorizontal size={16} />
                                                    </button>
                                                </div>
                                            </div>

                                            <h3 className="text-sm font-bold text-[hsl(var(--foreground))] mb-1 group-hover:text-[hsl(var(--primary))] transition-colors">
                                                {group.name}
                                            </h3>

                                            <div className="space-y-1.5 mt-3 mb-4">
                                                {group.address && (
                                                    <div className="flex items-center gap-2 text-[hsl(var(--muted-foreground))]">
                                                        <MapPin size={11} className="shrink-0" />
                                                        <span className="text-xs font-medium truncate">{group.address}</span>
                                                    </div>
                                                )}
                                                {group.zone && (
                                                    <div className="flex items-center gap-2 text-[hsl(var(--muted-foreground))]">
                                                        <Star size={11} className="shrink-0" />
                                                        <span className="text-xs font-medium">Zona: {group.zone}</span>
                                                    </div>
                                                )}
                                                {group.leader_name && (
                                                    <div className="flex items-center gap-2 text-[hsl(var(--muted-foreground))]">
                                                        <Shield size={11} className="shrink-0" />
                                                        <span className="text-xs font-medium">Líder: {group.leader_name}</span>
                                                    </div>
                                                )}
                                                {group.schedule && (
                                                    <div className="flex items-center gap-2 text-[hsl(var(--muted-foreground))]">
                                                        <Calendar size={11} className="shrink-0" />
                                                        <span className="text-xs font-medium">{group.schedule}</span>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Occupancy bar */}
                                            <div className="space-y-1.5">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Ocupación</span>
                                                    <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">
                                                        {group.personas_count || 0}/{group.capacity || '—'}
                                                    </span>
                                                </div>
                                                <div className="h-1.5 bg-[hsl(var(--surface-2))] rounded-full overflow-hidden">
                                                    <motion.div
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${Math.min(occupancy, 100)}%` }}
                                                        transition={{ duration: 0.8, delay: idx * 0.04 + 0.2, ease: 'easeOut' }}
                                                        className={`h-full rounded-full bg-gradient-to-r ${getZoneColor(group.id)}`}
                                                    />
                                                </div>
                                            </div>

                                            <div className="flex items-center justify-between mt-4 pt-4 border-t border-[hsl(var(--border))]">
                                                <div className="flex items-center gap-1.5 text-[hsl(var(--muted-foreground))]">
                                                    <Users size={13} />
                                                    <span className="text-xs font-bold">{group.personas_count || 0} integrantes</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button onClick={e => { e.stopPropagation(); setInviteGroup(group); }} className="p-2 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] rounded-md transition-colors" aria-label="Agregar">
                                                        <UserPlus size={14} />
                                                    </button>
                                                    <ChevronRight size={16} className="text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] group-hover:translate-x-1 transition-all" />
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
                    setPersonaQuery('');
                }}
                title="Invitar persona"
                subtitle={inviteGroup ? `Agregar persona a ${inviteGroup.name}` : undefined}
            >
                <div className="space-y-2">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]" size={16} />
                        <input
                            value={personaQuery}
                            onChange={event => setPersonaQuery(event.target.value)}
                            placeholder="Buscar persona..."
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] py-1.5 pl-11 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] text-[hsl(var(--foreground))]"
                        />
                    </div>
                    <div className="space-y-2">
                        {filteredPersonas.map(persona => (
                            <div key={persona.id} className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] p-4">
                                <div>
                                    <p className="text-sm font-bold text-[hsl(var(--foreground))]">{persona.nombre_completo || `${persona.first_name ?? ''} ${persona.last_name ?? ''}`.trim()}</p>
                                    <p className="text-xs text-[hsl(var(--muted-foreground))]">{persona.church_role || 'Persona'}</p>
                                </div>
                                <button
                                    onClick={() => handleInvitePersona(persona.id)}
                                    disabled={assigningPersonaId === persona.id}
                                    className="flex items-center gap-2 rounded-md bg-[hsl(var(--success))] px-4 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] disabled:opacity-60"
                                >
                                    {assigningPersonaId === persona.id ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />}
                                    Agregar
                                </button>
                            </div>
                        ))}
                        {personasError && (
                            <div className="rounded-lg border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-left">
                                <p className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--warning))]">
                                    No se pudo cargar la lista de personas
                                </p>
                                <p className="text-sm text-[hsl(var(--warning))] mt-1 break-words">
                                    {personasError}
                                </p>
                                <button
                                    onClick={() => {
                                        setInviteGroup(current => (current ? { ...current } : current));
                                    }}
                                    className="mt-3 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide shadow-sm hover:opacity-90 transition-all"
                                >
                                    Reintentar
                                </button>
                            </div>
                        )}
                        {!personasError && filteredPersonas.length === 0 && (
                            <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-sm text-[hsl(var(--muted-foreground))]">
                                No se encontraron personas.
                            </div>
                        )}
                    </div>
                </div>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

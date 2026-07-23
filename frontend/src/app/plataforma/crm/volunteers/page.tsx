"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { extractErrorMessage, apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Heart,
    Users,
    Plus,
    LayoutDashboard,
    Search,
    Clock,
    ChevronRight,
    Shield,
    Star,
    Loader2,
    X,
    CheckCircle2,
    CircleDot,
    Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { Volunteer } from '@/types/crm';

const TEAMS = ['Alabanza', 'Ujieres', 'Niños', 'Cocina', 'Medios', 'Oración', 'Evangelismo', 'Limpieza', 'Logística', 'Otro'];
const VOLUNTEER_ROLES = ['Líder de Equipo', 'Asistente de Líder', 'Servidor', 'Apoyo'];

const TEAM_COLORS: Record<string, string> = {
    'Alabanza': 'from-[hsl(var(--info))] to-[hsl(var(--info))]',
    'Ujieres': 'from-[hsl(var(--info))] to-[hsl(var(--info))]',
    'Niños': 'from-[hsl(var(--domain-pink))] to-[hsl(var(--danger))]',
    'Cocina': 'from-orange-500 to-[hsl(var(--warning))]',
    'Medios': 'from-[hsl(var(--domain-cyan))] to-[hsl(var(--info))]',
    'Oración': 'from-[hsl(var(--success))] to-[hsl(var(--domain-teal))]',
    'Evangelismo': 'from-[hsl(var(--warning))] to-yellow-600',
    'Limpieza': 'from-[hsl(var(--surface-3))] to-[hsl(var(--bg-muted))]',
    'Logística': 'from-[hsl(var(--info))] to-[hsl(var(--info))]',
    'Otro': 'from-[hsl(var(--domain-fuchsia))] to-[hsl(var(--domain-pink))]',
};

function getTeamColor(team: string) {
    return TEAM_COLORS[team] || 'from-[hsl(var(--surface-3))] to-[hsl(var(--bg-muted))]';
}


export default function VolunteersPage() {
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const router = useRouter();
    const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
    const [loading, setLoading] = useState(true);
    const [volunteersError, setVolunteersError] = useState<string | null>(null);
    const [query, setQuery] = useState('');
    const [teamFilter, setTeamFilter] = useState('Todos');
    const [showFilters, setShowFilters] = useState(false);
    const [showAddForm, setShowAddForm] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formErrors, setFormErrors] = useState<{ name?: boolean }>({});
    const [form, setForm] = useState({
        name: '', role: VOLUNTEER_ROLES[2], team: TEAMS[0], notes: '',
        shift_start: '', shift_end: '',
    });

    const loadVolunteers = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setVolunteersError(null);
        try {
            const data = await apiFetch<Volunteer[]>('/crm/volunteers', { token });
            setVolunteers(data);
        } catch (err) {
            setVolunteers([]);
            const message = extractErrorMessage(err, 'Error al cargar servidores');
            setVolunteersError(message);
            toast.error(message);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadVolunteers();
    }, [loadVolunteers]);

    const filtered = useMemo(() => {
        let list = volunteers;
        if (query) {
            const q = query.toLowerCase();
            list = list.filter(v =>
                v.name?.toLowerCase().includes(q) ||
                v.team?.toLowerCase().includes(q) ||
                v.role?.toLowerCase().includes(q)
            );
        }
        if (teamFilter !== 'Todos') {
            list = list.filter(v => v.team === teamFilter);
        }
        return list;
    }, [volunteers, query, teamFilter]);

    const stats = useMemo(() => {
        const total = volunteers.length;
        const teams = new Set(volunteers.map(v => v.team)).size;
        const active = volunteers.filter(v => !v.status || v.status === 'active').length;
        const leaders = volunteers.filter(v => v.role?.includes('Líder')).length;
        return { total, teams, active, leaders };
    }, [volunteers]);

    // Group by team for team-view
    const byTeam = useMemo(() => {
        const map: Record<string, Volunteer[]> = {};
        filtered.forEach(v => {
            const team = v.team || 'Sin Equipo';
            if (!map[team]) map[team] = [];
            map[team].push(v);
        });
        return map;
    }, [filtered]);

    const handleSave = async () => {
        if (!canEditCrm) return;
        const newErrors = { name: !form.name.trim() };
        setFormErrors(newErrors);
        if (newErrors.name) {
            toast.error('El nombre es obligatorio');
            return;
        }
        setSaving(true);
        try {
            await apiFetch('/crm/volunteers', {
                method: 'POST',
                token,
                body: { ...form, persona_id: null },
            });
            toast.success('Servidor registrado exitosamente');
            setShowAddForm(false);
            setForm({ name: '', role: VOLUNTEER_ROLES[2], team: TEAMS[0], notes: '', shift_start: '', shift_end: '' });
            await loadVolunteers();
        } catch {
            toast.error('Error al registrar servidor');
        } finally {
            setSaving(false);
        }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/plataforma/crm' },
                { label: 'Voluntariado', icon: Heart },
            ]}
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {/* Header */}
                <div className="px-3 py-4 border-b border-[hsl(var(--border))]/50 dark:border-white/5 mb-4 flex items-center justify-between">
                    <h1 className="text-2xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Voluntariado</h1>
                    {canEditCrm && (
                        <button
                            onClick={() => setShowAddForm(true)}
                            className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--primary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-sm hover:shadow-md hover:scale-105 transition-all active:scale-95 shrink-0"
                        >
                            <Plus size={16} /> Registrar Servidor
                        </button>
                    )}
                </div>

                {volunteersError && (
                    <div className="mx-3 mb-3 rounded-lg border border-[hsl(var(--warning)/30%)]/60 bg-warning-soft dark:bg-[hsl(var(--warning))]/10 dark:border-[hsl(var(--warning)/100%)]/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-[11px] font-bold uppercase tracking-wide text-warning-text dark:text-[hsl(var(--warning))]">No se pudo cargar el voluntariado</p>
                            <p className="text-sm text-warning-text/80 dark:text-[hsl(var(--warning)/80%)] mt-1 break-words">{volunteersError}</p>
                        </div>
                        <button
                            onClick={loadVolunteers}
                            className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:opacity-90 transition-all"
                        >
                            Reintentar
                        </button>
                    </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-3 -mt-3 mb-3 relative z-10">
                    {[
                        { label: 'Total Servidores', value: stats.total, icon: Heart, bg: 'bg-[hsl(var(--primary))]' },
                        { label: 'Equipos Activos', value: stats.teams, icon: Users, bg: 'bg-[hsl(var(--primary))]' },
                        { label: 'Disponibles', value: stats.active, icon: CheckCircle2, bg: 'bg-[hsl(var(--success))]' },
                        { label: 'Líderes de Equipo', value: stats.leaders, icon: Shield, bg: 'bg-[hsl(var(--warning))]' },
                    ].map(s => (
                        <div key={s.label} className="bg-[hsl(var(--surface-1))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-3 shadow-sm hover:shadow-lg transition-all duration-300">
                            <div className={`inline-flex size-8 rounded-md ${s.bg} items-center justify-center text-white mb-3 shadow-md`}>
                                <s.icon size={18} />
                            </div>
                            <div className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{loading ? '—' : s.value}</div>
                            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">{s.label}</p>
                        </div>
                    ))}
                </div>

                <div className="px-3 space-y-3 pb-12">
                    {/* Toolbar */}
                    <div className="flex flex-col md:flex-row md:items-center gap-3">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
                            <input
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                                placeholder="Buscar servidor, equipo o rol..."
                                aria-label="Buscar servidores"
                                className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-1.5 pl-11 pr-4 text-xs font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] focus:border-[hsl(var(--info)/40%)] transition-all placeholder:text-[hsl(var(--text-secondary))]"
                            />
                        </div>
                        <button
                            onClick={() => setShowFilters(p => !p)}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wide transition-all border ${showFilters ? 'bg-info-soft dark:bg-[hsl(var(--info))]/20 border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)] text-[hsl(var(--primary))]' : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]'}`}
                        >
                            <Filter size={14} /> Equipos
                        </button>
                    </div>

                    {/* Team Filters */}
                    <AnimatePresence>
                        {showFilters && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                                <div className="bg-[hsl(var(--surface-1))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4">
                                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Filtrar por Equipo</p>
                                    <div className="flex flex-wrap gap-2">
                                        {['Todos', ...TEAMS].map(t => (
                                            <button
                                                key={t}
                                                onClick={() => setTeamFilter(t)}
                                                className={`px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wide transition-all ${teamFilter === t ? 'bg-[hsl(var(--primary))] text-white shadow-md' : 'bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10'}`}
                                            >
                                                {t}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Add Form */}
                    <AnimatePresence>
                        {showAddForm && (
                            <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} className="bg-[hsl(var(--surface-1))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/30%)] p-4 shadow-xl">
                                <div className="flex items-center justify-between mb-5">
                                    <h3 className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">Registrar Servidor</h3>
                                    <button onClick={() => setShowAddForm(false)} aria-label="Cerrar" className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-colors"><X size={16} /></button>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">Nombre Completo *</label>
                                        <input required aria-invalid={!!formErrors.name} aria-describedby="vol-name-error" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Nombre del servidor..." className={`w-full px-3 py-2.5 text-xs font-medium bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] border rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all placeholder:text-[hsl(var(--text-secondary))] ${formErrors.name ? 'border-red-500 dark:border-red-500/50' : 'border-[hsl(var(--border))] dark:border-white/10'}`} />
                                        {formErrors.name && <p id="vol-name-error" className="text-red-500 text-xs mt-1">Campo requerido</p>}
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">Equipo</label>
                                        <select required value={form.team} onChange={e => setForm(p => ({ ...p, team: e.target.value }))} className="w-full px-3 py-2.5 text-xs font-medium bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all">
                                            {TEAMS.map(t => <option key={t}>{t}</option>)}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">Rol en el Equipo</label>
                                        <select value={form.role} onChange={e => setForm(p => ({ ...p, role: e.target.value }))} className="w-full px-3 py-2.5 text-xs font-medium bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all">
                                            {VOLUNTEER_ROLES.map(r => <option key={r}>{r}</option>)}
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">Notas (opcional)</label>
                                        <input value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} placeholder="Habilidades, disponibilidad..." className="w-full px-3 py-2.5 text-xs font-medium bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all placeholder:text-[hsl(var(--text-secondary))]" />
                                    </div>
                                </div>
                                <div className="flex justify-end gap-3 mt-5">
                                    <button onClick={() => setShowAddForm(false)} className="px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-md hover:bg-[hsl(var(--surface-3))] transition-colors">Cancelar</button>
                                    <button onClick={handleSave} disabled={saving} className="flex items-center gap-2 px-4 py-2.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] transition-all active:scale-95 disabled:opacity-60">
                                        {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                                        {saving ? 'Guardando...' : 'Registrar'}
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Loading */}
                    {loading && (
                        <div className="space-y-4">
                            {[...Array(3)].map((_, i) => <div key={i} className="bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg animate-pulse h-40" />)}
                        </div>
                    )}

                    {/* Empty */}
                    {!loading && !volunteersError && filtered.length === 0 && (
                        <div className="py-1.5 text-center">
                            <div className="size-10 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center mx-auto mb-3">
                                <Heart size={36} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                            </div>
                            <h3 className="text-sm font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-2">Sin servidores registrados</h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] font-medium mb-3">
                                {query ? `No se encontraron servidores con "${query}"` : 'Registra el primer servidor de la comunidad.'}
                            </p>
                            {!query && canEditCrm && (
                                <button onClick={() => setShowAddForm(true)} className="inline-flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] transition-all active:scale-95">
                                    <Plus size={14} /> Registrar Primer Servidor
                                </button>
                            )}
                        </div>
                    )}

                    {/* By Team Groups */}
                    {!loading && filtered.length > 0 && (
                        <div className="space-y-3">
                            {Object.entries(byTeam).map(([team, personas]) => (
                                <div key={team}>
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className={`size-8 rounded-md bg-gradient-to-br ${getTeamColor(team)} flex items-center justify-center text-white`}>
                                            <Users size={14} />
                                        </div>
                                        <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{team}</h3>
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2.5 py-0.5 rounded-full">{personas.length}</span>
                                        <div className="flex-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {personas.map((v, idx) => (
                                            <motion.div
                                                key={v.id}
                                                initial={{ opacity: 0, y: 12 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: idx * 0.03 }}
                                                onClick={() => router.push(`/plataforma/crm/volunteers/${v.id}`)}
                                                role="button"
                                                tabIndex={0}
                                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); router.push(`/plataforma/crm/volunteers/${v.id}`); } }}
                                                className="group bg-[hsl(var(--surface-1))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-3 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 cursor-pointer overflow-hidden"
                                            >
                                                <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${getTeamColor(team)} opacity-0 group-hover:opacity-100 transition-opacity`} />

                                                <div className="flex items-start justify-between mb-3">
                                                    <div className={`size-8 rounded-md bg-gradient-to-br ${getTeamColor(team)} flex items-center justify-center text-white text-xs font-bold shadow-md`}>
                                                        {String(v.name || '?')
                                                            .split(' ')
                                                            .filter(Boolean)
                                                            .map(n => n[0] ?? '')
                                                            .join('')
                                                            .slice(0, 2)
                                                            .toUpperCase()}
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <CircleDot size={10} className={`${!v.status || v.status === 'active' ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--text-secondary))]'}`} />
                                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                                                            {!v.status || v.status === 'active' ? 'Activo' : 'Inactivo'}
                                                        </span>
                                                    </div>
                                                </div>

                                                <h4 className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white mb-1 group-hover:text-[hsl(var(--primary))] dark:group-hover:text-[hsl(var(--primary))] transition-colors">
                                                    {v.name || 'Sin nombre'}
                                                </h4>

                                                <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] mb-3">
                                                    {v.role === 'Líder de Equipo' ? <Star size={11} className="text-[hsl(var(--warning))]" /> : <Shield size={11} />}
                                                    <span className="text-[11px] font-medium">{v.role || 'Servidor'}</span>
                                                </div>

                                                {(v.shift_start || v.notes) && (
                                                    <div className="pt-3 border-t border-[hsl(var(--border))] dark:border-white/5">
                                                        {v.shift_start && (
                                                            <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))] mb-1">
                                                                <Clock size={11} />
                                                                <span className="text-[11px] font-medium">
                                                                    {new Date(v.shift_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                                    {v.shift_end && ` – ${new Date(v.shift_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
                                                                </span>
                                                            </div>
                                                        )}
                                                        {v.notes && (
                                                            <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium truncate">{v.notes}</p>
                                                        )}
                                                    </div>
                                                )}

                                                <div className="flex justify-end mt-2">
                                                    <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] group-hover:translate-x-1 transition-all" />
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </CrmShell>
    );
}

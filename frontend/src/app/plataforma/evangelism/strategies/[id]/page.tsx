"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
    ArrowLeft, Flame, Calendar, Clock, CheckCircle2,
    AlertCircle, Sparkles, Save, Trash2, Users,
    BarChart3, FolderOpen, Plus, X, Home, UserPlus,
    Search, UserMinus, UserCheck
} from 'lucide-react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { motion } from 'framer-motion';

interface Strategy {
    id: number;
    name: string;
    description: string;
    typology: string;
    recurrence: string | null;
    day_of_week: string | null;
    start_time: string | null;
    event_format: string | null;
    niche_objective: string | null;
    status: 'active' | 'pending' | 'done';
    strategy_type: string;
    start_date?: string | null;
    end_date?: string | null;
    created_at: string;
    updated_at: string;
    group_count?: number;
}

interface StrategyGroup {
    id: number;
    name: string;
    zone: string | null;
    leader_name: string | null;
    members_count: number;
}

type TabId = 'overview' | 'groups' | 'sessions' | 'metrics';

const STATUS_COLORS = {
    pending: '#F59E0B',
    active: '#2563EB',
    done: '#10B981',
};

const STATUS_LABELS = {
    pending: 'No iniciada',
    active: 'Iniciada',
    done: 'Terminada',
};

const TYPOLOGY_LABELS: Record<string, string> = {
    relacional: 'Relacional',
    evento_masivo: 'Evento Masivo',
    sectorial: 'Sectorial',
};

const TYPOLOGY_COLORS: Record<string, string> = {
    relacional: '#3B82F6',
    evento_masivo: '#F97316',
    sectorial: '#8B5CF6',
};

const TABS: { id: TabId; label: string; icon: typeof Users }[] = [
    { id: 'overview', label: 'General', icon: Sparkles },
    { id: 'groups', label: 'Grupos', icon: FolderOpen },
    { id: 'sessions', label: 'Sesiones', icon: Calendar },
    { id: 'metrics', label: 'Métricas', icon: BarChart3 },
];

export default function StrategyDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = (params?.id as string) || '';
    const [strategy, setStrategy] = useState<Strategy | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editName, setEditName] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [editType, setEditType] = useState('');
    const [editStatus, setEditStatus] = useState<'active' | 'pending' | 'done'>('pending');
    const [editStartDate, setEditStartDate] = useState('');
    const [editEndDate, setEditEndDate] = useState('');
    const [activeTab, setActiveTab] = useState<TabId>('overview');
    const [groups, setGroups] = useState<StrategyGroup[]>([]);
    const [metrics, setMetrics] = useState<any>(null);
    const [members, setMembers] = useState<any[]>([]);

    // Group creation drawer
    const [isGroupDrawerOpen, setIsGroupDrawerOpen] = useState(false);
    const [groupForm, setGroupForm] = useState({
        name: '',
        zone: '',
        address: '',
        capacity: 15,
        day_of_week: '',
        start_time: '',
        end_time: '',
        leader_id: null as number | null,
        assistant_id: null as number | null,
        host_id: null as number | null,
    });
    const [groupSaving, setGroupSaving] = useState(false);

    // Group member management
    const [isMemberDrawerOpen, setIsMemberDrawerOpen] = useState(false);
    const [selectedGroup, setSelectedGroup] = useState<StrategyGroup | null>(null);
    const [groupMembers, setGroupMembers] = useState<any[]>([]);
    const [allMembers, setAllMembers] = useState<any[]>([]);
    const [memberSearch, setMemberSearch] = useState('');
    const [memberSaving, setMemberSaving] = useState(false);

    const fetchStrategy = useCallback(async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('ccf_token') || '';
            const result = await apiFetch<Strategy>(`/evangelism/strategies/${id}`, { token });
            setStrategy(result);
            setEditName(result.name);
            setEditDesc(result.description || '');
            setEditType(result.strategy_type || '');
            setEditStatus(result.status || 'pending');
            setEditStartDate(result.start_date ? result.start_date.substring(0, 10) : '');
            setEditEndDate(result.end_date ? result.end_date.substring(0, 10) : '');
        } catch {
            toast.error('Error al cargar la estrategia');
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        fetchStrategy();
    }, [fetchStrategy]);

    const fetchGroups = useCallback(async () => {
        const token = localStorage.getItem('ccf_token') || '';
        try {
            const all = await apiFetch<StrategyGroup[]>('/evangelism/glory-houses/', { token });
            setGroups((all || []).filter(g => (g as any).evangelism_strategy_id === parseInt(id)));
        } catch {
            // Silently fail
        }
    }, [id]);

    const fetchMetrics = useCallback(async () => {
        const token = localStorage.getItem('ccf_token') || '';
        try {
            const m = await apiFetch<any>(`/evangelism/strategies/${id}/metrics`, { token });
            setMetrics(m);
        } catch {
            // Silently fail
        }
    }, [id]);

    useEffect(() => {
        if (activeTab === 'groups') fetchGroups();
        if (activeTab === 'metrics') fetchMetrics();
    }, [activeTab, fetchGroups, fetchMetrics]);

    // Fetch members for leader/assistant/host dropdowns
    useEffect(() => {
        if (isGroupDrawerOpen && members.length === 0) {
            const token = localStorage.getItem('ccf_token') || '';
            apiFetch<any[]>('/crm/members/', { token }).then(m => setMembers(m || [])).catch(() => {});
        }
    }, [isGroupDrawerOpen, members.length]);

    const openGroupDrawer = () => {
        // Inherit strategy config for relacional typology
        setGroupForm({
            name: '',
            zone: '',
            address: '',
            capacity: 15,
            day_of_week: strategy?.typology === 'relacional' ? strategy.day_of_week || '' : '',
            start_time: strategy?.typology === 'relacional' ? strategy.start_time || '' : '',
            end_time: '',
            leader_id: null,
            assistant_id: null,
            host_id: null,
        });
        setIsGroupDrawerOpen(true);
    };

    const handleCreateGroup = async () => {
        if (!groupForm.name.trim()) {
            toast.error('El nombre del grupo es obligatorio');
            return;
        }
        setGroupSaving(true);
        try {
            const token = localStorage.getItem('ccf_token') || '';
            await apiFetch('/evangelism/glory-houses', {
                method: 'POST',
                token,
                body: {
                    name: groupForm.name.trim(),
                    code: null,
                    zone: groupForm.zone || null,
                    address: groupForm.address || null,
                    latitude: null,
                    longitude: null,
                    leader_name: null,
                    leader_id: groupForm.leader_id,
                    assistant_id: groupForm.assistant_id,
                    host_id: groupForm.host_id,
                    evangelism_strategy_id: parseInt(id),
                    members_count: 0,
                    capacity: groupForm.capacity,
                    status: 'active',
                    day_of_week: groupForm.day_of_week || null,
                    start_time: groupForm.start_time || null,
                    end_time: groupForm.end_time || null,
                },
            });
            toast.success('Grupo Faro creado');
            setIsGroupDrawerOpen(false);
            fetchGroups();
            fetchStrategy(); // refresh group_count
        } catch (e: any) {
            toast.error('Error al crear: ' + (e.message || 'Intente de nuevo'));
        } finally {
            setGroupSaving(false);
        }
    };

    const handleDeleteGroup = async (groupId: number, groupName: string) => {
        if (!window.confirm(`¿Eliminar "${groupName}"? Se borrará todo el historial de asistencia.`)) return;
        try {
            const token = localStorage.getItem('ccf_token') || '';
            await apiFetch(`/evangelism/glory-houses/${groupId}`, { method: 'DELETE', token });
            toast.success('Grupo eliminado');
            fetchGroups();
            fetchStrategy();
        } catch {
            toast.error('Error al eliminar');
        }
    };

    // ── Member management ──
    const openMemberDrawer = async (group: StrategyGroup) => {
        setSelectedGroup(group);
        setIsMemberDrawerOpen(true);
        const token = localStorage.getItem('ccf_token') || '';
        // Fetch all members for search
        if (allMembers.length === 0) {
            try {
                const m = await apiFetch<any[]>('/crm/members/', { token });
                setAllMembers(m || []);
            } catch { /* ignore */ }
        }
        // Fetch current group members
        try {
            const house = await apiFetch<any>(`/evangelism/glory-houses/${group.id}`, { token });
            setGroupMembers(house?.base_attendees?.map((a: any) => ({
                id: a.member_id,
                name: `${a.member?.first_name || ''} ${a.member?.last_name || ''}`.trim(),
                email: a.member?.email || '',
                role: a.role || 'asistente'
            })) || []);
        } catch {
            setGroupMembers([]);
        }
    };

    const handleSaveMembers = async () => {
        if (!selectedGroup) return;
        setMemberSaving(true);
        try {
            const token = localStorage.getItem('ccf_token') || '';
            await apiFetch(`/evangelism/glory-houses/${selectedGroup.id}`, {
                method: 'PUT',
                token,
                body: { base_attendee_ids: groupMembers.map(m => m.id) }
            });
            toast.success('Miembros actualizados');
            setIsMemberDrawerOpen(false);
            fetchGroups();
        } catch (e: any) {
            toast.error('Error al guardar: ' + (e.message || 'Intente de nuevo'));
        } finally {
            setMemberSaving(false);
        }
    };

    const addMemberToGroup = (member: any) => {
        if (groupMembers.find(m => m.id === member.id)) return;
        setGroupMembers(prev => [...prev, {
            id: member.id,
            name: `${member.first_name} ${member.last_name}`,
            email: member.email || '',
            role: 'asistente'
        }]);
    };

    const removeMemberFromGroup = (memberId: number) => {
        setGroupMembers(prev => prev.filter(m => m.id !== memberId));
    };

    const handleSave = async () => {
        if (!strategy) return;
        setSaving(true);
        try {
            const token = localStorage.getItem('ccf_token') || '';
            const body = {
                name: editName,
                description: editDesc,
                strategy_type: editType,
                status: editStatus,
                start_date: editStartDate ? new Date(editStartDate).toISOString() : null,
                end_date: editEndDate ? new Date(editEndDate).toISOString() : null,
            };
            await apiFetch(`/evangelism/strategies/${id}`, {
                method: 'PUT',
                token,
                body,
            });
            toast.success('Estrategia actualizada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            fetchStrategy();
        } catch {
            toast.error('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!strategy) return;
        if (!window.confirm('¿Está seguro de eliminar esta estrategia?')) return;
        try {
            const token = localStorage.getItem('ccf_token') || '';
            await apiFetch(`/evangelism/strategies/${id}`, { method: 'DELETE', token });
            toast.success('Estrategia eliminada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            router.push('/plataforma/evangelism');
        } catch {
            toast.error('Error al eliminar');
        }
    };

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return 'Sin fecha';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
        } catch {
            return dateStr;
        }
    };

    if (loading) {
        return (
            <EvangelismShell
                breadcrumbs={[
                    { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
                    { label: 'Estrategias', href: '/plataforma/evangelism' },
                    { label: 'Cargando...' }
                ]}
            >
                <div className="space-y-3 p-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-12 bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse" />
                    ))}
                </div>
            </EvangelismShell>
        );
    }

    if (!strategy) {
        return (
            <EvangelismShell
                breadcrumbs={[
                    { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
                    { label: 'Estrategias', href: '/plataforma/evangelism' },
                    { label: 'No encontrada' }
                ]}
            >
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <AlertCircle size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                    <h2 className="text-lg font-bold text-slate-700 dark:text-slate-300">Estrategia no encontrada</h2>
                    <button
                        onClick={() => router.push('/plataforma/evangelism')}
                        className="mt-4 px-4 h-9 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors"
                    >
                        Volver a Estrategias
                    </button>
                </div>
            </EvangelismShell>
        );
    }

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
                { label: 'Estrategias', href: '/plataforma/evangelism' },
                { label: strategy.name }
            ]}
        >
            <div className="p-4 lg:p-3 space-y-3 animate-fade-in max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <button
                            onClick={() => router.push('/plataforma/evangelism')}
                            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-all mt-1"
                        >
                            <ArrowLeft size={16} />
                        </button>
                        <div>
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white">{strategy.name}</h1>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 font-medium flex-wrap">
                                {strategy.typology && (
                                    <span
                                        className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                        style={{
                                            backgroundColor: `${TYPOLOGY_COLORS[strategy.typology]}18`,
                                            color: TYPOLOGY_COLORS[strategy.typology],
                                        }}
                                    >
                                        {TYPOLOGY_LABELS[strategy.typology]}
                                    </span>
                                )}
                                {strategy.recurrence && (
                                    <span className="inline-flex items-center gap-1.5">
                                        <Clock size={12} />
                                        {strategy.recurrence}
                                    </span>
                                )}
                                <span
                                    className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                    style={{
                                        backgroundColor: `${STATUS_COLORS[strategy.status]}18`,
                                        color: STATUS_COLORS[strategy.status],
                                    }}
                                >
                                    {STATUS_LABELS[strategy.status]}
                                </span>
                                {strategy.group_count !== undefined && (
                                    <span className="inline-flex items-center gap-1.5">
                                        <Users size={12} />
                                        {strategy.group_count} grupo{strategy.group_count !== 1 ? 's' : ''}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={handleDelete}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all"
                        title="Eliminar estrategia"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-1 border-b border-slate-200 dark:border-white/10">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
                                activeTab === tab.id
                                    ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            <tab.icon size={14} />
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                {activeTab === 'overview' && (
                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 space-y-4">
                        <div>
                            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                Nombre
                            </label>
                            <input
                                type="text"
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors"
                            />
                        </div>

                        <div>
                            <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                Descripción
                            </label>
                            <textarea
                                value={editDesc}
                                onChange={(e) => setEditDesc(e.target.value)}
                                rows={3}
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors resize-none"
                                placeholder="Detalles sobre la estrategia..."
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                    Tipo
                                </label>
                                <select
                                    value={editType}
                                    onChange={(e) => setEditType(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors"
                                >
                                    <option value="">General</option>
                                    <option value="Campaña de Alcance">Campaña de Alcance</option>
                                    <option value="Consolidación">Consolidación</option>
                                    <option value="Discipulado">Discipulado</option>
                                    <option value="Evangelismo Personal">Evangelismo Personal</option>
                                    <option value="Jesús Transforma">Jesús Transforma</option>
                                    <option value="Alcance Carcelario">Alcance Carcelario</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                    Estado
                                </label>
                                <select
                                    value={editStatus}
                                    onChange={(e) => setEditStatus(e.target.value as 'active' | 'pending' | 'done')}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors"
                                >
                                    <option value="pending">No iniciada</option>
                                    <option value="active">Iniciada</option>
                                    <option value="done">Terminada</option>
                                </select>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                    Fecha de inicio
                                </label>
                                <input
                                    type="date"
                                    value={editStartDate}
                                    onChange={(e) => setEditStartDate(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                                    Fecha de fin
                                </label>
                                <input
                                    type="date"
                                    value={editEndDate}
                                    onChange={(e) => setEditEndDate(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm text-slate-900 dark:text-white focus:border-blue-500 focus:outline-none transition-colors"
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-white/5">
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={handleSave}
                                disabled={saving}
                                className="inline-flex items-center gap-2 px-4 h-9 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-60 transition-colors"
                            >
                                <Save size={14} />
                                {saving ? 'Guardando...' : 'Guardar cambios'}
                            </motion.button>
                        </div>
                    </div>
                )}

                {activeTab === 'groups' && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                                    Grupos de esta estrategia
                                </h2>
                                {strategy.typology === 'relacional' && (
                                    <p className="text-[11px] text-slate-400 mt-0.5">
                                        Configuración heredada: {strategy.recurrence} · {strategy.day_of_week ? `Día: ${strategy.day_of_week}` : ''} {strategy.start_time ? `Hora: ${strategy.start_time}` : ''}
                                    </p>
                                )}
                            </div>
                            <button
                                onClick={openGroupDrawer}
                                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors"
                            >
                                <Plus size={14} />
                                Nuevo grupo
                            </button>
                        </div>
                        {groups.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg">
                                <Home size={32} className="text-slate-300 dark:text-slate-600 mb-2" />
                                <p className="text-sm font-medium text-slate-500">Sin grupos aún</p>
                                <p className="text-xs text-slate-400">Crea el primer grupo para esta estrategia</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {groups.map(g => (
                                    <div
                                        key={g.id}
                                        className="group bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 hover:border-blue-300 dark:hover:border-blue-800 transition-all cursor-pointer relative"
                                        onClick={() => openMemberDrawer(g)}
                                    >
                                        <button
                                            onClick={(e) => { e.stopPropagation(); handleDeleteGroup(g.id, g.name); }}
                                            className="absolute top-2 right-2 p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all z-10"
                                            title="Eliminar grupo"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); router.push(`/plataforma/evangelism/faro/${g.id}`); }}
                                            className="absolute top-2 right-8 p-1 rounded text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 opacity-0 group-hover:opacity-100 transition-all z-10"
                                            title="Ver detalle del grupo"
                                        >
                                            <Calendar size={14} />
                                        </button>
                                        <h3 className="text-sm font-bold text-slate-900 dark:text-white pr-16">{g.name}</h3>
                                        <p className="text-xs text-slate-400 mt-1">{g.zone || 'Sin zona'}</p>
                                        <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                                                <Users size={12} />
                                                {g.members_count} miembros
                                            </span>
                                            {g.leader_name && (
                                                <span>Líder: {g.leader_name}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'sessions' && (
                    <div className="space-y-3">
                        <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                            Sesiones semanales
                        </h2>
                        <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-8 text-center">
                            <Calendar size={32} className="text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                            <p className="text-sm font-medium text-slate-500">Próximamente</p>
                            <p className="text-xs text-slate-400 mt-1">Reporte semanal de asistencia</p>
                        </div>
                    </div>
                )}

                {activeTab === 'metrics' && (
                    <div className="space-y-3">
                        <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                            Métricas de la estrategia
                        </h2>
                        {!metrics ? (
                            <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-8 text-center">
                                <BarChart3 size={32} className="text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                                <p className="text-sm font-medium text-slate-500">Cargando métricas...</p>
                            </div>
                        ) : (
                            <>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Grupos</p>
                                        <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.summary.total_groups}</p>
                                    </div>
                                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Sesiones</p>
                                        <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{metrics.summary.total_sessions}</p>
                                    </div>
                                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Primeriza</p>
                                        <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">{metrics.summary.total_first_timers}</p>
                                    </div>
                                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Inasistencias</p>
                                        <p className="text-2xl font-bold text-red-500 dark:text-red-400 mt-1">{metrics.summary.total_absences}</p>
                                    </div>
                                </div>

                                {/* Weekly chart */}
                                {metrics.weekly && metrics.weekly.length > 0 && (
                                    <div className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4">
                                        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-4">Asistencia semanal</h3>
                                        <div className="flex items-end gap-2 h-32">
                                            {metrics.weekly.map((w: any) => {
                                                const max = Math.max(...metrics.weekly.map((x: any) => x.present + x.absent), 1);
                                                const height = ((w.present + w.absent) / max) * 100;
                                                return (
                                                    <div key={w.week} className="flex-1 flex flex-col items-center gap-1">
                                                        <div className="w-full flex flex-col" style={{ height: '100px' }}>
                                                            <div
                                                                className="w-full rounded-t bg-blue-500 dark:bg-blue-600 transition-all"
                                                                style={{ height: `${(w.present / max) * 100}%`, minHeight: w.present > 0 ? '4px' : '0' }}
                                                            />
                                                            {w.absent > 0 && (
                                                                <div
                                                                    className="w-full rounded-t bg-red-300 dark:bg-red-800 transition-all"
                                                                    style={{ height: `${(w.absent / max) * 100}%`, minHeight: '4px' }}
                                                                />
                                                            )}
                                                        </div>
                                                        <span className="text-[9px] text-slate-400 truncate w-full text-center">
                                                            {w.week.slice(5)}
                                                        </span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Metadata */}
                {activeTab === 'overview' && (
                    <div className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 rounded-lg p-4">
                        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3">Información</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                            <div>
                                <p className="text-slate-400 font-medium">ID</p>
                                <p className="text-slate-700 dark:text-white font-bold">#{strategy.id}</p>
                            </div>
                            <div>
                                <p className="text-slate-400 font-medium">Inicio</p>
                                <p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.start_date)}</p>
                            </div>
                            <div>
                                <p className="text-slate-400 font-medium">Fin</p>
                                <p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.end_date)}</p>
                            </div>
                            <div>
                                <p className="text-slate-400 font-medium">Última actualización</p>
                                <p className="text-slate-700 dark:text-white font-bold">{formatDate(strategy.updated_at)}</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* ── Group Creation Drawer ── */}
            <WorkspaceDrawer
                isOpen={isGroupDrawerOpen}
                onClose={() => setIsGroupDrawerOpen(false)}
                title="Nuevo Grupo Faro"
                subtitle={`Estrategia: ${strategy?.name}`}
                actions={
                    <>
                        <button
                            onClick={() => setIsGroupDrawerOpen(false)}
                            className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleCreateGroup}
                            disabled={groupSaving || !groupForm.name.trim()}
                            className="px-4 py-1.5 text-[12px] font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
                        >
                            {groupSaving ? (
                                <><Sparkles size={14} className="animate-spin" /> Creando...</>
                            ) : (
                                <><Plus size={14} /> Crear Grupo</>
                            )}
                        </button>
                    </>
                }
            >
                <div className="space-y-5">
                    {/* Strategy config notice */}
                    {strategy?.typology === 'relacional' && (
                        <div className="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-[11px] text-blue-700 dark:text-blue-300">
                            <p className="font-semibold">Configuración heredada de la estrategia</p>
                            <p>Recurrencia: {strategy.recurrence} · Día: {strategy.day_of_week} · Hora: {strategy.start_time}</p>
                        </div>
                    )}

                    {/* Name */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Nombre del grupo *
                        </label>
                        <input
                            value={groupForm.name}
                            onChange={e => setGroupForm(f => ({ ...f, name: e.target.value }))}
                            placeholder="Ej: Faro Esperanza - Norte"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>

                    {/* Zone */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Zona / Sector
                        </label>
                        <input
                            value={groupForm.zone}
                            onChange={e => setGroupForm(f => ({ ...f, zone: e.target.value }))}
                            placeholder="Ej: Zona Norte, Barrio La Paz"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>

                    {/* Address */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Dirección
                        </label>
                        <input
                            value={groupForm.address}
                            onChange={e => setGroupForm(f => ({ ...f, address: e.target.value }))}
                            placeholder="Dirección completa"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>

                    {/* Capacity */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Capacidad máxima
                        </label>
                        <input
                            type="number"
                            value={groupForm.capacity}
                            onChange={e => setGroupForm(f => ({ ...f, capacity: parseInt(e.target.value) || 15 }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>

                    {/* Day & Time */}
                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                                Día de reunión
                            </label>
                            <select
                                value={groupForm.day_of_week}
                                onChange={e => setGroupForm(f => ({ ...f, day_of_week: e.target.value }))}
                                className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            >
                                <option value="">Sin día fijo</option>
                                <option value="Domingo">Domingo</option>
                                <option value="Lunes">Lunes</option>
                                <option value="Martes">Martes</option>
                                <option value="Miércoles">Miércoles</option>
                                <option value="Jueves">Jueves</option>
                                <option value="Viernes">Viernes</option>
                                <option value="Sábado">Sábado</option>
                            </select>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                                    Inicio
                                </label>
                                <input
                                    type="time"
                                    value={groupForm.start_time}
                                    onChange={e => setGroupForm(f => ({ ...f, start_time: e.target.value }))}
                                    className="w-full px-2 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                />
                            </div>
                            <div>
                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                                    Fin
                                </label>
                                <input
                                    type="time"
                                    value={groupForm.end_time}
                                    onChange={e => setGroupForm(f => ({ ...f, end_time: e.target.value }))}
                                    className="w-full px-2 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Leader */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Líder
                        </label>
                        <select
                            value={groupForm.leader_id || ''}
                            onChange={e => setGroupForm(f => ({ ...f, leader_id: e.target.value ? parseInt(e.target.value) : null }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        >
                            <option value="">Sin asignar</option>
                            {members.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.first_name} {m.last_name} {m.church_role ? `(${m.church_role})` : ''}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Assistant */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Colíder
                        </label>
                        <select
                            value={groupForm.assistant_id || ''}
                            onChange={e => setGroupForm(f => ({ ...f, assistant_id: e.target.value ? parseInt(e.target.value) : null }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        >
                            <option value="">Sin asignar</option>
                            {members.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.first_name} {m.last_name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Host */}
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Anfitrión
                        </label>
                        <select
                            value={groupForm.host_id || ''}
                            onChange={e => setGroupForm(f => ({ ...f, host_id: e.target.value ? parseInt(e.target.value) : null }))}
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        >
                            <option value="">Sin asignar</option>
                            {members.map(m => (
                                <option key={m.id} value={m.id}>
                                    {m.first_name} {m.last_name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </WorkspaceDrawer>

            {/* ── Member Management Drawer ── */}
            <WorkspaceDrawer
                isOpen={isMemberDrawerOpen}
                onClose={() => setIsMemberDrawerOpen(false)}
                title="Gestionar Miembros"
                subtitle={selectedGroup?.name || ''}
                actions={
                    <>
                        <button
                            onClick={() => setIsMemberDrawerOpen(false)}
                            className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleSaveMembers}
                            disabled={memberSaving}
                            className="px-4 py-1.5 text-[12px] font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
                        >
                            {memberSaving ? (
                                <><Sparkles size={14} className="animate-spin" /> Guardando...</>
                            ) : (
                                <><UserCheck size={14} /> Guardar ({groupMembers.length})</>
                            )}
                        </button>
                    </>
                }
            >
                <div className="space-y-4">
                    {/* Current members */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                                Miembros actuales ({groupMembers.length})
                            </label>
                        </div>
                        {groupMembers.length === 0 ? (
                            <p className="text-xs text-slate-400 italic py-2">Sin miembros asignados</p>
                        ) : (
                            <div className="space-y-1 max-h-60 overflow-y-auto">
                                {groupMembers.map(m => (
                                    <div key={m.id} className="flex items-center justify-between px-2 py-1.5 bg-slate-50 dark:bg-white/5 rounded-md text-xs">
                                        <div>
                                            <span className="font-medium text-slate-700 dark:text-slate-200">{m.name}</span>
                                            {m.email && <span className="text-slate-400 ml-2">{m.email}</span>}
                                        </div>
                                        <button
                                            onClick={() => removeMemberFromGroup(m.id)}
                                            className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                            title="Remover"
                                        >
                                            <UserMinus size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Search and add members */}
                    <div className="border-t border-slate-100 dark:border-white/5 pt-4">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Agregar miembros
                        </label>
                        <div className="relative mb-2">
                            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                value={memberSearch}
                                onChange={e => setMemberSearch(e.target.value)}
                                placeholder="Buscar por nombre o email..."
                                className="w-full pl-9 pr-3 py-2 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            />
                        </div>
                        <div className="space-y-1 max-h-48 overflow-y-auto">
                            {allMembers
                                .filter(m => {
                                    if (!memberSearch) return true;
                                    const term = memberSearch.toLowerCase();
                                    const name = `${m.first_name} ${m.last_name}`.toLowerCase();
                                    return name.includes(term) || (m.email || '').toLowerCase().includes(term);
                                })
                                .filter(m => !groupMembers.find(gm => gm.id === m.id))
                                .slice(0, 20)
                                .map(m => (
                                    <button
                                        key={m.id}
                                        onClick={() => addMemberToGroup(m)}
                                        className="w-full flex items-center justify-between px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-white/5 rounded-md text-xs text-left transition-colors group/add"
                                    >
                                        <div>
                                            <span className="font-medium text-slate-700 dark:text-slate-200">{m.first_name} {m.last_name}</span>
                                            {m.email && <span className="text-slate-400 ml-2">{m.email}</span>}
                                        </div>
                                        <Plus size={14} className="text-slate-300 group-hover/add:text-blue-500 transition-colors" />
                                    </button>
                                ))}
                            {allMembers.filter(m => {
                                if (!memberSearch) return true;
                                const term = memberSearch.toLowerCase();
                                return `${m.first_name} ${m.last_name}`.toLowerCase().includes(term) || (m.email || '').toLowerCase().includes(term);
                            }).filter(m => !groupMembers.find(gm => gm.id === m.id)).length === 0 && (
                                <p className="text-xs text-slate-400 italic py-2">No se encontraron miembros</p>
                            )}
                        </div>
                    </div>
                </div>
            </WorkspaceDrawer>
        </EvangelismShell>
    );
}

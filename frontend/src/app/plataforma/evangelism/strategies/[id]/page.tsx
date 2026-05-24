"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
    ArrowLeft, Flame, Calendar, Clock, CheckCircle2,
    AlertCircle, Sparkles, Save, Trash2, Users,
    BarChart3, FolderOpen, Plus
} from 'lucide-react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { motion } from 'framer-motion';

interface Strategy {
    id: number;
    name: string;
    description: string;
    typology: string;
    recurrence: string | null;
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

    const fetchStrategy = useCallback(async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('auth_token') || '';
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
        const token = localStorage.getItem('auth_token') || '';
        try {
            const all = await apiFetch<StrategyGroup[]>('/evangelism/glory-houses/', { token });
            setGroups((all || []).filter(g => (g as any).evangelism_strategy_id === parseInt(id)));
        } catch {
            // Silently fail
        }
    }, [id]);

    const fetchMetrics = useCallback(async () => {
        const token = localStorage.getItem('auth_token') || '';
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

    const handleSave = async () => {
        if (!strategy) return;
        setSaving(true);
        try {
            const token = localStorage.getItem('auth_token') || '';
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
            const token = localStorage.getItem('auth_token') || '';
            await apiFetch(`/evangelism/strategies/${id}`, { method: 'DELETE', token });
            toast.success('Estrategia eliminada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            router.push('/evangelism');
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
                    { label: 'Evangelismo', icon: Flame, href: '/evangelism' },
                    { label: 'Estrategias', href: '/evangelism' },
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
                    { label: 'Evangelismo', icon: Flame, href: '/evangelism' },
                    { label: 'Estrategias', href: '/evangelism' },
                    { label: 'No encontrada' }
                ]}
            >
                <div className="flex flex-col items-center justify-center py-16 text-center">
                    <AlertCircle size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                    <h2 className="text-lg font-bold text-slate-700 dark:text-slate-300">Estrategia no encontrada</h2>
                    <button
                        onClick={() => router.push('/evangelism')}
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
                { label: 'Evangelismo', icon: Flame, href: '/evangelism' },
                { label: 'Estrategias', href: '/evangelism' },
                { label: strategy.name }
            ]}
        >
            <div className="p-4 lg:p-3 space-y-3 animate-fade-in max-w-5xl mx-auto">
                {/* Header */}
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <button
                            onClick={() => router.push('/evangelism')}
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
                            <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                                Grupos de esta estrategia
                            </h2>
                            <button
                                onClick={() => router.push(`/evangelism/faro/groups?strategy=${id}`)}
                                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors"
                            >
                                <Plus size={14} />
                                Nuevo grupo
                            </button>
                        </div>
                        {groups.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg">
                                <FolderOpen size={32} className="text-slate-300 dark:text-slate-600 mb-2" />
                                <p className="text-sm font-medium text-slate-500">Sin grupos aún</p>
                                <p className="text-xs text-slate-400">Crea grupos para esta estrategia</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {groups.map(g => (
                                    <div
                                        key={g.id}
                                        className="bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg p-4 hover:border-slate-300 dark:hover:border-white/20 transition-colors cursor-pointer"
                                        onClick={() => router.push(`/evangelism/faro/groups`)}
                                    >
                                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">{g.name}</h3>
                                        <p className="text-xs text-slate-400 mt-1">{g.zone || 'Sin zona'}</p>
                                        <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                                            <span className="flex items-center gap-1">
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
        </EvangelismShell>
    );
}

"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { 
    Flame, 
    Calendar, 
    Trash2, 
    ChevronRight, 
    Sparkles, 
    Clock, 
    CheckCircle2, 
    Save
} from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { useCreation } from '@/context/CreationContext';
import { ViewType } from '@/components/ViewSwitcher';
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { motion } from 'framer-motion';

export interface EvangelismStrategy {
    id: string;
    name: string;
    description: string;
    status: 'active' | 'pending' | 'done';
    strategy_type: string;
    start_date?: string | null;
    end_date?: string | null;
    created_at: string;
    updated_at: string;
}

export default function EvangelismClient() {
    const { token } = useAuth();
    const { openModal } = useCreation();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
    const [data, setData] = useState<EvangelismStrategy[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('table');
    const [search, setSearch] = useState('');
    const [selectedStrategy, setSelectedStrategy] = useState<EvangelismStrategy | null>(null);

    // Form fields for editing
    const [editName, setEditName] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [editType, setEditType] = useState('');
    const [editStatus, setEditStatus] = useState<'active' | 'pending' | 'done'>('pending');
    const [editStartDate, setEditStartDate] = useState('');
    const [editEndDate, setEditEndDate] = useState('');
    const [saving, setSaving] = useState(false);

    const fetchStrategies = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const result = await apiFetch<EvangelismStrategy[]>('/evangelism/strategies/', { token });
            setData(Array.isArray(result) ? result : []);
        } catch {
            toast.error('Error al cargar estrategias de evangelismo');
            setData([]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchStrategies();
    }, [fetchStrategies]);

    // Reactively refresh when a new strategy is created globally
    useEffect(() => {
        const handleCreated = () => {
            fetchStrategies();
        };
        window.addEventListener('evangelism-strategy-created', handleCreated);
        return () => {
            window.removeEventListener('evangelism-strategy-created', handleCreated);
        };
    }, [fetchStrategies]);

    // Handle closing RightPanel
    useEffect(() => {
        if (!layers?.RIGHT && selectedStrategy) {
            setSelectedStrategy(null);
        }
    }, [layers?.RIGHT, selectedStrategy]);

    const filteredData = useMemo(() => {
        if (!search) return data;
        const term = search.toLowerCase();
        return data.filter(item => 
            item.name.toLowerCase().includes(term) ||
            (item.description && item.description.toLowerCase().includes(term)) ||
            (item.strategy_type && item.strategy_type.toLowerCase().includes(term))
        );
    }, [data, search]);

    const handleAddItem = () => {
        openModal('evangelism_strategy');
    };

    const handleSelectStrategy = (strat: EvangelismStrategy) => {
        setSelectedStrategy(strat);
        setEditName(strat.name);
        setEditDesc(strat.description || '');
        setEditType(strat.strategy_type || '');
        setEditStatus(strat.status || 'pending');
        setEditStartDate(strat.start_date ? strat.start_date.substring(0, 10) : '');
        setEditEndDate(strat.end_date ? strat.end_date.substring(0, 10) : '');
        setRightMode('overlay');
        openLayer('RIGHT');
    };

    const handleUpdateItem = async (id: string, updatedFields: Partial<EvangelismStrategy>) => {
        setData(prev => prev.map(item => item.id === id ? { ...item, ...updatedFields } : item));
        try {
            await apiFetch(`/evangelism/strategies/${id}`, {
                method: 'PUT',
                token,
                body: updatedFields
            });
            toast.success('Estrategia actualizada');
            fetchStrategies();
        } catch {
            toast.error('Error al actualizar la estrategia');
            fetchStrategies();
        }
    };

    const handleSaveDetails = async () => {
        if (!selectedStrategy) return;
        setSaving(true);
        try {
            const bodyPayload = {
                name: editName,
                description: editDesc,
                strategy_type: editType,
                status: editStatus,
                start_date: editStartDate ? new Date(editStartDate).toISOString() : null,
                end_date: editEndDate ? new Date(editEndDate).toISOString() : null
            };
            await handleUpdateItem(selectedStrategy.id, bodyPayload);
            closeLayer('RIGHT');
            setSelectedStrategy(null);
        } catch {
            toast.error('Error al guardar cambios');
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteStrategy = async (id: string) => {
        if (!window.confirm('¿Está seguro de eliminar esta estrategia de evangelismo?')) return;
        try {
            await apiFetch(`/evangelism/strategies/${id}`, {
                method: 'DELETE',
                token
            });
            toast.success('Estrategia eliminada con éxito');
            closeLayer('RIGHT');
            setSelectedStrategy(null);
            fetchStrategies();
        } catch {
            toast.error('Error al eliminar la estrategia');
        }
    };

    const statusColors = {
        pending: '#F59E0B', // amber-500
        active: '#2563EB', // blue-600
        done: '#10B981', // emerald-500
    };

    const statusLabels = {
        pending: 'No iniciada',
        active: 'Iniciada',
        done: 'Terminada',
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

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Flame },
                { label: 'Estrategias' }
            ]}
            viewOptions={['table', 'board', 'list']}
            viewType={viewType}
            onViewChange={setViewType}
            onSearch={setSearch}
            onAdd={handleAddItem}
        >
            <div className="h-full flex flex-col relative">
                {loading ? (
                    <div className="p-4 space-y-4">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full rounded-lg" />)}
                    </div>
                ) : filteredData.length === 0 ? (
                    <EmptyState
                        title="No hay estrategias"
                        description="Las estrategias te permiten planificar campañas de alcance, consolidación y discipulado en tu comunidad."
                        icon={Flame}
                        onAction={handleAddItem}
                        actionLabel="Crear Estrategia"
                    />
                ) : (
                    <div className="pb-16 flex-1">
                        {/* ── TABLE VIEW ─────────────────────────────── */}
                        {viewType === 'table' && (
                            <div className="overflow-x-auto border border-slate-200 dark:border-white/[0.06] rounded-lg bg-white dark:bg-[#1e1f21]">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/10">
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-16">ID</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Estrategia</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-32">Estado</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-44">Tipo</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-40">Inicio</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-40">Fin</th>
                                            <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 w-12"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                                        {filteredData.map((strategy, idx) => (
                                            <motion.tr 
                                                key={strategy.id}
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: idx * 0.03, duration: 0.2 }}
                                                onClick={() => handleSelectStrategy(strategy)}
                                                className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02] cursor-pointer group transition-colors"
                                            >
                                                <td className="px-3 py-1.5 font-semibold text-slate-400 dark:text-slate-600">
                                                    #{strategy.id}
                                                </td>
                                                <td className="px-3 py-1.5">
                                                    <div className="text-[13px] font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                                        {strategy.name}
                                                    </div>
                                                    {strategy.description && (
                                                        <div className="text-[11px] text-slate-400 dark:text-slate-500 font-medium truncate max-w-[300px] mt-0.5">
                                                            {strategy.description}
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-3 py-1.5">
                                                    <span 
                                                        className="px-2.5 py-1 rounded-full text-[10px] font-bold"
                                                        style={{ 
                                                            backgroundColor: `${statusColors[strategy.status]}12`, 
                                                            color: statusColors[strategy.status] 
                                                        }}
                                                    >
                                                        {statusLabels[strategy.status]}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300">
                                                    {strategy.strategy_type || 'General'}
                                                </td>
                                                <td className="px-3 py-1.5 text-[12px] text-slate-500 dark:text-slate-400 font-medium">
                                                    {formatDate(strategy.start_date)}
                                                </td>
                                                <td className="px-3 py-1.5 text-[12px] text-slate-500 dark:text-slate-400 font-medium">
                                                    {formatDate(strategy.end_date)}
                                                </td>
                                                <td className="px-3 py-1.5 text-right">
                                                    <ChevronRight size={16} className="text-slate-300 group-hover:text-slate-600 dark:group-hover:text-white transition-all transform group-hover:translate-x-0.5" />
                                                </td>
                                            </motion.tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* ── BOARD VIEW ─────────────────────────────── */}
                        {viewType === 'board' && (
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-full min-h-48 items-start">
                                {/* Columns map */}
                                {(['pending', 'active', 'done'] as const).map(colStatus => {
                                    const colItems = filteredData.filter(item => item.status === colStatus);
                                    return (
                                        <div 
                                            key={colStatus}
                                            className="bg-slate-50/50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5 rounded-lg p-4 flex flex-col max-h-[80vh] overflow-y-auto scrollbar-thin"
                                        >
                                            <header className="flex items-center justify-between mb-4 px-2 shrink-0">
                                                <div className="flex items-center gap-2">
                                                    <span 
                                                        className="size-2.5 rounded-full" 
                                                        style={{ backgroundColor: statusColors[colStatus] }}
                                                    />
                                                    <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                                                        {statusLabels[colStatus]}
                                                    </h3>
                                                </div>
                                                <span className="font-semibold bg-slate-200/50 dark:bg-white/5 px-2 py-0.5 rounded-md text-slate-500">
                                                    {colItems.length}
                                                </span>
                                            </header>

                                            <div className="space-y-4">
                                                {colItems.map((strategy) => (
                                                    <motion.div
                                                        key={strategy.id}
                                                        initial={{ opacity: 0, scale: 0.96 }}
                                                        animate={{ opacity: 1, scale: 1 }}
                                                        transition={{ duration: 0.2 }}
                                                        onClick={() => handleSelectStrategy(strategy)}
                                                        className="group relative bg-white dark:bg-[#252528] rounded-lg border border-slate-200/70 dark:border-white/5 p-3 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99] border-t-4"
                                                        style={{ borderTopColor: statusColors[strategy.status] }}
                                                    >
                                                        <div className="flex items-start justify-between gap-4">
                                                            <h4 className="text-[13px] font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                                                {strategy.name}
                                                            </h4>
                                                            <span className="font-semibold text-slate-400 shrink-0">
                                                                #{strategy.id}
                                                            </span>
                                                        </div>

                                                        {strategy.description && (
                                                            <p className="text-[11px] text-slate-500 mt-2 font-medium line-clamp-2 leading-relaxed">
                                                                {strategy.description}
                                                            </p>
                                                        )}

                                                        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 flex flex-wrap gap-2 items-center justify-between">
                                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[9px] font-semibold uppercase tracking-wide bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400">
                                                                {strategy.strategy_type || 'General'}
                                                            </span>
                                                            
                                                            <div className="flex items-center gap-1 text-[10px] text-slate-400 font-bold">
                                                                <Calendar size={11} />
                                                                <span>{formatDate(strategy.start_date).split(' ')[0]}</span>
                                                                <span>-</span>
                                                                <span>{formatDate(strategy.end_date).split(' ')[0]}</span>
                                                            </div>
                                                        </div>
                                                    </motion.div>
                                                ))}

                                                {colItems.length === 0 && (
                                                    <div className="py-8 text-center border border-dashed border-slate-200 dark:border-white/5 rounded-lg text-[10px] font-bold uppercase tracking-wide text-slate-400">
                                                        Vacío
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* ── LIST VIEW ─────────────────────────────── */}
                        {viewType === 'list' && (
                            <div className="space-y-4 max-w-4xl mx-auto">
                                {filteredData.map((strategy, idx) => (
                                    <motion.div
                                        key={strategy.id}
                                        initial={{ opacity: 0, y: 12 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.03 }}
                                        onClick={() => handleSelectStrategy(strategy)}
                                        className="group bg-white dark:bg-[#252528] rounded-lg border border-slate-200/70 dark:border-white/5 p-3 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer flex items-center justify-between gap-3"
                                    >
                                        <div className="flex items-start gap-4 flex-1 min-w-0">
                                            <div 
                                                className="size-10 rounded-md flex items-center justify-center shrink-0"
                                                style={{ backgroundColor: `${statusColors[strategy.status]}12`, color: statusColors[strategy.status] }}
                                            >
                                                <Flame size={20} />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-3">
                                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                                        {strategy.name}
                                                    </h3>
                                                    <span className="font-semibold bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded">
                                                        #{strategy.id}
                                                    </span>
                                                </div>
                                                {strategy.description && (
                                                    <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 font-medium line-clamp-1">
                                                        {strategy.description}
                                                    </p>
                                                )}
                                                <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                                                    <span>Tipo: {strategy.strategy_type || 'General'}</span>
                                                    <span>•</span>
                                                    <span>Inicio: {formatDate(strategy.start_date)}</span>
                                                    <span>•</span>
                                                    <span>Fin: {formatDate(strategy.end_date)}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4">
                                            <span 
                                                className="px-2.5 py-1 rounded-full text-[10px] font-bold shrink-0"
                                                style={{ 
                                                    backgroundColor: `${statusColors[strategy.status]}12`, 
                                                    color: statusColors[strategy.status] 
                                                }}
                                            >
                                                {statusLabels[strategy.status]}
                                            </span>
                                            <ChevronRight size={18} className="text-slate-300 group-hover:text-slate-600 dark:group-hover:text-white transition-all transform group-hover:translate-x-0.5" />
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* ── RIGHT PANEL FOR DETAILS & EDITING ────────────────── */}
            {selectedStrategy && (
                <RightPanel title="Detalle de Estrategia" width={480}>
                    <div className="flex flex-col h-full overflow-hidden">
                        <header className="p-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/20 shrink-0">
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                ID #{selectedStrategy.id}
                            </span>
                            <button 
                                onClick={() => handleDeleteStrategy(selectedStrategy.id)}
                                className="p-2 hover:bg-rose-50 dark:hover:bg-rose-950/20 text-rose-500 hover:text-rose-600 rounded-md transition-colors"
                                title="Eliminar Estrategia"
                            >
                                <Trash2 size={16} />
                            </button>
                        </header>

                        <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin">
                            {/* Strategy Name */}
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                    Nombre de la Estrategia
                                </label>
                                <input
                                    type="text"
                                    value={editName}
                                    onChange={e => setEditName(e.target.value)}
                                    placeholder="Nombre..."
                                    className="w-full px-4 py-2.5 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all placeholder:text-slate-400"
                                />
                            </div>

                            {/* Strategy Type */}
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                    Tipo de Estrategia
                                </label>
                                <select
                                    value={editType}
                                    onChange={e => setEditType(e.target.value)}
                                    className="w-full px-4 py-2.5 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all text-slate-700 dark:text-slate-300"
                                >
                                    <option value="Campaña de Alcance">Campaña de Alcance</option>
                                    <option value="Consolidación">Consolidación</option>
                                    <option value="Discipulado">Discipulado</option>
                                    <option value="Evangelismo Personal">Evangelismo Personal</option>
                                </select>
                            </div>

                            {/* Status Selector */}
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                    Estado actual
                                </label>
                                <div className="grid grid-cols-3 gap-2">
                                    {(['pending', 'active', 'done'] as const).map(status => (
                                        <button
                                            key={status}
                                            type="button"
                                            onClick={() => setEditStatus(status)}
                                            className="px-3 py-2 rounded-md border text-[11px] font-bold transition-all flex flex-col items-center justify-center gap-1 shadow-sm active:scale-95"
                                            style={{
                                                borderColor: editStatus === status ? statusColors[status] : 'transparent',
                                                backgroundColor: editStatus === status ? `${statusColors[status]}15` : undefined,
                                                color: editStatus === status ? statusColors[status] : undefined,
                                            }}
                                        >
                                            {status === 'pending' && <Clock size={14} />}
                                            {status === 'active' && <Sparkles size={14} />}
                                            {status === 'done' && <CheckCircle2 size={14} />}
                                            {statusLabels[status]}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Description */}
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                    Descripción detallada
                                </label>
                                <textarea
                                    value={editDesc}
                                    onChange={e => setEditDesc(e.target.value)}
                                    rows={4}
                                    placeholder="Detalles sobre la ejecución de la estrategia..."
                                    className="w-full px-4 py-2.5 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all placeholder:text-slate-400 resize-none"
                                />
                            </div>

                            {/* Date fields */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                        Fecha de Inicio
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            value={editStartDate}
                                            onChange={e => setEditStartDate(e.target.value)}
                                            className="w-full px-4 py-2.5 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all text-slate-700 dark:text-slate-300"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                        Fecha de Finalización
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            value={editEndDate}
                                            onChange={e => setEditEndDate(e.target.value)}
                                            className="w-full px-4 py-2.5 text-[13px] font-medium bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-md outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all text-slate-700 dark:text-slate-300"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <footer className="p-4 border-t border-slate-100 dark:border-white/5 flex gap-4 bg-white dark:bg-[#1e1f21] shrink-0">
                            <button 
                                onClick={() => {
                                    closeLayer('RIGHT');
                                    setSelectedStrategy(null);
                                }}
                                className="flex-1 py-2.5 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-100 transition-all"
                            >
                                Cancelar
                            </button>
                            <button 
                                onClick={handleSaveDetails}
                                disabled={saving}
                                className="flex-1 py-2.5 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-blue-700 shadow-xl shadow-blue-500/20 active:scale-95 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
                            >
                                <Save size={12} />
                                {saving ? 'Guardando...' : 'Guardar Cambios'}
                            </button>
                        </footer>
                    </div>
                </RightPanel>
            )}
        </EvangelismShell>
    );
}

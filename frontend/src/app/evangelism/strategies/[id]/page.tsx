"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
    ArrowLeft, Flame, Calendar, Clock, CheckCircle2,
    AlertCircle, Sparkles, Save, Trash2
} from 'lucide-react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { motion } from 'framer-motion';

interface Strategy {
    id: number;
    name: string;
    description: string;
    status: 'active' | 'pending' | 'done';
    strategy_type: string;
    start_date?: string | null;
    end_date?: string | null;
    created_at: string;
    updated_at: string;
}

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

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Flame, href: '/evangelism' },
                { label: 'Estrategias', href: '/evangelism' },
                { label: strategy?.name || 'Detalle' }
            ]}
        >
 <div className="p-4 lg:p-3 space-y-3 animate-fade-in w-full">
                {loading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-12 bg-slate-100 dark:bg-white/5 rounded-lg animate-pulse" />
                        ))}
                    </div>
                ) : strategy ? (
                    <>
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
                                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 font-medium">
                                        <span className="inline-flex items-center gap-1.5">
                                            <Sparkles size={12} />
                                            {strategy.strategy_type || 'General'}
                                        </span>
                                        <span>•</span>
                                        <span
                                            className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                                            style={{
                                                backgroundColor: `${STATUS_COLORS[strategy.status]}18`,
                                                color: STATUS_COLORS[strategy.status],
                                            }}
                                        >
                                            {STATUS_LABELS[strategy.status]}
                                        </span>
                                        <span>•</span>
                                        <span className="inline-flex items-center gap-1.5">
                                            <Clock size={12} />
                                            Creada {formatDate(strategy.created_at)}
                                        </span>
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

                        {/* Form */}
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

                        {/* Metadata */}
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
                    </>
                ) : (
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
                )}
            </div>
        </EvangelismShell>
    );
}

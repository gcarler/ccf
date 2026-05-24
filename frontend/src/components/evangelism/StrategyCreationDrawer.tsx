"use client";

import React, { useState } from 'react';
import {
    Users, Flame, Target, MapPin, Clock, Sparkles, Calendar, FileText, X
} from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface StrategyCreationDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated?: () => void;
}

export default function StrategyCreationDrawer({
    isOpen,
    onClose,
    onCreated
}: StrategyCreationDrawerProps) {
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);

    // Form state
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [typology, setTypology] = useState<string>('');
    const [recurrence, setRecurrence] = useState('SEMANAL');
    const [eventFormat, setEventFormat] = useState('UNICA_LOCACION');
    const [nicheObjective, setNicheObjective] = useState('');
    const [phases, setPhases] = useState<{ name: string; type: string; start_date: string; end_date: string }[]>([]);
    const [strategyType, setStrategyType] = useState('Campaña de Alcance');
    const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState('');

    const resetForm = () => {
        setName('');
        setDescription('');
        setTypology('');
        setRecurrence('SEMANAL');
        setEventFormat('UNICA_LOCACION');
        setNicheObjective('');
        setPhases([]);
        setStrategyType('Campaña de Alcance');
        setStartDate(new Date().toISOString().split('T')[0]);
        setEndDate('');
    };

    const handleClose = () => {
        resetForm();
        onClose();
    };

    const handleSubmit = async () => {
        if (!name.trim()) {
            toast.error('El nombre de la estrategia es obligatorio');
            return;
        }
        if (!token) {
            toast.error('No hay sesión activa');
            return;
        }

        setLoading(true);
        try {
            await apiFetch('/evangelism/strategies', {
                method: 'POST',
                token,
                body: {
                    name: name.trim(),
                    description: description || null,
                    typology: typology || null,
                    recurrence: typology === 'relacional' ? recurrence : null,
                    event_format: typology === 'evento_masivo' ? eventFormat : null,
                    phases: typology === 'evento_masivo' && phases.length > 0 ? phases : null,
                    niche_objective: typology === 'sectorial' ? nicheObjective : null,
                    strategy_type: strategyType,
                    start_date: startDate ? new Date(startDate).toISOString() : null,
                    end_date: endDate ? new Date(endDate).toISOString() : null,
                    status: 'active'
                }
            });
            toast.success('Estrategia de evangelismo creada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            resetForm();
            onCreated?.();
            onClose();
        } catch (e: any) {
            console.error(e);
            toast.error('Error al crear: ' + (e.message || 'Intente de nuevo más tarde'));
        } finally {
            setLoading(false);
        }
    };

    const strategyTypes = [
        'Campaña de Alcance',
        'Consolidación',
        'Discipulado',
        'Evangelismo Personal',
        'Jesús Transforma',
        'Alcance Carcelario',
    ];

    return (
        <WorkspaceDrawer
            isOpen={isOpen}
            onClose={handleClose}
            title="Nueva Estrategia"
            subtitle="Evangelismo"
            actions={
                <>
                    <button
                        onClick={handleClose}
                        className="px-4 py-1.5 text-[12px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !name.trim()}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <Sparkles size={14} className="animate-spin" />
                                Creando...
                            </>
                        ) : (
                            <>
                                <Sparkles size={14} />
                                Crear Estrategia
                            </>
                        )}
                    </button>
                </>
            }
        >
            <div className="space-y-5">
                {/* ── Typology Selector ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Tipología
                    </label>
                    <div className="flex gap-2">
                        {[
                            { id: 'relacional', label: 'Relacional', icon: Users },
                            { id: 'evento_masivo', label: 'Evento Masivo', icon: Flame },
                            { id: 'sectorial', label: 'Sectorial', icon: Target },
                        ].map(t => (
                            <button
                                key={t.id}
                                onClick={() => setTypology(t.id)}
                                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-bold transition-all flex-1 justify-center ${
                                    typology === t.id
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'bg-slate-50 dark:bg-white/5 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10'
                                }`}
                            >
                                <t.icon size={14} />
                                {t.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* ── Relacional fields ── */}
                {typology === 'relacional' && (
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Recurrencia
                        </label>
                        <div className="flex gap-2">
                            {['SEMANAL', 'QUINCENAL', 'MENSUAL'].map(r => (
                                <button
                                    key={r}
                                    onClick={() => setRecurrence(r)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex-1 justify-center ${
                                        recurrence === r
                                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                                            : 'bg-slate-50 dark:bg-white/5 text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10'
                                    }`}
                                >
                                    <Clock size={12} />
                                    {r}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Evento Masivo fields ── */}
                {typology === 'evento_masivo' && (
                    <>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                                Formato
                            </label>
                            <div className="flex gap-2">
                                {[
                                    { id: 'UNICA_LOCACION', label: 'Una Ubicación' },
                                    { id: 'MULTILOCACION', label: 'Multi-sede' },
                                ].map(f => (
                                    <button
                                        key={f.id}
                                        onClick={() => setEventFormat(f.id)}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex-1 justify-center ${
                                            eventFormat === f.id
                                                ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-800'
                                                : 'bg-slate-50 dark:bg-white/5 text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10'
                                        }`}
                                    >
                                        <MapPin size={12} />
                                        {f.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Phases */}
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                                    Fases ({phases.length})
                                </label>
                                <button
                                    onClick={() => setPhases(prev => [...prev, { name: '', type: 'preparacion', start_date: '', end_date: '' }])}
                                    className="text-[11px] font-bold text-blue-500 hover:text-blue-600"
                                >
                                    + Agregar Fase
                                </button>
                            </div>
                            {phases.map((phase, i) => (
                                <div key={i} className="flex items-center gap-2 mb-2">
                                    <input
                                        type="text"
                                        value={phase.name}
                                        onChange={e => setPhases(prev => prev.map((p, j) => j === i ? { ...p, name: e.target.value } : p))}
                                        placeholder={`Fase ${i + 1}`}
                                        className="flex-1 px-2.5 py-1.5 text-[12px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-slate-200 focus:border-blue-500 focus:outline-none"
                                    />
                                    <select
                                        value={phase.type}
                                        onChange={e => setPhases(prev => prev.map((p, j) => j === i ? { ...p, type: e.target.value } : p))}
                                        className="px-2 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300"
                                    >
                                        <option value="preparacion">Prep.</option>
                                        <option value="impacto">Impacto</option>
                                        <option value="cosecha">Cosecha</option>
                                        <option value="seguimiento">Seg.</option>
                                    </select>
                                    <input
                                        type="date"
                                        value={phase.start_date}
                                        onChange={e => setPhases(prev => prev.map((p, j) => j === i ? { ...p, start_date: e.target.value } : p))}
                                        className="px-1.5 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300"
                                    />
                                    <button
                                        onClick={() => setPhases(prev => prev.filter((_, j) => j !== i))}
                                        className="p-1.5 text-slate-400 hover:text-red-500 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </>
                )}

                {/* ── Sectorial fields ── */}
                {typology === 'sectorial' && (
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                            Nicho Objetivo
                        </label>
                        <input
                            value={nicheObjective}
                            onChange={e => setNicheObjective(e.target.value)}
                            placeholder="Ej: Universidades, Cárceles, Fundaciones"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>
                )}

                {/* ── Strategy Type ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Tipo de Estrategia
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        {strategyTypes.map(opt => (
                            <button
                                key={opt}
                                onClick={() => setStrategyType(opt)}
                                className={`px-3 py-2 rounded-lg text-[11px] font-bold transition-all text-left ${
                                    strategyType === opt
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'bg-slate-50 dark:bg-white/5 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10'
                                }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>

                {/* ── Name ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Nombre
                    </label>
                    <input
                        value={name}
                        onChange={e => setName(e.target.value)}
                        placeholder="Nombre de la estrategia..."
                        className="w-full px-3 py-2 text-[14px] font-medium bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                    />
                </div>

                {/* ── Dates ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Periodo
                    </label>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 flex-1">
                            <Calendar size={14} className="text-slate-400 shrink-0" />
                            <input
                                type="date"
                                value={startDate}
                                onChange={e => setStartDate(e.target.value)}
                                className="flex-1 px-2.5 py-1.5 text-[12px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
                            />
                        </div>
                        <span className="text-slate-400 text-[11px] font-semibold">→</span>
                        <div className="flex items-center gap-2 flex-1">
                            <input
                                type="date"
                                value={endDate}
                                onChange={e => setEndDate(e.target.value)}
                                className="flex-1 px-2.5 py-1.5 text-[12px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
                            />
                        </div>
                    </div>
                </div>

                {/* ── Description ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Descripción
                    </label>
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Propósito u objetivos de la estrategia..."
                        className="w-full min-h-[80px] px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                    />
                </div>
            </div>
        </WorkspaceDrawer>
    );
}

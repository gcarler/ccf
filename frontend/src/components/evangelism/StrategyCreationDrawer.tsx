"use client";

import React, { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import {
    Users, Flame, Target, MapPin, Clock, Sparkles, Calendar, X
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

interface Phase {
    name: string;
    type: string;
    start_date: string;
    end_date: string;
}

interface FormValues {
    name: string;
    description: string;
    typology: string;
    recurrence: string;
    eventFormat: string;
    nicheObjective: string;
    phases: Phase[];
    strategyType: string;
    startDate: string;
    endDate: string;
}

export default function StrategyCreationDrawer({
    isOpen,
    onClose,
    onCreated
}: StrategyCreationDrawerProps) {
    const { token } = useAuth();

    const { register, handleSubmit, reset, watch, control, setValue, formState: { isSubmitting } } = useForm<FormValues>({
        defaultValues: {
            name: '',
            description: '',
            typology: '',
            recurrence: 'SEMANAL',
            eventFormat: 'UNICA_LOCACION',
            nicheObjective: '',
            phases: [],
            strategyType: 'Geográfica',
            startDate: new Date().toISOString().split('T')[0],
            endDate: '',
        }
    });

    const { fields, append, remove } = useFieldArray({ control, name: 'phases' });
    const typology = watch('typology');

    useEffect(() => {
        if (isOpen) {
            reset({
                name: '',
                description: '',
                typology: '',
                recurrence: 'SEMANAL',
                eventFormat: 'UNICA_LOCACION',
                nicheObjective: '',
                phases: [],
                strategyType: 'Geográfica',
                startDate: new Date().toISOString().split('T')[0],
                endDate: '',
            });
        }
    }, [isOpen, reset]);

    const handleClose = () => {
        reset();
        onClose();
    };

    const onSubmit = async (data: FormValues) => {
        if (!data.name.trim()) {
            toast.error('El nombre de la estrategia es obligatorio');
            return;
        }
        if (!token) {
            toast.error('No hay sesión activa');
            return;
        }

        try {
            await apiFetch('/evangelism/strategies', {
                method: 'POST',
                token,
                body: {
                    name: data.name.trim(),
                    description: data.description || null,
                    typology: data.typology || null,
                    clase_raiz: data.typology || null,
                    recurrence: data.typology === 'relacional' ? data.recurrence : null,
                    event_format: data.typology === 'evento_masivo' ? data.eventFormat : null,
                    phases: data.typology === 'evento_masivo' && data.phases.length > 0
                        ? data.phases.map(p => ({ name: p.name, type: p.type, start_date: p.start_date, end_date: p.end_date }))
                        : null,
                    niche_objective: data.typology === 'sectorial' ? data.nicheObjective : null,
                    strategy_type: data.strategyType,
                    start_date: data.startDate ? new Date(data.startDate).toISOString() : null,
                    end_date: data.endDate ? new Date(data.endDate).toISOString() : null,
                    status: 'active',
                    activa: true
                }
            });
            toast.success('Estrategia de evangelismo creada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            reset();
            onCreated?.();
            onClose();
        } catch (e: any) {
            console.error(e);
            toast.error('Error al crear: ' + (e.message || 'Intente de nuevo más tarde'));
        }
    };

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
                        onClick={handleSubmit(onSubmit)}
                        disabled={isSubmitting || !watch('name').trim()}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
                    >
                        {isSubmitting ? (
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
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
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
                                type="button"
                                onClick={() => setValue('typology', t.id)}
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
                                    type="button"
                                    onClick={() => setValue('recurrence', r)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex-1 justify-center ${
                                        watch('recurrence') === r
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
                                        type="button"
                                        onClick={() => setValue('eventFormat', f.id)}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex-1 justify-center ${
                                            watch('eventFormat') === f.id
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
                                    Fases ({fields.length})
                                </label>
                                <button
                                    type="button"
                                    onClick={() => append({ name: '', type: 'preparacion', start_date: '', end_date: '' })}
                                    className="text-[11px] font-bold text-blue-500 hover:text-blue-600"
                                >
                                    + Agregar Fase
                                </button>
                            </div>
                            {fields.map((field, i) => (
                                <div key={field.id} className="flex items-center gap-2 mb-2">
                                    <input
                                        {...register(`phases.${i}.name`)}
                                        placeholder={`Fase ${i + 1}`}
                                        className="flex-1 px-2.5 py-1.5 text-[12px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-slate-200 focus:border-blue-500 focus:outline-none"
                                    />
                                    <select
                                        {...register(`phases.${i}.type`)}
                                        className="px-2 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300"
                                    >
                                        <option value="preparacion">Prep.</option>
                                        <option value="impacto">Impacto</option>
                                        <option value="cosecha">Cosecha</option>
                                        <option value="seguimiento">Seg.</option>
                                    </select>
                                    <input
                                        type="date"
                                        {...register(`phases.${i}.start_date`)}
                                        className="px-1.5 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => remove(i)}
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
                            {...register('nicheObjective')}
                            placeholder="Ej: Universidades, Cárceles, Fundaciones"
                            className="w-full px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>
                )}

                {/* ── Name ── */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 block">
                        Nombre
                    </label>
                    <input
                        {...register('name', { required: true })}
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
                                {...register('startDate')}
                                className="flex-1 px-2.5 py-1.5 text-[12px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
                            />
                        </div>
                        <span className="text-slate-400 text-[11px] font-semibold">→</span>
                        <div className="flex items-center gap-2 flex-1">
                            <input
                                type="date"
                                {...register('endDate')}
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
                        {...register('description')}
                        placeholder="Propósito u objetivos de la estrategia..."
                        className="w-full min-h-[80px] px-3 py-2 text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

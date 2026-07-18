"use client";

import React, { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import {
    Users, Flame, Target, MapPin, Clock, Sparkles, Calendar, X
} from 'lucide-react';
import { toast } from 'sonner';
import { ApiError, apiFetch } from '@/lib/http';
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
    dayOfWeek: string;
    startTime: string;
    eventFormat: string;
    nicheObjective: string;
    phases: Phase[];
    strategyType: string;
    startDate: string;
    endDate: string;
}

function getErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
        const detail = error.detail;
        if (typeof detail === 'string') return detail;
        if (detail && typeof detail === 'object' && 'detail' in detail) {
            return String((detail as { detail?: unknown }).detail || fallback);
        }
    }
    return error instanceof Error ? error.message : fallback;
}

const formatLocalDate = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

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
            dayOfWeek: '',
            startTime: '',
            eventFormat: 'UNICA_LOCACION',
            nicheObjective: '',
            phases: [],
            strategyType: 'Geográfica',
            startDate: formatLocalDate(new Date()),
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
                dayOfWeek: '',
                startTime: '',
                eventFormat: 'UNICA_LOCACION',
                nicheObjective: '',
                phases: [],
                strategyType: 'Geográfica',
                startDate: formatLocalDate(new Date()),
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
        if (!data.typology) {
            toast.error('Selecciona una tipología (Relacional, Evento Masivo o Sectorial)');
            return;
        }
        if (data.typology === 'relacional' && !data.recurrence) {
            toast.error('Selecciona la recurrencia para estrategias relacionales');
            return;
        }
        if (data.typology === 'relacional' && !data.dayOfWeek) {
            toast.error('Selecciona el día de reunión para estrategias relacionales');
            return;
        }
        if (data.startDate && data.endDate && new Date(data.startDate) > new Date(data.endDate)) {
            toast.error('La fecha de inicio no puede ser posterior a la fecha de fin');
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
                silent: true,
                body: {
                    name: data.name.trim(),
                    description: data.description || null,
                    typology: data.typology || null,
                    clase_raiz: data.typology || null,
                    recurrence: data.typology === 'relacional' ? data.recurrence : null,
                    day_of_week: data.typology === 'relacional' ? data.dayOfWeek || null : null,
                    start_time: data.typology === 'relacional' ? data.startTime || null : null,
                    event_format: data.typology === 'evento_masivo' ? data.eventFormat : null,
                    phases: data.typology === 'evento_masivo' && data.phases.length > 0
                        ? data.phases.map(p => ({ name: p.name, type: p.type, start_date: p.start_date, end_date: p.end_date }))
                        : null,
                    niche_objective: data.typology === 'sectorial' ? data.nicheObjective : null,
                    strategy_type: data.strategyType,
                    start_date: data.startDate || null,
                    end_date: data.endDate || null,
                    status: 'active',
                    activa: true
                }
            });
            toast.success('Estrategia de evangelismo creada');
            window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            reset();
            onCreated?.();
            onClose();
        } catch (error: unknown) {
            toast.error('Error al crear: ' + getErrorMessage(error, 'Intente de nuevo más tarde'));
        }
    };

    const strategyTypes = [
        'Geográfica',
        'Temática',
        'Sectorial',
        'Poblacional',
        'Servicios (Cultos)',
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
                        className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSubmit(onSubmit)}
                        disabled={isSubmitting || !watch('name').trim()}
                        className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
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
                    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
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
                                        ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                        : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10'
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
                    <>
                    <div>
                        <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
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
                                            ? 'bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] border border-blue-200 dark:border-blue-800'
                                            : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10'
                                    }`}
                                >
                                    <Clock size={12} />
                                    {r}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                            Día de reunión <span className="text-[hsl(var(--destructive))]">*</span>
                        </label>
                        <div className="flex gap-1.5 flex-wrap">
                            {['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'].map(d => (
                                <button
                                    key={d}
                                    type="button"
                                    onClick={() => setValue('dayOfWeek', d)}
                                    className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
                                        watch('dayOfWeek') === d
                                            ? 'bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] border border-blue-200 dark:border-blue-800'
                                            : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10'
                                    }`}
                                >
                                    {d}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                            Hora de reunión
                        </label>
                        <input
                            type="time"
                            value={watch('startTime')}
                            onChange={e => setValue('startTime', e.target.value)}
                            className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>
                    </>
                )}

                {/* ── Evento Masivo fields ── */}
                {typology === 'evento_masivo' && (
                    <>
                        <div>
                            <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
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
                                                : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10'
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
                                <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                                    Fases ({fields.length})
                                </label>
                                <button
                                    type="button"
                                    onClick={() => append({ name: '', type: 'preparacion', start_date: '', end_date: '' })}
                                    className="text-[11px] font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))]"
                                >
                                    + Agregar Fase
                                </button>
                            </div>
                            {fields.map((field, i) => (
                                <div key={field.id} className="flex items-center gap-2 mb-2">
                                    <input
                                        {...register(`phases.${i}.name`)}
                                        placeholder={`Fase ${i + 1}`}
                                        className="flex-1 px-2.5 py-1.5 text-[12px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] focus:border-blue-500 focus:outline-none"
                                    />
                                    <select
                                        {...register(`phases.${i}.type`)}
                                        className="px-2 py-1.5 text-[11px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                                    >
                                        <option value="preparacion">Prep.</option>
                                        <option value="impacto">Impacto</option>
                                        <option value="cosecha">Cosecha</option>
                                        <option value="seguimiento">Seg.</option>
                                    </select>
                                    <input
                                        type="date"
                                        {...register(`phases.${i}.start_date`)}
                                        className="px-1.5 py-1.5 text-[11px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => remove(i)}
                                        className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
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
                        <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                            Nicho Objetivo
                        </label>
                        <input
                            {...register('nicheObjective')}
                            placeholder="Ej: Universidades, Cárceles, Fundaciones"
                            className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                        />
                    </div>
                )}

                {/* ── Strategy Type ── */}
                <div>
                    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                        Tipo de Estrategia
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        {strategyTypes.map(opt => (
                            <button
                                key={opt}
                                type="button"
                                onClick={() => setValue('strategyType', opt)}
                                className={`px-3 py-2 rounded-lg text-[11px] font-bold transition-all text-left ${
                                    watch('strategyType') === opt
                                        ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                        : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10'
                                }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>

                {/* ── Name ── */}
                <div>
                    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                        Nombre
                    </label>
                    <input
                        {...register('name', { required: true })}
                        placeholder="Nombre de la estrategia..."
                        className="w-full px-3 py-2 text-[14px] font-medium bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                    />
                </div>

                {/* ── Dates ── */}
                <div>
                    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                        Periodo
                    </label>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 flex-1">
                            <Calendar size={14} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            <input
                                type="date"
                                {...register('startDate')}
                                className="flex-1 px-2.5 py-1.5 text-[12px] font-semibold bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
                            />
                        </div>
                        <span className="text-[hsl(var(--text-secondary))] text-[11px] font-semibold">→</span>
                        <div className="flex items-center gap-2 flex-1">
                            <input
                                type="date"
                                {...register('endDate')}
                                className="flex-1 px-2.5 py-1.5 text-[12px] font-semibold bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 cursor-pointer"
                            />
                        </div>
                    </div>
                </div>

                {/* ── Description ── */}
                <div>
                    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">
                        Descripción
                    </label>
                    <textarea
                        {...register('description')}
                        placeholder="Propósito u objetivos de la estrategia..."
                        className="w-full min-h-[80px] px-3 py-2 text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

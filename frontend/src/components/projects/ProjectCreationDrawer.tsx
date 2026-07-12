"use client";

import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import {
    CheckSquare,
    Type,
    AlignLeft,
    Flag,
    Loader2,
    User,
    Palette,
    Sparkles,
} from 'lucide-react';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import PersonaSelect from '@/components/ui/PersonaSelect';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: {
        title: string;
        description: string;
        status: string;
        owner_id: string | null;
        color: string;
    }) => Promise<void>;
    defaultStatus?: string;
}

interface FormValues {
    title: string;
    description: string;
    status: string;
    owner_id: string | null;
    color: string;
}

/** Paleta curada para usar como color semilla del proyecto.
 *  Equivale a la paleta categórica permitida por AGENTS_FRONTEND.md §4. */
const COLOR_OPTIONS = [
    { value: '#2563eb', label: 'Azul ministerial', preview: 'bg-[hsl(var(--primary))]' },
    { value: '#0891b2', label: 'Cyan teal', preview: 'bg-[#0891b2]' },
    { value: '#16a34a', label: 'Verde pastoral', preview: 'bg-[#16a34a]' },
    { value: '#f59e0b', label: 'Ámbar misión', preview: 'bg-[hsl(var(--warning))]' },
    { value: '#ef4444', label: 'Rojo urgente', preview: 'bg-[#ef4444]' },
];

const STATUS_OPTIONS = [
    { value: 'planning', label: 'Planificación', dot: 'bg-amber-500' },
    { value: 'active', label: 'En Marcha', dot: 'bg-emerald-500' },
];

export default function ProjectCreationDrawer({ isOpen, onClose, onSubmit }: Props) {
    const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } =
        useForm<FormValues>({
            defaultValues: {
                title: '',
                description: '',
                status: 'planning',
                owner_id: null,
                color: COLOR_OPTIONS[0].value,
            },
        });

    const status = watch('status');
    const ownerId = watch('owner_id');
    const color = watch('color');

    useEffect(() => {
        if (isOpen) {
            reset({
                title: '',
                description: '',
                status: 'planning',
                owner_id: null,
                color: COLOR_OPTIONS[0].value,
            });
        }
    }, [isOpen, reset]);

    const handleFormSubmit = async (data: FormValues) => {
        await onSubmit(data);
        onClose();
    };

    return (
        <WorkspaceDrawer
            isOpen={isOpen}
            onClose={onClose}
            title="Nuevo Proyecto"
            subtitle="Inicio de Iniciativa"
            actions={
                <>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-3 py-1.5 text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit(handleFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? (
                            <Loader2 className="animate-spin" size={12} />
                        ) : (
                            <CheckSquare size={12} />
                        )}
                        {isSubmitting ? 'Creando...' : 'Crear Proyecto'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit(handleFormSubmit)} className="mt-3 space-y-4">
                {/* Título */}
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <Type size={12} /> Título del proyecto
                    </label>
                    <input
                        autoFocus
                        {...register('title', { required: true })}
                        placeholder="Ej: Escuela de Liderazgo 2026"
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] transition-all text-[hsl(var(--text-primary))] dark:text-white"
                    />
                </div>

                {/* Descripción */}
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (opcional)
                    </label>
                    <textarea
                        {...register('description')}
                        placeholder="Objetivo, alcance o notas iniciales…"
                        rows={4}
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 focus:border-[hsl(var(--primary))] transition-all resize-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                    />
                </div>

                {/* Estado inicial */}
                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <Sparkles size={12} /> Estado inicial
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        {STATUS_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setValue('status', option.value)}
                                className={clsx(
                                    'py-2 px-3 rounded-md flex items-center justify-center gap-2 border text-[11px] font-bold uppercase tracking-wide transition-all',
                                    status === option.value
                                        ? 'bg-[hsl(var(--primary))] border-transparent text-white shadow-md'
                                        : 'bg-transparent border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                                )}
                            >
                                {status !== option.value && (
                                    <span className={clsx('size-1.5 rounded-full', option.dot)} />
                                )}
                                {option.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Color semilla */}
                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <Palette size={12} /> Color del proyecto
                    </label>
                    <div className="grid grid-cols-5 gap-2">
                        {COLOR_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setValue('color', option.value)}
                                title={option.label}
                                className={clsx(
                                    'h-10 rounded-md border-2 transition-all flex items-center justify-center',
                                    option.preview,
                                    color === option.value
                                        ? 'border-[hsl(var(--text-primary))] dark:border-white scale-105 shadow-md'
                                        : 'border-transparent hover:scale-105 hover:shadow-md'
                                )}
                            >
                                {color === option.value && (
                                    <CheckSquare size={14} className="text-white drop-shadow" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Responsable */}
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <User size={12} /> Asignar responsable
                    </label>
                    <PersonaSelect
                        value={ownerId}
                        onChange={(v) => setValue('owner_id', v)}
                        placeholder="Seleccionar responsable del proyecto"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

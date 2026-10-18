"use client";

import { useEffect, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import {
    BadgeCheck,
    CheckSquare,
    Circle,
    CircleCheck,
    Type,
    AlignLeft,
    Loader2,
    User,
    Palette,
    Sparkles,
} from 'lucide-react';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import PersonaSelect from '@/components/ui/PersonaSelect';
import { PROJECT_COLOR_OPTIONS } from '@/lib/projects/palette';
import { PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';

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

const MIN_DESCRIPTION_LENGTH = 20;

/** PMI §4.1 — Plantillas de Objetivo / Caso de Negocio (1-clic, anexadas a description). */
interface PmiObjectiveTemplate {
    readonly testId: string;
    readonly label: string;
    readonly snippet: string;
}

const PMI_OBJECTIVE_TEMPLATES: readonly PmiObjectiveTemplate[] = [
    {
        testId: 'project-template-predictive',
        label: '[Predictivo PMI] Objetivo, Alcance Inicial y Criterio de Exito',
        snippet: '[Predictivo PMI]\nObjetivo: \nAlcance Inicial: \nCriterio de Exito: ',
    },
    {
        testId: 'project-template-hybrid',
        label: '[Hibrido Stage-Gate] Valor Incremental e Hitos de Control',
        snippet: '[Hibrido Stage-Gate]\nValor Incremental: \nHito de Control 1: \nHito de Control 2: ',
    },
    {
        testId: 'project-template-agile',
        label: '[Adaptativo / Agil] Vision de Producto y Entregables Iterativos',
        snippet: '[Adaptativo / Agil]\nVision de Producto: \nEntregables Iterativos: ',
    },
];

const STATUS_OPTIONS = [
    { value: 'planning', label: 'Planificación', dot: 'bg-[hsl(var(--warning))]' },
    { value: 'active', label: 'En Marcha', dot: 'bg-[hsl(var(--success))]' },
];

export default function ProjectCreationDrawer({ isOpen, onClose, onSubmit, defaultStatus }: Props) {
    const initialStatus = (typeof defaultStatus === 'string' && defaultStatus.trim()) ? defaultStatus : 'planning';
    const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } =
        useForm<FormValues>({
            defaultValues: {
                title: '',
                description: '',
                status: initialStatus,
                owner_id: null,
                color: PROJECT_COLOR_OPTIONS[0].value,
            },
        });

    const title = watch('title');
    const description = watch('description');
    const status = watch('status');
    const ownerId = watch('owner_id');
    const color = watch('color');

    // PMI §4.1 Project Initiation — criterios de gobernanza evaluados reactivamente.
    const pmiCriteria = useMemo(() => ([
        {
            id: 'title',
            label: 'Nombre del Proyecto definido',
            met: title.trim().length > 0,
        },
        {
            id: 'description',
            label: 'Justificación / Caso de Negocio / Objetivo documentado',
            met: description.trim().length >= MIN_DESCRIPTION_LENGTH,
        },
        {
            id: 'status',
            label: 'Estado Inicial de Ciclo de Vida definido',
            met: status.trim().length > 0,
        },
        {
            id: 'owner',
            label: 'Patrocinador / Director de Proyecto asignado',
            met: Boolean(ownerId),
        },
    ]), [description, ownerId, status, title]);
    const pmiScore = pmiCriteria.filter((c) => c.met).length;
    const pmiComplete = pmiScore === pmiCriteria.length;

    const handleApplyPmiTemplate = (snippet: string) => {
        const current = description.trim();
        const next = current ? `${current}\n\n${snippet}` : snippet;
        setValue('description', next, { shouldDirty: true });
    };

    useEffect(() => {
        if (isOpen) {
            reset({
                title: '',
                description: '',
                status: initialStatus,
                owner_id: null,
                color: PROJECT_COLOR_OPTIONS[0].value,
            });
        }
    }, [initialStatus, isOpen, reset]);

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
                        className="px-3 py-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit(handleFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.9)] active:scale-95 transition-all disabled:opacity-50"
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
                {/* Tarjeta Ejecutiva de Alistamiento PMI §4.1 */}
                <section
                    data-testid="project-creation-pmi-readiness"
                    aria-label="Alistamiento PMI"
                    className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 space-y-2"
                >
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                            <BadgeCheck size={12} /> Alistamiento Gobernanza PMI §4.1
                        </h3>
                        <span
                            data-testid="project-creation-pmi-score"
                            aria-live="polite"
                            className={clsx(
                                'shrink-0 px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wide border',
                                pmiComplete
                                    ? 'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.4)]'
                                    : 'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.4)]'
                            )}
                        >
                            {pmiScore}/{pmiCriteria.length} Criterios PMI ·{' '}
                            {pmiComplete ? 'Alistamiento Completo' : 'Gobernanza Parcial'}
                        </span>
                    </div>
                    <ul className="grid grid-cols-1 gap-1">
                        {pmiCriteria.map((criterion) => (
                            <li key={criterion.id} className="flex items-center gap-1.5 text-2xs font-medium">
                                {criterion.met ? (
                                    <CircleCheck
                                        size={12}
                                        className="shrink-0 text-[hsl(var(--success))]"
                                        aria-hidden="true"
                                    />
                                ) : (
                                    <Circle
                                        size={12}
                                        className="shrink-0 text-[hsl(var(--muted-foreground))]"
                                        aria-hidden="true"
                                    />
                                )}
                                <span
                                    className={clsx(
                                        criterion.met
                                            ? 'text-[hsl(var(--success))]'
                                            : 'text-[hsl(var(--muted-foreground))]'
                                    )}
                                >
                                    {criterion.label}
                                </span>
                            </li>
                        ))}
                    </ul>
                </section>

                {/* Título */}
                <div className="space-y-1.5">
                    <label htmlFor="project-title" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Type size={12} /> Título del proyecto
                    </label>
                    <input
                        id="project-title"
                        autoFocus
                        {...register('title', { required: true, maxLength: PROJECT_TITLE_MAX_LENGTH })}
                        maxLength={PROJECT_TITLE_MAX_LENGTH}
                        placeholder="Ej: Escuela de Liderazgo 2026"
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] transition-all text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
                    />
                </div>

                {/* Selector rapido de Plantillas de Objetivo / Caso de Negocio PMI */}
                <div
                    data-testid="project-creation-pmi-templates"
                    role="group"
                    aria-label="Plantillas de Objetivo PMI"
                    className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5 space-y-2"
                >
                    <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                        <AlignLeft size={12} /> Plantillas de Objetivo / Caso de Negocio
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {PMI_OBJECTIVE_TEMPLATES.map((template) => (
                            <button
                                key={template.testId}
                                type="button"
                                data-testid={template.testId}
                                onClick={() => handleApplyPmiTemplate(template.snippet)}
                                className="px-2 py-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-2xs font-semibold text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:border-[hsl(var(--primary))] transition-colors"
                            >
                                {template.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Descripción */}
                <div className="space-y-1.5">
                    <label htmlFor="project-description" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (opcional)
                    </label>
                    <textarea
                        id="project-description"
                        {...register('description')}
                        placeholder="Objetivo, alcance o notas iniciales…"
                        rows={4}
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] transition-all resize-none text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
                    />
                </div>

                {/* Estado inicial */}
                <div role="group" aria-labelledby="project-status-label" className="space-y-2">
                    <span id="project-status-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Sparkles size={12} /> Estado inicial
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                        {STATUS_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setValue('status', option.value)}
                                aria-pressed={status === option.value}
                                className={clsx(
                                    'py-2 px-3 rounded-md flex items-center justify-center gap-2 border text-xs font-bold uppercase tracking-wide transition-all',
                                    status === option.value
                                        ? 'bg-[hsl(var(--primary))] border-transparent text-[hsl(var(--primary-foreground))] shadow-md'
                                        : 'bg-transparent border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'
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
                <div role="group" aria-labelledby="project-color-label" className="space-y-2">
                    <span id="project-color-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Palette size={12} /> Color del proyecto
                    </span>
                    <div className="grid grid-cols-5 gap-2">
                        {PROJECT_COLOR_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setValue('color', option.value)}
                                aria-label={`Color ${option.label}`}
                                aria-pressed={color === option.value}
                                title={option.label}
                                className={clsx(
                                    'h-10 rounded-md border-2 transition-all flex items-center justify-center',
                                    option.preview,
                                    color === option.value
                                        ? 'border-[hsl(var(--foreground))] scale-105 shadow-md'
                                        : 'border-transparent hover:scale-105 hover:shadow-md'
                                )}
                            >
                                {color === option.value && (
                                    <CheckSquare size={14} className="text-[hsl(var(--primary-foreground))] drop-shadow" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Responsable */}
                <div role="group" aria-labelledby="project-owner-label" className="space-y-1.5">
                    <span id="project-owner-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <User size={12} /> Asignar responsable
                    </span>
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

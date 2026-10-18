"use client";

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { CheckSquare, Type, AlignLeft, Flag, Loader2, User, Layers, Plus, ShieldCheck, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import PersonaSelect from '@/components/ui/PersonaSelect';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { PRIORITY_LABELS, TASK_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectComponentsBreakdown } from '@/types/projects';

interface Props {
    isOpen: boolean;
    projectId?: string;
    defaultStatus?: string;
    defaultComponentId?: string | null;
    onClose: () => void;
    onSubmit: (data: {
        title: string;
        description: string;
        priority: string;
        status: string;
        assignee_id?: string | null;
        node?: string | null;
        component_id?: string | null;
    }) => Promise<boolean> | Promise<void> | boolean | void;
}

interface FormValues {
    title: string;
    description: string;
    priority: string;
    assignee_id: string | null;
    node: string | null;
    component_id: string | null;
}

const PRIORITIES = [
    { value: 'urgent', label: PRIORITY_LABELS.urgent, color: 'bg-[hsl(var(--destructive))]', iconColor: 'text-[hsl(var(--destructive))]' },
    { value: 'high', label: PRIORITY_LABELS.high, color: 'bg-[hsl(var(--warning))]', iconColor: 'text-[hsl(var(--warning))]' },
    { value: 'medium', label: PRIORITY_LABELS.medium, color: 'bg-[hsl(var(--primary))]', iconColor: 'text-[hsl(var(--primary))]' },
    { value: 'low', label: PRIORITY_LABELS.low, color: 'bg-[hsl(var(--surface-2))]', iconColor: 'text-[hsl(var(--text-secondary))]' }
];

const PMI_DESCRIPTION_TEMPLATES: Array<{
    id: string;
    testId: string;
    label: string;
    content: string;
}> = [
    {
        id: 'wbs',
        testId: 'task-template-wbs',
        label: '[Diccionario EDT] Entregable y Criterio',
        content:
            'Entregable Verificable: Documentación y artefacto operativo validado.\nSupuestos y Restricciones: Cumplimiento de línea base técnica.\nCriterio de Aceptación PMI: Aprobado por responsable del paquete.',
    },
    {
        id: 'dod',
        testId: 'task-template-dod',
        label: '[Checklist DoD] Verificación de Calidad',
        content:
            'Checklist Definition of Done (DoD):\n- [ ] Revisión técnica de pares completada\n- [ ] Evidencia adjunta en el paquete WBS\n- [ ] Validado sin defectos críticos abiertos',
    },
    {
        id: 'milestone',
        testId: 'task-template-milestone',
        label: '[Hito de Control] Evidencia de Salida',
        content:
            'Criterio de Salida Stage-Gate:\n- [ ] Acta o evidencia formal cargada\n- [ ] Indicadores de desempeño dentro de umbral\n- [ ] Autorización de transición a siguiente fase',
    },
];

export default function TaskCreationDrawer({
    isOpen,
    projectId,
    defaultStatus = 'todo',
    defaultComponentId,
    onClose,
    onSubmit,
}: Props) {
    const { token } = useAuth();
    const [components, setComponents] = useState<Array<{ id: string; code: string; name: string }>>([]);
    const [showNewComponentForm, setShowNewComponentForm] = useState(false);
    const [newComponentCode, setNewComponentCode] = useState('');
    const [newComponentName, setNewComponentName] = useState('');
    const [isCreatingComponent, setIsCreatingComponent] = useState(false);
    const [componentError, setComponentError] = useState<string | null>(null);

    const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } = useForm<FormValues>({
        defaultValues: {
            title: '',
            description: '',
            priority: 'medium',
            assignee_id: null,
            node: null,
            component_id: defaultComponentId ?? '',
        }
    });

    const priority = watch('priority');
    const assigneeId = watch('assignee_id');
    const watchedTitle = watch('title');
    const watchedDescription = watch('description');
    const watchedComponentId = watch('component_id');
    const watchedNode = watch('node');

    const wbsCriteria = [
        { key: 'title', label: 'Nombre del Paquete', ok: (watchedTitle || '').trim().length > 0 },
        { key: 'dod', label: 'Criterio de Aceptación (DoD)', ok: (watchedDescription || '').trim().length >= 15 },
        { key: 'raci', label: 'Responsable RACI', ok: Boolean(assigneeId) },
        { key: 'edt', label: 'Anclaje EDT / Componente', ok: Boolean(watchedComponentId || watchedNode) },
    ];
    const wbsReadyCount = wbsCriteria.filter((c) => c.ok).length;
    const isWbsReady = wbsReadyCount === wbsCriteria.length;

    const handleApplyTemplate = (templateContent: string) => {
        const current = (watchedDescription || '').trim();
        const nextValue = current ? `${current}\n\n${templateContent}` : templateContent;
        setValue('description', nextValue, { shouldDirty: true, shouldValidate: true });
    };

    useEffect(() => {
        if (!isOpen || !projectId || !token) {
            setComponents([]);
            return;
        }
        let isCurrent = true;
        Promise.resolve(apiFetch<ProjectComponentsBreakdown>(`/projects/${projectId}/components-breakdown`, { token }))
            .then((res) => {
                if (isCurrent && res?.components) {
                    setComponents(res.components.map((c) => ({ id: c.id, code: c.code, name: c.name })));
                }
            })
            .catch(() => {});
        return () => { isCurrent = false; };
    }, [isOpen, projectId, token]);

    useEffect(() => {
        if (isOpen) {
            reset({
                title: '',
                description: '',
                priority: 'medium',
                assignee_id: null,
                node: null,
                component_id: defaultComponentId ?? '',
            });
            setShowNewComponentForm(false);
            setComponentError(null);
        }
    }, [isOpen, defaultComponentId, reset]);

    const handleOpenNewComponent = () => {
        setNewComponentCode(`EDT-${components.length + 1}.0`);
        setNewComponentName('');
        setComponentError(null);
        setShowNewComponentForm(true);
    };

    const handleCreateComponent = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!projectId || !token) return;
        const code = newComponentCode.trim();
        const name = newComponentName.trim();
        if (!code || !name) {
            setComponentError('El código y el nombre son obligatorios');
            return;
        }
        setIsCreatingComponent(true);
        setComponentError(null);
        try {
            const created = await apiFetch<{ id: string; code: string; name: string }>(
                `/projects/${projectId}/components`,
                {
                    method: 'POST',
                    token,
                    body: { code, name },
                }
            );
            if (created?.id) {
                setComponents((prev) => [...prev, { id: created.id, code: created.code, name: created.name }]);
                setValue('component_id', created.id);
                setShowNewComponentForm(false);
                setNewComponentCode('');
                setNewComponentName('');
                toast.success('Componente EDT creado correctamente');
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Error al crear componente';
            setComponentError(message);
            toast.error('No se pudo crear el componente');
        } finally {
            setIsCreatingComponent(false);
        }
    };

    const onFormSubmit = async (data: FormValues) => {
        const result = await onSubmit({
            ...data,
            component_id: data.component_id ? data.component_id : null,
            status: defaultStatus,
        });
        if (result === true || result === undefined) {
            onClose();
        }
    };

    return (
        <WorkspaceDrawer
            isOpen={isOpen}
            onClose={onClose}
            title="Nueva Actividad"
            subtitle="Definición de Acción"
            actions={
                <>
                    <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit(onFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-bold uppercase tracking-wide shadow-md shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" size={12} /> : <CheckSquare size={12} />}
                        {isSubmitting ? 'Creando...' : 'Crear Actividad'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit(onFormSubmit)} className="mt-3 space-y-4">
                {/* Tarjeta de Alistamiento de Paquete de Trabajo PMI §5.4 */}
                <div
                    data-testid="task-creation-pmi-readiness"
                    className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 space-y-2"
                >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                            <ShieldCheck size={13} className="text-[hsl(var(--primary))]" />
                            Alistamiento de Paquete de Trabajo (PMI §5.4)
                        </span>
                        <div className="flex items-center gap-1.5">
                            <span
                                data-testid="task-creation-pmi-score"
                                className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]"
                            >
                                {wbsReadyCount}/4 Criterios WBS
                            </span>
                            <span
                                className={clsx(
                                    'px-2 py-0.5 rounded text-2xs font-bold uppercase tracking-wider',
                                    isWbsReady
                                        ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]'
                                        : 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]'
                                )}
                            >
                                {isWbsReady ? 'Paquete Listo' : 'Definición Parcial'}
                            </span>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 pt-0.5">
                        {wbsCriteria.map((criterion) => (
                            <div
                                key={criterion.key}
                                className={clsx(
                                    'text-2xs font-medium px-2 py-1 rounded border flex items-center justify-between',
                                    criterion.ok
                                        ? 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.08)] text-[hsl(var(--success))]'
                                        : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                                )}
                            >
                                <span className="truncate">{criterion.label}</span>
                                <span className="font-bold ml-1">{criterion.ok ? 'OK' : 'Pend.'}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="space-y-1.5">
                    <label htmlFor="task-title" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Type size={12} /> Título de la actividad
                    </label>
                    <input
                        id="task-title"
                        autoFocus
                        {...register('title', { required: true, maxLength: TASK_TITLE_MAX_LENGTH })}
                        maxLength={TASK_TITLE_MAX_LENGTH}
                        placeholder="Ej: Revisión de Mezcla de Audio"
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--foreground))]"
                    />
                </div>

                <div className="space-y-1.5">
                    <label htmlFor="task-description" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (Opcional)
                    </label>
                    <div
                        data-testid="task-creation-pmi-templates"
                        className="flex items-center gap-1.5 flex-wrap pb-1"
                    >
                        <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] inline-flex items-center gap-1 mr-1">
                            <Sparkles size={10} className="text-[hsl(var(--primary))]" />
                            Plantillas PMI:
                        </span>
                        {PMI_DESCRIPTION_TEMPLATES.map((tpl) => (
                            <button
                                key={tpl.id}
                                type="button"
                                data-testid={tpl.testId}
                                onClick={() => handleApplyTemplate(tpl.content)}
                                className="px-2 py-0.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.5)] hover:text-[hsl(var(--primary))] text-2xs font-semibold text-[hsl(var(--muted-foreground))] transition-colors"
                            >
                                {tpl.label}
                            </button>
                        ))}
                    </div>
                    <textarea
                        id="task-description"
                        {...register('description')}
                        placeholder="Detalles adicionales, links, etc..."
                        rows={5}
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all resize-none text-[hsl(var(--foreground))]"
                    />
                </div>

                <div role="group" aria-labelledby="task-priority-label" className="space-y-2">
                    <span id="task-priority-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Flag size={12} /> Nivel de Prioridad
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                        {PRIORITIES.map((p) => (
                            <button
                                key={p.value}
                                type="button"
                                onClick={() => setValue('priority', p.value)}
                                aria-pressed={priority === p.value}
                                className={clsx(
                                    "py-2 px-3 rounded-md flex items-center justify-center gap-2 border text-xs font-bold uppercase tracking-wide transition-all",
                                    priority === p.value
                                        ? `${p.color} border-transparent text-[hsl(var(--primary-foreground))] shadow-sm`
                                        : `bg-transparent border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]`
                                )}
                            >
                                {priority !== p.value && <div className={clsx("size-1.5 rounded-full", p.color)} />}
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div role="group" aria-labelledby="task-assignee-label" className="space-y-1.5">
                    <span id="task-assignee-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <User size={12} /> Asignar a
                    </span>
                    <PersonaSelect
                        value={assigneeId}
                        onChange={(v) => setValue('assignee_id', v)}
                        placeholder="Seleccionar responsable"
                    />
                </div>

                <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                        <label htmlFor="task-component" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                            <Layers size={12} /> Componente (EDT)
                        </label>
                        {projectId && (
                            <button
                                type="button"
                                onClick={() => {
                                    if (showNewComponentForm) {
                                        setShowNewComponentForm(false);
                                    } else {
                                        handleOpenNewComponent();
                                    }
                                }}
                                className="text-2xs font-bold text-[hsl(var(--primary))] hover:underline flex items-center gap-1"
                            >
                                <Plus size={10} />
                                {showNewComponentForm ? 'Cancelar nuevo' : '+ Nuevo componente'}
                            </button>
                        )}
                    </div>
                    <select
                        id="task-component"
                        aria-label="Componente (EDT)"
                        {...register('component_id')}
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--foreground))]"
                    >
                        <option value="">Sin componente (General)</option>
                        {components.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.code} · {c.name}
                            </option>
                        ))}
                    </select>

                    {showNewComponentForm && (
                        <div data-testid="inline-edt-form" className="p-2.5 rounded-md border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--surface-1))] space-y-2 mt-2">
                            <p className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-1">
                                <Layers size={11} className="text-[hsl(var(--primary))]" />
                                Crear Componente EDT
                            </p>
                            {componentError && (
                                <p className="text-2xs text-[hsl(var(--destructive))] font-medium">{componentError}</p>
                            )}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                <div>
                                    <label htmlFor="inline-edt-code" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] block mb-1">
                                        Código
                                    </label>
                                    <input
                                        id="inline-edt-code"
                                        aria-label="Código del componente EDT"
                                        value={newComponentCode}
                                        onChange={(e) => setNewComponentCode(e.target.value)}
                                        placeholder="Ej: EDT-1.0"
                                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                                    />
                                </div>
                                <div className="sm:col-span-2">
                                    <label htmlFor="inline-edt-name" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] block mb-1">
                                        Nombre del Componente
                                    </label>
                                    <input
                                        id="inline-edt-name"
                                        aria-label="Nombre del componente EDT"
                                        value={newComponentName}
                                        onChange={(e) => setNewComponentName(e.target.value)}
                                        placeholder="Ej: Infraestructura y Redes"
                                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                                    />
                                </div>
                            </div>
                            <div className="flex items-center justify-end gap-2 pt-1">
                                <button
                                    type="button"
                                    onClick={() => setShowNewComponentForm(false)}
                                    className="px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCreateComponent}
                                    disabled={isCreatingComponent}
                                    className="flex items-center gap-1 px-2.5 py-1 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded text-2xs font-bold shadow-xs hover:opacity-90 disabled:opacity-50"
                                >
                                    {isCreatingComponent ? <Loader2 size={10} className="animate-spin" /> : <Plus size={10} />}
                                    Guardar
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

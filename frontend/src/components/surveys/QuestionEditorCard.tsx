"use client";

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
    GripVertical,
    Trash2,
    Copy,
    Plus,
    X,
    AlignLeft,
    Type,
    CircleDot,
    CheckSquare,
    ChevronDownSquare,
    Sliders,
    Grid,
    Calendar,
    Clock,
    UploadCloud,
    Split,
} from 'lucide-react';
import { EncuestaPregunta, TipoPregunta, PreguntaOpcion, PreguntaMatrizItem } from '@/types/surveys';

interface QuestionEditorCardProps {
    pregunta: EncuestaPregunta;
    index: number;
    availableQuestions: EncuestaPregunta[];
    isSelected: boolean;
    onSelect: () => void;
    onChange: (updated: EncuestaPregunta) => void;
    onDuplicate: () => void;
    onDelete: () => void;
}

const TIPO_PREGUNTA_CONFIG: Record<TipoPregunta, { label: string; icon: React.ElementType }> = {
    TEXTO_CORTO: { label: 'Respuesta Corta', icon: Type },
    PARRAFO: { label: 'Párrafo', icon: AlignLeft },
    OPCION_MULTIPLE: { label: 'Opción Múltiple', icon: CircleDot },
    CASILLAS: { label: 'Casillas de Verificación', icon: CheckSquare },
    DESPLEGABLE: { label: 'Desplegable', icon: ChevronDownSquare },
    ESCALA_LINEAL: { label: 'Escala Lineal', icon: Sliders },
    CUADRICULA_RADIO: { label: 'Cuadrícula de Opción Múltiple', icon: Grid },
    CUADRICULA_CASILLAS: { label: 'Cuadrícula de Casillas', icon: Grid },
    FECHA: { label: 'Fecha', icon: Calendar },
    HORA: { label: 'Hora', icon: Clock },
    SUBIR_ARCHIVO: { label: 'Subir Archivo', icon: UploadCloud },
    SECCION_SALTO: { label: 'División de Sección', icon: Split },
};

export default function QuestionEditorCard({
    pregunta,
    index,
    availableQuestions,
    isSelected,
    onSelect,
    onChange,
    onDuplicate,
    onDelete,
}: QuestionEditorCardProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: pregunta.id });

    const style: React.CSSProperties = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 50 : isSelected ? 10 : 1,
    };

    const handleTypeChange = (newType: TipoPregunta) => {
        let defaultOptions: PreguntaOpcion[] = pregunta.opciones;
        if (
            ['OPCION_MULTIPLE', 'CASILLAS', 'DESPLEGABLE'].includes(newType) &&
            (!defaultOptions || defaultOptions.length === 0)
        ) {
            defaultOptions = [
                { id: `opt-${Date.now()}-1`, label: 'Opción 1' },
                { id: `opt-${Date.now()}-2`, label: 'Opción 2' },
            ];
        }

        let defaultFilas: PreguntaMatrizItem[] = pregunta.filas;
        let defaultColumnas: PreguntaMatrizItem[] = pregunta.columnas;
        if (['CUADRICULA_RADIO', 'CUADRICULA_CASILLAS'].includes(newType)) {
            if (!defaultFilas || defaultFilas.length === 0) {
                defaultFilas = [
                    { id: `row-${Date.now()}-1`, label: 'Fila 1' },
                    { id: `row-${Date.now()}-2`, label: 'Fila 2' },
                ];
            }
            if (!defaultColumnas || defaultColumnas.length === 0) {
                defaultColumnas = [
                    { id: `col-${Date.now()}-1`, label: 'Columna 1' },
                    { id: `col-${Date.now()}-2`, label: 'Columna 2' },
                ];
            }
        }

        onChange({
            ...pregunta,
            tipo_pregunta: newType,
            opciones: defaultOptions,
            filas: defaultFilas,
            columnas: defaultColumnas,
        });
    };

    const handleAddOption = () => {
        const nextIdx = (pregunta.opciones?.length || 0) + 1;
        const newOpt: PreguntaOpcion = {
            id: `opt-${Date.now()}-${nextIdx}`,
            label: `Opción ${nextIdx}`,
        };
        onChange({
            ...pregunta,
            opciones: [...(pregunta.opciones || []), newOpt],
        });
    };

    const handleUpdateOption = (optId: string, label: string) => {
        const updated = (pregunta.opciones || []).map((o) =>
            o.id === optId ? { ...o, label } : o
        );
        onChange({ ...pregunta, opciones: updated });
    };

    const handleRemoveOption = (optId: string) => {
        const updated = (pregunta.opciones || []).filter((o) => o.id !== optId);
        onChange({ ...pregunta, opciones: updated });
    };

    // Cuadrícula Filas/Columnas
    const handleAddRow = () => {
        const nextIdx = (pregunta.filas?.length || 0) + 1;
        onChange({
            ...pregunta,
            filas: [...(pregunta.filas || []), { id: `row-${Date.now()}-${nextIdx}`, label: `Fila ${nextIdx}` }],
        });
    };

    const handleUpdateRow = (id: string, label: string) => {
        onChange({
            ...pregunta,
            filas: (pregunta.filas || []).map((r) => (r.id === id ? { ...r, label } : r)),
        });
    };

    const handleRemoveRow = (id: string) => {
        onChange({
            ...pregunta,
            filas: (pregunta.filas || []).filter((r) => r.id !== id),
        });
    };

    const handleAddColumn = () => {
        const nextIdx = (pregunta.columnas?.length || 0) + 1;
        onChange({
            ...pregunta,
            columnas: [...(pregunta.columnas || []), { id: `col-${Date.now()}-${nextIdx}`, label: `Columna ${nextIdx}` }],
        });
    };

    const handleUpdateColumn = (id: string, label: string) => {
        onChange({
            ...pregunta,
            columnas: (pregunta.columnas || []).map((c) => (c.id === id ? { ...c, label } : c)),
        });
    };

    const handleRemoveColumn = (id: string) => {
        onChange({
            ...pregunta,
            columnas: (pregunta.columnas || []).filter((c) => c.id !== id),
        });
    };

    const isSection = pregunta.tipo_pregunta === 'SECCION_SALTO';
    const conditionalSources = availableQuestions.filter((candidate) =>
        candidate.orden < pregunta.orden &&
        ['OPCION_MULTIPLE', 'DESPLEGABLE'].includes(candidate.tipo_pregunta) &&
        candidate.opciones.length > 0
    );
    const visibleIfRaw = pregunta.configuracion?.visible_if;
    const visibleIf = visibleIfRaw && typeof visibleIfRaw === 'object' && !Array.isArray(visibleIfRaw)
        ? visibleIfRaw as { pregunta_id?: string; operador?: 'igual_a' | 'distinto_de'; opcion_id?: string }
        : null;
    const conditionSource = conditionalSources.find((candidate) => candidate.id === visibleIf?.pregunta_id);
    const targetSections = availableQuestions.filter((candidate) =>
        candidate.tipo_pregunta === 'SECCION_SALTO' && candidate.id !== pregunta.id
    );

    const updateCondition = (next: typeof visibleIf) => {
        const configuracion = { ...pregunta.configuracion };
        if (next) configuracion.visible_if = next;
        else delete configuracion.visible_if;
        onChange({ ...pregunta, configuracion });
    };

    const updateOptionJump = (optionId: string, targetId: string) => {
        onChange({
            ...pregunta,
            opciones: pregunta.opciones.map((option) => option.id === optionId
                ? { ...option, salto_seccion_id: targetId || null }
                : option),
        });
    };

    const updateSectionJump = (targetId: string) => {
        const sectionOption = pregunta.opciones[0] ?? { id: `section-${pregunta.id}`, label: '' };
        onChange({
            ...pregunta,
            opciones: [{ ...sectionOption, salto_seccion_id: targetId || null }, ...pregunta.opciones.slice(1)],
        });
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            onClick={onSelect}
            className={`group relative rounded-xl border transition-all duration-200 ${
                isDragging
                    ? 'opacity-60 shadow-2xl scale-[1.01] border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))]'
                    : isSelected
                    ? 'border-[hsl(var(--primary))] shadow-md bg-[hsl(var(--surface-1))] ring-1 ring-[hsl(var(--primary))]/30'
                    : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--border))]/80 hover:shadow-sm'
            } ${isSection ? 'border-l-4 border-l-[hsl(var(--primary))] bg-[hsl(var(--surface-2))]/30' : ''}`}
        >
            {/* Barra superior de arrastre */}
            <div
                {...attributes}
                {...listeners}
                className="flex items-center justify-center py-1.5 cursor-grab active:cursor-grabbing text-[hsl(var(--text-secondary))]/40 hover:text-[hsl(var(--text-secondary))] transition-colors select-none"
                title="Arrastrar para reordenar"
            >
                <GripVertical className="size-4" />
            </div>

            <div className="px-5 pb-5 pt-1">
                {/* Cabecera de la pregunta: Título + Selector de Tipo */}
                <div className="flex flex-col sm:flex-row gap-3.5 items-start sm:items-center justify-between mb-4">
                    <div className="flex-1 w-full">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                                {isSection ? 'SECCIÓN' : `#${index + 1}`}
                            </span>
                            {pregunta.es_requerida && !isSection && (
                                <span className="text-[11px] font-medium text-[hsl(var(--destructive))]">
                                    * Obligatoria
                                </span>
                            )}
                        </div>
                        <input
                            type="text"
                            value={pregunta.titulo}
                            onChange={(e) => onChange({ ...pregunta, titulo: e.target.value })}
                            placeholder={isSection ? 'Título de la sección' : 'Pregunta sin título'}
                            className="w-full text-sm sm:text-base font-semibold text-[hsl(var(--text-primary))] bg-transparent border-b border-transparent hover:border-[hsl(var(--border))] focus:border-[hsl(var(--primary))] focus:outline-none py-1 transition-colors"
                        />
                    </div>

                    <div className="w-full sm:w-auto">
                        <select
                            value={pregunta.tipo_pregunta}
                            onChange={(e) => handleTypeChange(e.target.value as TipoPregunta)}
                            className="w-full sm:w-60 px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] font-medium focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] transition-all"
                        >
                            {Object.entries(TIPO_PREGUNTA_CONFIG).map(([tipo, cfg]) => (
                                <option key={tipo} value={tipo}>
                                    {cfg.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Descripción / Instrucciones secundarias */}
                <div className="mb-4">
                    <input
                        type="text"
                        value={pregunta.descripcion || ''}
                        onChange={(e) => onChange({ ...pregunta, descripcion: e.target.value || null })}
                        placeholder={
                            isSection
                                ? 'Descripción o instrucciones opcionales para esta sección...'
                                : 'Texto de ayuda o descripción (opcional)...'
                        }
                        className="w-full text-xs text-[hsl(var(--text-secondary))] bg-transparent border-b border-transparent hover:border-[hsl(var(--border))] focus:border-[hsl(var(--primary))] focus:outline-none py-0.5 transition-colors"
                    />
                </div>

                {!isSection && conditionalSources.length > 0 && (
                    <fieldset className="mb-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 p-3">
                        <legend className="px-1 text-xs font-semibold text-[hsl(var(--text-primary))]">Visibilidad condicional</legend>
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                            <label className="text-xs text-[hsl(var(--text-secondary))]">
                                Mostrar cuando
                                <select
                                    aria-label={`Pregunta que controla ${pregunta.titulo}`}
                                    value={visibleIf?.pregunta_id ?? ''}
                                    onChange={(event) => {
                                        const source = conditionalSources.find((candidate) => candidate.id === event.target.value);
                                        const firstOption = source?.opciones[0];
                                        updateCondition(source && firstOption ? {
                                            pregunta_id: source.id,
                                            operador: 'igual_a',
                                            opcion_id: firstOption.id,
                                        } : null);
                                    }}
                                    className="mt-1 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs text-[hsl(var(--text-primary))]"
                                >
                                    <option value="">Siempre visible</option>
                                    {conditionalSources.map((source) => <option key={source.id} value={source.id}>{source.titulo || `Pregunta ${source.orden + 1}`}</option>)}
                                </select>
                            </label>
                            <label className="text-xs text-[hsl(var(--text-secondary))]">
                                Operador
                                <select
                                    aria-label={`Operador condicional para ${pregunta.titulo}`}
                                    value={visibleIf?.operador ?? 'igual_a'}
                                    disabled={!conditionSource}
                                    onChange={(event) => updateCondition(visibleIf ? { ...visibleIf, operador: event.target.value as 'igual_a' | 'distinto_de' } : null)}
                                    className="mt-1 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs text-[hsl(var(--text-primary))] disabled:opacity-50"
                                >
                                    <option value="igual_a">es igual a</option>
                                    <option value="distinto_de">es diferente de</option>
                                </select>
                            </label>
                            <label className="text-xs text-[hsl(var(--text-secondary))]">
                                Respuesta
                                <select
                                    aria-label={`Respuesta condicional para ${pregunta.titulo}`}
                                    value={visibleIf?.opcion_id ?? ''}
                                    disabled={!conditionSource}
                                    onChange={(event) => updateCondition(visibleIf ? { ...visibleIf, opcion_id: event.target.value } : null)}
                                    className="mt-1 w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs text-[hsl(var(--text-primary))] disabled:opacity-50"
                                >
                                    {(conditionSource?.opciones ?? []).map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
                                </select>
                            </label>
                        </div>
                        {visibleIf && <button type="button" onClick={() => updateCondition(null)} className="mt-2 text-xs text-[hsl(var(--destructive))]">Quitar condición</button>}
                    </fieldset>
                )}

                {isSection && targetSections.length > 0 && (
                    <label className="mb-4 flex flex-col gap-1 text-xs text-[hsl(var(--text-secondary))]">
                        Al terminar esta sección, continuar con
                        <select
                            aria-label={`Destino al terminar ${pregunta.titulo}`}
                            value={pregunta.opciones[0]?.salto_seccion_id ?? ''}
                            onChange={(event) => updateSectionJump(event.target.value)}
                            className="w-full max-w-md rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs text-[hsl(var(--text-primary))]"
                        >
                            <option value="">La siguiente sección</option>
                            {targetSections.map((section) => <option key={section.id} value={section.id}>{section.titulo || `Sección ${section.orden + 1}`}</option>)}
                            <option value="__submit__">Finalizar encuesta</option>
                        </select>
                    </label>
                )}

                {/* Contenido Contextual según Tipo de Pregunta */}
                <div className="py-2 mb-4 border-t border-[hsl(var(--border))]/50 pt-3">
                    {/* 1. TEXTO CORTO */}
                    {pregunta.tipo_pregunta === 'TEXTO_CORTO' && (
                        <div className="max-w-md py-2 border-b border-dashed border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))]/60 select-none">
                            Texto de respuesta breve...
                        </div>
                    )}

                    {/* 2. PARRAFO */}
                    {pregunta.tipo_pregunta === 'PARRAFO' && (
                        <div className="w-full py-4 border-b border-dashed border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))]/60 select-none">
                            Texto de respuesta larga...
                        </div>
                    )}

                    {/* 3, 4, 5: OPCION MULTIPLE, CASILLAS, DESPLEGABLE */}
                    {['OPCION_MULTIPLE', 'CASILLAS', 'DESPLEGABLE'].includes(pregunta.tipo_pregunta) && (
                        <div className="flex flex-col gap-2">
                            {(pregunta.opciones || []).map((opt, optIdx) => (
                                <div key={opt.id} className="flex items-center gap-2.5">
                                    <div className="text-[hsl(var(--text-secondary))]/50">
                                        {pregunta.tipo_pregunta === 'OPCION_MULTIPLE' && (
                                            <div className="size-4 rounded-full border-2 border-[hsl(var(--border))]" />
                                        )}
                                        {pregunta.tipo_pregunta === 'CASILLAS' && (
                                            <div className="size-4 rounded border-2 border-[hsl(var(--border))]" />
                                        )}
                                        {pregunta.tipo_pregunta === 'DESPLEGABLE' && (
                                            <span className="text-xs font-mono">{optIdx + 1}.</span>
                                        )}
                                    </div>
                                    <input
                                        type="text"
                                        value={opt.label}
                                        onChange={(e) => handleUpdateOption(opt.id, e.target.value)}
                                        placeholder={`Opción ${optIdx + 1}`}
                                        className="flex-1 text-xs px-2.5 py-1.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                                    />
                                    {pregunta.tipo_pregunta === 'OPCION_MULTIPLE' && availableQuestions.some((candidate) => candidate.tipo_pregunta === 'SECCION_SALTO') && (
                                        <select
                                            aria-label={`Destino de ${opt.label}`}
                                            value={opt.salto_seccion_id ?? ''}
                                            onChange={(event) => updateOptionJump(opt.id, event.target.value)}
                                            className="max-w-44 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1 text-[11px] text-[hsl(var(--text-secondary))]"
                                        >
                                            <option value="">Continuar normalmente</option>
                                            {availableQuestions.filter((candidate) => candidate.tipo_pregunta === 'SECCION_SALTO').map((section) => <option key={section.id} value={section.id}>Ir a: {section.titulo || `Sección ${section.orden + 1}`}</option>)}
                                            <option value="__submit__">Finalizar encuesta</option>
                                        </select>
                                    )}
                                    {(pregunta.opciones?.length || 0) > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveOption(opt.id)}
                                            className="p-1 rounded text-[hsl(var(--text-secondary))]/50 hover:text-[hsl(var(--destructive))] transition-colors"
                                            title="Eliminar opción"
                                        >
                                            <X className="size-3.5" />
                                        </button>
                                    )}
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={handleAddOption}
                                className="flex items-center gap-1.5 text-xs text-[hsl(var(--primary))] font-medium hover:underline mt-1 w-fit"
                            >
                                <Plus className="size-3.5" />
                                Agregar opción
                            </button>
                        </div>
                    )}

                    {/* 6. ESCALA LINEAL */}
                    {pregunta.tipo_pregunta === 'ESCALA_LINEAL' && (
                        <div className="flex flex-col gap-3 max-w-lg">
                            <div className="flex items-center gap-3">
                                <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))]">
                                    <span>Desde:</span>
                                    <select
                                        value={pregunta.escala_min}
                                        onChange={(e) => onChange({ ...pregunta, escala_min: Number(e.target.value) })}
                                        className="px-2 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                                    >
                                        <option value={0}>0</option>
                                        <option value={1}>1</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))]">
                                    <span>Hasta:</span>
                                    <select
                                        value={pregunta.escala_max}
                                        onChange={(e) => onChange({ ...pregunta, escala_max: Number(e.target.value) })}
                                        className="px-2 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                                    >
                                        <option value={5}>5</option>
                                        <option value={10}>10</option>
                                    </select>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-[11px] text-[hsl(var(--text-secondary))] mb-1">
                                        Etiqueta para {pregunta.escala_min} (ej. Regular, Muy insatisfecho)
                                    </label>
                                    <input
                                        type="text"
                                        value={pregunta.escala_min_etiqueta || ''}
                                        onChange={(e) => onChange({ ...pregunta, escala_min_etiqueta: e.target.value || null })}
                                        placeholder="Regular"
                                        className="w-full text-xs px-2.5 py-1.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[11px] text-[hsl(var(--text-secondary))] mb-1">
                                        Etiqueta para {pregunta.escala_max} (ej. Excelente, Muy satisfecho)
                                    </label>
                                    <input
                                        type="text"
                                        value={pregunta.escala_max_etiqueta || ''}
                                        onChange={(e) => onChange({ ...pregunta, escala_max_etiqueta: e.target.value || null })}
                                        placeholder="Excelente"
                                        className="w-full text-xs px-2.5 py-1.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 7 & 8: CUADRICULA RADIO / CASILLAS */}
                    {['CUADRICULA_RADIO', 'CUADRICULA_CASILLAS'].includes(pregunta.tipo_pregunta) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Filas */}
                            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40">
                                <span className="block text-xs font-semibold text-[hsl(var(--text-primary))] mb-2">
                                    Filas
                                </span>
                                <div className="flex flex-col gap-2">
                                    {(pregunta.filas || []).map((row, rIdx) => (
                                        <div key={row.id} className="flex items-center gap-2">
                                            <span className="text-xs text-[hsl(var(--text-secondary))]/50 font-mono w-4">
                                                {rIdx + 1}.
                                            </span>
                                            <input
                                                type="text"
                                                value={row.label}
                                                onChange={(e) => handleUpdateRow(row.id, e.target.value)}
                                                placeholder={`Fila ${rIdx + 1}`}
                                                className="flex-1 text-xs px-2.5 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                                            />
                                            {(pregunta.filas?.length || 0) > 1 && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleRemoveRow(row.id)}
                                                    className="p-1 rounded text-[hsl(var(--text-secondary))]/50 hover:text-[hsl(var(--destructive))]"
                                                >
                                                    <X className="size-3" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                    <button
                                        type="button"
                                        onClick={handleAddRow}
                                        className="text-xs text-[hsl(var(--primary))] font-medium flex items-center gap-1 mt-1"
                                    >
                                        <Plus className="size-3" /> Agregar fila
                                    </button>
                                </div>
                            </div>

                            {/* Columnas */}
                            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40">
                                <span className="block text-xs font-semibold text-[hsl(var(--text-primary))] mb-2">
                                    Columnas
                                </span>
                                <div className="flex flex-col gap-2">
                                    {(pregunta.columnas || []).map((col, cIdx) => (
                                        <div key={col.id} className="flex items-center gap-2">
                                            <span className="text-xs text-[hsl(var(--text-secondary))]/50 font-mono w-4">
                                                {cIdx + 1}.
                                            </span>
                                            <input
                                                type="text"
                                                value={col.label}
                                                onChange={(e) => handleUpdateColumn(col.id, e.target.value)}
                                                placeholder={`Columna ${cIdx + 1}`}
                                                className="flex-1 text-xs px-2.5 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                                            />
                                            {(pregunta.columnas?.length || 0) > 1 && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleRemoveColumn(col.id)}
                                                    className="p-1 rounded text-[hsl(var(--text-secondary))]/50 hover:text-[hsl(var(--destructive))]"
                                                >
                                                    <X className="size-3" />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                    <button
                                        type="button"
                                        onClick={handleAddColumn}
                                        className="text-xs text-[hsl(var(--primary))] font-medium flex items-center gap-1 mt-1"
                                    >
                                        <Plus className="size-3" /> Agregar columna
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 9. FECHA */}
                    {pregunta.tipo_pregunta === 'FECHA' && (
                        <div className="flex items-center gap-2 max-w-xs py-2 border-b border-dashed border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))]/60">
                            <Calendar className="size-4" />
                            <span>dd/mm/aaaa</span>
                        </div>
                    )}

                    {/* 10. HORA */}
                    {pregunta.tipo_pregunta === 'HORA' && (
                        <div className="flex items-center gap-2 max-w-xs py-2 border-b border-dashed border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))]/60">
                            <Clock className="size-4" />
                            <span>hh:mm</span>
                        </div>
                    )}

                    {/* 11. SUBIR ARCHIVO */}
                    {pregunta.tipo_pregunta === 'SUBIR_ARCHIVO' && (
                        <div className="flex items-center gap-3 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/30 max-w-md">
                            <UploadCloud className="size-5 text-[hsl(var(--primary))]" />
                            <div className="text-xs">
                                <span className="font-medium text-[hsl(var(--text-primary))] block">
                                    Subida de archivos habilitada
                                </span>
                                <span className="text-[hsl(var(--text-secondary))] text-[11px]">
                                    Máximo {pregunta.archivo_max_mb || 10} MB por archivo
                                </span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer de Tarjeta: Controles y Acciones */}
                <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--border))] text-xs">
                    <div className="flex items-center gap-2">
                        {!isSection && (
                            <label className="flex items-center gap-2 cursor-pointer select-none">
                                <input
                                    type="checkbox"
                                    checked={pregunta.es_requerida}
                                    onChange={(e) => onChange({ ...pregunta, es_requerida: e.target.checked })}
                                    className="size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-0 cursor-pointer"
                                />
                                <span className="text-xs font-medium text-[hsl(var(--text-primary))]">
                                    Obligatoria
                                </span>
                            </label>
                        )}
                    </div>

                    <div className="flex items-center gap-1.5">
                        <button
                            type="button"
                            onClick={onDuplicate}
                            className="p-1.5 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                            title="Duplicar pregunta"
                        >
                            <Copy className="size-3.5" />
                        </button>
                        <button
                            type="button"
                            onClick={onDelete}
                            className="p-1.5 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                            title="Eliminar pregunta"
                        >
                            <Trash2 className="size-3.5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

"use client";

import React, { useState } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
    Plus,
    Split,
    Save,
    Eye,
    Palette,
    Loader2,
    Sparkles,
} from 'lucide-react';
import QuestionEditorCard from './QuestionEditorCard';
import { EncuestaFormulario, EncuestaPregunta, TipoPregunta } from '@/types/surveys';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface FormBuilderTabProps {
    survey: EncuestaFormulario;
    onSurveyUpdated: (updated: EncuestaFormulario) => void;
}

const THEME_COLORS = [
    { label: 'Azul CCF', hex: '#0284c7' },
    { label: 'Índigo Real', hex: '#6366f1' },
    { label: 'Violeta Reino', hex: '#8b5cf6' },
    { label: 'Esmeralda Vida', hex: '#10b981' },
    { label: 'Ámbar Faro', hex: '#f59e0b' },
    { label: 'Rosa Bendición', hex: '#ec4899' },
    { label: 'Pizarra Clásico', hex: '#475569' },
];

export default function FormBuilderTab({ survey, onSurveyUpdated }: FormBuilderTabProps) {
    const [titulo, setTitulo] = useState(survey.titulo || '');
    const [descripcion, setDescripcion] = useState(survey.descripcion || '');
    const [colorPrimario, setColorPrimario] = useState(survey.config_visual?.color_primario || '#0284c7');
    const [preguntas, setPreguntas] = useState<EncuestaPregunta[]>(survey.preguntas || []);
    const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(
        survey.preguntas?.[0]?.id || null
    );
    const [isSaving, setIsSaving] = useState(false);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 5,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id) {
            setPreguntas((items) => {
                const oldIndex = items.findIndex((i) => i.id === active.id);
                const newIndex = items.findIndex((i) => i.id === over.id);
                const reordered = arrayMove(items, oldIndex, newIndex);
                return reordered.map((q, idx) => ({ ...q, orden: idx }));
            });
        }
    };

    const handleAddQuestion = (tipo: TipoPregunta = 'OPCION_MULTIPLE') => {
        const newId = `q-${Date.now()}`;
        const newQuestion: EncuestaPregunta = {
            id: newId,
            formulario_id: survey.id,
            titulo: 'Pregunta sin título',
            descripcion: null,
            tipo_pregunta: tipo,
            orden: preguntas.length,
            es_requerida: false,
            opciones: ['OPCION_MULTIPLE', 'CASILLAS', 'DESPLEGABLE'].includes(tipo)
                ? [
                      { id: `opt-${Date.now()}-1`, label: 'Opción 1' },
                      { id: `opt-${Date.now()}-2`, label: 'Opción 2' },
                  ]
                : [],
            filas: [],
            columnas: [],
            escala_min: 1,
            escala_max: 5,
            archivo_tipos_permitidos: [],
            archivo_max_mb: 10,
            archivo_max_archivos: 1,
            configuracion: {},
        };

        const updated = [...preguntas, newQuestion];
        setPreguntas(updated);
        setSelectedQuestionId(newId);
    };

    const handleAddSection = () => {
        handleAddQuestion('SECCION_SALTO');
    };

    const handleUpdateQuestion = (updated: EncuestaPregunta) => {
        setPreguntas((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
    };

    const handleDuplicateQuestion = (idx: number) => {
        const original = preguntas[idx];
        const newId = `q-${Date.now()}`;
        const duplicate: EncuestaPregunta = {
            ...original,
            id: newId,
            titulo: `${original.titulo} (Copia)`,
            orden: idx + 1,
        };

        const updated = [...preguntas];
        updated.splice(idx + 1, 0, duplicate);
        const reordered = updated.map((q, i) => ({ ...q, orden: i }));
        setPreguntas(reordered);
        setSelectedQuestionId(newId);
    };

    const handleDeleteQuestion = (idx: number) => {
        const updated = preguntas.filter((_, i) => i !== idx);
        const reordered = updated.map((q, i) => ({ ...q, orden: i }));
        setPreguntas(reordered);
        if (selectedQuestionId === preguntas[idx]?.id) {
            setSelectedQuestionId(reordered[0]?.id || null);
        }
    };

    const handleSaveAll = async () => {
        setIsSaving(true);
        try {
            // 1. Guardar metadatos del formulario vía PATCH
            const updatedSurveyData = await apiFetch<EncuestaFormulario>(`/api/surveys/${survey.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    titulo: titulo.trim(),
                    descripcion: descripcion.trim() || null,
                    config_visual: {
                        ...(survey.config_visual || {}),
                        color_primario: colorPrimario,
                    },
                }),
            });

            // 2. Sincronizar batch de preguntas vía PUT
            const formattedPreguntas = preguntas.map((q, idx) => ({
                titulo: q.titulo,
                descripcion: q.descripcion || null,
                tipo_pregunta: q.tipo_pregunta,
                orden: idx,
                es_requerida: q.es_requerida,
                opciones: q.opciones || [],
                filas: q.filas || [],
                columnas: q.columnas || [],
                escala_min: q.escala_min || 1,
                escala_max: q.escala_max || 5,
                escala_min_etiqueta: q.escala_min_etiqueta || null,
                escala_max_etiqueta: q.escala_max_etiqueta || null,
                archivo_tipos_permitidos: q.archivo_tipos_permitidos || [],
                archivo_max_mb: q.archivo_max_mb || 10,
                archivo_max_archivos: q.archivo_max_archivos || 1,
                configuracion: q.configuracion || {},
            }));

            const updatedQuestions = await apiFetch<EncuestaPregunta[]>(`/api/surveys/${survey.id}/questions`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preguntas: formattedPreguntas }),
            });

            const mergedSurvey: EncuestaFormulario = {
                ...updatedSurveyData,
                preguntas: updatedQuestions,
            };

            setPreguntas(updatedQuestions);
            onSurveyUpdated(mergedSurvey);
            toast.success('Formulario guardado y sincronizado exitosamente');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al guardar los cambios';
            toast.error(msg);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto pb-24">
            {/* Barra superior de acciones fijas */}
            <div className="sticky top-0 z-20 flex items-center justify-between py-3 mb-6 bg-[hsl(var(--surface-1))]/90 backdrop-blur-md border-b border-[hsl(var(--border))]">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[hsl(var(--text-secondary))]">
                        {preguntas.length} {preguntas.length === 1 ? 'pregunta' : 'preguntas'}
                    </span>
                    <span className="size-1 rounded-full bg-[hsl(var(--border))]" />
                    <span className="text-xs text-[hsl(var(--text-secondary))]/70">
                        {survey.estado}
                    </span>
                </div>

                <div className="flex items-center gap-2.5">
                    <a
                        href={`/surveys/${survey.slug || survey.id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                        title="Abrir vista pública para encuestados"
                    >
                        <Eye className="size-3.5" />
                        Vista Previa
                    </a>

                    <button
                        type="button"
                        onClick={handleSaveAll}
                        disabled={isSaving}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-medium hover:opacity-95 transition-opacity disabled:opacity-50 shadow-sm"
                    >
                        {isSaving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
                        {isSaving ? 'Guardando...' : 'Guardar Cambios'}
                    </button>
                </div>
            </div>

            <div className="flex flex-col gap-5">
                {/* 1. Tarjeta de Cabecera del Formulario */}
                <div
                    className="relative overflow-hidden rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-6 shadow-sm"
                    style={{ borderTop: `6px solid ${colorPrimario}` }}
                >
                    <div className="flex flex-col gap-3">
                        <input
                            type="text"
                            value={titulo}
                            onChange={(e) => setTitulo(e.target.value)}
                            placeholder="Título de la Encuesta"
                            className="text-2xl sm:text-3xl font-bold text-[hsl(var(--text-primary))] bg-transparent border-b border-transparent hover:border-[hsl(var(--border))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors pb-1"
                        />
                        <textarea
                            value={descripcion}
                            onChange={(e) => setDescripcion(e.target.value)}
                            placeholder="Descripción o instrucciones del formulario..."
                            rows={2}
                            className="text-xs sm:text-sm text-[hsl(var(--text-secondary))] bg-transparent border-b border-transparent hover:border-[hsl(var(--border))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors resize-none"
                        />
                    </div>

                    {/* Paleta de Acento Visual */}
                    <div className="flex items-center gap-3 pt-4 mt-4 border-t border-[hsl(var(--border))]/60">
                        <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))] font-medium">
                            <Palette className="size-3.5" />
                            <span>Color de tema:</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {THEME_COLORS.map((c) => (
                                <button
                                    key={c.hex}
                                    type="button"
                                    onClick={() => setColorPrimario(c.hex)}
                                    title={c.label}
                                    className={`size-5 rounded-full transition-transform ${
                                        colorPrimario === c.hex ? 'scale-125 ring-2 ring-[hsl(var(--border))]' : 'hover:scale-110'
                                    }`}
                                    style={{ backgroundColor: c.hex }}
                                />
                            ))}
                        </div>
                    </div>
                </div>

                {/* 2. Lista de Preguntas con Drag and Drop */}
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext items={preguntas.map((q) => q.id)} strategy={verticalListSortingStrategy}>
                        <div className="flex flex-col gap-4">
                            {preguntas.map((pregunta, index) => (
                            <QuestionEditorCard
                                key={pregunta.id}
                                pregunta={pregunta}
                                index={index}
                                availableQuestions={preguntas}
                                    isSelected={selectedQuestionId === pregunta.id}
                                    onSelect={() => setSelectedQuestionId(pregunta.id)}
                                    onChange={handleUpdateQuestion}
                                    onDuplicate={() => handleDuplicateQuestion(index)}
                                    onDelete={() => handleDeleteQuestion(index)}
                                />
                            ))}
                        </div>
                    </SortableContext>
                </DndContext>

                {/* Estado vacío si no hay preguntas */}
                {preguntas.length === 0 && (
                    <div className="p-8 text-center rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/30">
                        <Sparkles className="size-8 mx-auto text-[hsl(var(--text-secondary))]/50 mb-2" />
                        <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                            Esta encuesta aún no tiene preguntas
                        </h4>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 mb-4">
                            Haz clic en el botón de abajo para añadir tu primera pregunta.
                        </p>
                        <button
                            type="button"
                            onClick={() => handleAddQuestion('OPCION_MULTIPLE')}
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-medium"
                        >
                            <Plus className="size-3.5" />
                            Añadir Primera Pregunta
                        </button>
                    </div>
                )}

                {/* 3. Barra de Agregar Pregunta / Sección */}
                <div className="flex items-center justify-center gap-3 pt-4">
                    <button
                        type="button"
                        onClick={() => handleAddQuestion('OPCION_MULTIPLE')}
                        className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs font-semibold text-[hsl(var(--text-primary))] hover:border-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-all shadow-sm"
                    >
                        <Plus className="size-4 text-[hsl(var(--primary))]" />
                        Añadir Pregunta
                    </button>

                    <button
                        type="button"
                        onClick={handleAddSection}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs font-semibold text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-all shadow-sm"
                    >
                        <Split className="size-4 text-[hsl(var(--text-secondary))]" />
                        Añadir Sección
                    </button>
                </div>
            </div>
        </div>
    );
}

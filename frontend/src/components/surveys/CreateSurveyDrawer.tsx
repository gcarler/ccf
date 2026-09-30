"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import SidePanel from '@/components/ui/SidePanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { FileText, Sparkles, HeartHandshake, Calendar, Loader2 } from 'lucide-react';
import { TipoPregunta } from '@/types/surveys';

interface CreateSurveyDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated?: (surveyId: string) => void;
}

interface TemplateOption {
    id: string;
    title: string;
    description: string;
    icon: React.ElementType;
    preguntas: Array<{
        titulo: string;
        tipo_pregunta: TipoPregunta;
        es_requerida: boolean;
        opciones?: Array<{ id: string; label: string }>;
        escala_min?: number;
        escala_max?: number;
        escala_min_etiqueta?: string;
        escala_max_etiqueta?: string;
    }>;
}

const TEMPLATES: TemplateOption[] = [
    {
        id: 'blank',
        title: 'Formulario en Blanco',
        description: 'Empieza desde cero con una encuesta vacía y personalizada.',
        icon: FileText,
        preguntas: [
            {
                titulo: 'Pregunta sin título',
                tipo_pregunta: 'OPCION_MULTIPLE',
                es_requerida: false,
                opciones: [
                    { id: 'opt-1', label: 'Opción 1' },
                    { id: 'opt-2', label: 'Opción 2' },
                ],
            },
        ],
    },
    {
        id: 'satisfaction',
        title: 'Satisfacción del Servicio',
        description: 'Mide la experiencia de la congregación en los servicios dominicales.',
        icon: Sparkles,
        preguntas: [
            {
                titulo: '¿Cómo calificarías el servicio general de hoy?',
                tipo_pregunta: 'ESCALA_LINEAL',
                es_requerida: true,
                escala_min: 1,
                escala_max: 5,
                escala_min_etiqueta: 'Regular',
                escala_max_etiqueta: 'Excelente',
            },
            {
                titulo: '¿A qué reunión asististe?',
                tipo_pregunta: 'OPCION_MULTIPLE',
                es_requerida: true,
                opciones: [
                    { id: 's1', label: '8:00 AM (Primera)' },
                    { id: 's2', label: '10:30 AM (Segunda)' },
                    { id: 's3', label: '6:00 PM (Noche)' },
                ],
            },
            {
                titulo: '¿Qué fue lo más edificante para tu vida?',
                tipo_pregunta: 'PARRAFO',
                es_requerida: false,
            },
        ],
    },
    {
        id: 'volunteers',
        title: 'Censo y Registro de Voluntarios',
        description: 'Captación de personas interesadas en servir en los ministerios de CCF.',
        icon: HeartHandshake,
        preguntas: [
            {
                titulo: 'Nombre Completo',
                tipo_pregunta: 'TEXTO_CORTO',
                es_requerida: true,
            },
            {
                titulo: '¿En qué ministerio te apasiona servir?',
                tipo_pregunta: 'OPCION_MULTIPLE',
                es_requerida: true,
                opciones: [
                    { id: 'm1', label: 'Alabanza y Adoración' },
                    { id: 'm2', label: 'Evangelismo y Casas de Bendición' },
                    { id: 'm3', label: 'Medios y Comunicaciones' },
                    { id: 'm4', label: 'Ministerio de Niños (Generación Faro)' },
                    { id: 'm5', label: 'Ujieres y Protocolo' },
                ],
            },
            {
                titulo: 'Disponibilidad de días para capacitaciones y servicio',
                tipo_pregunta: 'CASILLAS',
                es_requerida: true,
                opciones: [
                    { id: 'd1', label: 'Entre semana en las noches' },
                    { id: 'd2', label: 'Sábados' },
                    { id: 'd3', label: 'Domingos' },
                ],
            },
        ],
    },
    {
        id: 'event_feedback',
        title: 'Feedback de Retiro o Evento',
        description: 'Evaluación post-evento para medir impacto espiritual y logística.',
        icon: Calendar,
        preguntas: [
            {
                titulo: 'Calificación de la logística y atención',
                tipo_pregunta: 'ESCALA_LINEAL',
                es_requerida: true,
                escala_min: 1,
                escala_max: 5,
            },
            {
                titulo: '¿Participarías en el próximo evento?',
                tipo_pregunta: 'OPCION_MULTIPLE',
                es_requerida: true,
                opciones: [
                    { id: 'y', label: '¡Totalmente, no me lo perdería!' },
                    { id: 'm', label: 'Probablemente sí' },
                    { id: 'n', label: 'No estoy seguro' },
                ],
            },
        ],
    },
];

export default function CreateSurveyDrawer({ isOpen, onClose, onCreated }: CreateSurveyDrawerProps) {
    const router = useRouter();
    const [titulo, setTitulo] = useState('');
    const [descripcion, setDescripcion] = useState('');
    const [slug, setSlug] = useState('');
    const [selectedTemplate, setSelectedTemplate] = useState('blank');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!titulo.trim()) {
            toast.error('Por favor escribe un título para la encuesta');
            return;
        }

        setIsSubmitting(true);
        try {
            const template = TEMPLATES.find((t) => t.id === selectedTemplate) || TEMPLATES[0];

            const payload = {
                titulo: titulo.trim(),
                descripcion: descripcion.trim() || null,
                slug: slug.trim() || undefined,
                estado: 'BORRADOR',
                config_visual: {
                    tema: 'light',
                    color_primario: '#0284c7',
                    fuente: 'Inter',
                },
                preguntas: template.preguntas,
            };

            const data = await apiFetch<any>('/api/surveys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            toast.success('¡Encuesta creada exitosamente!');
            onClose();
            if (onCreated) {
                onCreated(data.id);
            }
            router.push(`/plataforma/surveys/${data.id}`);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al crear la encuesta';
            toast.error(msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <SidePanel
            isOpen={isOpen}
            onClose={onClose}
            title="Nueva Encuesta Dinámica"
            subtitle="CREACIÓN CON PARIDAD GOOGLE FORMS"
            width="w-[520px]"
        >
            <form onSubmit={handleSubmit} className="flex flex-col gap-6 p-6">
                <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                        Título de la Encuesta *
                    </label>
                    <input
                        type="text"
                        value={titulo}
                        onChange={(e) => setTitulo(e.target.value)}
                        placeholder="Ej. Censo de Voluntarios CCF 2026"
                        required
                        className="w-full px-3.5 py-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] transition-all placeholder:text-[hsl(var(--text-secondary))]/50"
                    />
                </div>

                <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                        Descripción o Instrucciones
                    </label>
                    <textarea
                        value={descripcion}
                        onChange={(e) => setDescripcion(e.target.value)}
                        placeholder="Explica a los miembros de CCF el propósito de esta encuesta..."
                        rows={3}
                        className="w-full px-3.5 py-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] transition-all placeholder:text-[hsl(var(--text-secondary))]/50 resize-none"
                    />
                </div>

                <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                        Slug Personalizado (Opcional)
                    </label>
                    <div className="flex items-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden">
                        <span className="px-3 text-xs text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] border-r border-[hsl(var(--border))] py-2.5 select-none font-mono">
                            /surveys/
                        </span>
                        <input
                            type="text"
                            value={slug}
                            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, '-'))}
                            placeholder="censo-voluntarios-2026"
                            className="flex-1 px-3 py-2 text-sm bg-transparent text-[hsl(var(--text-primary))] focus:outline-none font-mono text-xs"
                        />
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">
                        Si lo dejas en blanco, se generará automáticamente a partir del título.
                    </p>
                </div>

                <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2">
                        Seleccionar Plantilla Inicial
                    </label>
                    <div className="grid grid-cols-1 gap-2.5">
                        {TEMPLATES.map((tmpl) => {
                            const Icon = tmpl.icon;
                            const isSelected = selectedTemplate === tmpl.id;
                            return (
                                <button
                                    key={tmpl.id}
                                    type="button"
                                    onClick={() => setSelectedTemplate(tmpl.id)}
                                    className={`flex items-start gap-3.5 p-3.5 rounded-xl border text-left transition-all ${
                                        isSelected
                                            ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 ring-1 ring-[hsl(var(--primary))]'
                                            : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--border))]/80 hover:bg-[hsl(var(--surface-2))]'
                                    }`}
                                >
                                    <div
                                        className={`p-2 rounded-lg ${
                                            isSelected
                                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                                : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                                        }`}
                                    >
                                        <Icon className="size-4" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                                            {tmpl.title}
                                        </div>
                                        <div className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5 line-clamp-2">
                                            {tmpl.description}
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))] mt-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isSubmitting}
                        className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        disabled={isSubmitting || !titulo.trim()}
                        className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-medium hover:opacity-95 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                        {isSubmitting && <Loader2 className="size-3.5 animate-spin" />}
                        {isSubmitting ? 'Creando...' : 'Crear Encuesta'}
                    </button>
                </div>
            </form>
        </SidePanel>
    );
}

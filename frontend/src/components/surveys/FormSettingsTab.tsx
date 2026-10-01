"use client";

import React, { useState } from 'react';
import {
    Share2,
    Copy,
    Check,
    Globe,
    Clock,
    Shield,
    MessageSquare,
    Link as Loader2,
} from 'lucide-react';
import { EncuestaFormulario, EstadoFormulario } from '@/types/surveys';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface FormSettingsTabProps {
    survey: EncuestaFormulario;
    onSurveyUpdated: (updated: EncuestaFormulario) => void;
}

export default function FormSettingsTab({ survey, onSurveyUpdated }: FormSettingsTabProps) {
    const [estado, setEstado] = useState<EstadoFormulario>(survey.estado || 'BORRADOR');
    const [slug, setSlug] = useState(survey.slug || '');
    const [limitarUnaRespuesta, setLimitarUnaRespuesta] = useState(survey.limitar_una_respuesta || false);
    const [requiereAutenticacion, setRequiereAutenticacion] = useState(survey.requiere_autenticacion || false);
    const [mostrarBarraProgreso, setMostrarBarraProgreso] = useState(survey.mostrar_barra_progreso ?? true);
    const [permitirEditar] = useState(survey.permitir_editar_respuesta || false);
    const [mensajeConfirmacion, setMensajeConfirmacion] = useState(
        survey.mensaje_confirmacion || '¡Tu respuesta ha sido registrada exitosamente!'
    );
    const [redirigirUrl, setRedirigirUrl] = useState(survey.redirigir_url || '');
    const [maxRespuestas, setMaxRespuestas] = useState<string>(
        survey.max_respuestas ? String(survey.max_respuestas) : ''
    );
    const [fechaApertura, setFechaApertura] = useState(
        survey.fecha_apertura ? survey.fecha_apertura.substring(0, 16) : ''
    );
    const [fechaCierre, setFechaCierre] = useState(
        survey.fecha_cierre ? survey.fecha_cierre.substring(0, 16) : ''
    );

    const [isSaving, setIsSaving] = useState(false);
    const [copied, setCopied] = useState(false);

    const publicUrl = typeof window !== 'undefined'
        ? `${window.location.origin}/surveys/${survey.slug || survey.id}`
        : `/surveys/${survey.slug || survey.id}`;

    const handleCopyLink = () => {
        navigator.clipboard.writeText(publicUrl);
        setCopied(true);
        toast.success('¡Enlace público copiado al portapapeles!');
        setTimeout(() => setCopied(false), 2500);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            const payload = {
                estado,
                slug: slug.trim() || undefined,
                limitar_una_respuesta: limitarUnaRespuesta,
                requiere_autenticacion: requiereAutenticacion,
                mostrar_barra_progreso: mostrarBarraProgreso,
                permitir_editar_respuesta: permitirEditar,
                mensaje_confirmacion: mensajeConfirmacion.trim() || null,
                redirigir_url: redirigirUrl.trim() || null,
                max_respuestas: maxRespuestas ? parseInt(maxRespuestas, 10) : null,
                fecha_apertura: fechaApertura ? new Date(fechaApertura).toISOString() : null,
                fecha_cierre: fechaCierre ? new Date(fechaCierre).toISOString() : null,
            };

            const updated = await apiFetch<EncuestaFormulario>(`/surveys/${survey.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            onSurveyUpdated(updated);
            toast.success('Configuración de la encuesta actualizada');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al guardar la configuración';
            toast.error(msg);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <form onSubmit={handleSave} className="max-w-3xl mx-auto pb-24 flex flex-col gap-6">
            {/* 1. Tarjeta de Enlace Público y Compartir */}
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                    <Share2 className="size-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Enlace Público para Encuestados
                    </h3>
                </div>
                <p className="text-xs text-[hsl(var(--text-secondary))] mb-3">
                    Comparte este enlace con los miembros de CCF, grupos de WhatsApp o en los servicios dominicales.
                </p>
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        readOnly
                        value={publicUrl}
                        className="flex-1 px-3 py-2 text-xs font-mono rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] select-all"
                    />
                    <button
                        type="button"
                        onClick={handleCopyLink}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-medium hover:opacity-95 transition-all shadow-sm"
                    >
                        {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                        {copied ? 'Copiado' : 'Copiar Enlace'}
                    </button>
                </div>
            </div>

            {/* 2. Ciclo de Vida y Estado */}
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <Globe className="size-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Estado del Formulario
                    </h3>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {(['BORRADOR', 'PUBLICADO', 'CERRADO', 'ARCHIVADO'] as EstadoFormulario[]).map((st) => {
                        const isSelected = estado === st;
                        return (
                            <button
                                key={st}
                                type="button"
                                onClick={() => setEstado(st)}
                                className={`py-2 px-3 rounded-lg border text-xs font-medium transition-all ${
                                    isSelected
                                        ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] font-semibold ring-1 ring-[hsl(var(--primary))]'
                                        : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))]'
                                }`}
                            >
                                {st}
                            </button>
                        );
                    })}
                </div>

                <div>
                    <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                        Slug Personalizado (URL)
                    </label>
                    <input
                        type="text"
                        value={slug}
                        onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, '-'))}
                        placeholder="censo-faro-2026"
                        className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    />
                </div>
            </div>

            {/* 3. Control de Respuestas y Privacidad */}
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <Shield className="size-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Control de Respuestas y Privacidad
                    </h3>
                </div>

                <div className="flex flex-col gap-3.5">
                    <label className="flex items-start gap-3 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={limitarUnaRespuesta}
                            onChange={(e) => setLimitarUnaRespuesta(e.target.checked)}
                            className="mt-0.5 size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))]"
                        />
                        <div>
                            <span className="text-xs font-semibold text-[hsl(var(--text-primary))] block">
                                Limitar a 1 respuesta por persona
                            </span>
                            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                                Previene envíos duplicados identificando al usuario o su sesión.
                            </span>
                        </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={requiereAutenticacion}
                            onChange={(e) => setRequiereAutenticacion(e.target.checked)}
                            className="mt-0.5 size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))]"
                        />
                        <div>
                            <span className="text-xs font-semibold text-[hsl(var(--text-primary))] block">
                                Requerir inicio de sesión obligatorio
                            </span>
                            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                                Solo usuarios con cuenta activa en la plataforma podrán contestar.
                            </span>
                        </div>
                    </label>

                    <label className="flex items-start gap-3 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            checked={mostrarBarraProgreso}
                            onChange={(e) => setMostrarBarraProgreso(e.target.checked)}
                            className="mt-0.5 size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))]"
                        />
                        <div>
                            <span className="text-xs font-semibold text-[hsl(var(--text-primary))] block">
                                Mostrar barra de progreso
                            </span>
                            <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                                Muestra un indicador visual de avance a medida que el encuestado responde las secciones.
                            </span>
                        </div>
                    </label>
                </div>
            </div>

            {/* 4. Ventana de Vigencia y Cupo Máximo */}
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <Clock className="size-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Vigencia y Límites
                    </h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                            Fecha de Apertura
                        </label>
                        <input
                            type="datetime-local"
                            value={fechaApertura}
                            onChange={(e) => setFechaApertura(e.target.value)}
                            className="w-full text-xs px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                            Fecha de Cierre
                        </label>
                        <input
                            type="datetime-local"
                            value={fechaCierre}
                            onChange={(e) => setFechaCierre(e.target.value)}
                            className="w-full text-xs px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                            Límite Máximo de Respuestas
                        </label>
                        <input
                            type="number"
                            value={maxRespuestas}
                            onChange={(e) => setMaxRespuestas(e.target.value)}
                            placeholder="Ilimitado"
                            className="w-full text-xs px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                        />
                    </div>
                </div>
            </div>

            {/* 5. Mensaje de Cierre y Redirección */}
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <MessageSquare className="size-4 text-[hsl(var(--primary))]" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Experiencia al Enviar
                    </h3>
                </div>

                <div>
                    <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                        Mensaje de Confirmación
                    </label>
                    <textarea
                        value={mensajeConfirmacion}
                        onChange={(e) => setMensajeConfirmacion(e.target.value)}
                        rows={2}
                        className="w-full text-xs px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] resize-none"
                    />
                </div>

                <div>
                    <label className="block text-xs font-semibold text-[hsl(var(--text-secondary))] mb-1.5">
                        URL de Redirección (Opcional)
                    </label>
                    <input
                        type="url"
                        value={redirigirUrl}
                        onChange={(e) => setRedirigirUrl(e.target.value)}
                        placeholder="https://ccf.org/gracias"
                        className="w-full text-xs px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))]"
                    />
                </div>
            </div>

            {/* Botón Guardar Cambios */}
            <div className="flex justify-end">
                <button
                    type="submit"
                    disabled={isSaving}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold hover:opacity-95 transition-opacity disabled:opacity-50 shadow-sm"
                >
                    {isSaving && <Loader2 className="size-3.5 animate-spin" />}
                    {isSaving ? 'Guardando ajustes...' : 'Guardar Ajustes'}
                </button>
            </div>
        </form>
    );
}

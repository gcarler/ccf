"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    BarChart3,
    Table as TableIcon,
    Download,
    Calendar,
    User,
    Mail,
    RefreshCw,
    Loader2,
    Eye,
    Inbox,
} from 'lucide-react';
import SidePanel from '@/components/ui/SidePanel';
import {
    EncuestaFormulario,
    EncuestaAnalyticsSummary,
    EncuestaRespuestasTableResponse,
    EncuestaRespuestaIndividual,
} from '@/types/surveys';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface FormResponsesTabProps {
    survey: EncuestaFormulario;
}

export default function FormResponsesTab({ survey }: FormResponsesTabProps) {
    const [subTab, setSubTab] = useState<'analytics' | 'table'>('analytics');
    const [analytics, setAnalytics] = useState<EncuestaAnalyticsSummary | null>(null);
    const [tableData, setTableData] = useState<EncuestaRespuestasTableResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [page] = useState(0);
    const pageSize = 20;

    // Drawer de detalle individual
    const [selectedEnvioId, setSelectedEnvioId] = useState<string | null>(null);
    const [individualResponse, setIndividualResponse] = useState<EncuestaRespuestaIndividual | null>(null);
    const [isLoadingIndividual, setIsLoadingIndividual] = useState(false);

    const loadAnalytics = useCallback(async () => {
        try {
            const data = await apiFetch<EncuestaAnalyticsSummary>(`/surveys/${survey.id}/analytics/summary`);
            setAnalytics(data);
        } catch (err: unknown) {
            console.error('Error cargando analítica:', err);
        }
    }, [survey.id]);

    const loadTable = useCallback(async (skipCount: number) => {
        try {
            const data = await apiFetch<EncuestaRespuestasTableResponse>(
                `/surveys/${survey.id}/responses/table?skip=${skipCount}&limit=${pageSize}`
            );
            setTableData(data);
        } catch (err: unknown) {
            console.error('Error cargando tabla de respuestas:', err);
        }
    }, [survey.id, pageSize]);

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        await Promise.all([loadAnalytics(), loadTable(page * pageSize)]);
        setIsLoading(false);
    }, [loadAnalytics, loadTable, page, pageSize]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleOpenIndividual = async (envioId: string) => {
        setSelectedEnvioId(envioId);
        setIsLoadingIndividual(true);
        try {
            const data = await apiFetch<EncuestaRespuestaIndividual>(
                `/surveys/${survey.id}/responses/individual/${envioId}`
            );
            setIndividualResponse(data);
        } catch (err: unknown) {
            toast.error('No se pudo cargar la respuesta individual');
            setSelectedEnvioId(null);
        } finally {
            setIsLoadingIndividual(false);
        }
    };

    const handleExportCSV = async () => {
        try {
            toast.info('Generando archivo CSV...');
            window.location.href = `/api/surveys/${survey.id}/export/csv`;
        } catch (err: unknown) {
            toast.error('Error al exportar CSV');
        }
    };

    return (
        <div className="max-w-5xl mx-auto pb-24">
            {/* Header de la Pestaña de Respuestas */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4 mb-6 border-b border-[hsl(var(--border))]">
                <div className="flex items-center gap-3">
                    <div className="flex items-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-1">
                        <button
                            type="button"
                            onClick={() => setSubTab('analytics')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                subTab === 'analytics'
                                    ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] shadow-sm'
                                    : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                            }`}
                        >
                            <BarChart3 className="size-3.5" />
                            Resumen Estadístico
                        </button>
                        <button
                            type="button"
                            onClick={() => setSubTab('table')}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                                subTab === 'table'
                                    ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] shadow-sm'
                                    : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                            }`}
                        >
                            <TableIcon className="size-3.5" />
                            Tabla de Respuestas
                        </button>
                    </div>

                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                        {analytics?.total_respuestas || survey.total_respuestas || 0} respuestas
                    </span>
                </div>

                <div className="flex items-center gap-2.5">
                    <button
                        type="button"
                        onClick={fetchData}
                        disabled={isLoading}
                        className="p-2 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                        title="Actualizar datos"
                    >
                        <RefreshCw className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                    <button
                        type="button"
                        onClick={handleExportCSV}
                        className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-medium hover:opacity-95 transition-opacity shadow-sm"
                    >
                        <Download className="size-3.5" />
                        Descargar CSV (Excel)
                    </button>
                </div>
            </div>

            {isLoading && (
                <div className="py-20 flex flex-col items-center justify-center text-[hsl(var(--text-secondary))]">
                    <Loader2 className="size-8 animate-spin text-[hsl(var(--primary))] mb-3" />
                    <span className="text-xs">Cargando respuestas y analítica...</span>
                </div>
            )}

            {!isLoading && (analytics?.total_respuestas || 0) === 0 && (
                <div className="py-20 text-center rounded-2xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/20">
                    <Inbox className="size-12 mx-auto text-[hsl(var(--text-secondary))]/40 mb-3" />
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        Aún no hay respuestas registradas
                    </h3>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 max-w-sm mx-auto">
                        Comparte el enlace público de tu encuesta para comenzar a recolectar información en tiempo real.
                    </p>
                </div>
            )}

            {/* VISTA 1: RESUMEN ANALÍTICO */}
            {!isLoading && (analytics?.total_respuestas || 0) > 0 && subTab === 'analytics' && (
                <div className="flex flex-col gap-6">
                    {/* Tarjeta de Métricas Globales */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-1">
                                Total Respuestas
                            </span>
                            <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">
                                {analytics?.total_respuestas}
                            </span>
                        </div>
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-1">
                                Primera Respuesta
                            </span>
                            <span className="text-xs text-[hsl(var(--text-primary))] font-medium">
                                {analytics?.primera_respuesta
                                    ? new Date(analytics.primera_respuesta).toLocaleDateString('es-CO', {
                                          day: '2-digit',
                                          month: 'short',
                                          year: 'numeric',
                                          hour: '2-digit',
                                          minute: '2-digit',
                                      })
                                    : 'N/A'}
                            </span>
                        </div>
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-1">
                                Última Respuesta
                            </span>
                            <span className="text-xs text-[hsl(var(--text-primary))] font-medium">
                                {analytics?.ultima_respuesta
                                    ? new Date(analytics.ultima_respuesta).toLocaleDateString('es-CO', {
                                          day: '2-digit',
                                          month: 'short',
                                          year: 'numeric',
                                          hour: '2-digit',
                                          minute: '2-digit',
                                      })
                                    : 'N/A'}
                            </span>
                        </div>
                    </div>

                    {/* Desglose por Pregunta */}
                    {analytics?.preguntas.map((p, idx) => (
                        <div
                            key={p.pregunta_id}
                            className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm"
                        >
                            <div className="flex items-start justify-between gap-4 mb-4">
                                <div>
                                    <span className="text-[11px] font-mono text-[hsl(var(--text-secondary))] block">
                                        Pregunta {idx + 1} • {p.tipo_pregunta}
                                    </span>
                                    <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))] mt-0.5">
                                        {p.titulo}
                                    </h4>
                                </div>
                                <span className="text-xs text-[hsl(var(--text-secondary))] whitespace-nowrap">
                                    {p.total_respuestas} {p.total_respuestas === 1 ? 'respuesta' : 'respuestas'}
                                </span>
                            </div>

                            {/* Gráfico de barras para Selección */}
                            {['OPCION_MULTIPLE', 'CASILLAS', 'DESPLEGABLE'].includes(p.tipo_pregunta) && (
                                <div className="flex flex-col gap-2.5 pt-2">
                                    {Object.entries(p.distribucion_opciones || {}).map(([opcion, count]) => {
                                        const pct =
                                            p.total_respuestas > 0
                                                ? Math.round((count / p.total_respuestas) * 100)
                                                : 0;
                                        return (
                                            <div key={opcion} className="flex flex-col gap-1">
                                                <div className="flex items-center justify-between text-xs">
                                                    <span className="text-[hsl(var(--text-primary))] font-medium">
                                                        {opcion}
                                                    </span>
                                                    <span className="text-[hsl(var(--text-secondary))] font-mono">
                                                        {count} ({pct}%)
                                                    </span>
                                                </div>
                                                <div className="h-2 w-full rounded-full bg-[hsl(var(--surface-2))] overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full bg-[hsl(var(--primary))]"
                                                        style={{ width: `${pct}%` }}
                                                    />
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* Tarjeta de Promedio para Escala Lineal */}
                            {p.tipo_pregunta === 'ESCALA_LINEAL' && (
                                <div className="flex items-center gap-6 p-4 rounded-lg bg-[hsl(var(--surface-2))]/50 border border-[hsl(var(--border))]">
                                    <div>
                                        <span className="text-[11px] text-[hsl(var(--text-secondary))] block">
                                            Promedio
                                        </span>
                                        <span className="text-3xl font-extrabold text-[hsl(var(--primary))]">
                                            {p.promedio !== null && p.promedio !== undefined ? p.promedio : '-'}
                                        </span>
                                    </div>
                                    <div className="border-l border-[hsl(var(--border))] pl-6 flex flex-col gap-1 text-xs">
                                        <div>
                                            <span className="text-[hsl(var(--text-secondary))]">Mínimo:</span>{' '}
                                            <span className="font-semibold text-[hsl(var(--text-primary))]">
                                                {p.minimo || '-'}
                                            </span>
                                        </div>
                                        <div>
                                            <span className="text-[hsl(var(--text-secondary))]">Máximo:</span>{' '}
                                            <span className="font-semibold text-[hsl(var(--text-primary))]">
                                                {p.maximo || '-'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Respuestas de Texto */}
                            {['TEXTO_CORTO', 'PARRAFO'].includes(p.tipo_pregunta) && (
                                <div className="flex flex-col gap-2 pt-2">
                                    {p.respuestas_recientes && p.respuestas_recientes.length > 0 ? (
                                        p.respuestas_recientes.map((r, rIdx) => (
                                            <div
                                                key={rIdx}
                                                className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/30 text-xs text-[hsl(var(--text-primary))]"
                                            >
                                                &ldquo;{r}&rdquo;
                                            </div>
                                        ))
                                    ) : (
                                        <span className="text-xs text-[hsl(var(--text-secondary))] italic">
                                            Sin comentarios
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* VISTA 2: TABLA DE RESPUESTAS */}
            {!isLoading && (analytics?.total_respuestas || 0) > 0 && subTab === 'table' && (
                <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]">
                                    {(tableData?.columnas || []).map((col) => (
                                        <th
                                            key={col.key}
                                            className="px-4 py-3 font-semibold whitespace-nowrap min-w-[140px]"
                                        >
                                            {col.label}
                                        </th>
                                    ))}
                                    <th className="px-4 py-3 text-right font-semibold">Acción</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[hsl(var(--border))]">
                                {(tableData?.filas || []).map((row, rowIdx) => (
                                    <tr
                                        key={rowIdx}
                                        className="hover:bg-[hsl(var(--surface-2))]/50 transition-colors"
                                    >
                                        {(tableData?.columnas || []).map((col) => (
                                            <td
                                                key={col.key}
                                                className="px-4 py-2.5 text-[hsl(var(--text-primary))] max-w-xs truncate"
                                            >
                                                {String(row[col.key] || '-')}
                                            </td>
                                        ))}
                                        <td className="px-4 py-2.5 text-right whitespace-nowrap">
                                            <button
                                                type="button"
                                                onClick={() => handleOpenIndividual(String(row.envio_id))}
                                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                                                title="Ver respuesta completa"
                                            >
                                                <Eye className="size-3" />
                                                Ver
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* DRAWER LATERAL: RESPUESTA INDIVIDUAL (ZERO-MODALS) */}
            <SidePanel
                isOpen={Boolean(selectedEnvioId)}
                onClose={() => {
                    setSelectedEnvioId(null);
                    setIndividualResponse(null);
                }}
                title="Detalle de Respuesta Individual"
                subtitle="VISOR DE FORMULARIO COMPLETADO"
                width="w-[500px]"
            >
                <div className="p-6 flex flex-col gap-5">
                    {isLoadingIndividual && (
                        <div className="py-16 text-center text-[hsl(var(--text-secondary))]">
                            <Loader2 className="size-6 animate-spin mx-auto text-[hsl(var(--primary))] mb-2" />
                            <span className="text-xs">Cargando respuesta individual...</span>
                        </div>
                    )}

                    {!isLoadingIndividual && individualResponse && (
                        <>
                            {/* Metadata del respondente */}
                            <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/40 flex flex-col gap-2">
                                <div className="flex items-center gap-2 text-xs font-semibold text-[hsl(var(--text-primary))]">
                                    <User className="size-3.5 text-[hsl(var(--text-secondary))]" />
                                    <span>{individualResponse.nombre_respondente || 'Anónimo'}</span>
                                </div>
                                {individualResponse.email_respondente && (
                                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
                                        <Mail className="size-3.5" />
                                        <span>{individualResponse.email_respondente}</span>
                                    </div>
                                )}
                                <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
                                    <Calendar className="size-3.5" />
                                    <span>
                                        {new Date(individualResponse.created_at).toLocaleString('es-CO')}
                                    </span>
                                </div>
                            </div>

                            {/* Lista de preguntas y respuestas respondidas */}
                            <div className="flex flex-col gap-4">
                                {individualResponse.detalles.map((det, dIdx) => {
                                    const p = survey.preguntas.find((q) => q.id === det.pregunta_id);
                                    return (
                                        <div
                                            key={dIdx}
                                            className="p-3.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]"
                                        >
                                            <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] block mb-1">
                                                {p?.titulo || `Pregunta ${dIdx + 1}`}
                                            </span>
                                            <div className="text-xs font-medium text-[hsl(var(--text-primary))]">
                                                {det.valor_texto !== null && det.valor_texto !== undefined
                                                    ? det.valor_texto
                                                    : det.valor_numero !== null && det.valor_numero !== undefined
                                                    ? det.valor_numero
                                                    : det.valor_fecha ||
                                                      det.valor_hora ||
                                                      (det.valor_json
                                                          ? JSON.stringify(det.valor_json)
                                                          : '(Sin respuesta)')}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    )}
                </div>
            </SidePanel>
        </div>
    );
}

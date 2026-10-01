"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
    Plus,
    Search,
    BarChart3,
    FileText,
    ExternalLink,
    Trash2,
    Users,
    CheckCircle2,
    AlertCircle,
    Archive,
    Loader2,
    Inbox,
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import CreateSurveyDrawer from '@/components/surveys/CreateSurveyDrawer';
import SidePanel from '@/components/ui/SidePanel';
import { EncuestaFormulario, EstadoFormulario } from '@/types/surveys';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

export default function SurveysManagementPage() {
    const router = useRouter();
    const [surveys, setSurveys] = useState<EncuestaFormulario[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('ALL');

    // Drawer de Creación (Zero-Modals!)
    const [isCreateOpen, setIsCreateOpen] = useState(false);

    // Drawer de Confirmación de Eliminación (Zero-Modals!)
    const [surveyToDelete, setSurveyToDelete] = useState<EncuestaFormulario | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const loadSurveys = useCallback(async () => {
        setIsLoading(true);
        try {
            let url = '/api/surveys';
            const params = new URLSearchParams();
            if (statusFilter !== 'ALL') {
                params.append('estado', statusFilter);
            }
            if (searchQuery.trim()) {
                params.append('search', searchQuery.trim());
            }
            if (params.toString()) {
                url += `?${params.toString()}`;
            }

            const data = await apiFetch<EncuestaFormulario[]>(url);
            setSurveys(data || []);
        } catch (err: unknown) {
            console.error('Error cargando encuestas:', err);
            toast.error('No se pudieron cargar las encuestas');
        } finally {
            setIsLoading(false);
        }
    }, [statusFilter, searchQuery]);

    useEffect(() => {
        loadSurveys();
    }, [loadSurveys]);

    const handleDeleteSurvey = async () => {
        if (!surveyToDelete) return;
        setIsDeleting(true);
        try {
            await apiFetch(`/surveys/${surveyToDelete.id}`, {
                method: 'DELETE',
            });
            toast.success('Encuesta eliminada correctamente');
            setSurveyToDelete(null);
            loadSurveys();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al eliminar la encuesta';
            toast.error(msg);
        } finally {
            setIsDeleting(false);
        }
    };

    // Métricas calculadas
    const totalSurveys = surveys.length;
    const totalResponses = surveys.reduce((acc, s) => acc + (s.total_respuestas || 0), 0);
    const publishedCount = surveys.filter((s) => s.estado === 'PUBLICADO').length;

    const getStatusBadge = (estado: EstadoFormulario) => {
        switch (estado) {
            case 'PUBLICADO':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[hsl(var(--success-muted))] text-[hsl(var(--success-text))] border border-[hsl(var(--success))]/30">
                        <CheckCircle2 className="size-3" />
                        Publicado
                    </span>
                );
            case 'BORRADOR':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                        <FileText className="size-3" />
                        Borrador
                    </span>
                );
            case 'CERRADO':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] border border-[hsl(var(--warning))]/30">
                        <AlertCircle className="size-3" />
                        Cerrado
                    </span>
                );
            case 'ARCHIVADO':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]/70 border border-[hsl(var(--border))]">
                        <Archive className="size-3" />
                        Archivado
                    </span>
                );
            default:
                return null;
        }
    };

    return (
        <WorkspaceLayout sidebarTitle="Encuestas Dinámicas">
            <div className="flex-1 overflow-y-auto p-6 max-w-7xl mx-auto w-full">
                {/* Header Principal */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-bold text-[hsl(var(--text-primary))] tracking-tight">
                            Encuestas y Formularios Dinámicos
                        </h1>
                        <p className="text-xs sm:text-sm text-[hsl(var(--text-secondary))] mt-0.5">
                            Crea, distribuye y analiza formularios interactivos con paridad Google Forms para la congregación.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => setIsCreateOpen(true)}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold hover:opacity-95 transition-all shadow-sm"
                    >
                        <Plus className="size-4" />
                        Nueva Encuesta
                    </button>
                </div>

                {/* Métricas Resumen */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
                        <div className="flex items-center justify-between text-[hsl(var(--text-secondary))] mb-1">
                            <span className="text-xs font-medium uppercase tracking-wider">Total Formularios</span>
                            <FileText className="size-4 text-[hsl(var(--primary))]" />
                        </div>
                        <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">{totalSurveys}</span>
                    </div>

                    <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
                        <div className="flex items-center justify-between text-[hsl(var(--text-secondary))] mb-1">
                            <span className="text-xs font-medium uppercase tracking-wider">Respuestas Recolectadas</span>
                            <Users className="size-4 text-[hsl(var(--success))]" />
                        </div>
                        <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">{totalResponses}</span>
                    </div>

                    <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm">
                        <div className="flex items-center justify-between text-[hsl(var(--text-secondary))] mb-1">
                            <span className="text-xs font-medium uppercase tracking-wider">Activas / Publicadas</span>
                            <CheckCircle2 className="size-4 text-[hsl(var(--primary))]" />
                        </div>
                        <span className="text-2xl font-bold text-[hsl(var(--text-primary))]">{publishedCount}</span>
                    </div>
                </div>

                {/* Barra de Filtros y Búsqueda */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-6 p-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                    <div className="relative flex-1">
                        <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Buscar encuestas por título o descripción..."
                            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-transparent text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]/50 focus:outline-none"
                        />
                    </div>

                    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
                        {['ALL', 'PUBLICADO', 'BORRADOR', 'CERRADO', 'ARCHIVADO'].map((filter) => (
                            <button
                                key={filter}
                                type="button"
                                onClick={() => setStatusFilter(filter)}
                                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                                    statusFilter === filter
                                        ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xs'
                                        : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'
                                }`}
                            >
                                {filter === 'ALL' ? 'Todas' : filter}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Lista / Grid de Encuestas */}
                {isLoading && (
                    <div className="py-20 flex flex-col items-center justify-center text-[hsl(var(--text-secondary))]">
                        <Loader2 className="size-8 animate-spin text-[hsl(var(--primary))] mb-3" />
                        <span className="text-xs">Cargando encuestas dinámicas...</span>
                    </div>
                )}

                {!isLoading && surveys.length === 0 && (
                    <div className="py-20 text-center rounded-2xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                        <Inbox className="size-12 mx-auto text-[hsl(var(--text-secondary))]/40 mb-3" />
                        <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                            No se encontraron encuestas
                        </h3>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 mb-4 max-w-sm mx-auto">
                            {searchQuery || statusFilter !== 'ALL'
                                ? 'No hay resultados que coincidan con los filtros aplicados.'
                                : 'Comienza creando tu primera encuesta interactiva para la congregación.'}
                        </p>
                        <button
                            type="button"
                            onClick={() => setIsCreateOpen(true)}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold"
                        >
                            <Plus className="size-4" />
                            Crear Nueva Encuesta
                        </button>
                    </div>
                )}

                {!isLoading && surveys.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {surveys.map((survey) => (
                            <div
                                key={survey.id}
                                className="group flex flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 hover:border-[hsl(var(--primary))]/50 hover:shadow-md transition-all"
                            >
                                <div>
                                    <div className="flex items-center justify-between gap-2 mb-3">
                                        {getStatusBadge(survey.estado)}
                                        <span className="text-[11px] font-mono text-[hsl(var(--text-secondary))]">
                                            {survey.preguntas?.length || 0} preguntas
                                        </span>
                                    </div>

                                    <h3
                                        onClick={() => router.push(`/plataforma/surveys/${survey.id}`)}
                                        className="text-sm font-bold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] cursor-pointer transition-colors line-clamp-1"
                                    >
                                        {survey.titulo}
                                    </h3>

                                    {survey.descripcion && (
                                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 line-clamp-2">
                                            {survey.descripcion}
                                        </p>
                                    )}
                                </div>

                                <div className="pt-4 mt-4 border-t border-[hsl(var(--border))]/60 flex flex-col gap-3">
                                    <div className="flex items-center justify-between text-xs text-[hsl(var(--text-secondary))]">
                                        <span className="font-semibold text-[hsl(var(--text-primary))]">
                                            {survey.total_respuestas || 0} respuestas
                                        </span>
                                        <span className="text-[11px]">
                                            {new Date(survey.updated_at).toLocaleDateString('es-CO', {
                                                day: '2-digit',
                                                month: 'short',
                                            })}
                                        </span>
                                    </div>

                                    <div className="flex items-center justify-between gap-2 pt-1">
                                        <div className="flex items-center gap-1.5">
                                            <button
                                                type="button"
                                                onClick={() => router.push(`/plataforma/surveys/${survey.id}`)}
                                                className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] text-xs font-medium hover:border-[hsl(var(--primary))] transition-colors"
                                            >
                                                Constructor
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() =>
                                                    router.push(`/plataforma/surveys/${survey.id}?tab=responses`)
                                                }
                                                className="p-1.5 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                                                title="Ver analítica y respuestas"
                                            >
                                                <BarChart3 className="size-3.5" />
                                            </button>

                                            {survey.estado === 'PUBLICADO' && (
                                                <a
                                                    href={`/surveys/${survey.slug || survey.id}`}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="p-1.5 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                                                    title="Abrir formulario público"
                                                >
                                                    <ExternalLink className="size-3.5" />
                                                </a>
                                            )}
                                        </div>

                                        <button
                                            type="button"
                                            onClick={() => setSurveyToDelete(survey)}
                                            className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))]/60 hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))]/10 transition-colors"
                                            title="Eliminar encuesta"
                                        >
                                            <Trash2 className="size-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* DRAWER LATERAL: CREACIÓN DE ENCUESTAS (ZERO-MODALS) */}
                <CreateSurveyDrawer
                    isOpen={isCreateOpen}
                    onClose={() => setIsCreateOpen(false)}
                    onCreated={() => loadSurveys()}
                />

                {/* DRAWER LATERAL: CONFIRMACIÓN DE ELIMINACIÓN (ZERO-MODALS) */}
                <SidePanel
                    isOpen={Boolean(surveyToDelete)}
                    onClose={() => setSurveyToDelete(null)}
                    title="Confirmar Eliminación"
                    subtitle="ACCIÓN DESTRUCTORA SEGURA"
                    width="w-[420px]"
                >
                    <div className="p-6 flex flex-col gap-5">
                        <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                            ¿Estás seguro de que deseas eliminar la encuesta{' '}
                            <strong className="text-[hsl(var(--text-primary))] font-semibold">
                                &ldquo;{surveyToDelete?.titulo}&rdquo;
                            </strong>
                            ? Esta acción moverá el formulario a la papelera (soft-delete). Las respuestas recolectadas
                            se preservarán en base de datos de acuerdo con los estándares de plataforma.
                        </p>

                        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))]">
                            <button
                                type="button"
                                onClick={() => setSurveyToDelete(null)}
                                disabled={isDeleting}
                                className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
                            >
                                Cancelar
                            </button>
                            <button
                                type="button"
                                onClick={handleDeleteSurvey}
                                disabled={isDeleting}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--destructive))] text-white text-xs font-semibold hover:opacity-90 disabled:opacity-50"
                            >
                                {isDeleting && <Loader2 className="size-3.5 animate-spin" />}
                                {isDeleting ? 'Eliminando...' : 'Sí, Eliminar'}
                            </button>
                        </div>
                    </div>
                </SidePanel>
            </div>
        </WorkspaceLayout>
    );
}

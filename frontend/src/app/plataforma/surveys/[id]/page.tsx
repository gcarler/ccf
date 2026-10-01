"use client";

import React, { useState, useEffect, useCallback, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
    ChevronLeft,
    FileText,
    BarChart3,
    Settings,
    Eye,
    Loader2,
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import FormBuilderTab from '@/components/surveys/FormBuilderTab';
import FormResponsesTab from '@/components/surveys/FormResponsesTab';
import FormSettingsTab from '@/components/surveys/FormSettingsTab';
import { EncuestaFormulario } from '@/types/surveys';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface SurveyDetailPageProps {
    params: Promise<{ id: string }>;
}

export default function SurveyDetailPage({ params }: SurveyDetailPageProps) {
    const resolvedParams = use(params);
    const surveyId = resolvedParams.id;
    const router = useRouter();
    const searchParams = useSearchParams();

    const [survey, setSurvey] = useState<EncuestaFormulario | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'builder' | 'responses' | 'settings'>('builder');

    useEffect(() => {
        const tabParam = searchParams?.get('tab');
        if (tabParam === 'responses') {
            setActiveTab('responses');
        } else if (tabParam === 'settings') {
            setActiveTab('settings');
        }
    }, [searchParams]);

    const loadSurvey = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await apiFetch<EncuestaFormulario>(`/surveys/${surveyId}`);
            setSurvey(data);
        } catch (err: unknown) {
            console.error('Error cargando encuesta:', err);
            toast.error('No se pudo cargar la encuesta solicitada');
            router.push('/plataforma/surveys');
        } finally {
            setIsLoading(false);
        }
    }, [surveyId, router]);

    useEffect(() => {
        loadSurvey();
    }, [loadSurvey]);

    const handleSurveyUpdated = (updated: EncuestaFormulario) => {
        setSurvey(updated);
    };

    if (isLoading) {
        return (
            <WorkspaceLayout sidebarTitle="Constructor de Encuestas">
                <div className="flex-1 flex flex-col items-center justify-center p-12 text-[hsl(var(--text-secondary))]">
                    <Loader2 className="size-8 animate-spin text-[hsl(var(--primary))] mb-3" />
                    <span className="text-xs font-medium">Cargando constructor de encuesta...</span>
                </div>
            </WorkspaceLayout>
        );
    }

    if (!survey) {
        return null;
    }

    return (
        <WorkspaceLayout sidebarTitle="Constructor de Encuestas">
            <div className="flex-1 flex flex-col h-full overflow-hidden bg-[hsl(var(--surface-2))]/30">
                {/* Header Superior del Constructor */}
                <header className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 px-6 py-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shrink-0">
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={() => router.push('/plataforma/surveys')}
                            className="p-1.5 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                            title="Volver a la lista de encuestas"
                        >
                            <ChevronLeft className="size-4" />
                        </button>

                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-[hsl(var(--text-primary))] max-w-[280px] sm:max-w-md truncate">
                                {survey.titulo}
                            </span>
                            <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                                {survey.estado}
                            </span>
                        </div>
                    </div>

                    {/* Selector de Pestañas Centrado (Estilo Google Forms) */}
                    <div className="flex items-center justify-center">
                        <div className="flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-1">
                            <button
                                type="button"
                                onClick={() => setActiveTab('builder')}
                                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                                    activeTab === 'builder'
                                        ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                            >
                                <FileText className="size-3.5" />
                                Preguntas
                            </button>

                            <button
                                type="button"
                                onClick={() => setActiveTab('responses')}
                                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                                    activeTab === 'responses'
                                        ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                            >
                                <BarChart3 className="size-3.5" />
                                Respuestas
                                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
                                    {survey.total_respuestas || 0}
                                </span>
                            </button>

                            <button
                                type="button"
                                onClick={() => setActiveTab('settings')}
                                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all ${
                                    activeTab === 'settings'
                                        ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                            >
                                <Settings className="size-3.5" />
                                Configuración
                            </button>
                        </div>
                    </div>

                    {/* Acción Rápida: Vista Previa */}
                    <div className="flex items-center justify-end gap-2">
                        <a
                            href={`/surveys/${survey.slug || survey.id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                        >
                            <Eye className="size-3.5" />
                            Vista Pública
                        </a>
                    </div>
                </header>

                {/* Contenido según Pestaña Activa */}
                <main className="flex-1 overflow-y-auto p-4 sm:p-6">
                    {activeTab === 'builder' && (
                        <FormBuilderTab survey={survey} onSurveyUpdated={handleSurveyUpdated} />
                    )}

                    {activeTab === 'responses' && (
                        <FormResponsesTab survey={survey} />
                    )}

                    {activeTab === 'settings' && (
                        <FormSettingsTab survey={survey} onSurveyUpdated={handleSurveyUpdated} />
                    )}
                </main>
            </div>
        </WorkspaceLayout>
    );
}

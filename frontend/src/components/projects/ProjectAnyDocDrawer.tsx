"use client";

import React, { useState, useRef } from 'react';
import RightPanel from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import type { DocumentConversionResponse, ConvertAndPublishWikiResponse } from '@/types/projects';
import {
    FileText,
    UploadCloud,
    Loader2,
    Copy,
    Check,
    Download,
    BookOpen,
    Globe,
    Layers,
    Clock,
    FileSpreadsheet,
    FileCode,
    Sparkles,
    RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';

interface ProjectAnyDocDrawerProps {
    projectId: string;
    projectTitle?: string;
    isOpen: boolean;
    onClose: () => void;
    onPublished?: (res: ConvertAndPublishWikiResponse) => void;
}

export function ProjectAnyDocDrawer({
    projectId,
    projectTitle = 'Proyecto',
    isOpen,
    onClose,
    onPublished,
}: ProjectAnyDocDrawerProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isConverting, setIsConverting] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [conversion, setConversion] = useState<DocumentConversionResponse | null>(null);
    const [activeTab, setActiveTab] = useState<'preview' | 'source'>('preview');
    const [copied, setCopied] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            setConversion(null);
            void executeConversion(selectedFile);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            setFile(droppedFile);
            setConversion(null);
            void executeConversion(droppedFile);
        }
    };

    const executeConversion = async (targetFile: File) => {
        setIsConverting(true);
        try {
            const reader = new FileReader();
            reader.onload = async () => {
                try {
                    const arrayBuffer = reader.result as ArrayBuffer;
                    const bytes = new Uint8Array(arrayBuffer);
                    let binary = '';
                    const len = bytes.byteLength;
                    for (let i = 0; i < len; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64 = btoa(binary);

                    const data = await apiFetch<DocumentConversionResponse>('/projects/convert-document', {
                        method: 'POST',
                        body: {
                            filename: targetFile.name,
                            content_base64: base64,
                        },
                    });

                    setConversion(data);
                    toast.success(`Documento '${targetFile.name}' convertido con AnyDoc`);
                } catch (err: unknown) {
                    const message = err instanceof Error ? err.message : 'Error durante la conversión documental';
                    toast.error(message);
                } finally {
                    setIsConverting(false);
                }
            };
            reader.readAsArrayBuffer(targetFile);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Error procesando archivo';
            toast.error(message);
            setIsConverting(false);
        }
    };

    const handlePublish = async (targetType: 'project_wiki' | 'platform_wiki') => {
        if (!file || !conversion) return;
        setIsPublishing(true);
        try {
            const reader = new FileReader();
            reader.onload = async () => {
                try {
                    const arrayBuffer = reader.result as ArrayBuffer;
                    const bytes = new Uint8Array(arrayBuffer);
                    let binary = '';
                    const len = bytes.byteLength;
                    for (let i = 0; i < len; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64 = btoa(binary);

                    const res = await apiFetch<ConvertAndPublishWikiResponse>(
                        `/projects/${projectId}/documents/convert-and-publish`,
                        {
                            method: 'POST',
                            body: {
                                filename: file.name,
                                content_base64: base64,
                                target_type: targetType,
                                title: file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '),
                            },
                        }
                    );

                    toast.success(res.message);
                    if (onPublished) {
                        onPublished(res);
                    }
                } catch (err: unknown) {
                    const message = err instanceof Error ? err.message : 'Error al publicar documento';
                    toast.error(message);
                } finally {
                    setIsPublishing(false);
                }
            };
            reader.readAsArrayBuffer(file);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Error al publicar';
            toast.error(message);
            setIsPublishing(false);
        }
    };

    const handleCopy = () => {
        if (!conversion?.markdown) return;
        void navigator.clipboard.writeText(conversion.markdown);
        setCopied(true);
        toast.success('Markdown copiado al portapapeles');
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownload = () => {
        if (!conversion?.markdown || !file) return;
        const blob = new Blob([conversion.markdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${file.name.replace(/\.[^/.]+$/, '')}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('Archivo Markdown descargado');
    };

    return (
        <RightPanel
            isOpen={isOpen}
            onClose={onClose}
            title={
                <div className="flex items-center gap-2">
                    <FileSpreadsheet className="text-[hsl(var(--primary))]" size={18} />
                    <span className="font-bold text-sm uppercase tracking-tight">
                        Conversor Universal AnyDoc & Markdown
                    </span>
                </div>
            }
            subtitle={
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    Pipeline de Documentación PMI • {projectTitle}
                </span>
            }
            width="w-full sm:max-w-2xl md:max-w-3xl"
        >
            <div className="p-4 sm:p-6 space-y-6">
                {/* Tarjeta de Ingesta de Conocimiento y Activos OPA PMI §4.4 */}
                <div
                    data-testid="anydoc-pmi-opa-card"
                    className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.5)] space-y-2.5"
                >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                            <Sparkles size={13} className="text-[hsl(var(--primary))]" />
                            Activos de Procesos de la Organización (OPA PMI §4.4)
                        </span>
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded-full border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                            Repositorio de Conocimiento
                        </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1.5">
                            <span className="text-2xs font-bold text-[hsl(var(--foreground))] block">
                                Actas y Gobernanza
                            </span>
                            <span className="text-2xs text-[hsl(var(--muted-foreground))] block">
                                Project Charter, minutas CCB y aprobaciones
                            </span>
                        </div>
                        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1.5">
                            <span className="text-2xs font-bold text-[hsl(var(--foreground))] block">
                                Líneas Base y Matrices
                            </span>
                            <span className="text-2xs text-[hsl(var(--muted-foreground))] block">
                                Diccionario EDT/WBS, presupuesto BAC y riesgos
                            </span>
                        </div>
                        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1.5">
                            <span className="text-2xs font-bold text-[hsl(var(--foreground))] block">
                                Lecciones Aprendidas y Cierre
                            </span>
                            <span className="text-2xs text-[hsl(var(--muted-foreground))] block">
                                Retrospectivas, transferencia y cierre §4.7
                            </span>
                        </div>
                    </div>
                </div>

                {/* Drag and Drop Zone */}
                <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-[hsl(var(--border))] hover:border-[hsl(var(--primary))] rounded-xl p-6 text-center cursor-pointer transition-colors bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))]"
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".docx,.doc,.xlsx,.xls,.pptx,.ppt,.pdf,.csv,.odt,.ods,.odp,.rtf,.epub,.txt,.md"
                        onChange={handleFileSelect}
                    />
                    <div className="flex flex-col items-center justify-center gap-2">
                        <div className="p-3 rounded-full bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                            <UploadCloud size={28} />
                        </div>
                        <h4 className="font-semibold text-sm text-[hsl(var(--foreground))]">
                            Arrastra y suelta tu archivo o haz clic para seleccionarlo
                        </h4>
                        <p className="text-xs text-[hsl(var(--muted-foreground))] max-w-md">
                            Soporta Word (.docx), Excel (.xlsx), PowerPoint (.pptx), PDF, CSV, OpenDocument, RTF y Markdown.
                        </p>
                        <div className="flex items-center gap-1.5 mt-2">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]">
                                <Sparkles size={11} className="text-[hsl(var(--primary))]" /> Motor AnyDoc v0.2.4 (Rust Core)
                            </span>
                        </div>
                    </div>
                </div>

                {/* Loading State */}
                {isConverting && (
                    <div className="p-8 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-col items-center justify-center gap-3">
                        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={28} />
                        <p className="text-sm font-medium text-[hsl(var(--foreground))]">
                            Procesando documento con AnyDoc...
                        </p>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                            Extrayendo estructura tabular, jerarquía de títulos y contenido GFM
                        </span>
                    </div>
                )}

                {/* Conversion Results */}
                {conversion && !isConverting && (() => {
                    const combinedSource = `${conversion.filename || ''} ${conversion.markdown || ''}`;
                    const opaType = /acta|charter|comite|patrocinador|alcance|objetivo/i.test(combinedSource)
                        ? 'Acta / Gobernanza PMI'
                        : /cronograma|presupuesto|riesgo|edt|wbs|evm|indicador|\|.*\|/i.test(combinedSource)
                        ? 'Matriz / Línea Base Técnica'
                        : 'Base de Conocimiento / Lecciones Aprendidas';
                    const hasRichGfm = (/^#{1,3}\s+/m.test(conversion.markdown || '') || /\|.*\|/.test(conversion.markdown || '')) && conversion.word_count >= 5;

                    return (
                    <div className="space-y-4">
                        {/* Header Stats */}
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-wrap items-center justify-between gap-3">
                            <div className="flex items-center gap-2.5">
                                <div className="p-2 rounded-lg bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                                    <FileText size={18} />
                                </div>
                                <div>
                                    <h5 className="font-semibold text-sm text-[hsl(var(--foreground))] truncate max-w-xs">
                                        {conversion.filename}
                                    </h5>
                                    <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                                        <span className="uppercase font-bold text-[hsl(var(--primary))]">
                                            {conversion.format}
                                        </span>
                                        <span>•</span>
                                        <span className="flex items-center gap-1">
                                            <Clock size={12} /> {conversion.processing_time_ms} ms
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3 text-xs">
                                <div className="text-right">
                                    <span className="font-bold text-[hsl(var(--foreground))] block">
                                        {conversion.word_count.toLocaleString()}
                                    </span>
                                    <span className="text-[hsl(var(--muted-foreground))]">Palabras</span>
                                </div>
                                <div className="h-6 w-px bg-[hsl(var(--border))]" />
                                <div className="text-right">
                                    <span className="font-bold text-[hsl(var(--foreground))] block">
                                        {conversion.char_count.toLocaleString()}
                                    </span>
                                    <span className="text-[hsl(var(--muted-foreground))]">Caracteres</span>
                                </div>
                            </div>
                        </div>

                        {/* Diagnóstico de Clasificación OPA PMI */}
                        <div
                            data-testid="anydoc-pmi-opa-diagnostics"
                            className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.6)] flex flex-wrap items-center justify-between gap-2"
                        >
                            <div className="flex items-center gap-2">
                                <span className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Clasificación OPA:
                                </span>
                                <span
                                    data-testid="anydoc-pmi-opa-type"
                                    className="px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]"
                                >
                                    {opaType}
                                </span>
                            </div>
                            <span
                                data-testid="anydoc-pmi-structure-quality"
                                className={
                                    hasRichGfm
                                        ? 'px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]'
                                        : 'px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]'
                                }
                            >
                                {hasRichGfm ? 'Estructura Óptima para Wiki PMI' : 'Texto Plano Básico'}
                            </span>
                        </div>

                        {/* Actions Toolbar */}
                        <div className="flex items-center justify-between gap-2 border-b border-[hsl(var(--border))] pb-2">
                            <div className="flex items-center gap-1">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('preview')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                                        activeTab === 'preview'
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                                    }`}
                                >
                                    <BookOpen size={13} /> Vista Previa
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('source')}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
                                        activeTab === 'source'
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                                    }`}
                                >
                                    <FileCode size={13} /> Markdown Puro
                                </button>
                            </div>

                            <div className="flex items-center gap-1.5">
                                <button
                                    type="button"
                                    onClick={handleCopy}
                                    title="Copiar Markdown"
                                    className="p-1.5 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] transition-colors text-xs flex items-center gap-1"
                                >
                                    {copied ? <Check size={14} className="text-[hsl(var(--success))]" /> : <Copy size={14} />}
                                    <span className="hidden sm:inline">Copiar</span>
                                </button>
                                <button
                                    type="button"
                                    onClick={handleDownload}
                                    title="Descargar .md"
                                    className="p-1.5 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] transition-colors text-xs flex items-center gap-1"
                                >
                                    <Download size={14} />
                                    <span className="hidden sm:inline">Descargar</span>
                                </button>
                            </div>
                        </div>

                        {/* Content Area */}
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] min-h-[300px] max-h-[500px] overflow-y-auto">
                            {activeTab === 'preview' ? (
                                <div className="prose prose-invert prose-sm max-w-none text-[hsl(var(--foreground))] space-y-2">
                                    {conversion.markdown ? (
                                        <pre className="font-mono text-xs whitespace-pre-wrap leading-relaxed text-[hsl(var(--foreground))]">
                                            {conversion.markdown}
                                        </pre>
                                    ) : (
                                        <p className="text-xs text-[hsl(var(--muted-foreground))] italic">
                                            El documento no contiene texto extraíble.
                                        </p>
                                    )}
                                </div>
                            ) : (
                                <textarea
                                    readOnly
                                    value={conversion.markdown}
                                    rows={16}
                                    className="w-full bg-transparent font-mono text-xs text-[hsl(var(--foreground))] resize-none focus:outline-none"
                                />
                            )}
                        </div>

                        {/* Publishing Options */}
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3">
                            <h6 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
                                <Layers size={13} className="text-[hsl(var(--primary))]" /> Destino de Publicación
                            </h6>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                <button
                                    type="button"
                                    disabled={isPublishing}
                                    onClick={() => handlePublish('project_wiki')}
                                    className="p-3 rounded-lg border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-left transition-colors flex items-start gap-2.5 disabled:opacity-50"
                                >
                                    <BookOpen size={16} className="text-[hsl(var(--primary))] shrink-0 mt-0.5" />
                                    <div>
                                        <span className="text-xs font-semibold text-[hsl(var(--foreground))] block">
                                            Wiki del Proyecto
                                        </span>
                                        <span className="text-[11px] text-[hsl(var(--muted-foreground))] block">
                                            Documentación directa vinculada a este proyecto
                                        </span>
                                    </div>
                                </button>

                                <button
                                    type="button"
                                    disabled={isPublishing}
                                    onClick={() => handlePublish('platform_wiki')}
                                    className="p-3 rounded-lg border border-[hsl(var(--border))] hover:border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-left transition-colors flex items-start gap-2.5 disabled:opacity-50"
                                >
                                    <Globe size={16} className="text-[hsl(var(--primary))] shrink-0 mt-0.5" />
                                    <div>
                                        <span className="text-xs font-semibold text-[hsl(var(--foreground))] block">
                                            Wiki Ministerial
                                        </span>
                                        <span className="text-[11px] text-[hsl(var(--muted-foreground))] block">
                                            Página pública transversal para toda la sede
                                        </span>
                                    </div>
                                </button>
                            </div>

                            {isPublishing && (
                                <div className="flex items-center justify-center gap-2 text-xs text-[hsl(var(--primary))] py-1">
                                    <RefreshCw className="animate-spin" size={13} />
                                    <span>Publicando y versionando contenido en la plataforma...</span>
                                </div>
                            )}
                        </div>
                    </div>
                    );
                })()}
            </div>
        </RightPanel>
    );
}


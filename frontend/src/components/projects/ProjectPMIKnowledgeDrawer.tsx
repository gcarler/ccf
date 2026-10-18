"use client";

import React, { useState, useEffect, useMemo } from 'react';
import RightPanel from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import type { PMIKnowledgeVolume, PMIDoctrineIndexResponse } from '@/types/projects';
import {
    BookOpen,
    Search,
    RefreshCw,
    Copy,
    Check,
    Tag,
} from 'lucide-react';
import { toast } from 'sonner';

interface ProjectPMIKnowledgeDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    initialVolume?: number;
}

export function ProjectPMIKnowledgeDrawer({
    isOpen,
    onClose,
    initialVolume = 0,
}: ProjectPMIKnowledgeDrawerProps) {
    const [volumes, setVolumes] = useState<PMIKnowledgeVolume[]>([]);
    const [selectedVolIndex, setSelectedVolIndex] = useState<number>(initialVolume);
    const [searchTerm, setSearchTerm] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        if (!isOpen) return;

        let isMounted = true;
        const fetchDoctrine = async () => {
            setIsLoading(true);
            try {
                const res = await apiFetch<PMIDoctrineIndexResponse>('/projects/pmi-doctrine?include_content=true');
                if (isMounted) {
                    setVolumes(res.volumes || []);
                }
            } catch (err: unknown) {
                const message = err instanceof Error ? err.message : 'Error cargando compendio PMI';
                toast.error(message);
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        };

        void fetchDoctrine();
        return () => {
            isMounted = false;
        };
    }, [isOpen]);

    const filteredVolumes = useMemo(() => {
        if (!searchTerm.trim()) return volumes;
        const q = searchTerm.trim().toLocaleLowerCase();
        return volumes.filter(
            (v) =>
                v.title.toLocaleLowerCase().includes(q) ||
                v.summary.toLocaleLowerCase().includes(q) ||
                v.tags.some((t) => t.toLocaleLowerCase().includes(q)) ||
                (v.content ?? '').toLocaleLowerCase().includes(q)
        );
    }, [volumes, searchTerm]);

    useEffect(() => {
        if (
            filteredVolumes.length > 0 &&
            !filteredVolumes.some((volume) => volume.vol === selectedVolIndex)
        ) {
            setSelectedVolIndex(filteredVolumes[0].vol);
        }
    }, [filteredVolumes, selectedVolIndex]);

    const activeVolume = useMemo(() => {
        if (!filteredVolumes.length) return null;
        return filteredVolumes.find((v) => v.vol === selectedVolIndex) || filteredVolumes[0];
    }, [filteredVolumes, selectedVolIndex]);

    const activeSections = useMemo(() => {
        if (!activeVolume) return [];
        return parseMarkdownSections(activeVolume.content ?? '', activeVolume.vol);
    }, [activeVolume]);

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            const res = await apiFetch<PMIDoctrineIndexResponse>('/projects/pmi-doctrine/sync', {
                method: 'POST',
            });
            setVolumes(res.volumes || []);
            toast.success(
                `Doctrina PMI sincronizada: ${res.wiki_seeded_count} páginas en Wiki y ${res.kb_indexed_count} en Base de Conocimiento.`
            );
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Error al sincronizar doctrina PMI';
            toast.error(message);
        } finally {
            setIsSyncing(false);
        }
    };

    const handleCopy = () => {
        if (!activeVolume?.content) return;
        void navigator.clipboard.writeText(activeVolume.content);
        setCopied(true);
        toast.success(`Volumen ${activeVolume.vol} copiado al portapapeles`);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <RightPanel
            isOpen={isOpen}
            onClose={onClose}
            title={
                <div className="flex items-center gap-2">
                    <BookOpen className="text-[hsl(var(--primary))]" size={18} />
                    <span className="font-bold text-sm uppercase tracking-tight">
                        Biblioteca Metodológica Oficial PMI / PMBOK
                    </span>
                </div>
            }
            subtitle={
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    Compendio Canónico de 7 Volúmenes • Estándar de Gestión CCF
                </span>
            }
            width="w-full sm:max-w-2xl md:max-w-3xl lg:max-w-4xl"
        >
            <div className="p-4 sm:p-6 space-y-6">
                {/* Search Bar & Sync Action */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <div className="relative flex-1">
                        <Search
                            size={14}
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
                        />
                        <input
                            type="text"
                            placeholder="Buscar en la doctrina PMI (EVM, EDT, Cuadrantes, Riesgos...)"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-9 pr-3 py-1.5 rounded-lg text-xs bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                        />
                    </div>

                    <button
                        type="button"
                        disabled={isSyncing}
                        onClick={handleSync}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity flex items-center justify-center gap-1.5 disabled:opacity-50 shrink-0"
                    >
                        <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
                        <span>Sincronizar a Wiki de Sede</span>
                    </button>
                </div>

                {/* Volume Selector Carousel / Chips */}
                <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
                    {filteredVolumes.map((v) => {
                        const isSelected = activeVolume?.vol === v.vol;
                        return (
                            <button
                                key={v.vol}
                                type="button"
                                onClick={() => setSelectedVolIndex(v.vol)}
                                className={`px-3 py-2 rounded-xl text-xs font-medium shrink-0 transition-all border text-left flex flex-col gap-0.5 ${
                                    isSelected
                                        ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))] shadow-sm'
                                        : 'bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]'
                                }`}
                            >
                                <span className={`text-[10px] uppercase font-bold tracking-wider ${isSelected ? 'text-[hsl(var(--primary-foreground))/0.8]' : 'text-[hsl(var(--primary))]'}`}>
                                    Volumen {v.vol}
                                </span>
                                <span className="font-semibold truncate max-w-[140px] text-xs">
                                    {v.title.split('(')[0].replace('Compendio Maestro de ', '').replace('Estructura de Desglose del Trabajo', 'EDT / WBS')}
                                </span>
                            </button>
                        );
                    })}
                </div>

                {/* Content Area */}
                {isLoading ? (
                    <div className="p-12 text-center border border-[hsl(var(--border))] rounded-xl bg-[hsl(var(--surface-1))]">
                        <RefreshCw className="animate-spin text-[hsl(var(--primary))] mx-auto mb-2" size={24} />
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">
                            Cargando compendio canónico de doctrina PMI...
                        </span>
                    </div>
                ) : activeVolume ? (
                    <div className="space-y-4">
                        {/* Volume Header Card */}
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
                                            Volumen {activeVolume.vol} (Compendio de {volumes.length} volúmenes)
                                        </span>
                                        <span className="text-[11px] text-[hsl(var(--muted-foreground))]">
                                            {activeVolume.word_count.toLocaleString()} palabras • {activeVolume.char_count.toLocaleString()} caracteres
                                        </span>
                                    </div>
                                    <h3 className="font-bold text-base text-[hsl(var(--foreground))]">
                                        {activeVolume.title}
                                    </h3>
                                </div>

                                <button
                                    type="button"
                                    onClick={handleCopy}
                                    className="p-1.5 rounded-lg bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--foreground))] transition-colors text-xs flex items-center gap-1.5 shrink-0"
                                >
                                    {copied ? <Check size={14} className="text-[hsl(var(--success))]" /> : <Copy size={14} />}
                                    <span>Copiar Volumen</span>
                                </button>
                            </div>

                            {/* Summary callout */}
                            <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border-l-4 border-[hsl(var(--primary))] text-xs text-[hsl(var(--muted-foreground))] leading-relaxed">
                                <span className="font-semibold text-[hsl(var(--foreground))] block mb-1">
                                    Resumen Metodológico:
                                </span>
                                {activeVolume.summary}
                            </div>

                            {/* Tag Chips */}
                            <div className="flex flex-wrap items-center gap-1.5">
                                {activeVolume.tags.map((tag) => (
                                    <span
                                        key={tag}
                                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]"
                                    >
                                        <Tag size={10} /> {tag}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {activeSections.some((section) => section.title) && (
                            <nav aria-label="Índice rápido de secciones" className="space-y-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                                <h4 className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">Índice rápido de secciones</h4>
                                <div className="flex flex-wrap gap-2">
                                    {activeSections.filter((section) => section.title).map((section) => (
                                        <a
                                            key={section.id}
                                            href={`#${section.id}`}
                                            className="rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-1 text-xs text-[hsl(var(--text-primary))] transition-colors hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))]"
                                        >
                                            {section.title}
                                        </a>
                                    ))}
                                </div>
                            </nav>
                        )}

                        {/* Markdown Content Viewer */}
                        <div className="p-6 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] min-h-[400px] max-h-[600px] overflow-y-auto leading-relaxed">
                            {activeSections.map((section) => (
                                <section key={section.id}>
                                    {section.title && (
                                        <h4 id={section.id} className="mb-2 scroll-mt-4 text-sm font-bold text-[hsl(var(--foreground))]">
                                            {section.title}
                                        </h4>
                                    )}
                                    {section.content && (
                                        <pre className="font-sans text-xs whitespace-pre-wrap text-[hsl(var(--foreground))] font-normal leading-relaxed selection:bg-[hsl(var(--primary)/0.2)]">
                                            {section.content}
                                        </pre>
                                    )}
                                </section>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="p-8 text-center border border-[hsl(var(--border))] rounded-xl bg-[hsl(var(--surface-1))]">
                        <BookOpen size={32} className="text-[hsl(var(--muted-foreground))] mx-auto mb-2 opacity-50" />
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">
                            No se encontraron volúmenes que coincidan con la búsqueda.
                        </p>
                    </div>
                )}
            </div>
        </RightPanel>
    );
}

interface PMIKnowledgeSection {
    id: string;
    title: string | null;
    content: string;
}

function parseMarkdownSections(content: string, volume: number): PMIKnowledgeSection[] {
    const sections: PMIKnowledgeSection[] = [];
    const lines = content.split('\n');
    let currentTitle: string | null = null;
    let currentLines: string[] = [];
    let sectionIndex = 0;

    const pushSection = () => {
        if (currentTitle === null && currentLines.length === 0) return;
        sections.push({
            id: `pmi-volume-${volume}-section-${sectionIndex}`,
            title: currentTitle,
            content: currentLines.join('\n').trim(),
        });
        sectionIndex += 1;
    };

    for (const line of lines) {
        const heading = line.match(/^##(?!#)\s+(.+?)\s*#*\s*$/);
        if (heading) {
            pushSection();
            currentTitle = heading[1].trim();
            currentLines = [];
        } else {
            currentLines.push(line);
        }
    }
    pushSection();
    return sections;
}

"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
    Network, Search, ZoomIn, ZoomOut, Maximize2,
    RefreshCw, Filter, ArrowLeft, BookOpen, FileText,
    ExternalLink, ArrowDownLeft, ArrowUpRight,
    Play, Pause, X
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { DSSkeleton } from '@/design';

// Dynamically import ForceGraph2D with SSR disabled since canvas requires DOM
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
    ssr: false,
    loading: () => (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 bg-[hsl(var(--surface-1))] dark:bg-[#0e1014]">
            <DSSkeleton className="size-16 rounded-full" />
            <span className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                Inicializando Motor Gráfico 2D...
            </span>
        </div>
    )
});

interface GraphNode {
    id: string;
    title: string;
    category?: string | null;
    links_count: number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    [key: string]: unknown;
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    [key: string]: unknown;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphLink[];
}

const CATEGORY_COLORS: Record<string, string> = {
    Pastoral: '#8b5cf6', // Violet
    Liderazgo: '#3b82f6', // Blue
    Doctrina: '#10b981', // Emerald
    Discipulado: '#f59e0b', // Amber
    Operaciones: '#06b6d4', // Cyan
    Administración: '#0284c7', // Sky
    Comunidad: '#ec4899', // Pink
    Jóvenes: '#f97316', // Orange
    General: '#6366f1', // Indigo
    Pendiente: '#94a3b8', // Slate
};

function getCategoryColor(category?: string | null): string {
    if (!category) return CATEGORY_COLORS.General;
    const directMatch = CATEGORY_COLORS[category];
    if (directMatch) return directMatch;
    
    // Fuzzy match
    const catLower = category.toLowerCase();
    for (const [key, color] of Object.entries(CATEGORY_COLORS)) {
        if (catLower.includes(key.toLowerCase())) return color;
    }
    return CATEGORY_COLORS.General;
}

export default function WikiKnowledgeGraphPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const searchParams = useSearchParams();
    const focusParam = searchParams?.get('focus');

    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
    const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
    const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    const fgRef = useRef<any>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

    // Handle resize
    useEffect(() => {
        const updateSize = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.clientWidth,
                    height: containerRef.current.clientHeight
                });
            }
        };
        updateSize();
        window.addEventListener('resize', updateSize);
        return () => window.removeEventListener('resize', updateSize);
    }, []);

    // Load graph data from backend
    const loadGraph = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const data = await apiFetch<GraphData>('/wiki/graph-data', { token });
            if (data && Array.isArray(data.nodes)) {
                setGraphData(data);

                // If focus query param exists, auto select node
                if (focusParam) {
                    const match = data.nodes.find(n => n.id === focusParam || n.id === `wiki_${focusParam}`);
                    if (match) {
                        setSelectedNode(match);
                    }
                }
            }
        } catch (err) {
            console.error('Error loading graph data:', err);
            addToast('Error al cargar la red de conocimiento', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, focusParam, addToast]);

    useEffect(() => {
        loadGraph();
    }, [loadGraph]);

    // Distinct categories for filter pills
    const categories = useMemo(() => {
        const set = new Set<string>();
        graphData.nodes.forEach(n => {
            if (n.category) set.add(n.category);
            else set.add('General');
        });
        return Array.from(set);
    }, [graphData.nodes]);

    // Highlighted nodes set based on search and category
    const highlightNodes = useMemo(() => {
        const set = new Set<string>();
        const query = searchQuery.trim().toLowerCase();

        graphData.nodes.forEach(node => {
            const matchesQuery = !query || node.title.toLowerCase().includes(query) || node.id.toLowerCase().includes(query);
            const matchesCat = !selectedCategory || (node.category || 'General') === selectedCategory;

            if (matchesQuery && matchesCat) {
                set.add(node.id);
            }
        });
        return set;
    }, [graphData.nodes, searchQuery, selectedCategory]);

    // Focus on node when selectedNode changes
    useEffect(() => {
        if (selectedNode && fgRef.current && typeof selectedNode.x === 'number' && typeof selectedNode.y === 'number') {
            fgRef.current.centerAt(selectedNode.x, selectedNode.y, 800);
            fgRef.current.zoom(2.2, 800);
        }
    }, [selectedNode]);

    // Zoom controls
    const handleZoomIn = () => {
        if (fgRef.current) {
            const currentZoom = fgRef.current.zoom();
            fgRef.current.zoom(currentZoom * 1.3, 300);
        }
    };

    const handleZoomOut = () => {
        if (fgRef.current) {
            const currentZoom = fgRef.current.zoom();
            fgRef.current.zoom(currentZoom / 1.3, 300);
        }
    };

    const handleZoomToFit = () => {
        if (fgRef.current) {
            fgRef.current.zoomToFit(400, 60);
        }
    };

    const handleTogglePause = () => {
        if (fgRef.current) {
            if (isPaused) {
                fgRef.current.d3ReheatSimulation();
            } else {
                fgRef.current.pauseAnimation();
            }
            setIsPaused(!isPaused);
        }
    };

    // Connected links for selected node
    const nodeDetails = useMemo(() => {
        if (!selectedNode) return null;
        const currentId = selectedNode.id;

        const outgoing: string[] = [];
        const incoming: string[] = [];

        graphData.links.forEach(link => {
            const srcId = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source;
            const tgtId = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target;

            if (srcId === currentId) outgoing.push(tgtId);
            if (tgtId === currentId) incoming.push(srcId);
        });

        const outgoingDocs = graphData.nodes.filter(n => outgoing.includes(n.id));
        const incomingDocs = graphData.nodes.filter(n => incoming.includes(n.id));

        return {
            outgoingDocs,
            incomingDocs,
            totalLinks: outgoing.length + incoming.length
        };
    }, [selectedNode, graphData]);

    // Custom Canvas Node Painter
    const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const isHighlighted = highlightNodes.has(node.id);
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode?.id === node.id;

        const baseRadius = Math.max(5, Math.min(18, 5 + (node.links_count || 1) * 1.8));
        const radius = isSelected || isHovered ? baseRadius * 1.3 : baseRadius;
        const color = getCategoryColor(node.category);

        // Alpha opacity if searching and not in highlight set
        const alpha = highlightNodes.size === graphData.nodes.length || isHighlighted ? 1 : 0.15;
        ctx.globalAlpha = alpha;

        // Draw Outer Glow for selected/hovered/highlighted
        if (isSelected || isHovered) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI, false);
            ctx.fillStyle = color + '44'; // semi-transparent
            ctx.fill();
        }

        // Draw Node Body
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();

        // Border ring
        ctx.lineWidth = isSelected ? 3 : 1.5;
        ctx.strokeStyle = isSelected ? '#ffffff' : '#ffffff88';
        ctx.stroke();

        // Label rendering (render label if zoom level is high or node is highlighted)
        if (globalScale > 0.8 || isSelected || isHovered || (isHighlighted && searchQuery.trim().length > 0)) {
            const label = node.title || node.id;
            const fontSize = Math.max(10, Math.min(14, 12 / Math.sqrt(globalScale)));
            ctx.font = `600 ${fontSize}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            // Background pill for label legibility
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = 'rgba(15, 17, 23, 0.85)';
            ctx.fillRect(node.x - textWidth / 2 - 4, node.y + radius + 3, textWidth + 8, fontSize + 4);

            ctx.fillStyle = isSelected ? '#ffffff' : '#e2e8f0';
            ctx.fillText(label, node.x, node.y + radius + 5);
        }

        ctx.globalAlpha = 1;
    }, [highlightNodes, selectedNode, hoveredNode, graphData.nodes.length, searchQuery]);

    const sidebarSections = [
        {
            title: 'Wiki',
            items: [
                { id: 'wiki-home', label: 'Inicio', href: '/plataforma/wiki', icon: BookOpen },
                { id: 'wiki-graph', label: 'Red de Conocimiento', href: '/plataforma/wiki/graph', icon: Network },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Wiki" sidebarSections={sidebarSections}>
            <div className="flex-1 flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0c0d10] overflow-hidden">
                {/* Header Toolbar */}
                <header className="h-12 border-b border-[hsl(var(--border))]/70 dark:border-white/5 flex items-center justify-between px-4 shrink-0 bg-[hsl(var(--bg-primary))]/90 dark:bg-[#141517]/90 backdrop-blur-md z-10">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.push('/plataforma/wiki')}
                            className="p-1.5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                            title="Volver a Documentos"
                        >
                            <ArrowLeft size={18} />
                        </button>
                        <div className="flex items-center gap-2">
                            <div className="size-7 rounded-lg bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] flex items-center justify-center">
                                <Network size={16} />
                            </div>
                            <div>
                                <h1 className="text-xs font-black uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-white">
                                    Red de Conocimiento 2D
                                </h1>
                                <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                                    {graphData.nodes.length} documentos · {graphData.links.length} conexiones bidireccionales
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Search & Category Filter */}
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder="Filtrar nodos en tiempo real..."
                                className="pl-8 pr-3 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-transparent focus:border-[hsl(var(--primary)/0.5)] rounded-lg text-xs w-56 outline-none text-[hsl(var(--text-primary))] dark:text-white transition-all"
                            />
                            {searchQuery && (
                                <button
                                    onClick={() => setSearchQuery('')}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-white"
                                >
                                    <X size={12} />
                                </button>
                            )}
                        </div>

                        <div className="flex items-center gap-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1 rounded-lg border border-[hsl(var(--border))]/50 dark:border-white/5">
                            <button
                                onClick={handleZoomIn}
                                className="p-1.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[hsl(var(--text-secondary))]"
                                title="Acercar"
                            >
                                <ZoomIn size={14} />
                            </button>
                            <button
                                onClick={handleZoomOut}
                                className="p-1.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[hsl(var(--text-secondary))]"
                                title="Alejar"
                            >
                                <ZoomOut size={14} />
                            </button>
                            <button
                                onClick={handleZoomToFit}
                                className="p-1.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[hsl(var(--text-secondary))]"
                                title="Ajustar a pantalla"
                            >
                                <Maximize2 size={14} />
                            </button>
                            <button
                                onClick={handleTogglePause}
                                className={`p-1.5 rounded hover:bg-black/10 dark:hover:bg-white/10 ${isPaused ? 'text-amber-500' : 'text-[hsl(var(--text-secondary))]'}`}
                                title={isPaused ? 'Reanudar física' : 'Pausar física'}
                            >
                                {isPaused ? <Play size={14} /> : <Pause size={14} />}
                            </button>
                            <button
                                onClick={loadGraph}
                                className="p-1.5 rounded hover:bg-black/10 dark:hover:bg-white/10 text-[hsl(var(--text-secondary))]"
                                title="Recargar grafo"
                            >
                                <RefreshCw size={14} />
                            </button>
                        </div>
                    </div>
                </header>

                {/* Category Pills Bar */}
                <div className="px-4 py-2 border-b border-[hsl(var(--border))]/40 dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-[#111216]/50 flex items-center gap-1.5 overflow-x-auto custom-scrollbar shrink-0">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-[hsl(var(--text-secondary))] mr-1 flex items-center gap-1">
                        <Filter size={11} /> Categorías:
                    </span>
                    <button
                        onClick={() => setSelectedCategory(null)}
                        className={`px-2.5 py-1 rounded-full text-[10px] font-bold transition-all ${
                            selectedCategory === null
                                ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                                : 'bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))]'
                        }`}
                    >
                        Todas ({graphData.nodes.length})
                    </button>
                    {categories.map(cat => {
                        const count = graphData.nodes.filter(n => (n.category || 'General') === cat).length;
                        const catColor = getCategoryColor(cat);
                        const isSelected = selectedCategory === cat;

                        return (
                            <button
                                key={cat}
                                onClick={() => setSelectedCategory(isSelected ? null : cat)}
                                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold transition-all border ${
                                    isSelected
                                        ? 'border-white text-white shadow-md'
                                        : 'border-transparent bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-white'
                                }`}
                                style={{ backgroundColor: isSelected ? catColor : undefined }}
                            >
                                <span className="size-2 rounded-full" style={{ backgroundColor: catColor }} />
                                <span>{cat}</span>
                                <span className="opacity-70">({count})</span>
                            </button>
                        );
                    })}
                </div>

                {/* Graph Canvas & Side Drawer Area */}
                <div className="flex-1 relative flex overflow-hidden" ref={containerRef}>
                    {loading ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                            <DSSkeleton className="size-16 rounded-full animate-spin" />
                            <p className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                                Mapeando conexiones neuronales...
                            </p>
                        </div>
                    ) : (
                        <ForceGraph2D
                            ref={fgRef}
                            width={dimensions.width}
                            height={dimensions.height}
                            graphData={graphData}
                            nodeId="id"
                            nodeLabel=""
                            nodeCanvasObject={paintNode}
                            nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
                                const baseRadius = Math.max(6, Math.min(20, 6 + (node.links_count || 1) * 2));
                                ctx.beginPath();
                                ctx.arc(node.x, node.y, baseRadius + 4, 0, 2 * Math.PI, false);
                                ctx.fillStyle = color;
                                ctx.fill();
                            }}
                            linkColor={(link: any) => {
                                const srcId = typeof link.source === 'object' ? link.source.id : link.source;
                                const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
                                if (selectedNode && (srcId === selectedNode.id || tgtId === selectedNode.id)) {
                                    return 'hsl(var(--primary))';
                                }
                                if (hoveredNode && (srcId === hoveredNode.id || tgtId === hoveredNode.id)) {
                                    return '#38bdf8';
                                }
                                return '#ffffff1a';
                            }}
                            linkWidth={(link: any) => {
                                const srcId = typeof link.source === 'object' ? link.source.id : link.source;
                                const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
                                if (selectedNode && (srcId === selectedNode.id || tgtId === selectedNode.id)) {
                                    return 2.5;
                                }
                                return 1;
                            }}
                            linkDirectionalArrowLength={3.5}
                            linkDirectionalArrowRelPos={1}
                            linkDirectionalParticles={1}
                            linkDirectionalParticleSpeed={0.005}
                            onNodeClick={(node: any) => setSelectedNode(node as GraphNode)}
                            onNodeHover={(node: any) => setHoveredNode(node as GraphNode || null)}
                            onBackgroundClick={() => setSelectedNode(null)}
                            cooldownTicks={120}
                            d3AlphaDecay={0.02}
                            d3VelocityDecay={0.3}
                        />
                    )}

                    {/* Node Details Slide-Over Drawer */}
                    {selectedNode && (
                        <div className="absolute top-4 right-4 bottom-4 w-88 max-w-[calc(100vw-32px)] bg-[hsl(var(--bg-primary))]/95 dark:bg-[#16171b]/95 backdrop-blur-xl border border-[hsl(var(--border))] dark:border-white/10 rounded-2xl shadow-2xl flex flex-col z-20 overflow-hidden animate-in slide-in-from-right duration-200">
                            {/* Drawer Header */}
                            <div className="p-4 border-b border-[hsl(var(--border))]/70 dark:border-white/5 flex items-start justify-between gap-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5">
                                <div className="space-y-1 min-w-0">
                                    <div className="flex items-center gap-1.5">
                                        <span
                                            className="px-2 py-0.5 rounded text-[10px] font-black uppercase text-white shadow-sm"
                                            style={{ backgroundColor: getCategoryColor(selectedNode.category) }}
                                        >
                                            {selectedNode.category || 'General'}
                                        </span>
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                                            {nodeDetails?.totalLinks || 0} vínculos
                                        </span>
                                    </div>
                                    <h2 className="text-sm font-black text-[hsl(var(--text-primary))] dark:text-white leading-snug break-words">
                                        {selectedNode.title}
                                    </h2>
                                    <p className="text-[11px] font-mono text-[hsl(var(--text-secondary))] truncate">
                                        {selectedNode.id}
                                    </p>
                                </div>

                                <button
                                    onClick={() => setSelectedNode(null)}
                                    className="p-1 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 text-[hsl(var(--text-secondary))] shrink-0"
                                >
                                    <X size={16} />
                                </button>
                            </div>

                            {/* Drawer Body */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
                                {/* Action CTA */}
                                <Link
                                    href={`/plataforma/wiki/docs/${selectedNode.id}`}
                                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-[hsl(var(--primary))] text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-lg shadow-[hsl(var(--primary)/0.25)] hover:opacity-90 transition-all"
                                >
                                    <FileText size={14} />
                                    <span>Abrir y Editar Documento</span>
                                    <ExternalLink size={12} />
                                </Link>

                                {/* Outgoing Links */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-[11px] font-extrabold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        <span className="flex items-center gap-1">
                                            <ArrowUpRight size={13} className="text-cyan-500" />
                                            <span>Enlaces Salientes</span>
                                        </span>
                                        <span className="px-1.5 py-0.2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[10px]">
                                            {nodeDetails?.outgoingDocs.length || 0}
                                        </span>
                                    </div>

                                    {nodeDetails?.outgoingDocs && nodeDetails.outgoingDocs.length > 0 ? (
                                        <div className="space-y-1.5">
                                            {nodeDetails.outgoingDocs.map(doc => (
                                                <button
                                                    key={doc.id}
                                                    onClick={() => setSelectedNode(doc)}
                                                    className="w-full flex items-center justify-between p-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 text-left transition-all text-xs font-bold text-[hsl(var(--text-primary))] dark:text-zinc-200"
                                                >
                                                    <span className="truncate">{doc.title}</span>
                                                    <span
                                                        className="size-2 rounded-full shrink-0"
                                                        style={{ backgroundColor: getCategoryColor(doc.category) }}
                                                    />
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] italic py-1">
                                            No contiene enlaces a otros documentos.
                                        </p>
                                    )}
                                </div>

                                {/* Incoming Backlinks */}
                                <div className="space-y-2 pt-2 border-t border-[hsl(var(--border))]/50 dark:border-white/5">
                                    <div className="flex items-center justify-between text-[11px] font-extrabold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        <span className="flex items-center gap-1">
                                            <ArrowDownLeft size={13} className="text-blue-500" />
                                            <span>Retroenlaces Entrantes</span>
                                        </span>
                                        <span className="px-1.5 py-0.2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[10px]">
                                            {nodeDetails?.incomingDocs.length || 0}
                                        </span>
                                    </div>

                                    {nodeDetails?.incomingDocs && nodeDetails.incomingDocs.length > 0 ? (
                                        <div className="space-y-1.5">
                                            {nodeDetails.incomingDocs.map(doc => (
                                                <button
                                                    key={doc.id}
                                                    onClick={() => setSelectedNode(doc)}
                                                    className="w-full flex items-center justify-between p-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 text-left transition-all text-xs font-bold text-[hsl(var(--text-primary))] dark:text-zinc-200"
                                                >
                                                    <span className="truncate">{doc.title}</span>
                                                    <span
                                                        className="size-2 rounded-full shrink-0"
                                                        style={{ backgroundColor: getCategoryColor(doc.category) }}
                                                    />
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] italic py-1">
                                            Ningún otro documento enlaza aquí todavía.
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </WorkspaceLayout>
    );
}

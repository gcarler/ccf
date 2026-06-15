"use client";

import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import * as fabric from 'fabric';
import {
    MousePointer2, Pencil, Square, Circle, Type,
    Trash2, ZoomIn, ZoomOut,
    Cloud, Loader2, Sparkles,
    X, Layers, PencilRuler
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface Props {
    project_id: string;
    isOpen: boolean;
    onClose: () => void;
}

export default function ProjectWhiteboard({ project_id, isOpen, onClose }: Props) {
    const { token } = useAuth();
    const drawingAreaRef = useRef<HTMLDivElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fabricRef = useRef<fabric.Canvas | null>(null);
    const loadedFor = useRef<string | null>(null);
    const projectIdRef = useRef(project_id);
    const tokenRef = useRef(token);
    const restoringRef = useRef(false);
    const [isMounted, setIsMounted] = useState(false);
    const [tool, setTool] = useState<'select' | 'pencil' | 'rect' | 'circle' | 'text'>('select');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
    const [isAiDrawing, setIsAiDrawing] = useState(false);
    const [zoom, setZoom] = useState(100);

    useEffect(() => {
        projectIdRef.current = project_id;
        tokenRef.current = token;
    }, [project_id, token]);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    // ── Init canvas once (on mount) ─────────────────────────────────────────
    useEffect(() => {
        if (!isMounted) return;
        const el = canvasRef.current;
        if (!el) return;

        const getCanvasSize = () => {
            const rect = drawingAreaRef.current?.getBoundingClientRect();
            return {
                width: Math.max(320, Math.floor(rect?.width || window.innerWidth)),
                height: Math.max(320, Math.floor(rect?.height || window.innerHeight - 44)),
            };
        };
        const initialSize = getCanvasSize();
        const canvas = new fabric.Canvas(el, {
            width: initialSize.width,
            height: initialSize.height,
            backgroundColor: '#fafafa',
            preserveObjectStacking: true,
            selection: true,
            selectionColor: 'rgba(37, 99, 235, 0.1)',
            selectionBorderColor: '#2563eb',
            selectionLineWidth: 1,
        });
        fabricRef.current = canvas;

        const save = () => {
            if (restoringRef.current) return;
            const activeProjectId = projectIdRef.current;
            if (!activeProjectId) return;
            setSaveStatus('saving');
            apiFetch(`/projects/${activeProjectId}/whiteboard`, {
                method: 'POST',
                token: tokenRef.current,
                body: { title: 'Pizarra Estrategica', elements_json: JSON.stringify(canvas.toJSON()) },
            }).then(() => {
                setSaveStatus('saved');
                setTimeout(() => setSaveStatus('idle'), 2000);
            }).catch(() => setSaveStatus('idle'));
        };

        canvas.on('object:modified', save);
        canvas.on('object:added', save);
        canvas.on('object:removed', save);

        const onResize = () => {
            canvas.setDimensions(getCanvasSize());
            canvas.renderAll();
        };
        window.addEventListener('resize', onResize);

        return () => {
            window.removeEventListener('resize', onResize);
            canvas.dispose();
            fabricRef.current = null;
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isMounted]);

    // ── Load whiteboard data when opening ──────────────────────────────────
    useEffect(() => {
        if (!isOpen || !fabricRef.current) return;
        if (loadedFor.current === project_id) return; // already loaded

        const canvas = fabricRef.current;
        apiFetch<{ elements_json: string }>(`/projects/${project_id}/whiteboard`, { token })
            .then(async (data) => {
                if (data?.elements_json && data.elements_json !== '[]') {
                    try {
                        restoringRef.current = true;
                        await canvas.loadFromJSON(JSON.parse(data.elements_json));
                        canvas.renderAll();
                    } catch {
                        toast.error('No se pudo cargar la pizarra guardada.');
                    } finally {
                        restoringRef.current = false;
                    }
                }
                loadedFor.current = project_id;
            })
            .catch(() => {
                loadedFor.current = project_id;
            });
    }, [isOpen, project_id, token]);

    useEffect(() => {
        if (!isOpen || !fabricRef.current) return;
        const canvas = fabricRef.current;
        const frame = window.requestAnimationFrame(() => {
            const rect = drawingAreaRef.current?.getBoundingClientRect();
            canvas.setDimensions({
                width: Math.max(320, Math.floor(rect?.width || window.innerWidth)),
                height: Math.max(320, Math.floor(rect?.height || window.innerHeight - 44)),
            });
            canvas.renderAll();
        });
        return () => window.cancelAnimationFrame(frame);
    }, [isOpen]);

    // ── Esc to close ───────────────────────────────────────────────────────
    useEffect(() => {
        if (!isOpen) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if ((e.key === 'Delete' || e.key === 'Backspace') && document.activeElement?.tagName !== 'INPUT') {
                const fc = fabricRef.current;
                if (!fc) return;
                fc.remove(...fc.getActiveObjects());
                fc.discardActiveObject();
                fc.renderAll();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isOpen, onClose]);

    // ── Tools ──────────────────────────────────────────────────────────────
    const setActiveTool = (t: typeof tool) => {
        const fc = fabricRef.current;
        if (!fc) return;
        setTool(t);
        if (t === 'pencil') {
            fc.isDrawingMode = true;
            const brush = new fabric.PencilBrush(fc);
            brush.width = 3;
            brush.color = '#2563eb';
            fc.freeDrawingBrush = brush;
        } else if (t === 'rect') {
            addRect();
        } else if (t === 'circle') {
            addCircle();
        } else if (t === 'text') {
            addText();
        } else {
            fc.isDrawingMode = false;
        }
    };

    const addRect = () => {
        const fc = fabricRef.current;
        if (!fc) return;
        const rect = new fabric.Rect({
            left: 120, top: 120, width: 160, height: 100,
            fill: 'rgba(37,99,235,0.08)', stroke: '#2563eb', strokeWidth: 2, rx: 10, ry: 10,
        });
        fc.add(rect);
        fc.setActiveObject(rect);
        setActiveTool('select');
    };

    const addCircle = () => {
        const fc = fabricRef.current;
        if (!fc) return;
        const circle = new fabric.Circle({
            left: 140, top: 140, radius: 50,
            fill: 'rgba(16,185,129,0.1)', stroke: '#10b981', strokeWidth: 2,
        });
        fc.add(circle);
        fc.setActiveObject(circle);
        setActiveTool('select');
    };

    const addText = () => {
        const fc = fabricRef.current;
        if (!fc) return;
        const t = new fabric.IText('Escribe aquí', {
            left: 160, top: 160, fontSize: 20, fill: '#0f172a', fontFamily: 'Manrope',
        });
        fc.add(t);
        fc.setActiveObject(t);
        t.enterEditing();
        t.selectAll();
    };

    const deleteSelected = () => {
        const fc = fabricRef.current;
        if (!fc) return;
        fc.remove(...fc.getActiveObjects());
        fc.discardActiveObject();
        fc.renderAll();
    };

    const handleZoom = (delta: number) => {
        const fc = fabricRef.current;
        if (!fc) return;
        const next = Math.min(200, Math.max(25, zoom + delta));
        fc.setZoom(next / 100);
        setZoom(next);
        fc.renderAll();
    };

    const handleAiDiagram = async () => {
        const prompt = window.prompt('¿Qué proceso ministerial deseas diagramar?');
        if (!prompt) return;
        setIsAiDrawing(true);
        try {
            await apiFetch('/system/ai/generate', {
                method: 'POST', token,
                body: { prompt: `Genera un diagrama de pizarra para: ${prompt}`, context: 'Estética ministerial' },
            });
            toast.success('IA: Esqueleto del diagrama generado.');
        } catch {
            toast.error('Error en la IA de diagramación.');
        } finally {
            setIsAiDrawing(false);
        }
    };

    // ── Render ─────────────────────────────────────────────────────────────
    // Always in DOM — use CSS to hide/show. Avoids all Fabric.js ref/dispose issues.
    if (!isMounted) return null;

    const whiteboard = (
        <div
            className={clsx(
                'fixed inset-0 z-[9999] flex flex-col bg-[#f4f5f7] dark:bg-[#0f1115] transition-opacity duration-200',
                isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
            )}
            role="dialog"
            aria-label="Pizarra del proyecto"
            aria-hidden={!isOpen}
        >
            {/* Top Bar */}
            <header className="h-11 px-4 shrink-0 border-b border-slate-200 dark:border-white/5 flex items-center justify-between bg-white dark:bg-[#1e1f21] shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="size-7 rounded-md bg-orange-500 flex items-center justify-center text-white">
                        <PencilRuler size={14} />
                    </div>
                    <span className="text-[11px] font-bold text-slate-700 dark:text-white uppercase tracking-wide">
                        Pizarra del Proyecto
                    </span>
                    <div className="flex items-center gap-1.5 ml-2">
                        {saveStatus === 'saving' ? (
                            <>
                                <Loader2 size={10} className="animate-spin text-[hsl(var(--primary))]" />
                                <span className="text-[9px] font-semibold uppercase text-[hsl(var(--primary))]">Guardando...</span>
                            </>
                        ) : (
                            <>
                                <Cloud size={10} className="text-emerald-500" />
                                <span className="text-[9px] font-semibold uppercase text-emerald-500">Guardado</span>
                            </>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleAiDiagram}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity shadow-md"
                    >
                        {isAiDrawing ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
                        Diagramar con IA
                    </button>
                    <div className="w-px h-5 bg-slate-200 dark:bg-white/10" />
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md bg-slate-100 dark:bg-white/5 text-slate-500 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all"
                        title="Cerrar (Esc)"
                    >
                        <X size={16} />
                    </button>
                </div>
            </header>

            {/* Drawing Area */}
            <div ref={drawingAreaRef} className="flex-1 relative overflow-hidden bg-[#f8fafc] dark:bg-[#0f1115]">
                {/* Vertical toolbar */}
                <div className="absolute left-3 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-1 p-1.5 bg-white/95 dark:bg-[#1e1f21]/95 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-xl shadow-2xl">
                    <ToolBtn active={tool === 'select'} onClick={() => setActiveTool('select')} icon={MousePointer2} label="Seleccionar (V)" />
                    <ToolBtn active={tool === 'pencil'} onClick={() => setActiveTool('pencil')} icon={Pencil} label="Dibujar libre (P)" />
                    <div className="h-px w-7 bg-slate-100 dark:bg-white/10 mx-auto my-0.5" />
                    <ToolBtn active={tool === 'rect'} onClick={() => setActiveTool('rect')}  icon={Square} label="Rectángulo (R)" />
                    <ToolBtn active={tool === 'circle'} onClick={() => setActiveTool('circle')} icon={Circle} label="Círculo (C)" />
                    <ToolBtn active={tool === 'text'} onClick={() => setActiveTool('text')}   icon={Type}   label="Texto (T)" />
                    <div className="h-px w-7 bg-slate-100 dark:bg-white/10 mx-auto my-0.5" />
                    <ToolBtn active={false} onClick={deleteSelected} icon={Trash2} label="Eliminar (Del)" color="text-rose-500" />
                </div>

                {/* Canvas — fills the full drawing area */}
                <canvas ref={canvasRef} />

                {/* Zoom controls */}
                <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-white/90 dark:bg-[#1e1f21]/90 backdrop-blur-xl px-3 py-2 rounded-full border border-slate-200 dark:border-white/10 shadow-lg">
                    <button onClick={() => handleZoom(-25)} className="text-slate-400 hover:text-[hsl(var(--primary))] transition-colors"><ZoomOut size={16} /></button>
                    <span className="text-[11px] font-bold w-10 text-center text-slate-600 dark:text-slate-200 tabular-nums">{zoom}%</span>
                    <button onClick={() => handleZoom(+25)} className="text-slate-400 hover:text-[hsl(var(--primary))] transition-colors"><ZoomIn size={16} /></button>
                    <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                    <button className="text-slate-400 hover:text-[hsl(var(--primary))] transition-colors" title="Capas">
                        <Layers size={16} />
                    </button>
                </div>
            </div>
        </div>
    );

    return createPortal(whiteboard, document.body);
}

function ToolBtn({ active, onClick, icon: Icon, label, color = 'text-slate-500' }: {
    active: boolean; onClick: () => void; icon: React.ElementType; label: string; color?: string;
}) {
    return (
        <button
            onClick={onClick}
            title={label}
            className={clsx(
                'p-2 rounded-lg transition-all relative group',
                active ? 'bg-[hsl(var(--primary))] text-white shadow-md' : `hover:bg-slate-50 dark:hover:bg-white/5 ${color}`
            )}
        >
            <Icon size={18} />
            <span className="absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 px-2 py-1 bg-slate-800 text-white text-[9px] font-semibold rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[100]">
                {label}
            </span>
        </button>
    );
}

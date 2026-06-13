"use client";

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as fabric from 'fabric';
import {
    MousePointer2, Pencil, Square, Circle, Type,
    Trash2, ZoomIn, ZoomOut,
    Cloud, Loader2, Sparkles,
    X, Layers, PencilRuler
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const fabricCanvas = useRef<fabric.Canvas | null>(null);
    const [tool, setTool] = useState<'select' | 'pencil' | 'rect' | 'circle' | 'text'>('select');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
    const [isAiDrawing, setIsAiDrawing] = useState(false);
    const [zoom, setZoom] = useState(100);

    const resizeCanvas = useCallback(() => {
        const fc = fabricCanvas.current;
        const container = containerRef.current;
        if (!fc || !container) return;
        fc.setDimensions({ width: container.clientWidth, height: container.clientHeight });
        fc.renderAll();
    }, []);

    // Inicialización del Canvas
    useEffect(() => {
        if (!isOpen || !canvasRef.current || !containerRef.current) return;

        const container = containerRef.current;
        const canvas = new fabric.Canvas(canvasRef.current, {
            width: container.clientWidth,
            height: container.clientHeight,
            backgroundColor: '#ffffff',
            preserveObjectStacking: true,
        });

        fabricCanvas.current = canvas;

        const load = async () => {
            try {
                const data = await apiFetch<{elements_json: string}>(`/projects/${project_id}/whiteboard`, { token });
                if (data?.elements_json && data.elements_json !== '[]') {
                    await canvas.loadFromJSON(JSON.parse(data.elements_json));
                    canvas.renderAll();
                }
            } catch { /* empty canvas if no data */ }
        };
        load();

        const triggerSave = () => {
            setSaveStatus('saving');
            const json = JSON.stringify(canvas.toJSON());
            apiFetch(`/projects/${project_id}/whiteboard`, {
                method: 'POST',
                token,
                body: { title: 'Pizarra Estrategica', elements_json: json }
            }).then(() => {
                setSaveStatus('saved');
                setTimeout(() => setSaveStatus('idle'), 2000);
            });
        };

        canvas.on('object:modified', triggerSave);
        canvas.on('object:added', triggerSave);
        canvas.on('object:removed', triggerSave);

        const ro = new ResizeObserver(() => {
            canvas.setDimensions({ width: container.clientWidth, height: container.clientHeight });
            canvas.renderAll();
        });
        ro.observe(container);

        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if ((e.key === 'Delete' || e.key === 'Backspace') && document.activeElement?.tagName !== 'INPUT') {
                canvas.remove(...canvas.getActiveObjects());
                canvas.discardActiveObject();
                canvas.renderAll();
            }
        };
        window.addEventListener('keydown', handleKey);

        return () => {
            ro.disconnect();
            window.removeEventListener('keydown', handleKey);
            canvas.dispose();
            fabricCanvas.current = null;
        };
    }, [isOpen, project_id, token, onClose]);

    const setActiveTool = (t: typeof tool) => {
        const fc = fabricCanvas.current;
        if (!fc) return;
        setTool(t);
        if (t === 'pencil') {
            fc.isDrawingMode = true;
            const brush = new fabric.PencilBrush(fc);
            brush.width = 3;
            brush.color = '#2563eb';
            fc.freeDrawingBrush = brush;
        } else {
            fc.isDrawingMode = false;
        }
    };

    const addRect = () => {
        fabricCanvas.current?.add(new fabric.Rect({ left: 100, top: 100, fill: 'rgba(37, 99, 235, 0.1)', stroke: '#2563eb', strokeWidth: 2, width: 160, height: 100, rx: 12, ry: 12 }));
        setActiveTool('select');
    };

    const addCircle = () => {
        fabricCanvas.current?.add(new fabric.Circle({ left: 120, top: 120, radius: 50, fill: 'rgba(16, 185, 129, 0.12)', stroke: '#10b981', strokeWidth: 2 }));
        setActiveTool('select');
    };

    const addText = () => {
        const text = new fabric.IText('Texto', { left: 150, top: 150, fontSize: 22, fill: '#0f172a', fontFamily: 'sans-serif' });
        fabricCanvas.current?.add(text);
        fabricCanvas.current?.setActiveObject(text);
        text.enterEditing();
        text.selectAll();
        setActiveTool('select');
    };

    const deleteSelected = () => {
        const fc = fabricCanvas.current;
        if (!fc) return;
        fc.remove(...fc.getActiveObjects());
        fc.discardActiveObject();
        fc.renderAll();
    };

    const handleZoom = (delta: number) => {
        const fc = fabricCanvas.current;
        if (!fc) return;
        const next = Math.min(200, Math.max(25, zoom + delta));
        fc.setZoom(next / 100);
        setZoom(next);
    };

    const handleAiDiagram = async () => {
        const prompt = window.prompt("¿Qué proceso ministerial deseas diagramar?");
        if (!prompt) return;
        setIsAiDrawing(true);
        try {
            await apiFetch<{response: string}>('/system/ai/generate', {
                method: 'POST', token,
                body: { prompt: `Genera un diagrama de pizarra para: ${prompt}`, context: "Estética ministerial" }
            });
            toast.success("IA: Esqueleto del diagrama generado.");
        } catch {
            toast.error("Error en la IA de diagramación.");
        } finally {
            setIsAiDrawing(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18 }}
                    className="fixed inset-0 z-[9999] flex flex-col bg-[#f4f5f7] dark:bg-[#0f1115]"
                    role="dialog"
                    aria-label="Pizarra del proyecto"
                >
                    {/* ── Top Bar ── */}
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
                                    <><Loader2 size={10} className="animate-spin text-[hsl(var(--primary))]" />
                                    <span className="text-[9px] font-semibold uppercase text-[hsl(var(--primary))]">Guardando...</span></>
                                ) : (
                                    <><Cloud size={10} className="text-emerald-500" />
                                    <span className="text-[9px] font-semibold uppercase text-emerald-500">Guardado</span></>
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

                    {/* ── Drawing Area ── */}
                    <div className="flex-1 relative overflow-hidden">

                        {/* Vertical toolbar */}
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-1 p-1.5 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl">
                            <ToolBtn active={tool === 'select'}  onClick={() => setActiveTool('select')}  icon={MousePointer2} label="Seleccionar" />
                            <ToolBtn active={tool === 'pencil'}  onClick={() => setActiveTool('pencil')}  icon={Pencil}        label="Dibujar libre" />
                            <div className="h-px w-7 bg-slate-100 dark:bg-white/10 mx-auto my-0.5" />
                            <ToolBtn active={false} onClick={addRect}        icon={Square}       label="Rectángulo" />
                            <ToolBtn active={false} onClick={addCircle}      icon={Circle}       label="Círculo" />
                            <ToolBtn active={false} onClick={addText}        icon={Type}         label="Texto" />
                            <div className="h-px w-7 bg-slate-100 dark:bg-white/10 mx-auto my-0.5" />
                            <ToolBtn active={false} onClick={deleteSelected} icon={Trash2}       label="Eliminar" color="text-rose-500" />
                        </div>

                        {/* Canvas container — fills all available space */}
                        <div ref={containerRef} className="w-full h-full">
                            <canvas ref={canvasRef} />
                        </div>

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
                </motion.div>
            )}
        </AnimatePresence>
    );
}

function ToolBtn({ active, onClick, icon: Icon, label, color = "text-slate-500" }: {
    active: boolean; onClick: () => void; icon: React.ElementType; label: string; color?: string;
}) {
    return (
        <button
            onClick={onClick}
            title={label}
            className={clsx(
                "p-2 rounded-lg transition-all relative group",
                active
                    ? "bg-[hsl(var(--primary))] text-white shadow-md"
                    : `hover:bg-slate-50 dark:hover:bg-white/5 ${color}`
            )}
        >
            <Icon size={18} />
            <span className="absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 px-2 py-1 bg-slate-800 text-white text-[9px] font-semibold rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[100]">
                {label}
            </span>
        </button>
    );
}

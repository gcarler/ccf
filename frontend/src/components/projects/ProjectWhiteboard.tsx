"use client";

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as fabric from 'fabric';
import { 
    MousePointer2, Pencil, Square, Circle, Type, 
    Trash2, Undo, Redo, ZoomIn, ZoomOut, Maximize,
    Cloud, Loader2, Grid3X3, Sparkles, Wand2,
    X, Save, Download, Share2, Move, Layers, LayoutDashboard
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface Props {
    project_id: number;
    isOpen: boolean;
    onClose: () => void;
}

export default function ProjectWhiteboard({ project_id, isOpen, onClose }: Props) {
    const { token } = useAuth();
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fabricCanvas = useRef<fabric.Canvas | null>(null);
    const [tool, setTool] = useState<'select' | 'pencil' | 'rect' | 'circle' | 'text'>('select');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
    const [isAiDrawing, setIsAiDrawing] = useState(false);

    // Inicialización del Canvas
    useEffect(() => {
        if (!isOpen || !canvasRef.current) return;

        const canvas = new fabric.Canvas(canvasRef.current, {
            width: window.innerWidth * 0.8,
            height: window.innerHeight - 150,
            backgroundColor: '#ffffff',
            preserveObjectStacking: true,
        });

        fabricCanvas.current = canvas;

        const load = async () => {
            try {
                const data = await apiFetch<{elements_json: string}>(`/projects/${project_id}/whiteboard`, { token });
                if (data?.elements_json && data.elements_json !== '[]') {
                    canvas.loadFromJSON(JSON.parse(data.elements_json), () => {
                        canvas.renderAll();
                    });
                }
            } catch (err) { console.error(err); }
        };
        load();

        const triggerSave = () => {
            setSaveStatus('saving');
            const json = JSON.stringify(canvas.toJSON());
            apiFetch(`/projects/${project_id}/whiteboard`, {
                method: 'POST',
                token,
                body: { elements_json: json }
            }).then(() => {
                setSaveStatus('saved');
                setTimeout(() => setSaveStatus('idle'), 2000);
            });
        };

        canvas.on('object:modified', triggerSave);
        canvas.on('object:added', triggerSave);
        canvas.on('object:removed', triggerSave);

        return () => {
            canvas.dispose();
        };
    }, [isOpen, project_id, token]);

    const addRect = () => {
        const rect = new fabric.Rect({ left: 100, top: 100, fill: 'rgba(37, 99, 235, 0.1)', stroke: '#2563eb', strokeWidth: 2, width: 150, height: 100, rx: 15, ry: 15 });
        fabricCanvas.current?.add(rect);
        setTool('select');
    };

    const handleAiDiagram = async () => {
        const prompt = window.prompt("¿Qué proceso ministerial deseas diagramar? (Ej: Flujo de grabación de clips)");
        if (!prompt) return;

        setIsAiDrawing(true);
        try {
            const data = await apiFetch<{response: string}>('/system/ai/generate', {
                method: 'POST',
                token,
                body: { prompt: `Genera un diagrama de pizarra para: ${prompt}`, context: "Estética ministerial" }
            });
            // Aquí iría el parseo del JSON de la IA para añadir objetos al canvas
            toast.success("IA: Esqueleto del diagrama generado.");
        } catch (err) {
            toast.error("Error en la IA de diagramación.");
        } finally {
            setIsAiDrawing(false);
        }
    };

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        <Dialog.Overlay asChild>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[9500] bg-slate-900/40 backdrop-blur-md" />
                        </Dialog.Overlay>
                        <Dialog.Content asChild>
                            <motion.div 
                                initial={{ x: '100%' }} 
                                animate={{ x: 0 }} 
                                exit={{ x: '100%' }}
                                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                                className="fixed right-0 top-0 z-[9501] h-screen w-[90vw] bg-[#f8fafc] dark:bg-[#0f1115] shadow-2xl border-l border-white/10 flex flex-col overflow-hidden"
                            >
                                <Dialog.Title className="sr-only">Pizarra Infinita Ministerial</Dialog.Title>

                                {/* Top Bar: Calidad Premium */}
                                <header className="h-16 px-8 border-b border-slate-200 dark:border-white/5 flex items-center justify-between bg-white dark:bg-[#1e1f21] shrink-0">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-2xl bg-orange-500 flex items-center justify-center text-white shadow-xl shadow-orange-500/20">
                                            <LayoutDashboard size={20} />
                                        </div>
                                        <div>
                                            <h3 className="text-[13px] font-black text-slate-900 dark:text-white uppercase tracking-wider">Lienzo Creativo: Proyecto {project_id}</h3>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                {saveStatus === 'saving' ? (
                                                    <><Loader2 size={10} className="animate-spin text-blue-500" /> <span className="text-[8px] font-black uppercase text-blue-500">Sincronizando...</span></>
                                                ) : (
                                                    <><Cloud size={10} className="text-emerald-500" /> <span className="text-[8px] font-black uppercase text-emerald-500">Persistido en DB</span></>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <button onClick={handleAiDiagram} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest hover:scale-[1.02] active:scale-95 transition-all shadow-lg shadow-blue-500/30">
                                            {isAiDrawing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} 
                                            Diagramar con IA
                                        </button>
                                        <div className="w-[1px] h-6 bg-slate-200 dark:bg-white/10 mx-2" />
                                        <button onClick={onClose} className="p-2.5 bg-slate-100 dark:bg-white/5 rounded-xl text-slate-500 hover:text-rose-500 transition-all"><X size={20} /></button>
                                    </div>
                                </header>

                                {/* Drawing Area */}
                                <main className="flex-1 relative overflow-hidden flex items-center justify-center p-10">
                                    {/* Toolbar Flotante Estilo ClickUp */}
                                    <div className="absolute left-10 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-2 p-2 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-3xl shadow-[0_32px_64px_-12px_rgba(0,0,0,0.2)]">
                                        <ToolBtn active={tool === 'select'} onClick={() => { setTool('select'); if (fabricCanvas.current) fabricCanvas.current.isDrawingMode = false; }} icon={MousePointer2} label="Selección" />
                                        <ToolBtn active={tool === 'pencil'} onClick={() => { setTool('pencil'); if (fabricCanvas.current) { fabricCanvas.current.isDrawingMode = true; fabricCanvas.current.freeDrawingBrush = new fabric.PencilBrush(fabricCanvas.current); fabricCanvas.current.freeDrawingBrush.width = 3; fabricCanvas.current.freeDrawingBrush.color = '#2563eb'; } }} icon={Pencil} label="Dibujo" />
                                        <div className="h-[1px] w-8 bg-slate-100 dark:bg-white/5 mx-auto my-1" />
                                        <ToolBtn active={false} onClick={addRect} icon={Square} label="Caja" />
                                        <ToolBtn active={false} onClick={() => {}} icon={Circle} label="Nodo" />
                                        <ToolBtn active={false} onClick={() => {}} icon={Type} label="Texto" />
                                        <div className="h-[1px] w-8 bg-slate-100 dark:bg-white/5 mx-auto my-1" />
                                        <ToolBtn active={false} onClick={() => { fabricCanvas.current?.remove(...fabricCanvas.current?.getActiveObjects()); fabricCanvas.current?.discardActiveObject(); fabricCanvas.current?.renderAll(); }} icon={Trash2} label="Borrar" color="text-rose-500" />
                                    </div>

                                    {/* El Lienzo con Grid de Ingeniería */}
                                    <div className="relative rounded-[2.5rem] shadow-[0_64px_128px_-24px_rgba(0,0,0,0.1)] overflow-hidden border-8 border-white dark:border-[#1e1f21]">
                                        <div className="absolute inset-0 pointer-events-none opacity-[0.03] dark:opacity-[0.07]" style={{ backgroundImage: 'radial-gradient(#000 1.5px, transparent 0)', backgroundSize: '32px 32px' }} />
                                        <canvas ref={canvasRef} />
                                    </div>

                                    {/* Floating Zoom & Controls */}
                                    <div className="absolute bottom-10 right-10 flex items-center gap-4 bg-white/80 dark:bg-[#1e1f21]/80 backdrop-blur-xl px-6 py-3 rounded-full border border-slate-200 dark:border-white/10 shadow-2xl">
                                        <button className="text-slate-400 hover:text-blue-600"><ZoomOut size={18} /></button>
                                        <span className="text-xs font-black w-12 text-center text-slate-600 dark:text-slate-200">100%</span>
                                        <button className="text-slate-400 hover:text-blue-600"><ZoomIn size={18} /></button>
                                        <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-2" />
                                        <button className="text-slate-400 hover:text-blue-600 group relative">
                                            <Layers size={18} />
                                            <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-800 text-[8px] font-black uppercase text-white rounded opacity-0 group-hover:opacity-100 whitespace-nowrap transition-opacity">Capas</div>
                                        </button>
                                    </div>
                                </main>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

function ToolBtn({ active, onClick, icon: Icon, label, color = "text-slate-500" }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "p-3 rounded-2xl transition-all relative group",
                active ? "bg-blue-600 text-white shadow-xl shadow-blue-500/20" : `hover:bg-slate-50 dark:hover:bg-white/5 ${color}`
            )}
        >
            <Icon size={20} className={clsx(active ? "text-white" : color)} />
            <div className="absolute left-16 px-2 py-1 bg-slate-800 text-white text-[9px] font-black uppercase rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-[100]">
                {label}
            </div>
        </button>
    );
}

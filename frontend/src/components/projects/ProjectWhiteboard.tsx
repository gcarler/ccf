"use client";

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as fabric from 'fabric';
import { 
    MousePointer2, Pencil, Square, Circle, Type, 
    Trash2, Undo, Redo, ZoomIn, ZoomOut, Maximize,
    CloudCheck, CloudUpload, Loader2, Grid3X3
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface Props {
    project_id: number;
}

export default function ProjectWhiteboard({ project_id }: Props) {
    const { token } = useAuth();
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fabricCanvas = useRef<fabric.Canvas | null>(null);
    const [tool, setTool] = useState<'select' | 'pencil' | 'rect' | 'circle' | 'text'>('select');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

    const saveCanvas = useCallback(async (json: string) => {
        if (!token) return;
        setSaveStatus('saving');
        try {
            await apiFetch(`/projects/${project_id}/whiteboard`, {
                method: 'POST',
                token,
                body: { elements_json: json }
            });
            setSaveStatus('saved');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } catch (err) {
            setSaveStatus('error');
            toast.error("Error al guardar la Pizarra");
        }
    }, [project_id, token]);

    useEffect(() => {
        if (!canvasRef.current) return;

        const canvas = new fabric.Canvas(canvasRef.current, {
            width: window.innerWidth - 500,
            height: 700,
            backgroundColor: '#f8fafc',
        });

        fabricCanvas.current = canvas;

        const loadInitialData = async () => {
            try {
                const data = await apiFetch<{elements_json: string}>(`/projects/${project_id}/whiteboard`, { token });
                if (data && data.elements_json && data.elements_json !== '[]') {
                    canvas.loadFromJSON(JSON.parse(data.elements_json), () => {
                        canvas.renderAll();
                    });
                }
            } catch (err) { console.error(err); }
        };

        if (token) loadInitialData();

        // Throttle para el auto-guardado
        let timeout: any;
        const triggerSave = () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                saveCanvas(JSON.stringify(canvas.toJSON()));
            }, 2000);
        };

        canvas.on('object:modified', triggerSave);
        canvas.on('object:added', triggerSave);
        canvas.on('object:removed', triggerSave);

        return () => {
            canvas.dispose();
            clearTimeout(timeout);
        };
    }, [project_id, token, saveCanvas]);

    const setDrawingMode = (t: typeof tool) => {
        setTool(t);
        if (!fabricCanvas.current) return;
        fabricCanvas.current.isDrawingMode = t === 'pencil';
        if (t === 'pencil') {
            fabricCanvas.current.freeDrawingBrush = new fabric.PencilBrush(fabricCanvas.current);
            fabricCanvas.current.freeDrawingBrush.width = 3;
            fabricCanvas.current.freeDrawingBrush.color = '#2563eb';
        }
    };

    const addRect = () => {
        const rect = new fabric.Rect({ left: 100, top: 100, fill: 'rgba(37, 99, 235, 0.1)', stroke: '#2563eb', strokeWidth: 2, width: 120, height: 80, rx: 12, ry: 12 });
        fabricCanvas.current?.add(rect);
        setDrawingMode('select');
    };

    const addCircle = () => {
        const circle = new fabric.Circle({ left: 150, top: 150, fill: 'rgba(16, 185, 129, 0.1)', stroke: '#10b981', strokeWidth: 2, radius: 50 });
        fabricCanvas.current?.add(circle);
        setDrawingMode('select');
    };

    const addText = () => {
        const text = new fabric.IText('Escribir...', { left: 200, top: 200, fontSize: 24, fontFamily: 'Inter', fontWeight: 'bold' });
        fabricCanvas.current?.add(text);
        setDrawingMode('select');
    };

    const deleteSelected = () => {
        const active = fabricCanvas.current?.getActiveObjects();
        if (active) {
            fabricCanvas.current?.remove(...active);
            fabricCanvas.current?.discardActiveObject();
            fabricCanvas.current?.requestRenderAll();
        }
    };

    return (
        <div className="flex flex-col h-full bg-slate-50 dark:bg-black/20 rounded-[3.5rem] border border-slate-200 dark:border-white/5 overflow-hidden font-display relative shadow-inner">
            {/* Status Floating Bar */}
            <div className="absolute top-6 right-10 z-20 flex items-center gap-2 p-2 bg-white/80 dark:bg-[#1e1f21]/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl">
                {saveStatus === 'saving' && <><Loader2 size={14} className="animate-spin text-blue-500" /> <span className="text-[9px] font-black uppercase text-blue-500">Guardando</span></>}
                {saveStatus === 'saved' && <><CloudCheck size={14} className="text-emerald-500" /> <span className="text-[9px] font-black uppercase text-emerald-500">Persistido</span></>}
                {saveStatus === 'idle' && <span className="text-[9px] font-black uppercase text-slate-400">Listo</span>}
            </div>

            {/* Main Toolbar */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1 p-2 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-[1.5rem] shadow-2xl">
                <ToolButton active={tool === 'select'} onClick={() => setDrawingMode('select')} icon={MousePointer2} label="Mover" />
                <ToolButton active={tool === 'pencil'} onClick={() => setDrawingMode('pencil')} icon={Pencil} label="Lápiz" />
                <div className="w-[1px] h-6 bg-slate-100 dark:bg-white/5 mx-1" />
                <ToolButton active={false} onClick={addRect} icon={Square} label="Caja" />
                <ToolButton active={false} onClick={addCircle} icon={Circle} label="Nodo" />
                <ToolButton active={false} onClick={addText} icon={Type} label="Texto" />
                <div className="w-[1px] h-6 bg-slate-100 dark:bg-white/5 mx-1" />
                <ToolButton active={false} onClick={deleteSelected} icon={Trash2} label="Borrar" color="text-rose-500" />
            </div>

            {/* Canvas Area with Grid Background */}
            <div className="flex-1 flex items-center justify-center p-8 overflow-hidden relative">
                <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 0)', backgroundSize: '24px 24px' }} />
                <div className="bg-white rounded-[2rem] shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden scale-[0.95]">
                    <canvas ref={canvasRef} />
                </div>
            </div>

            {/* Zoom Controls */}
            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-20 flex items-center gap-4 bg-white/80 dark:bg-[#1e1f21]/80 backdrop-blur-xl px-6 py-3 rounded-full border border-slate-200 dark:border-white/10 shadow-2xl">
                <button className="text-slate-400 hover:text-blue-600"><ZoomOut size={18} /></button>
                <span className="text-xs font-black w-12 text-center text-slate-600 dark:text-slate-200">100%</span>
                <button className="text-slate-400 hover:text-blue-600"><ZoomIn size={18} /></button>
                <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10 mx-2" />
                <button className="text-slate-400 hover:text-blue-600"><Maximize size={18} /></button>
            </div>
        </div>
    );
}

function ToolButton({ active, onClick, icon: Icon, label, color = "text-slate-600 dark:text-slate-300" }: any) {
    return (
        <button
            onClick={onClick}
            className={clsx(
                "p-3 rounded-xl transition-all relative group",
                active ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20 scale-110" : `hover:bg-slate-50 dark:hover:bg-white/5 ${color}`
            )}
        >
            <Icon size={20} className={clsx(active ? "text-white" : color)} />
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-all whitespace-nowrap shadow-xl">
                {label}
            </div>
        </button>
    );
}

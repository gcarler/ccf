"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import * as fabric from "fabric";
import {
    Circle,
    Cloud,
    Download,
    Eraser,
    History,
    LayoutDashboard,
    Loader2,
    MousePointer2,
    Pencil,
    Save,
    Share2,
    Sparkles,
    Square,
    Trash2,
    Type,
} from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import clsx from "clsx";
import {
    readWhiteboards,
    upsertWhiteboard,
    whiteboardCanvasKey,
    WhiteboardRecord,
} from "@/lib/whiteboards";

type WhiteboardTool = "select" | "draw";

interface LayerRow {
    index: number;
    type: string;
    label: string;
}

export default function WhiteboardSessionPage() {
    const params = useParams();
    const id = params?.id as string;
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fabricCanvas = useRef<fabric.Canvas | null>(null);
    const restoringRef = useRef(false);
    const saveTimerRef = useRef<number | null>(null);

    const [title, setTitle] = useState("Lienzo colaborativo");
    const [description, setDescription] = useState("");
    const [tool, setTool] = useState<WhiteboardTool>("select");
    const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
    const [layers, setLayers] = useState<LayerRow[]>([]);

    const storageKey = useMemo(() => whiteboardCanvasKey(id || "unknown"), [id]);

    const syncLayers = useCallback(() => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const next = canvas.getObjects().map((object, index) => ({
            index,
            type: object.type || "object",
            label: getObjectLabel(object, index),
        })).reverse();
        setLayers(next);
    }, []);

    const persistCanvas = useCallback((status: "saving" | "saved" = "saving") => {
        const canvas = fabricCanvas.current;
        if (!canvas || restoringRef.current || typeof window === "undefined" || !id) return;

        if (saveTimerRef.current) {
            window.clearTimeout(saveTimerRef.current);
        }

        setSaveStatus(status);
        saveTimerRef.current = window.setTimeout(() => {
            window.localStorage.setItem(storageKey, JSON.stringify(canvas.toJSON()));
            const now = new Date().toISOString();
            const existing = readWhiteboards(window.localStorage).find((board) => board.id === id);
            upsertWhiteboard(window.localStorage, {
                id,
                title: existing?.title || title,
                description: existing?.description || description,
                created_at: existing?.created_at || now,
                updated_at: now,
            });
            setSaveStatus("saved");
            window.setTimeout(() => setSaveStatus("idle"), 1600);
        }, 350);
    }, [description, id, storageKey, title]);

    useEffect(() => {
        if (typeof window === "undefined" || !id) return;
        const board = readWhiteboards(window.localStorage).find((item) => item.id === id);
        if (board) {
            setTitle(board.title);
            setDescription(board.description || "");
        } else {
            const now = new Date().toISOString();
            const fallback: WhiteboardRecord = {
                id,
                title: "Lienzo colaborativo",
                description: "",
                created_at: now,
                updated_at: now,
            };
            upsertWhiteboard(window.localStorage, fallback);
        }
    }, [id]);

    useEffect(() => {
        if (!canvasRef.current || typeof window === "undefined") return;

        const canvas = new fabric.Canvas(canvasRef.current, {
            backgroundColor: "#ffffff",
            preserveObjectStacking: true,
            selection: true,
        });
        fabricCanvas.current = canvas;

        const resizeCanvas = () => {
            canvas.setDimensions({
                width: Math.max(760, window.innerWidth - 430),
                height: Math.max(520, window.innerHeight - 132),
            });
            canvas.renderAll();
        };
        resizeCanvas();
        window.addEventListener("resize", resizeCanvas);

        const saved = window.localStorage.getItem(storageKey);
        if (saved) {
            restoringRef.current = true;
            try {
                canvas.loadFromJSON(JSON.parse(saved), () => {
                    canvas.renderAll();
                    syncLayers();
                    restoringRef.current = false;
                });
            } catch {
                restoringRef.current = false;
            }
        } else {
            addStarterObjects(canvas);
            syncLayers();
            persistCanvas("saved");
        }

        const handleChanged = () => {
            syncLayers();
            persistCanvas();
        };

        canvas.on("object:added", handleChanged);
        canvas.on("object:modified", handleChanged);
        canvas.on("object:removed", handleChanged);

        return () => {
            if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
            window.removeEventListener("resize", resizeCanvas);
            canvas.dispose();
            fabricCanvas.current = null;
        };
    }, [persistCanvas, storageKey, syncLayers]);

    const activateTool = (next: WhiteboardTool) => {
        const canvas = fabricCanvas.current;
        setTool(next);
        if (!canvas) return;
        canvas.isDrawingMode = next === "draw";
        if (next === "draw") {
            canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
            canvas.freeDrawingBrush.width = 3;
            canvas.freeDrawingBrush.color = "#2563eb";
        }
    };

    const addRect = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const rect = new fabric.Rect({
            left: 120,
            top: 120,
            width: 180,
            height: 110,
            rx: 18,
            ry: 18,
            fill: "rgba(37, 99, 235, 0.08)",
            stroke: "#2563eb",
            strokeWidth: 2,
        });
        canvas.add(rect);
        canvas.setActiveObject(rect);
        activateTool("select");
    };

    const addCircle = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const circle = new fabric.Circle({
            left: 140,
            top: 150,
            radius: 54,
            fill: "rgba(16, 185, 129, 0.1)",
            stroke: "#10b981",
            strokeWidth: 2,
        });
        canvas.add(circle);
        canvas.setActiveObject(circle);
        activateTool("select");
    };

    const addText = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const text = new fabric.IText("Nuevo texto", {
            left: 160,
            top: 170,
            fontSize: 24,
            fill: "#0f172a",
            fontFamily: "Manrope",
        });
        canvas.add(text);
        canvas.setActiveObject(text);
        text.enterEditing();
        text.selectAll();
        activateTool("select");
    };

    const removeSelection = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const active = canvas.getActiveObjects();
        if (active.length === 0) return;
        canvas.remove(...active);
        canvas.discardActiveObject();
        canvas.requestRenderAll();
    };

    const clearCanvas = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        canvas.getObjects().forEach((object) => canvas.remove(object));
        canvas.requestRenderAll();
    };

    const focusLayer = (index: number) => {
        const canvas = fabricCanvas.current;
        const object = canvas?.getObjects()[index];
        if (!canvas || !object) return;
        canvas.setActiveObject(object);
        canvas.requestRenderAll();
    };

    const exportCanvas = () => {
        const canvas = fabricCanvas.current;
        if (!canvas || typeof window === "undefined") return;
        const payload = JSON.stringify({ title, description, canvas: canvas.toJSON() }, null, 2);
        const blob = new Blob([payload], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "whiteboard"}.json`;
        link.click();
        URL.revokeObjectURL(url);
    };

    const copyShareLink = async () => {
        if (typeof window === "undefined") return;
        await navigator.clipboard?.writeText(window.location.href);
    };

    const saveNow = () => persistCanvas("saving");

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#0b0d11]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "CCF Tools", icon: LayoutDashboard, href: "/whiteboard" },
                    { label: title, icon: Sparkles },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-[hsl(var(--bg-primary))] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5">
                            {saveStatus === "saving" ? <Loader2 size={12} className="animate-spin text-[hsl(var(--primary))]" /> : <Cloud size={12} className="text-emerald-500" />}
                            {saveStatus === "saving" ? "Guardando" : saveStatus === "saved" ? "Guardado" : "Local"}
                        </div>
                        <button onClick={copyShareLink} className="p-2 text-slate-400 transition-all hover:text-[hsl(var(--primary))]" title="Copiar enlace">
                            <Share2 size={18} />
                        </button>
                        <button onClick={exportCanvas} className="p-2 text-slate-400 transition-all hover:text-[hsl(var(--primary))]" title="Exportar JSON">
                            <Download size={18} />
                        </button>
                        <button onClick={saveNow} className="flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20 transition-all hover:scale-105">
                            <Save size={14} /> Guardar
                        </button>
                    </div>
                }
            />

            <div className="relative flex flex-1 overflow-hidden">
                <div className="absolute left-6 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-2 rounded-lg border border-slate-200 bg-white/90 p-2 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/90">
                    <ToolbarButton icon={MousePointer2} active={tool === "select"} onClick={() => activateTool("select")} label="Seleccionar" />
                    <ToolbarButton icon={Pencil} active={tool === "draw"} onClick={() => activateTool("draw")} label="Dibujo libre" />
                    <ToolbarButton icon={Square} active={false} onClick={addRect} label="Rectangulo" />
                    <ToolbarButton icon={Circle} active={false} onClick={addCircle} label="Circulo" />
                    <ToolbarButton icon={Type} active={false} onClick={addText} label="Texto" />
                    <div className="mx-2 my-1 h-px bg-slate-100 dark:bg-white/5" />
                    <ToolbarButton icon={Eraser} active={false} onClick={removeSelection} label="Borrar seleccion" />
                    <ToolbarButton icon={Trash2} active={false} onClick={clearCanvas} label="Limpiar lienzo" tone="danger" />
                </div>

                <main
                    className={clsx(
                        "flex-1 overflow-auto bg-[hsl(var(--bg-primary))] bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:32px_32px] p-4 pl-24 dark:bg-[#0f1114] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)]",
                        tool === "select" ? "cursor-default" : "cursor-crosshair"
                    )}
                >
                    <div className="inline-block overflow-hidden rounded-lg border-8 border-white bg-[hsl(var(--bg-primary))] shadow-[0_48px_96px_-32px_rgba(15,23,42,0.35)] dark:border-[#1e1f21]">
                        <canvas ref={canvasRef} />
                    </div>
                </main>

                <aside className="w-80 shrink-0 space-y-3 overflow-y-auto border-l border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-[#111418]">
                    <section className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Objetivo</p>
                        <h1 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h1>
                        <p className="text-xs font-medium leading-5 text-slate-500">{description || "Sin objetivo documentado."}</p>
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Capas reales</h3>
                        <div className="space-y-2">
                            {layers.map((layer) => (
                                <button
                                    key={`${layer.type}-${layer.index}`}
                                    onClick={() => focusLayer(layer.index)}
                                    className="flex w-full items-center justify-between rounded-md border border-slate-100 p-3 text-left text-xs font-medium text-slate-500 transition-all hover:border-blue-200 hover:bg-blue-50/40 dark:border-white/5 dark:hover:bg-blue-500/10"
                                >
                                    <span className="flex items-center gap-2">
                                        <History size={12} /> {layer.label}
                                    </span>
                                    <span className="text-[9px] opacity-50">#{layer.index + 1}</span>
                                </button>
                            ))}
                            {layers.length === 0 && (
                                <div className="rounded-md border border-dashed border-slate-200 p-4 text-center text-xs font-semibold text-slate-400 dark:border-white/10">
                                    No hay objetos en el lienzo.
                                </div>
                            )}
                        </div>
                    </section>
                </aside>
            </div>
        </div>
    );
}

function addStarterObjects(canvas: fabric.Canvas) {
    const title = new fabric.IText("Mapa inicial", {
        left: 96,
        top: 80,
        fontSize: 28,
        fill: "#0f172a",
        fontFamily: "Manrope",
        fontWeight: "bold",
    });
    const box = new fabric.Rect({
        left: 90,
        top: 150,
        width: 220,
        height: 120,
        rx: 20,
        ry: 20,
        fill: "rgba(37, 99, 235, 0.08)",
        stroke: "#2563eb",
        strokeWidth: 2,
    });
    const text = new fabric.IText("Doble clic para editar", {
        left: 118,
        top: 195,
        fontSize: 18,
        fill: "#1e293b",
        fontFamily: "Manrope",
    });
    canvas.add(title, box, text);
    canvas.renderAll();
}

function getObjectLabel(object: fabric.FabricObject, index: number) {
    if (object.type === "i-text" || object.type === "textbox") {
        const text = "text" in object ? String(object.text || "").trim() : "";
        return text || `Texto ${index + 1}`;
    }
    if (object.type === "rect") return `Rectangulo ${index + 1}`;
    if (object.type === "circle") return `Circulo ${index + 1}`;
    if (object.type === "path") return `Trazo ${index + 1}`;
    return `Objeto ${index + 1}`;
}

function ToolbarButton({
    icon: Icon,
    active,
    onClick,
    label,
    tone = "default",
}: {
    icon: React.ElementType;
    active: boolean;
    onClick: () => void;
    label: string;
    tone?: "default" | "danger";
}) {
    return (
        <button
            onClick={onClick}
            title={label}
            className={clsx(
                "group relative flex size-10 items-center justify-center rounded-md transition-all",
                active
                    ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20"
                    : tone === "danger"
                        ? "text-rose-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10"
                        : "text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5"
            )}
        >
            <Icon size={20} />
            <span className="pointer-events-none absolute left-full z-50 ml-4 whitespace-nowrap rounded-lg bg-slate-900 px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-white opacity-0 transition-opacity group-hover:opacity-100">
                {label}
            </span>
        </button>
    );
}

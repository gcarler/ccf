"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import * as fabric from "fabric";
import {
    Bold,
    Circle,
    Eraser,
    History,
    Italic,
    Layers,
    MousePointer2,
    Pencil,
    RotateCcw,
    RotateCw,
    Share2,
    Square,
    Trash2,
    Type,
    Grid3x3,
    BringToFront,
    SendToBack,
    Copy,
    EyeOff,
    FileJson,
    Image as ImageIcon,
    FileCode,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import {
    fetchProjectWhiteboard,
    GridStyle,
    GridSize,
    WHITEBOARD_COLORS,
    WHITEBOARD_COLOR_PRESETS,
} from "@/lib/whiteboards";
import { exportToPng, exportToSvg, exportToJson } from "@/lib/whiteboardExport";
import { useWhiteboardHistory } from "@/hooks/useWhiteboardHistory";
import { useWhiteboardSave } from "@/hooks/useWhiteboardSave";

type WhiteboardTool = "select" | "draw";

interface LayerRow {
    index: number;
    type: string;
    label: string;
}

interface WhiteboardEditorProps {
    projectId: string;
    token: string | null;
    initialTitle?: string;
    header?: (state: {
        title: string;
        saveStatus: "idle" | "saving" | "saved" | "error";
        saveNow: () => void;
    }) => React.ReactNode;
    className?: string;
}

const COLOR_PRESETS = WHITEBOARD_COLOR_PRESETS;

const FONT_FAMILIES = [
    { label: "Manrope", value: "Manrope" },
    { label: "Inter", value: "Inter" },
    { label: "Georgia", value: "Georgia" },
    { label: "Courier New", value: "Courier New" },
    { label: "Arial", value: "Arial" },
];

const FONT_SIZE_PRESETS = [12, 14, 16, 18, 24, 32, 48, 64];

const GRID_OPTIONS: { label: string; value: GridStyle; icon: React.ElementType }[] = [
    { label: "Puntos", value: "dots", icon: Grid3x3 },
    { label: "Líneas", value: "lines", icon: Grid3x3 },
    { label: "Renglones", value: "ruled", icon: Grid3x3 },
    { label: "Sin grilla", value: "none", icon: EyeOff },
];

const GRID_SIZES: { label: string; value: GridSize }[] = [
    { label: "16px", value: 16 },
    { label: "24px", value: 24 },
    { label: "32px", value: 32 },
];

function getGridBackground(style: GridStyle, size: GridSize, isDark: boolean): string {
    const color = isDark ? WHITEBOARD_COLORS.gridDark : WHITEBOARD_COLORS.gridLight;
    const dotColor = isDark ? WHITEBOARD_COLORS.gridDarkDot : WHITEBOARD_COLORS.gridLightDot;
    switch (style) {
        case "dots":
            return `radial-gradient(${dotColor} 1px, transparent 1px)`;
        case "lines":
            return `
                linear-gradient(90deg, ${color} 1px, transparent 1px),
                linear-gradient(0deg, ${color} 1px, transparent 1px)
            `;
        case "ruled":
            return `
                linear-gradient(0deg, ${color} 1px, transparent 1px)
            `;
        case "none":
            return "none";
    }
}

export default function WhiteboardEditor({
    projectId,
    token,
    initialTitle = "Lienzo colaborativo",
    header,
    className,
}: WhiteboardEditorProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fabricCanvas = useRef<fabric.Canvas | null>(null);

    // History hook for undo/redo
    const history = useWhiteboardHistory({ maxStates: 50 });
    const [title, setTitle] = useState(initialTitle);
    const [tool, setTool] = useState<WhiteboardTool>("select");
    const [layers, setLayers] = useState<LayerRow[]>([]);
    const [selectedObjectProps, setSelectedObjectProps] = useState<Record<string, unknown> | null>(null);
    const { saveStatus, save, saveNow } = useWhiteboardSave({
        projectId,
        token,
        title,
    });

    // Grid state
    const [gridStyle, setGridStyle] = useState<GridStyle>("dots");
    const [gridSize, setGridSize] = useState<GridSize>(24);
    const [showGridMenu, setShowGridMenu] = useState(false);

    // Fill/Stroke/Text color state
    const [fillColor, setFillColor] = useState<string>(WHITEBOARD_COLORS.primary);
    const [strokeColor, setStrokeColor] = useState<string>(WHITEBOARD_COLORS.primary);
    const [textColor, setTextColor] = useState<string>(WHITEBOARD_COLORS.textPrimary);

    // Text properties
    const [textFontFamily, setTextFontFamily] = useState("Manrope");
    const [textFontSize, setTextFontSize] = useState(24);
    const [textBold, setTextBold] = useState(false);
    const [textItalic, setTextItalic] = useState(false);

    // Stroke width & opacity
    const [strokeWidth, setStrokeWidth] = useState(2);
    const [opacity, setOpacity] = useState(100);

    // Position & size
    const [objLeft, setObjLeft] = useState(0);
    const [objTop, setObjTop] = useState(0);
    const [objWidth, setObjWidth] = useState(0);
    const [objHeight, setObjHeight] = useState(0);

    const [isCanvasReady, setIsCanvasReady] = useState(false);
    const [isDark, setIsDark] = useState(false);

    // Detect dark mode
    useEffect(() => {
        const check = () => {
            setIsDark(document.documentElement.classList.contains("dark"));
        };
        check();
        const observer = new MutationObserver(check);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
        return () => observer.disconnect();
    }, []);

    // Close grid menu on outside click
    useEffect(() => {
        if (!showGridMenu) return;
        const raf = requestAnimationFrame(() => {
            window.addEventListener("click", () => setShowGridMenu(false), { once: true });
        });
        return () => cancelAnimationFrame(raf);
    }, [showGridMenu]);

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

    const updateSelectedProps = useCallback(() => {
        const canvas = fabricCanvas.current;
        const active = canvas?.getActiveObject();
        if (!active) {
            setSelectedObjectProps(null);
            return;
        }
        setSelectedObjectProps({ type: active.type });
        setFillColor((active.fill as string) || WHITEBOARD_COLORS.primary);
        setStrokeColor((active.stroke as string) || WHITEBOARD_COLORS.primary);
        setStrokeWidth((active.strokeWidth as number) || 2);
        setOpacity(Math.round(((active.opacity as number) ?? 1) * 100));
        setObjLeft(Math.round((active.left as number) || 0));
        setObjTop(Math.round((active.top as number) || 0));
        setObjWidth(Math.round((active.width as number) || 0));
        setObjHeight(Math.round((active.height as number) || 0));

        if (active.type === "i-text" || active.type === "textbox") {
            const textObj = active as fabric.IText;
            setTextFontFamily(textObj.fontFamily || "Manrope");
            setTextFontSize(textObj.fontSize || 24);
            setTextBold(textObj.fontWeight === "bold");
            setTextItalic(!!textObj.fontStyle);
        }
    }, []);

    const applyProperty = useCallback((key: string, value: unknown) => {
        const canvas = fabricCanvas.current;
        const active = canvas?.getActiveObject();
        if (!active) return;
        // Cast is needed because Fabric exposes many optional properties
        // on subclasses (IText, Rect, Circle, etc.).
        active.set(key as keyof fabric.FabricObject, value as fabric.FabricObject[keyof fabric.FabricObject]);
        active.setCoords();
        canvas?.renderAll();
        // trigger save via the existing change handler
        canvas?.fire("object:modified", { target: active } as unknown as fabric.ModifiedEvent<fabric.TPointerEvent>);
    }, []);

    // ── Load board metadata ──
    useEffect(() => {
        if (!projectId || !token) return;
        let cancelled = false;
        const load = async () => {
            try {
                const board = await fetchProjectWhiteboard(projectId, token);
                if (cancelled) return;
                if (board) {
                    setTitle(board.title);
                }
            } catch (err) {
                console.error("Error loading whiteboard:", err);
            }
        };
        load();
        return () => {
            cancelled = true;
        };
    }, [projectId, token]);

    // Keep a stable ref to history methods so the canvas-init effect does not
    // depend on the `history` object (which changes identity every time
    // canUndo / canRedo state is toggled, causing the effect to re-run and
    // destroy the canvas).
    const historyRef = useRef(history);
    historyRef.current = history;

    // Same pattern for `save` / `saveNow` — they are already stable in
    // practice, but using a ref removes them from the dep array and
    // guarantees the canvas is only created once per projectId+token pair.
    const saveRef = useRef(save);
    saveRef.current = save;
    const saveNowRef = useRef(saveNow);
    saveNowRef.current = saveNow;

    // ── Init Fabric canvas ──
    useEffect(() => {
        if (!canvasRef.current || typeof window === "undefined" || !projectId || !token) return;

        const canvas = new fabric.Canvas(canvasRef.current, {
            backgroundColor: WHITEBOARD_COLORS.canvasDark,
            preserveObjectStacking: true,
            selection: true,
            selectionColor: "rgba(37, 99, 235, 0.1)",
            selectionBorderColor: WHITEBOARD_COLORS.primary,
            selectionLineWidth: 1,
        });
        fabricCanvas.current = canvas;
        setIsCanvasReady(true);

        const resizeCanvas = () => {
            canvas.setDimensions({
                width: Math.max(760, window.innerWidth - 430),
                height: Math.max(520, window.innerHeight - 132),
            });
            canvas.renderAll();
        };
        resizeCanvas();
        window.addEventListener("resize", resizeCanvas);

        // Load saved data from backend
        const loadSaved = async () => {
            try {
                const board = await fetchProjectWhiteboard(projectId, token);
                if (board?.elements_json && board.elements_json !== "[]") {
                    historyRef.current.restoringRef.current = true;
                    await canvas.loadFromJSON(JSON.parse(board.elements_json));
                    canvas.renderAll();
                    syncLayers();
                } else {
                    addStarterObjects(canvas);
                    syncLayers();
                    saveNowRef.current(canvas);
                }
            } catch {
                addStarterObjects(canvas);
                syncLayers();
                saveNowRef.current(canvas);
            } finally {
                historyRef.current.restoringRef.current = false;
                historyRef.current.clearHistory();
                historyRef.current.pushHistory(canvas);
            }
        };
        loadSaved();

        const handleChanged = () => {
            if (!historyRef.current.restoringRef.current) {
                historyRef.current.pushHistory(canvas);
                syncLayers();
                saveRef.current(canvas);
            }
        };

        canvas.on("object:added", handleChanged);
        canvas.on("object:modified", handleChanged);
        canvas.on("object:removed", handleChanged);
        canvas.on("selection:created", updateSelectedProps);
        canvas.on("selection:updated", updateSelectedProps);
        canvas.on("selection:cleared", () => setSelectedObjectProps(null));

        return () => {
            window.removeEventListener("resize", resizeCanvas);
            canvas.dispose();
            fabricCanvas.current = null;
            setIsCanvasReady(false);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- history/save/saveNow
        // are accessed via stable refs to avoid re-creating the canvas on every
        // undo/redo state change.
    }, [projectId, syncLayers, token, updateSelectedProps]);

    // ── Keyboard shortcuts ──
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            // Ignore if focus is in an input/textarea
            const tag = (e.target as HTMLElement)?.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA") return;

            const canvas = fabricCanvas.current;
            if (!canvas) return;

            const { activateTool, addRect, addCircle, addText, removeSelection, history } = keyboardActionsRef.current;

            if (e.key === "v" || e.key === "V") activateTool("select");
            else if (e.key === "p" || e.key === "P") activateTool("draw");
            else if (e.key === "r" || e.key === "R") addRect();
            else if (e.key === "c" || e.key === "C") addCircle();
            else if (e.key === "t" || e.key === "T") addText();
            else if (e.key === "Delete" || e.key === "Backspace") {
                removeSelection();
                e.preventDefault();
            }
            // Undo/Redo shortcuts
            else if ((e.ctrlKey || e.metaKey) && e.key === "z") {
                e.preventDefault();
                history.undo(canvas);
            }
            else if ((e.ctrlKey || e.metaKey) && e.key === "y") {
                e.preventDefault();
                history.redo(canvas);
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);

    const activateTool = (next: WhiteboardTool) => {
        const canvas = fabricCanvas.current;
        setTool(next);
        if (!canvas) return;
        canvas.isDrawingMode = next === "draw";
        if (next === "draw") {
            canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
            canvas.freeDrawingBrush.width = 3;
            canvas.freeDrawingBrush.color = WHITEBOARD_COLORS.primary;
        }
    };

    /** Return the center of the currently visible canvas viewport. */
    const getViewportCenter = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return { cx: 200, cy: 200 };
        const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
        const zoom = canvas.getZoom() || 1;
        const cx = (-vpt[4] + (canvas.width ?? 800) / 2) / zoom;
        const cy = (-vpt[5] + (canvas.height ?? 600) / 2) / zoom;
        return { cx, cy };
    };

    const addRect = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const rect = new fabric.Rect({
            left: cx - 90,
            top: cy - 55,
            width: 180,
            height: 110,
            rx: 18,
            ry: 18,
            fill: "rgba(37, 99, 235, 0.25)",
            stroke: WHITEBOARD_COLORS.primary,
            strokeWidth: 2,
        });
        canvas.add(rect);
        canvas.setActiveObject(rect);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addCircle = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const circle = new fabric.Circle({
            left: cx - 54,
            top: cy - 54,
            radius: 54,
            fill: "rgba(16, 185, 129, 0.25)",
            stroke: WHITEBOARD_COLORS.success,
            strokeWidth: 2,
        });
        canvas.add(circle);
        canvas.setActiveObject(circle);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addText = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const text = new fabric.IText("Nuevo texto", {
            left: cx - 60,
            top: cy - 14,
            fontSize: 24,
            fill: isDark ? "#e2e8f0" : WHITEBOARD_COLORS.textPrimary,
            fontFamily: "Manrope",
        });
        canvas.add(text);
        canvas.setActiveObject(text);
        canvas.requestRenderAll();
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
        history.restoringRef.current = true;
        canvas.getObjects().forEach((object) => canvas.remove(object));
        canvas.requestRenderAll();
        history.clearHistory();
        history.restoringRef.current = false;
        saveNow(canvas);
    };

    const duplicateSelection = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const active = canvas.getActiveObject();
        if (!active) return;
        active.clone().then((cloned: fabric.FabricObject) => {
            cloned.set({ left: (cloned.left ?? 0) + 40, top: (cloned.top ?? 0) + 40 });
            canvas.add(cloned);
            canvas.setActiveObject(cloned);
            canvas.renderAll();
        });
    };

    const bringForward = () => {
        const canvas = fabricCanvas.current;
        const active = canvas?.getActiveObject();
        if (!canvas || !active) return;
        canvas.bringObjectForward(active);
        canvas.renderAll();
    };

    const sendBackward = () => {
        const canvas = fabricCanvas.current;
        const active = canvas?.getActiveObject();
        if (!canvas || !active) return;
        canvas.sendObjectBackwards(active);
        canvas.renderAll();
    };

    const focusLayer = (index: number) => {
        const canvas = fabricCanvas.current;
        const object = canvas?.getObjects()[index];
        if (!canvas || !object) return;
        canvas.setActiveObject(object);
        canvas.requestRenderAll();
    };

    const copyShareLink = useCallback(async () => {
        if (typeof window === "undefined") return;
        const url = window.location.href;
        try {
            if (navigator.share) {
                await navigator.share({ title, url });
                toast.success("Compartiendo pizarra");
                return;
            }
            if (navigator.clipboard) {
                await navigator.clipboard.writeText(url);
                toast.success("Enlace copiado al portapapeles");
                return;
            }
            // Fallback for older browsers / insecure contexts
            const input = document.createElement("input");
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand("copy");
            document.body.removeChild(input);
            toast.success("Enlace copiado al portapapeles");
        } catch {
            toast.error("No se pudo compartir/copiar el enlace");
        }
    }, [title]);

    const isTextSelected = selectedObjectProps?.type === "i-text" || selectedObjectProps?.type === "textbox";
    const isObjectSelected = selectedObjectProps !== null;

    // Keep a live ref to canvas actions so the keyboard shortcut handler
    // always invokes the latest functions without re-attaching the listener.
    const keyboardActionsRef = useRef({ activateTool, addRect, addCircle, addText, removeSelection, history });
    keyboardActionsRef.current = { activateTool, addRect, addCircle, addText, removeSelection, history };

    const handleSaveNow = useCallback(() => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        saveNow(canvas);
    }, [saveNow]);

    return (
        <div className={clsx("flex h-full flex-col overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]", className)}>
            {header && header({ title, saveStatus, saveNow: handleSaveNow })}

            <div className="relative flex flex-1 overflow-hidden">
                {/* ── Export / share floating bar ── */}
                <div className="absolute right-4 top-4 z-20 flex items-center gap-1.5 rounded-xl border border-[hsl(var(--border))] bg-white/90 p-1.5 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]/90">
                    <ExportButton
                        icon={ImageIcon}
                        label="PNG"
                        aria-label="Exportar como PNG"
                        disabled={!isCanvasReady}
                        onClick={() => exportToPng(fabricCanvas.current!, title)}
                        data-testid="whiteboard-export-png"
                    />
                    <ExportButton
                        icon={FileCode}
                        label="SVG"
                        aria-label="Exportar como SVG"
                        disabled={!isCanvasReady}
                        onClick={() => exportToSvg(fabricCanvas.current!, title)}
                        data-testid="whiteboard-export-svg"
                    />
                    <ExportButton
                        icon={FileJson}
                        label="JSON"
                        aria-label="Exportar como JSON"
                        disabled={!isCanvasReady}
                        onClick={() => exportToJson(fabricCanvas.current!, title)}
                        data-testid="whiteboard-export-json"
                    />
                    <div className="h-4 w-px bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                    <ExportButton
                        icon={Share2}
                        label="Compartir"
                        aria-label="Compartir pizarra"
                        onClick={copyShareLink}
                    />
                </div>

                {/* ── Left toolbar ── */}
                <div className="absolute left-6 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-2 rounded-xl border border-[hsl(var(--border))] bg-white/90 p-2 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]/90">
                    <ToolbarButton icon={MousePointer2} active={tool === "select"} onClick={() => activateTool("select")} label="Seleccionar (V)" />
                    <ToolbarButton icon={Pencil} active={tool === "draw"} onClick={() => activateTool("draw")} label="Dibujo libre (P)" />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <ToolbarButton icon={Square} active={false} onClick={addRect} label="Rectángulo (R)" data-testid="whiteboard-add-rect" />
                    <ToolbarButton icon={Circle} active={false} onClick={addCircle} label="Círculo (C)" data-testid="whiteboard-add-circle" />
                    <ToolbarButton icon={Type} active={false} onClick={addText} label="Texto (T)" data-testid="whiteboard-add-text" />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <ToolbarButton icon={Eraser} active={false} onClick={removeSelection} label="Borrar selección" />
                    <ToolbarButton icon={Trash2} active={false} onClick={clearCanvas} label="Limpiar lienzo" tone="danger" />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <ToolbarButton
                        icon={RotateCcw}
                        active={false}
                        onClick={() => fabricCanvas.current && history.undo(fabricCanvas.current)}
                        label="Deshacer (Ctrl+Z)"
                        disabled={!history.canUndo}
                        data-testid="whiteboard-undo"
                    />
                    <ToolbarButton
                        icon={RotateCw}
                        active={false}
                        onClick={() => fabricCanvas.current && history.redo(fabricCanvas.current)}
                        label="Rehacer (Ctrl+Y)"
                        disabled={!history.canRedo}
                        data-testid="whiteboard-redo"
                    />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <div className="relative">
                        <ToolbarButton
                            icon={gridStyle === "none" ? EyeOff : Grid3x3}
                            active={showGridMenu}
                            onClick={() => setShowGridMenu((prev) => !prev)}
                            label={`Grilla: ${GRID_OPTIONS.find((g) => g.value === gridStyle)?.label}`}
                        />
                        {showGridMenu && (
                            <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 z-50 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-2 shadow-2xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))] min-w-[140px]">
                                <p className="px-2 pb-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estilo</p>
                                {GRID_OPTIONS.map((opt) => (
                                    <button
                                        key={opt.value}
                                        onClick={() => { setGridStyle(opt.value); setShowGridMenu(false); }}
                                        className={clsx(
                                            "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-semibold transition-all",
                                            gridStyle === opt.value
                                                ? "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--primary)/0.1)]"
                                                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                                        )}
                                    >
                                        <opt.icon size={14} />
                                        {opt.label}
                                    </button>
                                ))}
                                <div className="my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                                <p className="px-2 pb-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tamaño</p>
                                {GRID_SIZES.map((opt) => (
                                    <button
                                        key={opt.value}
                                        onClick={() => { setGridSize(opt.value); setShowGridMenu(false); }}
                                        className={clsx(
                                            "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-semibold transition-all",
                                            gridSize === opt.value
                                                ? "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--primary)/0.1)]"
                                                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
                                        )}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Canvas area ── */}
                <main
                    className="flex-1 overflow-auto p-4 pl-24"
                    style={{
                        background: gridStyle === "none"
                            ? "hsl(var(--bg-primary))"
                            : `${getGridBackground(gridStyle, gridSize, isDark)}`,
                        backgroundSize: gridStyle === "dots" ? `${gridSize}px ${gridSize}px` : `${gridSize}px ${gridSize}px`,
                        backgroundColor: "hsl(var(--bg-primary))",
                    }}
                >
                    <div className="inline-block overflow-hidden rounded-xl border-8 border-white bg-[hsl(var(--bg-primary))] shadow-[0_48px_96px_-32px_rgba(15,23,42,0.4)] dark:border-[hsl(var(--surface-1))]">
                        <canvas ref={canvasRef} className="whiteboard-canvas" />
                    </div>
                </main>

                {/* ── Right property panel ── */}
                <aside className="w-80 shrink-0 overflow-y-auto border-l border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-[hsl(var(--surface-2))]">
                    {/* Info section */}
                    <section className="space-y-2">
                        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Objetivo</p>
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{title}</h1>
                        <p className="text-xs font-medium leading-5 text-[hsl(var(--text-secondary))]">Sin objetivo documentado.</p>
                    </section>

                    {/* ── Object properties ── */}
                    {isObjectSelected && (
                        <section className="mt-5 space-y-4 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]/50 p-3 dark:border-white/5 dark:bg-white/[0.03]">
                            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                Propiedades — {String(selectedObjectProps?.type || "objeto")}
                            </p>

                            {/* Fill color */}
                            <div className="space-y-1.5">
                                <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Relleno</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="color"
                                        value={fillColor}
                                        onChange={(e) => { setFillColor(e.target.value); applyProperty("fill", e.target.value); }}
                                        className="size-8 cursor-pointer rounded-lg border border-[hsl(var(--border))] bg-transparent p-0 dark:border-white/10"
                                    />
                                    <div className="flex gap-1">
                                        {COLOR_PRESETS.map((c) => (
                                            <button
                                                key={c}
                                                onClick={() => { setFillColor(c); applyProperty("fill", c); }}
                                                className={clsx(
                                                    "size-5 rounded-full border transition-all hover:scale-125",
                                                    fillColor === c ? "scale-125 ring-2 ring-[hsl(var(--primary))] ring-offset-1 ring-offset-[hsl(var(--border))]" : "border-[hsl(var(--border))] dark:border-white/10"
                                                )}
                                                style={{ backgroundColor: c }}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Stroke color */}
                            <div className="space-y-1.5">
                                <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Borde</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        type="color"
                                        value={strokeColor}
                                        onChange={(e) => { setStrokeColor(e.target.value); applyProperty("stroke", e.target.value); }}
                                        className="size-8 cursor-pointer rounded-lg border border-[hsl(var(--border))] bg-transparent p-0 dark:border-white/10"
                                    />
                                    <div className="flex gap-1">
                                        {COLOR_PRESETS.map((c) => (
                                            <button
                                                key={c}
                                                onClick={() => { setStrokeColor(c); applyProperty("stroke", c); }}
                                                className={clsx(
                                                    "size-5 rounded-full border transition-all hover:scale-125",
                                                    strokeColor === c ? "scale-125 ring-2 ring-[hsl(var(--primary))] ring-offset-1 ring-offset-[hsl(var(--border))]" : "border-[hsl(var(--border))] dark:border-white/10"
                                                )}
                                                style={{ backgroundColor: c }}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Stroke width slider */}
                            <div className="space-y-1.5">
                                <label className="flex items-center justify-between text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <span>Grosor de borde</span>
                                    <span className="font-mono text-xs">{strokeWidth}px</span>
                                </label>
                                <input
                                    type="range"
                                    min={0}
                                    max={20}
                                    value={strokeWidth}
                                    onChange={(e) => { const v = Number(e.target.value); setStrokeWidth(v); applyProperty("strokeWidth", v); }}
                                    className="w-full accent-[hsl(var(--primary))]"
                                />
                            </div>

                            {/* Opacity slider */}
                            <div className="space-y-1.5">
                                <label className="flex items-center justify-between text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <span>Opacidad</span>
                                    <span className="font-mono text-xs">{opacity}%</span>
                                </label>
                                <input
                                    type="range"
                                    min={5}
                                    max={100}
                                    value={opacity}
                                    onChange={(e) => { const v = Number(e.target.value) / 100; setOpacity(Number(e.target.value)); applyProperty("opacity", v); }}
                                    className="w-full accent-[hsl(var(--primary))]"
                                />
                            </div>

                            {/* Text-specific properties */}
                            {isTextSelected && (
                                <>
                                    {/* Font family dropdown */}
                                    <div className="space-y-1.5">
                                        <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fuente</label>
                                        <select
                                            value={textFontFamily}
                                            onChange={(e) => { setTextFontFamily(e.target.value); applyProperty("fontFamily", e.target.value); }}
                                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-sm font-semibold outline-none dark:border-white/10 dark:bg-black/20"
                                        >
                                            {FONT_FAMILIES.map((f) => (
                                                <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>
                                                    {f.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Font size */}
                                    <div className="space-y-1.5">
                                        <label className="flex items-center justify-between text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                            <span>Tamaño</span>
                                            <span className="font-mono text-xs">{textFontSize}px</span>
                                        </label>
                                        <input
                                            type="range"
                                            min={8}
                                            max={120}
                                            value={textFontSize}
                                            onChange={(e) => { const v = Number(e.target.value); setTextFontSize(v); applyProperty("fontSize", v); }}
                                            className="w-full accent-[hsl(var(--primary))]"
                                        />
                                        <div className="flex flex-wrap gap-1">
                                            {FONT_SIZE_PRESETS.map((s) => (
                                                <button
                                                    key={s}
                                                    onClick={() => { setTextFontSize(s); applyProperty("fontSize", s); }}
                                                    className={clsx(
                                                        "rounded-md px-2 py-0.5 text-2xs font-bold transition-all",
                                                        textFontSize === s
                                                            ? "bg-[hsl(var(--primary))] text-white"
                                                            : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:bg-white/5 dark:hover:bg-white/10"
                                                    )}
                                                >
                                                    {s}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Text color */}
                                    <div className="space-y-1.5">
                                        <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Color texto</label>
                                        <input
                                            type="color"
                                            value={textColor}
                                            onChange={(e) => { setTextColor(e.target.value); applyProperty("fill", e.target.value); }}
                                            className="size-8 cursor-pointer rounded-lg border border-[hsl(var(--border))] bg-transparent p-0 dark:border-white/10"
                                        />
                                    </div>

                                    {/* Bold / Italic */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => { const v = textBold ? "normal" : "bold"; setTextBold(!textBold); applyProperty("fontWeight", v); }}
                                            className={clsx(
                                                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all",
                                                textBold ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5"
                                            )}
                                        >
                                            <Bold size={14} /> Negrita
                                        </button>
                                        <button
                                            onClick={() => { const v = textItalic ? "" : "italic"; setTextItalic(!textItalic); applyProperty("fontStyle", v); }}
                                            className={clsx(
                                                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all",
                                                textItalic ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5"
                                            )}
                                        >
                                            <Italic size={14} /> Cursiva
                                        </button>
                                    </div>
                                </>
                            )}

                            {/* Position & size */}
                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">X</label>
                                    <input
                                        type="number"
                                        value={objLeft}
                                        onChange={(e) => { const v = Number(e.target.value); setObjLeft(v); applyProperty("left", v); }}
                                        className="w-full rounded-md border border-[hsl(var(--border))] px-2 py-1 text-xs font-semibold outline-none dark:border-white/10 dark:bg-black/20"
                                    />
                                </div>
                                <div>
                                    <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Y</label>
                                    <input
                                        type="number"
                                        value={objTop}
                                        onChange={(e) => { const v = Number(e.target.value); setObjTop(v); applyProperty("top", v); }}
                                        className="w-full rounded-md border border-[hsl(var(--border))] px-2 py-1 text-xs font-semibold outline-none dark:border-white/10 dark:bg-black/20"
                                    />
                                </div>
                                <div>
                                    <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ancho</label>
                                    <input
                                        type="number"
                                        value={objWidth}
                                        onChange={(e) => { const v = Number(e.target.value); setObjWidth(v); applyProperty("width", v); }}
                                        className="w-full rounded-md border border-[hsl(var(--border))] px-2 py-1 text-xs font-semibold outline-none dark:border-white/10 dark:bg-black/20"
                                    />
                                </div>
                                <div>
                                    <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alto</label>
                                    <input
                                        type="number"
                                        value={objHeight}
                                        onChange={(e) => { const v = Number(e.target.value); setObjHeight(v); applyProperty("height", v); }}
                                        className="w-full rounded-md border border-[hsl(var(--border))] px-2 py-1 text-xs font-semibold outline-none dark:border-white/10 dark:bg-black/20"
                                    />
                                </div>
                            </div>

                            {/* Order actions */}
                            <div className="flex gap-2">
                                <button onClick={bringForward} className="flex items-center gap-1 rounded-lg bg-[hsl(var(--surface-2))] px-2 py-1.5 text-2xs font-bold text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-3))] dark:bg-white/5 dark:hover:bg-white/10">
                                    <BringToFront size={12} /> Al frente
                                </button>
                                <button onClick={sendBackward} className="flex items-center gap-1 rounded-lg bg-[hsl(var(--surface-2))] px-2 py-1.5 text-2xs font-bold text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-3))] dark:bg-white/5 dark:hover:bg-white/10">
                                    <SendToBack size={12} /> Atrás
                                </button>
                                <button onClick={duplicateSelection} className="flex items-center gap-1 rounded-lg bg-[hsl(var(--surface-2))] px-2 py-1.5 text-2xs font-bold text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-3))] dark:bg-white/5 dark:hover:bg-white/10">
                                    <Copy size={12} /> Duplicar
                                </button>
                            </div>

                            {/* Delete button */}
                            <button
                                onClick={removeSelection}
                                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[hsl(var(--destructive)/0.08)] py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--destructive))] transition-all hover:bg-[hsl(var(--destructive)/0.15)] dark:bg-[hsl(var(--destructive)/0.1)]"
                            >
                                <Trash2 size={14} /> Eliminar objeto
                            </button>
                        </section>
                    )}

                    {/* ── Layers ── */}
                    <section data-testid="whiteboard-layers" className={clsx("space-y-3", isObjectSelected ? "mt-5" : "mt-6")}>
                        <h3 className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            <Layers size={12} /> Capas reales
                        </h3>
                        <div className="space-y-1.5">
                            {layers.map((layer) => (
                                <button
                                    key={`${layer.type}-${layer.index}`}
                                    onClick={() => focusLayer(layer.index)}
                                    className="flex w-full items-center justify-between rounded-lg border border-[hsl(var(--border))] p-2.5 text-left text-xs font-medium text-[hsl(var(--text-secondary))] transition-all hover:border-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--info-muted))] dark:border-white/5 dark:hover:bg-[hsl(var(--primary)/0.1)]"
                                >
                                    <span className="flex items-center gap-2">
                                        <History size={12} /> {layer.label}
                                    </span>
                                    <span className="text-2xs font-bold opacity-40">#{layer.index + 1}</span>
                                </button>
                            ))}
                            {layers.length === 0 && (
                                <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-xs font-semibold text-[hsl(var(--text-secondary))] dark:border-white/10">
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
        fill: WHITEBOARD_COLORS.textPrimary,
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
        fill: WHITEBOARD_COLORS.primaryLight,
        stroke: WHITEBOARD_COLORS.primary,
        strokeWidth: 2,
    });
    const text = new fabric.IText("Doble clic para editar", {
        left: 118,
        top: 195,
        fontSize: 18,
        fill: WHITEBOARD_COLORS.textSecondary,
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
    if (object.type === "rect") return `Rectángulo ${index + 1}`;
    if (object.type === "circle") return `Círculo ${index + 1}`;
    if (object.type === "path") return `Trazo ${index + 1}`;
    return `Objeto ${index + 1}`;
}

function ExportButton({
    icon: Icon,
    label,
    onClick,
    disabled = false,
    "aria-label": ariaLabel,
    "data-testid": dataTestid,
}: {
    icon: React.ElementType;
    label: string;
    onClick: () => void;
    disabled?: boolean;
    "aria-label"?: string;
    "data-testid"?: string;
}) {
    return (
        <button
            onClick={onClick}
            title={label}
            aria-label={ariaLabel || label}
            disabled={disabled}
            data-testid={dataTestid}
            className={clsx(
                "group relative flex h-8 items-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-[hsl(var(--text-secondary))] transition-all",
                disabled
                    ? "cursor-not-allowed opacity-40"
                    : "hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] dark:hover:bg-white/5"
            )}
        >
            <Icon size={14} />
            <span>{label}</span>
        </button>
    );
}

function ToolbarButton({
    icon: Icon,
    active,
    onClick,
    label,
    tone = "default",
    disabled = false,
    "data-testid": dataTestid,
}: {
    icon: React.ElementType;
    active: boolean;
    onClick: () => void;
    label: string;
    tone?: "default" | "danger";
    disabled?: boolean;
    "data-testid"?: string;
}) {
    return (
        <button
            onClick={onClick}
            title={label}
            disabled={disabled}
            data-testid={dataTestid}
            className={clsx(
                "group relative flex size-10 items-center justify-center rounded-lg transition-all",
                active
                    ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-[hsl(var(--primary)/0.2)]"
                    : tone === "danger"
                        ? "text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] hover:text-[hsl(var(--destructive))] dark:hover:bg-[hsl(var(--destructive)/0.1)]"
                        : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5",
                disabled && "opacity-30 cursor-not-allowed"
            )}
        >
            <Icon size={20} />
            <span className="pointer-events-none absolute left-full z-50 ml-4 whitespace-nowrap rounded-lg bg-[hsl(var(--bg-muted))] px-2 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white opacity-0 transition-opacity group-hover:opacity-100">
                {label}
            </span>
        </button>
    );
}

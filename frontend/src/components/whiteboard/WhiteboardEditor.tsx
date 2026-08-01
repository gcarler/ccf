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
    ArrowUpRight,
    Diamond,
    Pill,
    Hexagon,
    Database,
    FileText,
    StickyNote,
    GitBranch,
    LayoutGrid,
    AlignCenter,
    Hand,
    AlertTriangle,
} from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import {
    fetchProjectWhiteboard,
    GridStyle,
    GridSize,
    WHITEBOARD_COLORS,
    WHITEBOARD_COLOR_PRESETS,
    uploadProjectWhiteboardThumbnail,
    dataUrlToBlob,
} from "@/lib/whiteboards";
import { exportToPng, exportToSvg, exportToJson } from "@/lib/whiteboardExport";
import { useWhiteboardHistory } from "@/hooks/useWhiteboardHistory";
import { useWhiteboardSave } from "@/hooks/useWhiteboardSave";
import {
    type AnchorPosition,
    generateShapeId,
    findShapeNearPoint,
    createConnectorLine,
    updateConnectors,
    ensureShapeIds,
    renderConnectors,
    renderAnchors,
} from "@/lib/whiteboard/connectors";
import {
    createDiamond,
    createPill,
    createData,
    createSubprocess,
    createDatabase,
    createDocument,
    createHexagon,
    createNote,
} from "@/lib/whiteboard/flowchartShapes";

import {
    calculateGuides,
    renderGuides,
    type Guide,
} from "@/lib/whiteboard/snapGuides";


type WhiteboardTool = "select" | "draw" | "connector" | "pan";

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
        isDirty: boolean;
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

/**
 * Convert any CSS color string (rgba, rgb, hex, named) to #rrggbb
 * so it can be used as the `value` of an <input type="color">.
 */
function toHex(color: string): string {
    if (!color) return "#000000";
    // Already hex
    if (/^#[0-9a-fA-F]{6}$/.test(color)) return color;
    if (/^#[0-9a-fA-F]{3}$/.test(color)) {
        const [, r, g, b] = color.match(/^#(.)(.)(.)$/)!;
        return `#${r}${r}${g}${g}${b}${b}`;
    }
    // Use an off-screen canvas to resolve any CSS color
    const ctx = document.createElement("canvas").getContext("2d");
    if (!ctx) return "#000000";
    ctx.fillStyle = color;
    const resolved = ctx.fillStyle; // browser normalises to #rrggbb or rgb()
    if (resolved.startsWith("#")) return resolved;
    const match = resolved.match(/\d+/g);
    if (!match) return "#000000";
    const [r, g, b] = match.map(Number);
    return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

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

    const [snapEnabled, setSnapEnabled] = useState(true);
    const [showShapePicker, setShowShapePicker] = useState(false);
    const snapEnabledRef = useRef(true);
    const smartGuidesRef = useRef<Guide[]>([]);

    const [title, setTitle] = useState(initialTitle);
    const [tool, setTool] = useState<WhiteboardTool>("select");
    const [layers, setLayers] = useState<LayerRow[]>([]);
    const [selectedObjectProps, setSelectedObjectProps] = useState<Record<string, unknown> | null>(null);
    const { saveStatus, save, saveNow, flushPending, isDirty } = useWhiteboardSave({
        projectId,
        token,
        title,
    });
    // True when the same board is open in another tab (detected via
    // BroadcastChannel) — warns that concurrent edits may overwrite each other.
    const [duplicateTabOpen, setDuplicateTabOpen] = useState(false);

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

    // Connector tool state
    const connectorFromRef = useRef<{ shapeId: string; anchor: AnchorPosition } | null>(null);
    const connectorPreviewRef = useRef<fabric.Line | null>(null);
    const hoveredShapeIdRef = useRef<string | null>(null);
    const toolRef = useRef<WhiteboardTool>("select");

    const isPanningRef = useRef(false);
    const lastPanPointRef = useRef<{ x: number; y: number } | null>(null);
    const spaceDownRef = useRef(false);
    const [zoomLevel, setZoomLevel] = useState(100);
    // Inline connector label editor
    const [connectorLabelState, setConnectorLabelState] = useState<{ obj: fabric.Line; value: string; x: number; y: number } | null>(null);

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
        setFillColor(toHex((active.fill as string) || WHITEBOARD_COLORS.primary));
        setStrokeColor(toHex((active.stroke as string) || WHITEBOARD_COLORS.primary));
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
    const flushPendingRef = useRef(flushPending);
    flushPendingRef.current = flushPending;

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
                ensureShapeIds(canvas);
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
        canvas.on("object:modified", () => { smartGuidesRef.current = []; canvas.requestRenderAll(); handleChanged(); });
        canvas.on("object:removed", (opt) => {
            // Remove orphan connectors whose fromShape or toShape was deleted
            const removedId = (opt.target as fabric.FabricObject)?.data?.shapeId as string | undefined;
            if (removedId) {
                const orphans = canvas.getObjects().filter(
                    o => o.data?.type === 'connector' &&
                    (o.data.fromShapeId === removedId || o.data.toShapeId === removedId)
                );
                orphans.forEach(o => canvas.remove(o));
            }
            handleChanged();
        });
        canvas.on("selection:created", updateSelectedProps);
        canvas.on("selection:updated", updateSelectedProps);
        canvas.on("selection:cleared", () => { smartGuidesRef.current = []; setSelectedObjectProps(null); });

        // Connector mode handlers
        canvas.on("mouse:move", (opt) => {
            // Pan mode
            if (isPanningRef.current && lastPanPointRef.current) {
                const vpt = canvas.viewportTransform;
                if (!vpt) return;
                const e = opt.e as MouseEvent;
                const dx = e.clientX - lastPanPointRef.current.x;
                const dy = e.clientY - lastPanPointRef.current.y;
                vpt[4] += dx;
                vpt[5] += dy;
                canvas.setViewportTransform(vpt);
                lastPanPointRef.current = { x: e.clientX, y: e.clientY };
                return;
            }
            if (toolRef.current !== "connector") return;
            const pointer = opt.scenePoint;
            // Update hover
            const near = findShapeNearPoint(canvas, pointer, 50);
            hoveredShapeIdRef.current = (near?.shape.data?.shapeId as string) || null;
            // Update preview line
            if (connectorFromRef.current && connectorPreviewRef.current) {
                const snap = findShapeNearPoint(canvas, pointer, 28);
                const end = snap ? snap.anchorPoint : pointer;
                connectorPreviewRef.current.set({ x2: end.x, y2: end.y });
                connectorPreviewRef.current.setCoords();
            }
            canvas.requestRenderAll();
        });

        canvas.on("mouse:down", (opt) => {
            // Space-drag panning (works in any tool)
            if (spaceDownRef.current) {
                isPanningRef.current = true;
                const e = opt.e as MouseEvent;
                lastPanPointRef.current = { x: e.clientX, y: e.clientY };
                canvas.defaultCursor = 'grabbing';
                return;
            }
            // Pan tool
            if (toolRef.current === 'pan') {
                isPanningRef.current = true;
                const e = opt.e as MouseEvent;
                lastPanPointRef.current = { x: e.clientX, y: e.clientY };
                canvas.defaultCursor = 'grabbing';
                return;
            }
            if (toolRef.current !== "connector") return;
            const pointer = opt.scenePoint;
            const target = findShapeNearPoint(canvas, pointer, 28);

            if (!connectorFromRef.current) {
                // Start connector — requires clicking on a shape anchor
                if (target) {
                    connectorFromRef.current = { shapeId: target.shape.data!.shapeId as string, anchor: target.anchor };
                    const preview = new fabric.Line(
                        [target.anchorPoint.x, target.anchorPoint.y, target.anchorPoint.x, target.anchorPoint.y],
                        { stroke: "#2563eb", strokeWidth: 2, strokeDashArray: [6, 4], selectable: false, evented: false }
                    );
                    canvas.add(preview);
                    connectorPreviewRef.current = preview;
                }
                // Click on empty space: do nothing (no connector started)
            } else {
                // Complete connector
                if (target && (target.shape.data!.shapeId as string) !== connectorFromRef.current.shapeId) {
                    const line = createConnectorLine(
                        canvas,
                        connectorFromRef.current.shapeId,
                        target.shape.data!.shapeId as string,
                        connectorFromRef.current.anchor,
                        target.anchor,
                    );
                    if (line) canvas.add(line);
                }
                // Click on empty space or same shape: cancel connector
                if (connectorPreviewRef.current) {
                    canvas.remove(connectorPreviewRef.current);
                    connectorPreviewRef.current = null;
                }
                connectorFromRef.current = null;
                canvas.requestRenderAll();
            }
        });

        canvas.on("mouse:up", () => {
            if (toolRef.current === 'pan' || spaceDownRef.current) {
                isPanningRef.current = false;
                lastPanPointRef.current = null;
                canvas.defaultCursor = spaceDownRef.current ? (toolRef.current === 'connector' ? 'crosshair' : toolRef.current === 'pan' ? 'grab' : 'default') : 'grab';
            }
        });

        canvas.on("mouse:wheel", (opt) => {
            const delta = opt.e.deltaY;
            let zoom = canvas.getZoom();
            zoom *= 0.999 ** delta;
            zoom = Math.min(Math.max(0.2, zoom), 5);
            canvas.zoomToPoint(new fabric.Point(opt.e.offsetX, opt.e.offsetY), zoom);
            // Use rAF so getZoom() reflects the updated value
            requestAnimationFrame(() => setZoomLevel(Math.round(canvas.getZoom() * 100)));
            opt.e.preventDefault();
            opt.e.stopPropagation();
        });

        // Update connectors when shapes move
        canvas.on("object:moving", (opt) => {
            if (snapEnabledRef.current && opt.target) {
                // Smart guides
                const allObjs = canvas.getObjects()
                    .filter(o => o !== opt.target && o.data?.type !== 'connector')
                    .map(o => ({ left: o.left||0, top: o.top||0, width: o.width||0, height: o.height||0, scaleX: o.scaleX||1, scaleY: o.scaleY||1 }));
                const t = opt.target;
                const active = { left: t.left||0, top: t.top||0, width: t.width||0, height: t.height||0, scaleX: t.scaleX||1, scaleY: t.scaleY||1 };
                const result = calculateGuides(active, allObjs);
                smartGuidesRef.current = result.guides;
                if (result.snapX !== null) opt.target.set({ left: result.snapX });
                if (result.snapY !== null) opt.target.set({ top: result.snapY });
            }
            updateConnectors(canvas);
            canvas.requestRenderAll();
        });

        // Render arrowheads and anchors overlay
        canvas.on("after:render", (opt: { ctx: CanvasRenderingContext2D }) => {
            renderConnectors(canvas, opt.ctx);
            if (smartGuidesRef.current.length > 0) {
                renderGuides(opt.ctx, smartGuidesRef.current, canvas.width || 800, canvas.height || 600, canvas.viewportTransform || [1,0,0,1,0,0]);
            }
            if (toolRef.current === "connector") {
                renderAnchors(canvas, opt.ctx, {
                    hoveredShapeId: hoveredShapeIdRef.current,
                    connectingFromId: connectorFromRef.current?.shapeId || null,
                });
            }
        });

        // Double-click to edit text inside Groups or connector labels
        canvas.on("mouse:dblclick", (opt) => {
            const target = opt.target;
            if (!target || toolRef.current === "connector") return;
            if (target?.data?.type === 'connector') {
                // Show inline label editor at connector midpoint
                const line = target as fabric.Line;
                const vpt = canvas.viewportTransform || [1,0,0,1,0,0];
                const mx = ((line.x1 || 0) + (line.x2 || 0)) / 2;
                const my = ((line.y1 || 0) + (line.y2 || 0)) / 2;
                const sx = mx * vpt[0] + vpt[4];
                const sy = my * vpt[3] + vpt[5];
                setConnectorLabelState({
                    obj: line,
                    value: (target.data.label as string) || '',
                    x: sx,
                    y: sy,
                });
                return;
            }
            if (target instanceof fabric.Group) {
                const textChild = target.getObjects().find((o) => o.type === "i-text" || o.type === "textbox");
                if (textChild && textChild instanceof fabric.IText) {
                    canvas.setActiveObject(textChild);
                    textChild.enterEditing();
                    textChild.selectAll();
                }
            }
        });

        return () => {
            window.removeEventListener("resize", resizeCanvas);
            // Flush any debounced/queued save BEFORE disposing the canvas so
            // the last edit is not lost when the panel closes.
            flushPendingRef.current();
            canvas.dispose();
            fabricCanvas.current = null;
            setIsCanvasReady(false);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- history/save/saveNow
        // are accessed via stable refs to avoid re-creating the canvas on every
        // undo/redo state change.
    }, [projectId, syncLayers, token, updateSelectedProps]);

    // ── Duplicate-tab detection (concurrent edits may overwrite each other) ──
    useEffect(() => {
        if (typeof window === "undefined" || typeof BroadcastChannel === "undefined" || !projectId) return;
        const channel = new BroadcastChannel(`ccf-whiteboard:${projectId}`);
        let lastSeen = Date.now();
        const markSeen = () => {
            lastSeen = Date.now();
            setDuplicateTabOpen(true);
        };
        channel.onmessage = (event) => {
            if (event.data?.type === "heartbeat") markSeen();
        };
        const heartbeat = setInterval(() => {
            channel.postMessage({ type: "heartbeat" });
            // Clear the banner when the other tab has been gone for a while.
            if (Date.now() - lastSeen > 12000) setDuplicateTabOpen(false);
        }, 4000);
        channel.postMessage({ type: "heartbeat" });
        return () => {
            clearInterval(heartbeat);
            channel.close();
        };
    }, [projectId]);

    // ── Thumbnail generation (throttled; best-effort, never blocks saves) ──
    const lastThumbAtRef = useRef(0);
    useEffect(() => {
        if (saveStatus !== "saved") return;
        const canvas = fabricCanvas.current;
        if (!canvas || !projectId || !token) return;
        const now = Date.now();
        if (now - lastThumbAtRef.current < 30000) return;
        lastThumbAtRef.current = now;
        try {
            const dataUrl = canvas.toDataURL({
                format: "jpeg",
                quality: 0.6,
                multiplier: 0.2,
            });
            const blob = dataUrlToBlob(dataUrl);
            if (!blob) return;
            uploadProjectWhiteboardThumbnail(projectId, blob, token).catch(() => {
                // Thumbnails are best-effort — ignore failures silently.
            });
        } catch {
            // toDataURL can throw for canvases with unusual state — ignore.
        }
    }, [saveStatus, projectId, token]);

    // ── Keyboard shortcuts ──
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            // Ignore if focus is in an input/textarea
            const tag = (e.target as HTMLElement)?.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA") return;

            const canvas = fabricCanvas.current;
            if (!canvas) return;

            const { activateTool, addRect, addCircle, addText, addDiamondShape, addPillShape, addDataShape, removeSelection, history } = keyboardActionsRef.current;

            if (e.key === "v" || e.key === "V") activateTool("select");
            else if (e.key === "p" || e.key === "P") activateTool("draw");
            else if (e.key === "a" || e.key === "A") activateTool("connector");
            else if (e.key === "h" || e.key === "H") activateTool("pan");
            else if (e.key === "Escape") {
                // Cancel connector in progress
                if (connectorFromRef.current && fabricCanvas.current) {
                    const cv = fabricCanvas.current;
                    if (connectorPreviewRef.current) { cv.remove(connectorPreviewRef.current); connectorPreviewRef.current = null; }
                    connectorFromRef.current = null;
                    cv.requestRenderAll();
                }
                setShowShapePicker(false);
            }
            else if (e.key === ' ' && !e.repeat) {
                spaceDownRef.current = true;
                if (fabricCanvas.current) {
                    fabricCanvas.current.defaultCursor = 'grab';
                    fabricCanvas.current.hoverCursor = 'grab';
                }
                e.preventDefault();
            }
            else if (e.key === "d" || e.key === "D") addDiamondShape();
            else if (e.key === "s" || e.key === "S") addPillShape();
            else if (e.key === "i" || e.key === "I") addDataShape();
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

        const keyupHandler = (e: KeyboardEvent) => {
            const tag = (e.target as HTMLElement)?.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA") return;

            if (e.key === ' ') {
                spaceDownRef.current = false;
                isPanningRef.current = false;
                lastPanPointRef.current = null;
                const canvas = fabricCanvas.current;
                if (canvas) {
                    canvas.defaultCursor = toolRef.current === 'connector' ? 'crosshair' : toolRef.current === 'pan' ? 'grab' : 'default';
                    canvas.hoverCursor = toolRef.current === 'connector' ? 'crosshair' : toolRef.current === 'pan' ? 'grab' : 'move';
                }
            }
        };

        window.addEventListener("keydown", handler);
        window.addEventListener("keyup", keyupHandler);
        return () => {
            window.removeEventListener("keydown", handler);
            window.removeEventListener("keyup", keyupHandler);
        };
    }, []);

    const activateTool = (next: WhiteboardTool) => {
        const canvas = fabricCanvas.current;
        setTool(next);
        toolRef.current = next;
        if (!canvas) return;

        if (next === "connector") {
            canvas.isDrawingMode = false;
            canvas.selection = false;
            canvas.defaultCursor = "crosshair";
            canvas.hoverCursor = "crosshair";
            canvas.discardActiveObject();
            canvas.forEachObject(o => { o.selectable = true; o.evented = true; });
        } else if (next === 'pan') {
            canvas.isDrawingMode = false;
            canvas.selection = false;
            canvas.defaultCursor = 'grab';
            canvas.hoverCursor = 'grab';
            canvas.discardActiveObject();
            // Make all objects non-selectable during pan
            canvas.forEachObject(o => { o.selectable = false; o.evented = false; });
        } else {
            canvas.selection = true;
            canvas.defaultCursor = "default";
            canvas.hoverCursor = "move";
            connectorFromRef.current = null;
            if (connectorPreviewRef.current) {
                canvas.remove(connectorPreviewRef.current);
                connectorPreviewRef.current = null;
            }
            // Restore object selectability when leaving pan
            canvas.forEachObject(o => { o.selectable = true; o.evented = true; });
        }

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
            data: { shapeId: generateShapeId() },
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
            data: { shapeId: generateShapeId() },
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
            data: { shapeId: generateShapeId() },
        });
        canvas.add(text);
        canvas.setActiveObject(text);
        canvas.requestRenderAll();
        text.enterEditing();
        text.selectAll();
        activateTool("select");
    };

    const addDiamondShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createDiamond({ left: cx - 55, top: cy - 55 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addPillShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createPill({ left: cx - 75, top: cy - 26 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addDataShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createData({ left: cx - 85, top: cy - 34 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };


    const addSubprocessShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createSubprocess({ left: cx - 90, top: cy - 40 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addDatabaseShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createDatabase({ left: cx - 55, top: cy - 40 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addDocumentShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createDocument({ left: cx - 80, top: cy - 40 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addHexagonShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createHexagon({ left: cx - 80, top: cy - 40 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
        activateTool("select");
    };

    const addNoteShape = () => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        const { cx, cy } = getViewportCenter();
        const group = createNote({ left: cx - 80, top: cy - 50 });
        canvas.add(group);
        canvas.setActiveObject(group);
        canvas.requestRenderAll();
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
    const keyboardActionsRef = useRef({ activateTool, addRect, addCircle, addText, addDiamondShape, addPillShape, addDataShape, addSubprocessShape, addDatabaseShape, addDocumentShape, addHexagonShape, addNoteShape, removeSelection, history });
    keyboardActionsRef.current = { activateTool, addRect, addCircle, addText, addDiamondShape, addPillShape, addDataShape, addSubprocessShape, addDatabaseShape, addDocumentShape, addHexagonShape, addNoteShape, removeSelection, history };

    const handleSaveNow = useCallback(() => {
        const canvas = fabricCanvas.current;
        if (!canvas) return;
        saveNow(canvas);
    }, [saveNow]);

    return (
        <div className={clsx("flex h-full flex-col overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]", className)}>
            {header && header({ title, saveStatus, isDirty, saveNow: handleSaveNow })}

            {duplicateTabOpen && (
                <div
                    data-testid="whiteboard-duplicate-tab"
                    className="z-30 flex items-center justify-center gap-2 border-b border-[hsl(var(--warning))]/20 bg-[hsl(var(--warning))]/10 px-4 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--warning))]"
                >
                    <AlertTriangle size={12} />
                    Esta pizarra está abierta en otra pestaña — los cambios simultáneos pueden sobrescribirse.
                </div>
            )}

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
                    <ToolbarButton icon={ArrowUpRight} active={tool === "connector"} onClick={() => activateTool("connector")} label="Conector (A)" />
                    <ToolbarButton icon={Hand} active={tool === "pan"} onClick={() => activateTool("pan")} label="Mover lienzo (H)" />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <div className="relative">
                        <ToolbarButton
                            icon={LayoutGrid}
                            active={showShapePicker}
                            onClick={() => setShowShapePicker(p => !p)}
                            label="Formas"
                        />
                        {showShapePicker && (
                            <div className="absolute left-full ml-3 top-0 z-30 grid grid-cols-3 gap-1.5 rounded-xl border border-[hsl(var(--border))] bg-white/95 p-3 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]/95" style={{ minWidth: '220px' }}>
                                <ShapePickerItem icon={Square} label="Rect" shortcut="R" onClick={() => { addRect(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={Circle} label="Círculo" shortcut="C" onClick={() => { addCircle(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={Diamond} label="Decisión" shortcut="D" onClick={() => { addDiamondShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={Pill} label="Terminal" shortcut="S" onClick={() => { addPillShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={Hexagon} label="Datos" shortcut="I" onClick={() => { addDataShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={GitBranch} label="Subproc." onClick={() => { addSubprocessShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={Database} label="BD" onClick={() => { addDatabaseShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={FileText} label="Docum." onClick={() => { addDocumentShape(); setShowShapePicker(false); }} />
                                <ShapePickerItem icon={StickyNote} label="Nota" onClick={() => { addNoteShape(); setShowShapePicker(false); }} />
                            </div>
                        )}
                    </div>
                    <ToolbarButton icon={Type} active={false} onClick={addText} label="Texto (T)" data-testid="whiteboard-add-text" />
                    <div className="mx-2 my-1 h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                    <ToolbarButton
                        icon={AlignCenter}
                        active={snapEnabled}
                        onClick={() => { setSnapEnabled(p => !p); snapEnabledRef.current = !snapEnabledRef.current; }}
                        label={snapEnabled ? 'Snap activado' : 'Snap desactivado'}
                    />
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

                {/* ── Zoom controls (bottom-right) ── */}
                <div className="absolute right-[340px] bottom-6 z-20 flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] bg-white/90 p-1 shadow-lg backdrop-blur-xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]/90">
                    {/* Fit to screen */}
                    <button
                        className="rounded-md px-2 py-1 text-xs font-medium hover:bg-[hsl(var(--surface-1))] transition-colors"
                        title="Ajustar a pantalla"
                        onClick={() => {
                            const canvas = fabricCanvas.current;
                            if (!canvas) return;
                            const objects = canvas.getObjects().filter(o => o.data?.type !== 'connector');
                            if (objects.length === 0) {
                                canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
                                requestAnimationFrame(() => setZoomLevel(100));
                                return;
                            }
                            // Get bounding box of all objects
                            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                            objects.forEach(o => {
                                const br = o.getBoundingRect();
                                minX = Math.min(minX, br.left); minY = Math.min(minY, br.top);
                                maxX = Math.max(maxX, br.left + br.width); maxY = Math.max(maxY, br.top + br.height);
                            });
                            const pad = 60;
                            const scaleX = (canvas.width || 800) / (maxX - minX + pad * 2);
                            const scaleY = (canvas.height || 600) / (maxY - minY + pad * 2);
                            const scale = Math.min(scaleX, scaleY, 2);
                            const cx = ((canvas.width || 800) - (maxX - minX) * scale) / 2 - minX * scale + pad * scale;
                            const cy = ((canvas.height || 600) - (maxY - minY) * scale) / 2 - minY * scale + pad * scale;
                            canvas.setViewportTransform([scale, 0, 0, scale, cx, cy]);
                            requestAnimationFrame(() => setZoomLevel(Math.round(canvas.getZoom() * 100)));
                        }}
                    >⊡</button>
                    <div className="h-4 w-px bg-[hsl(var(--surface-2))]" />
                    <button
                        className="rounded-md px-2 py-1 text-xs font-medium hover:bg-[hsl(var(--surface-1))] transition-colors"
                        onClick={() => {
                            const canvas = fabricCanvas.current;
                            if (!canvas) return;
                            const zoom = Math.max(0.2, canvas.getZoom() - 0.15);
                            canvas.zoomToPoint(new fabric.Point((canvas.width || 0) / 2, (canvas.height || 0) / 2), zoom);
                            requestAnimationFrame(() => setZoomLevel(Math.round(canvas.getZoom() * 100)));
                        }}
                    >−</button>
                    <span
                        className="min-w-[50px] text-center text-xs font-mono cursor-pointer select-none"
                        onClick={() => {
                            const canvas = fabricCanvas.current;
                            if (!canvas) return;
                            canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
                            requestAnimationFrame(() => setZoomLevel(Math.round(canvas.getZoom() * 100)));
                        }}
                        title="Reset zoom (100%)"
                    >{zoomLevel}%</span>
                    <button
                        className="rounded-md px-2 py-1 text-xs font-medium hover:bg-[hsl(var(--surface-1))] transition-colors"
                        onClick={() => {
                            const canvas = fabricCanvas.current;
                            if (!canvas) return;
                            const zoom = Math.min(5, canvas.getZoom() + 0.15);
                            canvas.zoomToPoint(new fabric.Point((canvas.width || 0) / 2, (canvas.height || 0) / 2), zoom);
                            requestAnimationFrame(() => setZoomLevel(Math.round(canvas.getZoom() * 100)));
                        }}
                    >+</button>
                </div>

                {/* ── Inline connector label editor ── */}
                {connectorLabelState && (
                    <div
                        className="absolute z-50 pointer-events-none"
                        style={{ left: connectorLabelState.x + 80, top: connectorLabelState.y + 96 }}
                    >
                        <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-[hsl(var(--border))] bg-white/95 p-1.5 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]/95">
                            <input
                                autoFocus
                                type="text"
                                value={connectorLabelState.value}
                                onChange={e => setConnectorLabelState(s => s ? { ...s, value: e.target.value } : null)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') {
                                        if (connectorLabelState.obj.data) {
                                            connectorLabelState.obj.data.label = connectorLabelState.value;
                                            fabricCanvas.current?.requestRenderAll();
                                        }
                                        setConnectorLabelState(null);
                                    } else if (e.key === 'Escape') {
                                        setConnectorLabelState(null);
                                    }
                                    e.stopPropagation();
                                }}
                                onBlur={() => {
                                    if (connectorLabelState.obj.data) {
                                        connectorLabelState.obj.data.label = connectorLabelState.value;
                                        fabricCanvas.current?.requestRenderAll();
                                    }
                                    setConnectorLabelState(null);
                                }}
                                className="h-7 w-40 rounded-lg border border-[hsl(var(--border))] bg-transparent px-2 text-xs font-medium text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] dark:border-white/10 dark:text-white"
                                placeholder="Etiqueta del conector…"
                            />
                            <span className="text-2xs text-[hsl(var(--text-secondary))]">↵</span>
                        </div>
                    </div>
                )}

                {/* ── Canvas area ── */}
                <main
                    className="flex-1 overflow-auto p-4 pl-24"
                    onClick={() => setShowShapePicker(false)}
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

function ShapePickerItem({ icon: Icon, label, shortcut, onClick }: { icon: React.ElementType; label: string; shortcut?: string; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className="flex flex-col items-center gap-1 rounded-lg p-2 text-xs transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/10"
            title={shortcut ? `${label} (${shortcut})` : label}
        >
            <Icon size={20} />
            <span className="text-[10px] opacity-70">{label}</span>
        </button>
    );
}

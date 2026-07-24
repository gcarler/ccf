"use client";

import { useCallback, useEffect, useRef, useState, RefObject, ElementType } from "react";
import { createPortal } from "react-dom";
import * as fabric from "fabric";
import {
  MousePointer2,
  Pencil,
  Square,
  Circle,
  Type,
  Trash2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RotateCw,
  Cloud,
  Loader2,
  Sparkles,
  Download,
  Eraser,
  X,
  Layers,
  PencilRuler,
  History,
} from "lucide-react";
import clsx from "clsx";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import TextPromptDrawer from "@/components/ui/TextPromptDrawer";
import { useWhiteboardHistory } from "@/hooks/useWhiteboardHistory";
import { useWhiteboardCanvas } from "@/hooks/useWhiteboardCanvas";
import { useWhiteboardSave } from "@/hooks/useWhiteboardSave";
import { WHITEBOARD_COLORS } from "@/lib/whiteboards";
import { exportToPng, exportToSvg } from "@/lib/whiteboardExport";

interface Props {
  project_id: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function ProjectWhiteboard({
  project_id,
  isOpen,
  onClose,
}: Props) {
  const { token, loading: authLoading } = useAuth();
  const loadedFor = useRef<string | null>(null);

  // Shared hooks
  const history = useWhiteboardHistory({ maxStates: 50 });
  const {
    canvasRef,
    fabricCanvas,
    isReady,
    addRect,
    addCircle,
    addText,
    removeSelected,
    setZoom,
    zoom,
  } = useWhiteboardCanvas({
    backgroundColor: WHITEBOARD_COLORS.canvasLight,
  });
  const { saveStatus, save, saveNow } = useWhiteboardSave({
    projectId: project_id,
    token,
    title: "Pizarra Estrategica",
  });

  // Local state
  const [isMounted, setIsMounted] = useState(false);
  const [tool, setTool] = useState<
    "select" | "pencil" | "rect" | "circle" | "text"
  >("select");
  const [isAiDrawing, setIsAiDrawing] = useState(false);
  const [diagramPromptOpen, setDiagramPromptOpen] = useState(false);
  const [diagramPromptDraft, setDiagramPromptDraft] = useState("");
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showLayers, setShowLayers] = useState(false);
  const [layers, setLayers] = useState<{ index: number; type: string; label: string }[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Sync layers from canvas
  const syncLayers = useCallback(() => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;
    const next = canvas.getObjects().map((object, index) => ({
      index,
      type: object.type || "object",
      label: getObjectLabel(object, index),
    })).reverse();
    setLayers(next);
  }, [fabricCanvas]);

  const setActiveTool = useCallback((t: typeof tool) => {
    const fc = fabricCanvas.current;
    if (!fc) return;
    setTool(t);
    if (t === "pencil") {
      fc.isDrawingMode = true;
      const brush = new fabric.PencilBrush(fc);
      brush.width = 3;
      brush.color = WHITEBOARD_COLORS.primary;
      fc.freeDrawingBrush = brush;
    } else {
      fc.isDrawingMode = false;
    }
  }, [fabricCanvas]);

  // Wire up history with canvas events
  useEffect(() => {
    if (!isReady || !fabricCanvas.current) return;

    const canvas = fabricCanvas.current;

    const handleObjectChange = () => {
      history.pushHistory(canvas);
      if (!history.restoringRef.current) {
        save(canvas);
      }
      syncLayers();
    };

    canvas.on("object:modified", handleObjectChange);
    canvas.on("object:added", handleObjectChange);
    canvas.on("object:removed", handleObjectChange);

    return () => {
      canvas.off("object:modified", handleObjectChange);
      canvas.off("object:added", handleObjectChange);
      canvas.off("object:removed", handleObjectChange);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fabricCanvas, history, isReady, save, syncLayers]);

  // Load whiteboard data when opening
  useEffect(() => {
    if (!isOpen || !fabricCanvas.current) return;
    if (loadedFor.current === project_id) return;
    if (authLoading) return;
    if (!token) {
      setLoadError('Debes iniciar sesión para abrir la pizarra del proyecto.');
      return;
    }

    const canvas = fabricCanvas.current;
    setLoadError(null);
    apiFetch<{ elements_json: string }>(
      `/projects/${project_id}/whiteboard`,
      { token }
    )
      .then(async (data) => {
        if (data?.elements_json && data.elements_json !== "[]") {
          try {
            history.restoringRef.current = true;
            await canvas.loadFromJSON(JSON.parse(data.elements_json));
            canvas.renderAll();
          } catch {
            setLoadError('No se pudo cargar la pizarra guardada.');
            toast.error("No se pudo cargar la pizarra guardada.");
          } finally {
            history.restoringRef.current = false;
          }
        }
        loadedFor.current = project_id;
        syncLayers();
        history.clearHistory();
        history.pushHistory(canvas);
      })
      .catch(() => {
        setLoadError('No se pudo cargar la pizarra del proyecto.');
        loadedFor.current = project_id;
        syncLayers();
        history.clearHistory();
        history.pushHistory(canvas);
      });
  }, [authLoading, fabricCanvas, history, isOpen, project_id, syncLayers, token]);

  // Resize on open
  useEffect(() => {
    if (!isOpen || !fabricCanvas.current) return;
    const canvas = fabricCanvas.current;
    const frame = window.requestAnimationFrame(() => {
      const container = canvasRef.current?.parentElement;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      canvas.setDimensions({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(320, Math.floor(rect.height)),
      });
      canvas.renderAll();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [canvasRef, fabricCanvas, isOpen]);

  // Esc to close + keyboard shortcuts
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (
        (e.key === "Delete" || e.key === "Backspace") &&
        document.activeElement?.tagName !== "INPUT"
      ) {
        removeSelected();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        if (fabricCanvas.current) history.undo(fabricCanvas.current);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        if (fabricCanvas.current) history.redo(fabricCanvas.current);
      }
      if (e.key === "v" || e.key === "V") setActiveTool("select");
      if (e.key === "p" || e.key === "P") setActiveTool("pencil");
      if (e.key === "r" || e.key === "R") addRect();
      if (e.key === "c" || e.key === "C") addCircle();
      if (e.key === "t" || e.key === "T") addText();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [
    isOpen,
    addCircle,
    addRect,
    addText,
    fabricCanvas,
    onClose,
    removeSelected,
    history,
    setActiveTool,
  ]);

  const deleteSelected = () => {
    removeSelected();
  };

  const handleUndo = () => {
    if (fabricCanvas.current) history.undo(fabricCanvas.current);
  };

  const handleRedo = () => {
    if (fabricCanvas.current) history.redo(fabricCanvas.current);
  };

  const handleExportPng = () => {
    const fc = fabricCanvas.current;
    if (!fc) return;
    exportToPng(fc, `pizarra-${project_id.slice(0, 8)}`);
  };

  const handleExportSvg = () => {
    const fc = fabricCanvas.current;
    if (!fc) return;
    exportToSvg(fc, `pizarra-${project_id.slice(0, 8)}`);
  };

  const focusLayer = (index: number) => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;
    const object = canvas.getObjects()[index];
    if (!object) return;
    canvas.setActiveObject(object);
    canvas.renderAll();
  };

  const clearCanvas = () => {
    if (!confirm("¿Limpiar toda la pizarra? Esta acción no se puede deshacer."))
      return;
    const fc = fabricCanvas.current;
    if (!fc) return;
    history.restoringRef.current = true;
    fc.clear();
    fc.backgroundColor = WHITEBOARD_COLORS.canvasLight;
    fc.renderAll();
    history.clearHistory();
    history.restoringRef.current = false;
    // Save empty state
    saveNow(fc);
  };

  const handleAiDiagram = async () => {
    setDiagramPromptDraft("");
    setDiagramPromptOpen(true);
  };

  const submitAiDiagram = async () => {
    const prompt = diagramPromptDraft.trim();
    if (!prompt) return;
    setIsAiDrawing(true);
    try {
      await apiFetch("/system/ai/generate", {
        method: "POST",
        token,
        body: {
          prompt: `Genera un diagrama de pizarra para: ${prompt}`,
          context: "Estética ministerial",
        },
      });
      toast.success("IA: Esqueleto del diagrama generado.");
    } catch {
      toast.error("Error en la IA de diagramación.");
    } finally {
      setIsAiDrawing(false);
      setDiagramPromptOpen(false);
    }
  };

  if (!isMounted) return null;

  const whiteboard = (
    <div
      className={clsx(
        "fixed inset-0 z-[9999] flex flex-col bg-[hsl(var(--bg-secondary))] dark:bg-[hsl(var(--bg-primary))] transition-opacity duration-200",
        isOpen
          ? "opacity-100 pointer-events-auto"
          : "opacity-0 pointer-events-none"
      )}
      role="application"
      aria-label="Pizarra del proyecto"
      aria-hidden={!isOpen}
    >
      <TextPromptDrawer
        isOpen={diagramPromptOpen}
        onClose={() => setDiagramPromptOpen(false)}
        onSubmit={submitAiDiagram}
        title="Generar diagrama con IA"
        subtitle="Describe el proceso ministerial"
        label="¿Qué proceso deseas diagramar?"
        value={diagramPromptDraft}
        onChange={setDiagramPromptDraft}
        placeholder="Ej. seguimiento de nuevos creyentes"
        submitLabel={isAiDrawing ? "Generando…" : "Generar"}
      />
      {loadError && (
        <div className="mx-4 mt-3 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
          <p className="text-[11px] font-bold uppercase tracking-wide">{loadError}</p>
        </div>
      )}
      {/* Top Bar */}
      <header className="h-11 px-4 shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] shadow-sm">
        <div className="flex items-center gap-3">
          <div className="size-7 rounded-md bg-orange-500 flex items-center justify-center text-white">
            <PencilRuler size={14} />
          </div>
          <span className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wide">
            Pizarra del Proyecto
          </span>
          <div className="flex items-center gap-1.5 ml-2">
            {saveStatus === "saving" ? (
              <>
                <Loader2
                  size={10}
                  className="animate-spin text-[hsl(var(--primary))]"
                />
                <span className="text-[9px] font-semibold uppercase text-[hsl(var(--primary))]">
                  Guardando...
                </span>
              </>
            ) : saveStatus === "error" ? (
              <>
                <Cloud size={10} className="text-[hsl(var(--danger))]" />
                <span className="text-[9px] font-semibold uppercase text-[hsl(var(--danger))]">
                  Error
                </span>
              </>
            ) : (
              <>
                <Cloud size={10} className="text-[hsl(var(--success))]" />
                <span className="text-[9px] font-semibold uppercase text-[hsl(var(--success))]">
                  Guardado
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleAiDiagram}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity shadow-md"
          >
            {isAiDrawing ? (
              <Loader2 size={11} className="animate-spin" />
            ) : (
              <Sparkles size={11} />
            )}
            Diagramar con IA
          </button>
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] transition-colors border border-[hsl(var(--border))] dark:border-white/10"
            >
              <Download size={11} /> Exportar
            </button>
            {showExportMenu && (
              <div className="absolute right-0 top-full mt-1 z-50 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-1 shadow-lg dark:border-white/10 dark:bg-[hsl(var(--bg-muted))]">
                <button
                  onClick={() => { handleExportPng(); setShowExportMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                >
                  <Download size={12} /> PNG
                </button>
                <button
                  onClick={() => { handleExportSvg(); setShowExportMenu(false); }}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[11px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                >
                  <Download size={12} /> SVG
                </button>
              </div>
            )}
          </div>
          <button
            onClick={clearCanvas}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-danger-soft text-danger-text rounded-md text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--danger-muted))] transition-colors border border-[hsl(var(--danger)/25%)] dark:border-[hsl(var(--danger)/100%)]/20"
          >
            <Eraser size={11} /> Limpiar
          </button>
          <div className="w-px h-5 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
          <button
            onClick={onClose}
            className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-all"
            title="Cerrar (Esc)"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      {/* Drawing Area */}
      <div className="flex-1 relative overflow-hidden bg-[hsl(var(--bg-secondary))] dark:bg-[hsl(var(--bg-primary))]">
        {/* Vertical toolbar */}
        <div className="absolute left-3 top-1/2 -translate-y-1/2 z-50 flex flex-col gap-1 p-1.5 bg-white/95 dark:bg-[hsl(var(--admin-bg-secondary))]/95 backdrop-blur-xl border border-[hsl(var(--border))] dark:border-white/10 rounded-xl shadow-2xl">
          <ToolBtn
            active={tool === "select"}
            onClick={() => setActiveTool("select")}
            icon={MousePointer2}
            label="Seleccionar (V)"
          />
          <ToolBtn
            active={tool === "pencil"}
            onClick={() => setActiveTool("pencil")}
            icon={Pencil}
            label="Dibujar libre (P)"
          />
          <div className="h-px w-7 bg-[hsl(var(--surface-2))] dark:bg-white/10 mx-auto my-0.5" />
          <ToolBtn
            active={tool === "rect"}
            onClick={() => {
              setTool("rect");
              addRect();
            }}
            icon={Square}
            label="Rectángulo (R)"
          />
          <ToolBtn
            active={tool === "circle"}
            onClick={() => {
              setTool("circle");
              addCircle();
            }}
            icon={Circle}
            label="Círculo (C)"
          />
          <ToolBtn
            active={tool === "text"}
            onClick={() => {
              setTool("text");
              addText();
            }}
            icon={Type}
            label="Texto (T)"
          />
          <div className="h-px w-7 bg-[hsl(var(--surface-2))] dark:bg-white/10 mx-auto my-0.5" />
          <ToolBtn
            active={false}
            onClick={deleteSelected}
            icon={Trash2}
            label="Eliminar (Del)"
            color="text-[hsl(var(--danger))]"
          />
          <div className="h-px w-7 bg-[hsl(var(--surface-2))] dark:bg-white/10 mx-auto my-0.5" />
          <ToolBtn
            active={false}
            onClick={handleUndo}
            icon={RotateCcw}
            label="Deshacer (Ctrl+Z)"
            color="text-[hsl(var(--text-secondary))]"
            disabled={!history.canUndo}
          />
          <ToolBtn
            active={false}
            onClick={handleRedo}
            icon={RotateCw}
            label="Rehacer (Ctrl+Y)"
            color="text-[hsl(var(--text-secondary))]"
            disabled={!history.canRedo}
          />
        </div>

        {/* Canvas */}
        <canvas ref={canvasRef as RefObject<HTMLCanvasElement>} className="whiteboard-canvas" />

        {/* Zoom controls */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-white/90 dark:bg-[hsl(var(--admin-bg-secondary))]/90 backdrop-blur-xl px-3 py-2 rounded-full border border-[hsl(var(--border))] dark:border-white/10 shadow-lg">
          <button
            onClick={() => setZoom(zoom - 25)}
            className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-[11px] font-bold w-10 text-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] tabular-nums">
            {zoom}%
          </span>
          <button
            onClick={() => setZoom(zoom + 25)}
            className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
          >
            <ZoomIn size={16} />
          </button>
          <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />
          <button
            onClick={() => setShowLayers(!showLayers)}
            className={clsx(
              "transition-colors",
              showLayers
                ? "text-[hsl(var(--primary))]"
                : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]"
            )}
            title="Capas"
          >
            <Layers size={16} />
          </button>
        </div>

        {/* Layers panel */}
        {showLayers && (
          <div className="absolute bottom-4 left-4 z-50 w-64 max-h-80 overflow-y-auto bg-white/95 dark:bg-[hsl(var(--admin-bg-secondary))]/95 backdrop-blur-xl border border-[hsl(var(--border))] dark:border-white/10 rounded-xl shadow-2xl p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Capas
              </h3>
              <button
                onClick={() => setShowLayers(false)}
                className="p-1 rounded hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
              >
                <X size={12} className="text-[hsl(var(--text-secondary))]" />
              </button>
            </div>
            <div className="space-y-1">
              {layers.map((layer) => (
                <button
                  key={`${layer.type}-${layer.index}`}
                  onClick={() => focusLayer(layer.index)}
                  className="flex w-full items-center justify-between rounded-lg border border-[hsl(var(--border))] p-2 text-left text-[11px] font-medium text-[hsl(var(--text-secondary))] transition-all hover:border-[hsl(var(--info)/25%)] hover:bg-info-soft/40 dark:border-white/5 dark:hover:bg-[hsl(var(--info))]/10"
                >
                  <span className="flex items-center gap-2">
                    <History size={12} /> {layer.label}
                  </span>
                  <span className="text-[8px] font-bold opacity-40">#{layer.index + 1}</span>
                </button>
              ))}
              {layers.length === 0 && (
                <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-[11px] font-semibold text-[hsl(var(--text-secondary))] dark:border-white/10">
                  No hay objetos en el lienzo.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(whiteboard, document.body);
}

function ToolBtn({
  active,
  onClick,
  icon: Icon,
  label,
  color = "text-[hsl(var(--text-secondary))]",
  disabled,
}: {
  active: boolean;
  onClick: () => void;
  icon: ElementType;
  label: string;
  color?: string;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      disabled={disabled}
      className={clsx(
        "p-2 rounded-lg transition-all relative group",
        active
          ? "bg-[hsl(var(--primary))] text-white shadow-md"
          : `hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 ${color}`,
        disabled && "opacity-30 cursor-not-allowed"
      )}
    >
      <Icon size={18} />
      <span className="absolute left-[calc(100%+8px)] top-1/2 -translate-y-1/2 px-2 py-1 bg-[hsl(var(--surface-2))] text-white text-[9px] font-semibold rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[100]">
        {label}
      </span>
    </button>
  );
}

function getObjectLabel(object: fabric.FabricObject, index: number): string {
  if (object.type === "i-text" || object.type === "textbox") {
    const text = "text" in object ? String(object.text || "").trim() : "";
    return text || `Texto ${index + 1}`;
  }
  if (object.type === "rect") return `Rectángulo ${index + 1}`;
  if (object.type === "circle") return `Círculo ${index + 1}`;
  if (object.type === "path") return `Trazo ${index + 1}`;
  return `Objeto ${index + 1}`;
}

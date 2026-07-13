"use client";

import React, { useEffect, useRef, useState } from "react";
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
  const { token } = useAuth();
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

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Wire up history with canvas events
  useEffect(() => {
    if (!isReady || !fabricCanvas.current) return;

    const canvas = fabricCanvas.current;

    const handleObjectChange = () => {
      history.pushHistory(canvas);
      save(canvas);
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
  }, [isReady]);

  // Load whiteboard data when opening
  useEffect(() => {
    if (!isOpen || !fabricCanvas.current) return;
    if (loadedFor.current === project_id) return;

    const canvas = fabricCanvas.current;
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
            toast.error("No se pudo cargar la pizarra guardada.");
          } finally {
            history.restoringRef.current = false;
          }
        }
        loadedFor.current = project_id;
      })
      .catch(() => {
        loadedFor.current = project_id;
      });
  }, [isOpen, project_id, token, history.restoringRef]);

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
  }, [isOpen, canvasRef]);

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
    onClose,
    removeSelected,
    history,
    addRect,
    addCircle,
    addText,
  ]);

  // Tools
  const setActiveTool = (t: typeof tool) => {
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
  };

  const deleteSelected = () => {
    removeSelected();
  };

  const handleUndo = () => {
    if (fabricCanvas.current) history.undo(fabricCanvas.current);
  };

  const handleRedo = () => {
    if (fabricCanvas.current) history.redo(fabricCanvas.current);
  };

  const exportPng = () => {
    const fc = fabricCanvas.current;
    if (!fc) return;
    const dataUrl = fc.toDataURL({ format: "png", multiplier: 2 });
    const link = document.createElement("a");
    link.download = `pizarra-${project_id.slice(0, 8)}.png`;
    link.href = dataUrl;
    link.click();
    toast.success("Pizarra exportada como PNG");
  };

  const clearCanvas = () => {
    if (!confirm("¿Limpiar toda la pizarra? Esta acción no se puede deshacer."))
      return;
    const fc = fabricCanvas.current;
    if (!fc) return;
    fc.clear();
    fc.backgroundColor = WHITEBOARD_COLORS.canvasLight;
    fc.renderAll();
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
            ) : (
              <>
                <Cloud size={10} className="text-emerald-500" />
                <span className="text-[9px] font-semibold uppercase text-emerald-500">
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
          <button
            onClick={exportPng}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] transition-colors border border-[hsl(var(--border))] dark:border-white/10"
          >
            <Download size={11} /> Exportar
          </button>
          <button
            onClick={clearCanvas}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-600 rounded-md text-[10px] font-bold uppercase tracking-wide hover:bg-rose-100 transition-colors border border-rose-200 dark:border-rose-500/20"
          >
            <Eraser size={11} /> Limpiar
          </button>
          <div className="w-px h-5 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
          <button
            onClick={onClose}
            className="p-1.5 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all"
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
            onClick={() => addRect()}
            icon={Square}
            label="Rectángulo (R)"
          />
          <ToolBtn
            active={tool === "circle"}
            onClick={() => addCircle()}
            icon={Circle}
            label="Círculo (C)"
          />
          <ToolBtn
            active={tool === "text"}
            onClick={() => addText()}
            icon={Type}
            label="Texto (T)"
          />
          <div className="h-px w-7 bg-[hsl(var(--surface-2))] dark:bg-white/10 mx-auto my-0.5" />
          <ToolBtn
            active={false}
            onClick={deleteSelected}
            icon={Trash2}
            label="Eliminar (Del)"
            color="text-rose-500"
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
        <canvas ref={canvasRef} />

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
            className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
            title="Capas"
          >
            <Layers size={16} />
          </button>
        </div>
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
  icon: React.ElementType;
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

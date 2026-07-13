"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import * as fabric from "fabric";

interface UseWhiteboardCanvasOptions {
  backgroundColor?: string;
  onObjectModified?: (canvas: fabric.Canvas) => void;
  onObjectAdded?: (canvas: fabric.Canvas) => void;
  onObjectRemoved?: (canvas: fabric.Canvas) => void;
}

interface UseWhiteboardCanvasReturn {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  fabricCanvas: React.MutableRefObject<fabric.Canvas | null>;
  isReady: boolean;
  addRect: (x?: number, y?: number, options?: Partial<fabric.RectProps>) => void;
  addCircle: (x?: number, y?: number, options?: Partial<fabric.CircleProps>) => void;
  addText: (x?: number, y?: number, options?: Partial<fabric.ITextProps>) => void;
  removeSelected: () => void;
  clearCanvas: () => void;
  duplicateSelected: () => void;
  bringForward: () => void;
  sendBackward: () => void;
  setZoom: (zoom: number) => void;
  zoom: number;
}

export function useWhiteboardCanvas(
  options: UseWhiteboardCanvasOptions = {}
): UseWhiteboardCanvasReturn {
  const {
    backgroundColor = "#ffffff",
    onObjectModified,
    onObjectAdded,
    onObjectRemoved,
  } = options;

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fabricCanvas = useRef<fabric.Canvas | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [zoom, setZoomState] = useState(100);

  // Initialize canvas
  useEffect(() => {
    if (!canvasRef.current || typeof window === "undefined") return;

    const canvas = new fabric.Canvas(canvasRef.current, {
      backgroundColor,
      preserveObjectStacking: true,
      selection: true,
      selectionColor: "rgba(37, 99, 235, 0.1)",
      selectionBorderColor: "#2563eb",
      selectionLineWidth: 1,
    });

    fabricCanvas.current = canvas;
    setIsReady(true);

    const resizeCanvas = () => {
      const container = canvasRef.current?.parentElement;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      canvas.setDimensions({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(320, Math.floor(rect.height)),
      });
      canvas.renderAll();
    };

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Wire up callbacks
    if (onObjectModified) {
      canvas.on("object:modified", () => onObjectModified(canvas));
    }
    if (onObjectAdded) {
      canvas.on("object:added", () => onObjectAdded(canvas));
    }
    if (onObjectRemoved) {
      canvas.on("object:removed", () => onObjectRemoved(canvas));
    }

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      canvas.dispose();
      fabricCanvas.current = null;
      setIsReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addRect = useCallback(
    (x = 120, y = 120, options?: Partial<fabric.RectProps>) => {
      const canvas = fabricCanvas.current;
      if (!canvas) return;

      const rect = new fabric.Rect({
        left: x,
        top: y,
        width: 160,
        height: 100,
        fill: "rgba(37, 99, 235, 0.08)",
        stroke: "#2563eb",
        strokeWidth: 2,
        rx: 10,
        ry: 10,
        ...options,
      });

      canvas.add(rect);
      canvas.setActiveObject(rect);
      canvas.renderAll();
    },
    []
  );

  const addCircle = useCallback(
    (x = 140, y = 140, options?: Partial<fabric.CircleProps>) => {
      const canvas = fabricCanvas.current;
      if (!canvas) return;

      const circle = new fabric.Circle({
        left: x,
        top: y,
        radius: 50,
        fill: "rgba(16, 185, 129, 0.1)",
        stroke: "#10b981",
        strokeWidth: 2,
        ...options,
      });

      canvas.add(circle);
      canvas.setActiveObject(circle);
      canvas.renderAll();
    },
    []
  );

  const addText = useCallback(
    (x = 160, y = 160, options?: Partial<fabric.ITextProps>) => {
      const canvas = fabricCanvas.current;
      if (!canvas) return;

      const text = new fabric.IText("Escribe aquí", {
        left: x,
        top: y,
        fontSize: 20,
        fill: "#0f172a",
        fontFamily: "Manrope",
        ...options,
      });

      canvas.add(text);
      canvas.setActiveObject(text);
      text.enterEditing();
      text.selectAll();
      canvas.renderAll();
    },
    []
  );

  const removeSelected = useCallback(() => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;

    const active = canvas.getActiveObjects();
    if (active.length === 0) return;

    canvas.remove(...active);
    canvas.discardActiveObject();
    canvas.renderAll();
  }, []);

  const clearCanvas = useCallback(() => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;

    canvas.getObjects().forEach((obj) => canvas.remove(obj));
    canvas.renderAll();
  }, []);

  const duplicateSelected = useCallback(() => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;

    const active = canvas.getActiveObject();
    if (!active) return;

    active.clone().then((cloned: fabric.FabricObject) => {
      cloned.set({
        left: (cloned.left ?? 0) + 40,
        top: (cloned.top ?? 0) + 40,
      });
      canvas.add(cloned);
      canvas.setActiveObject(cloned);
      canvas.renderAll();
    });
  }, []);

  const bringForward = useCallback(() => {
    const canvas = fabricCanvas.current;
    const active = canvas?.getActiveObject();
    if (!active) return;

    canvas?.bringObjectForward(active);
    canvas?.renderAll();
  }, []);

  const sendBackward = useCallback(() => {
    const canvas = fabricCanvas.current;
    const active = canvas?.getActiveObject();
    if (!active) return;

    canvas?.sendObjectBackwards(active);
    canvas?.renderAll();
  }, []);

  const setZoom = useCallback((newZoom: number) => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;

    const clamped = Math.min(400, Math.max(25, newZoom));
    canvas.setZoom(clamped / 100);
    setZoomState(clamped);
    canvas.renderAll();
  }, []);

  return {
    canvasRef,
    fabricCanvas,
    isReady,
    addRect,
    addCircle,
    addText,
    removeSelected,
    clearCanvas,
    duplicateSelected,
    bringForward,
    sendBackward,
    setZoom,
    zoom,
  };
}

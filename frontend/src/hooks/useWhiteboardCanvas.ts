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
  const backgroundColorRef = useRef(backgroundColor);
  const zoomRef = useRef(100);
  const callbacksRef = useRef({
    onObjectModified,
    onObjectAdded,
    onObjectRemoved,
  });
  const [isReady, setIsReady] = useState(false);
  const [zoom, setZoomState] = useState(100);

  useEffect(() => {
    backgroundColorRef.current = backgroundColor;
    callbacksRef.current = { onObjectModified, onObjectAdded, onObjectRemoved };
  }, [backgroundColor, onObjectAdded, onObjectModified, onObjectRemoved]);

  // Initialize canvas
  useEffect(() => {
    if (!canvasRef.current || typeof window === "undefined") return;

    const canvas = new fabric.Canvas(canvasRef.current, {
      backgroundColor: backgroundColorRef.current,
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
    const handleObjectModified = () => callbacksRef.current.onObjectModified?.(canvas);
    const handleObjectAdded = () => callbacksRef.current.onObjectAdded?.(canvas);
    const handleObjectRemoved = () => callbacksRef.current.onObjectRemoved?.(canvas);

    canvas.on("object:modified", handleObjectModified);
    canvas.on("object:added", handleObjectAdded);
    canvas.on("object:removed", handleObjectRemoved);

    // Pinch-to-zoom support
    let lastDistance = 0;

    const getDistance = (touch1: Touch, touch2: Touch) => {
      const dx = touch1.clientX - touch2.clientX;
      const dy = touch1.clientY - touch2.clientY;
      return Math.sqrt(dx * dx + dy * dy);
    };

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        lastDistance = getDistance(e.touches[0], e.touches[1]);
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const distance = getDistance(e.touches[0], e.touches[1]);
        const delta = distance - lastDistance;

        // Adjust zoom based on pinch distance change
        const zoomDelta = delta * 0.1;
        zoomRef.current = Math.min(400, Math.max(25, zoomRef.current + zoomDelta));
        canvas.setZoom(zoomRef.current / 100);
        canvas.renderAll();

        lastDistance = distance;
      }
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (e.touches.length < 2) {
        lastDistance = 0;
      }
    };

    const canvasElement = canvasRef.current;
    if (canvasElement) {
      canvasElement.addEventListener("touchstart", handleTouchStart, { passive: false });
      canvasElement.addEventListener("touchmove", handleTouchMove, { passive: false });
      canvasElement.addEventListener("touchend", handleTouchEnd);
    }

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      if (canvasElement) {
        canvasElement.removeEventListener("touchstart", handleTouchStart);
        canvasElement.removeEventListener("touchmove", handleTouchMove);
        canvasElement.removeEventListener("touchend", handleTouchEnd);
      }
      canvas.off("object:modified", handleObjectModified);
      canvas.off("object:added", handleObjectAdded);
      canvas.off("object:removed", handleObjectRemoved);
      canvas.dispose();
      fabricCanvas.current = null;
      setIsReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const canvas = fabricCanvas.current;
    if (!canvas) return;
    (canvas as fabric.Canvas & { backgroundColor?: string }).backgroundColor = backgroundColor;
    canvas.renderAll();
  }, [backgroundColor]);

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
    zoomRef.current = clamped;
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

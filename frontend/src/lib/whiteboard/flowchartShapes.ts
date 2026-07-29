/**
 * Flowchart shape factories — each function returns a fabric.Group
 * containing the visual shape + an editable IText label.
 *
 * All shapes carry `data.shapeId` so connectors can attach to them.
 */

import * as fabric from "fabric";
import { WHITEBOARD_COLORS } from "@/lib/whiteboards";
import { generateShapeId } from "./connectors";

// ═══════════════════════════════════════════════════════════════════════
// Internal helpers
// ═══════════════════════════════════════════════════════════════════════

function makeLabel(text: string, color: string, fontSize = 14): fabric.IText {
  return new fabric.IText(text, {
    fontSize,
    fontFamily: "Inter, sans-serif",
    fontWeight: "600",
    fill: color,
    textAlign: "center",
    originX: "center",
    originY: "center",
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Shape factories
// ═══════════════════════════════════════════════════════════════════════

interface ShapeOpts {
  left?: number;
  top?: number;
  label?: string;
}

/** Process — rounded rectangle. */
export function createProcess(opts: ShapeOpts = {}): fabric.Group {
  const rect = new fabric.Rect({
    width: 180,
    height: 80,
    rx: 14,
    ry: 14,
    fill: "rgba(37, 99, 235, 0.12)",
    stroke: WHITEBOARD_COLORS.primary,
    strokeWidth: 2,
    originX: "center",
    originY: "center",
  });
  const text = makeLabel(opts.label || "Proceso", "#1e3a5f");

  const group = new fabric.Group([rect, text], {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "process" };
  return group;
}

/** Decision — diamond (rotated square). */
export function createDiamond(opts: ShapeOpts = {}): fabric.Group {
  const s = 110;
  const h = s / 2;
  const diamond = new fabric.Polygon(
    [
      { x: h, y: 0 },
      { x: s, y: h },
      { x: h, y: s },
      { x: 0, y: h },
    ],
    {
      fill: "rgba(245, 158, 11, 0.14)",
      stroke: WHITEBOARD_COLORS.warning,
      strokeWidth: 2,
      originX: "center",
      originY: "center",
    },
  );
  const text = makeLabel(opts.label || "¿Decisión?", "#92400e", 13);

  const group = new fabric.Group([diamond, text], {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "diamond" };
  return group;
}

/** Terminal / Start‑End — pill shape (very rounded rect). */
export function createPill(opts: ShapeOpts = {}): fabric.Group {
  const rect = new fabric.Rect({
    width: 150,
    height: 52,
    rx: 26,
    ry: 26,
    fill: "rgba(139, 92, 246, 0.13)",
    stroke: WHITEBOARD_COLORS.lavender,
    strokeWidth: 2,
    originX: "center",
    originY: "center",
  });
  const text = makeLabel(opts.label || "Inicio", "#5b21b6");

  const group = new fabric.Group([rect, text], {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "pill" };
  return group;
}

/** Data / I‑O — parallelogram. */
export function createData(opts: ShapeOpts = {}): fabric.Group {
  const w = 170;
  const h = 68;
  const sk = 24;
  const pgram = new fabric.Polygon(
    [
      { x: sk, y: 0 },
      { x: w, y: 0 },
      { x: w - sk, y: h },
      { x: 0, y: h },
    ],
    {
      fill: "rgba(16, 185, 129, 0.12)",
      stroke: WHITEBOARD_COLORS.success,
      strokeWidth: 2,
      originX: "center",
      originY: "center",
    },
  );
  const text = makeLabel(opts.label || "Datos", "#065f46");

  const group = new fabric.Group([pgram, text], {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "data" };
  return group;
}

/** Circle node — for general‑purpose connections. */
export function createCircleNode(opts: ShapeOpts = {}): fabric.Group {
  const circle = new fabric.Circle({
    radius: 46,
    fill: "rgba(16, 185, 129, 0.14)",
    stroke: WHITEBOARD_COLORS.success,
    strokeWidth: 2,
    originX: "center",
    originY: "center",
  });
  const text = makeLabel(opts.label || "", "#065f46", 13);

  const group = new fabric.Group([circle, text], {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "circle" };
  return group;
}

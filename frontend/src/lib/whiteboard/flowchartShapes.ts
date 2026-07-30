/**
 * Flowchart shape factories v2 — comprehensive shape library.
 * Each factory returns a fabric.Group(shape + editable IText).
 */

import * as fabric from "fabric";
import { WHITEBOARD_COLORS } from "@/lib/whiteboards";
import { generateShapeId } from "./connectors";

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

interface ShapeOpts {
  left?: number;
  top?: number;
  label?: string;
}

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

function makeGroup(children: fabric.FabricObject[], opts: ShapeOpts, shapeType: string): fabric.Group {
  const group = new fabric.Group(children, {
    left: opts.left ?? 200,
    top: opts.top ?? 200,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType };
  return group;
}

// ═══════════════════════════════════════════════════════════════════════
// Core shapes
// ═══════════════════════════════════════════════════════════════════════

/** Process — rounded rectangle. */
export function createProcess(opts: ShapeOpts = {}): fabric.Group {
  const rect = new fabric.Rect({
    width: 180, height: 80, rx: 14, ry: 14,
    fill: "rgba(37, 99, 235, 0.12)",
    stroke: WHITEBOARD_COLORS.primary, strokeWidth: 2,
    originX: "center", originY: "center",
  });
  return makeGroup([rect, makeLabel(opts.label || "Proceso", "#1e3a5f")], opts, "process");
}

/** Decision — diamond. */
export function createDiamond(opts: ShapeOpts = {}): fabric.Group {
  const s = 110, h = s / 2;
  const diamond = new fabric.Polygon(
    [{ x: h, y: 0 }, { x: s, y: h }, { x: h, y: s }, { x: 0, y: h }],
    { fill: "rgba(245, 158, 11, 0.14)", stroke: WHITEBOARD_COLORS.warning, strokeWidth: 2, originX: "center", originY: "center" },
  );
  return makeGroup([diamond, makeLabel(opts.label || "¿Decisión?", "#92400e", 13)], opts, "diamond");
}

/** Terminal / Start-End — pill shape. */
export function createPill(opts: ShapeOpts = {}): fabric.Group {
  const rect = new fabric.Rect({
    width: 150, height: 52, rx: 26, ry: 26,
    fill: "rgba(139, 92, 246, 0.13)",
    stroke: WHITEBOARD_COLORS.lavender, strokeWidth: 2,
    originX: "center", originY: "center",
  });
  return makeGroup([rect, makeLabel(opts.label || "Inicio", "#5b21b6")], opts, "pill");
}

/** Data / I-O — parallelogram. */
export function createData(opts: ShapeOpts = {}): fabric.Group {
  const w = 170, h = 68, sk = 24;
  const pgram = new fabric.Polygon(
    [{ x: sk, y: 0 }, { x: w, y: 0 }, { x: w - sk, y: h }, { x: 0, y: h }],
    { fill: "rgba(16, 185, 129, 0.12)", stroke: WHITEBOARD_COLORS.success, strokeWidth: 2, originX: "center", originY: "center" },
  );
  return makeGroup([pgram, makeLabel(opts.label || "Datos", "#065f46")], opts, "data");
}

/** Circle node. */
export function createCircleNode(opts: ShapeOpts = {}): fabric.Group {
  const circle = new fabric.Circle({
    radius: 46,
    fill: "rgba(16, 185, 129, 0.14)",
    stroke: WHITEBOARD_COLORS.success, strokeWidth: 2,
    originX: "center", originY: "center",
  });
  return makeGroup([circle, makeLabel(opts.label || "", "#065f46", 13)], opts, "circle");
}

// ═══════════════════════════════════════════════════════════════════════
// Extended shapes
// ═══════════════════════════════════════════════════════════════════════

/** Subprocess — double-bordered rectangle (indicates a predefined process). */
export function createSubprocess(opts: ShapeOpts = {}): fabric.Group {
  const outer = new fabric.Rect({
    width: 180, height: 80, rx: 10, ry: 10,
    fill: "rgba(99, 102, 241, 0.10)",
    stroke: "#6366f1", strokeWidth: 2,
    originX: "center", originY: "center",
  });
  const inner = new fabric.Rect({
    width: 164, height: 64, rx: 6, ry: 6,
    fill: "transparent",
    stroke: "#6366f1", strokeWidth: 1.5,
    originX: "center", originY: "center",
  });
  return makeGroup([outer, inner, makeLabel(opts.label || "Subproceso", "#4338ca", 13)], opts, "subprocess");
}

/** Database — cylinder shape. */
export function createDatabase(opts: ShapeOpts = {}): fabric.Group {
  const w = 110, h = 80, e = 14;
  const bodyStr = `M 0 ${e} C 0 ${-e}, ${w} ${-e}, ${w} ${e} L ${w} ${h - e} C ${w} ${h + e}, 0 ${h + e}, 0 ${h - e} Z`;
  const topStr = `M 0 ${e} C 0 ${e * 2.5}, ${w} ${e * 2.5}, ${w} ${e}`;

  const body = new fabric.Path(bodyStr, {
    fill: "rgba(244, 63, 94, 0.10)",
    stroke: "#f43f5e", strokeWidth: 2,
    originX: "center", originY: "center",
  });
  const topArc = new fabric.Path(topStr, {
    fill: "transparent",
    stroke: "#f43f5e", strokeWidth: 1.5,
    originX: "center", originY: "center",
  });
  return makeGroup([body, topArc, makeLabel(opts.label || "Base de datos", "#9f1239", 11)], opts, "database");
}

/** Document — rectangle with wavy bottom edge. */
export function createDocument(opts: ShapeOpts = {}): fabric.Group {
  const w = 160, h = 80, wave = 10;
  const pathStr = `M 0 0 L ${w} 0 L ${w} ${h - wave} Q ${w * 0.75} ${h + wave}, ${w * 0.5} ${h - wave} Q ${w * 0.25} ${h - wave * 3}, 0 ${h - wave} Z`;
  const shape = new fabric.Path(pathStr, {
    fill: "rgba(14, 165, 233, 0.10)",
    stroke: "#0ea5e9", strokeWidth: 2,
    originX: "center", originY: "center",
  });
  return makeGroup([shape, makeLabel(opts.label || "Documento", "#0369a1", 13)], opts, "document");
}

/** Hexagon — preparation step. */
export function createHexagon(opts: ShapeOpts = {}): fabric.Group {
  const w = 160, h = 80, indent = 28;
  const hex = new fabric.Polygon(
    [
      { x: indent, y: 0 }, { x: w - indent, y: 0 },
      { x: w, y: h / 2 },
      { x: w - indent, y: h }, { x: indent, y: h },
      { x: 0, y: h / 2 },
    ],
    { fill: "rgba(236, 72, 153, 0.10)", stroke: "#ec4899", strokeWidth: 2, originX: "center", originY: "center" },
  );
  return makeGroup([hex, makeLabel(opts.label || "Preparación", "#9d174d", 13)], opts, "hexagon");
}

/** Note / Comment — rectangle with folded corner. */
export function createNote(opts: ShapeOpts = {}): fabric.Group {
  const w = 160, h = 100, fold = 20;
  const body = new fabric.Polygon(
    [
      { x: 0, y: 0 }, { x: w - fold, y: 0 },
      { x: w, y: fold }, { x: w, y: h },
      { x: 0, y: h },
    ],
    { fill: "rgba(251, 191, 36, 0.12)", stroke: "#f59e0b", strokeWidth: 2, originX: "center", originY: "center" },
  );
  const foldLine = new fabric.Polygon(
    [{ x: w - fold, y: 0 }, { x: w - fold, y: fold }, { x: w, y: fold }],
    { fill: "rgba(251, 191, 36, 0.25)", stroke: "#f59e0b", strokeWidth: 1, originX: "center", originY: "center" },
  );
  return makeGroup([body, foldLine, makeLabel(opts.label || "Nota", "#92400e", 12)], opts, "note");
}

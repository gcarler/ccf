/**
 * Whiteboard connector system v2 — bezier curves, arrowheads, labels, anchors.
 *
 * Connectors are stored as invisible fabric.Line objects (for hit detection)
 * while the visual bezier curves are rendered natively via after:render.
 */

import * as fabric from "fabric";

// Fabric.js v6 type augmentation — `data` exists at runtime but not in types
declare module "fabric" {
  interface FabricObject {
    data?: Record<string, unknown>;
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════

export type AnchorPosition = "top" | "right" | "bottom" | "left";

export interface ConnectorData {
  type: "connector";
  connectorId: string;
  fromShapeId: string;
  toShapeId: string;
  fromAnchor: AnchorPosition;
  toAnchor: AnchorPosition;
  label?: string;
  color?: string;
  lineWidth?: number;
  dash?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════
// ID generators
// ═══════════════════════════════════════════════════════════════════════

export function generateShapeId(): string {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

function generateConnectorId(): string {
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

// ═══════════════════════════════════════════════════════════════════════
// Anchor‑point geometry
// ═══════════════════════════════════════════════════════════════════════

export function getAnchorPoint(
  obj: fabric.FabricObject,
  anchor: AnchorPosition,
): { x: number; y: number } {
  const w = (obj.width || 0) * (obj.scaleX || 1);
  const h = (obj.height || 0) * (obj.scaleY || 1);
  const l = obj.left || 0;
  const t = obj.top || 0;
  switch (anchor) {
    case "top":    return { x: l + w / 2, y: t };
    case "bottom": return { x: l + w / 2, y: t + h };
    case "left":   return { x: l, y: t + h / 2 };
    case "right":  return { x: l + w, y: t + h / 2 };
  }
}

export function findNearestAnchor(
  obj: fabric.FabricObject,
  point: { x: number; y: number },
): { anchor: AnchorPosition; point: { x: number; y: number }; distance: number } {
  const anchors: AnchorPosition[] = ["top", "right", "bottom", "left"];
  let best: AnchorPosition = "top";
  let bestDist = Infinity;
  let bestPt = { x: 0, y: 0 };
  for (const a of anchors) {
    const p = getAnchorPoint(obj, a);
    const d = Math.hypot(p.x - point.x, p.y - point.y);
    if (d < bestDist) { bestDist = d; best = a; bestPt = p; }
  }
  return { anchor: best, point: bestPt, distance: bestDist };
}

// ═══════════════════════════════════════════════════════════════════════
// Shape lookup
// ═══════════════════════════════════════════════════════════════════════

export function findShapeById(canvas: fabric.Canvas, id: string): fabric.FabricObject | undefined {
  return canvas.getObjects().find((o) => o.data?.shapeId === id);
}

export function findShapeNearPoint(
  canvas: fabric.Canvas,
  point: { x: number; y: number },
  threshold = 28,
): { shape: fabric.FabricObject; anchor: AnchorPosition; anchorPoint: { x: number; y: number } } | null {
  type Hit = { shape: fabric.FabricObject; anchor: AnchorPosition; anchorPoint: { x: number; y: number }; dist: number };
  let best: Hit | null = null;
  for (const obj of canvas.getObjects()) {
    if (!obj.data?.shapeId || obj.data?.type === "connector") continue;
    const { anchor, point: ap, distance } = findNearestAnchor(obj, point);
    if (distance < threshold && (!best || distance < best.dist)) {
      best = { shape: obj, anchor, anchorPoint: ap, dist: distance };
    }
  }
  return best ? { shape: best.shape, anchor: best.anchor, anchorPoint: best.anchorPoint } : null;
}

// ═══════════════════════════════════════════════════════════════════════
// Bezier control‑point calculation
// ═══════════════════════════════════════════════════════════════════════

const ANCHOR_DIR: Record<AnchorPosition, { x: number; y: number }> = {
  top:    { x: 0, y: -1 },
  bottom: { x: 0, y:  1 },
  left:   { x: -1, y: 0 },
  right:  { x:  1, y: 0 },
};

export function calculateControlPoints(
  from: { x: number; y: number },
  to: { x: number; y: number },
  fromAnchor: AnchorPosition,
  toAnchor: AnchorPosition,
): { cp1: { x: number; y: number }; cp2: { x: number; y: number } } {
  const dx = Math.abs(to.x - from.x);
  const dy = Math.abs(to.y - from.y);
  const dist = Math.max(40, Math.min(180, Math.max(dx, dy) * 0.45));
  const d1 = ANCHOR_DIR[fromAnchor];
  const d2 = ANCHOR_DIR[toAnchor];
  return {
    cp1: { x: from.x + d1.x * dist, y: from.y + d1.y * dist },
    cp2: { x: to.x + d2.x * dist, y: to.y + d2.y * dist },
  };
}

// ═══════════════════════════════════════════════════════════════════════
// Connector CRUD
// ═══════════════════════════════════════════════════════════════════════

export function createConnectorLine(
  canvas: fabric.Canvas,
  fromShapeId: string,
  toShapeId: string,
  fromAnchor: AnchorPosition,
  toAnchor: AnchorPosition,
  opts: { color?: string; lineWidth?: number; label?: string; dash?: boolean } = {},
): fabric.Line | null {
  const fromObj = findShapeById(canvas, fromShapeId);
  const toObj = findShapeById(canvas, toShapeId);
  if (!fromObj || !toObj) return null;

  const from = getAnchorPoint(fromObj, fromAnchor);
  const to = getAnchorPoint(toObj, toAnchor);

  // Invisible Line for hit detection; visual is drawn in after:render
  const line = new fabric.Line([from.x, from.y, to.x, to.y], {
    stroke: "rgba(0,0,0,0.005)",
    strokeWidth: 14,
    fill: "transparent",
    selectable: true,
    evented: true,
    hasBorders: true,
    hasControls: false,
    lockMovementX: true,
    lockMovementY: true,
    perPixelTargetFind: false,
    padding: 6,
    hoverCursor: "pointer",
  });

  line.data = {
    type: "connector",
    connectorId: generateConnectorId(),
    fromShapeId,
    toShapeId,
    fromAnchor,
    toAnchor,
    label: opts.label || "",
    color: opts.color || "#2563eb",
    lineWidth: opts.lineWidth || 2,
    dash: opts.dash || false,
  };

  return line;
}

export function updateConnectors(canvas: fabric.Canvas): void {
  for (const obj of canvas.getObjects()) {
    if (obj.data?.type !== "connector") continue;
    const d = obj.data as unknown as ConnectorData;
    const fromObj = findShapeById(canvas, d.fromShapeId);
    const toObj = findShapeById(canvas, d.toShapeId);
    if (!fromObj || !toObj) continue;
    const from = getAnchorPoint(fromObj, d.fromAnchor);
    const to = getAnchorPoint(toObj, d.toAnchor);
    const line = obj as fabric.Line;
    line.set({ x1: from.x, y1: from.y, x2: to.x, y2: to.y });
    line.setCoords();
  }
}

export function ensureShapeIds(canvas: fabric.Canvas): void {
  for (const obj of canvas.getObjects()) {
    if (obj.data?.type === "connector") continue;
    if (!obj.data) obj.data = {};
    if (!obj.data.shapeId) obj.data.shapeId = generateShapeId();
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Rendering (called from canvas after:render)
// ═══════════════════════════════════════════════════════════════════════

function toScreen(x: number, y: number, vpt: number[]): { x: number; y: number } {
  return { x: x * vpt[0] + y * vpt[2] + vpt[4], y: x * vpt[1] + y * vpt[3] + vpt[5] };
}

/** Draw bezier curves + arrowheads + labels for every connector. */
export function renderConnectors(
  canvas: fabric.Canvas,
  ctx: CanvasRenderingContext2D,
): void {
  const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
  const zoom = canvas.getZoom();

  for (const obj of canvas.getObjects()) {
    if (obj.data?.type !== "connector") continue;
    const line = obj as fabric.Line;
    const d = obj.data as unknown as ConnectorData;
    if (line.x1 == null || line.y1 == null || line.x2 == null || line.y2 == null) continue;

    const p1 = toScreen(line.x1, line.y1, vpt);
    const p2 = toScreen(line.x2, line.y2, vpt);

    // Control points for bezier
    const { cp1, cp2 } = calculateControlPoints(
      { x: line.x1, y: line.y1 },
      { x: line.x2, y: line.y2 },
      d.fromAnchor, d.toAnchor,
    );
    const scp1 = toScreen(cp1.x, cp1.y, vpt);
    const scp2 = toScreen(cp2.x, cp2.y, vpt);

    const color = d.color || "#2563eb";
    const lw = (d.lineWidth || 2) * zoom;
    const isSelected = canvas.getActiveObject() === obj;

    // ── Selection glow ──
    if (isSelected) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.bezierCurveTo(scp1.x, scp1.y, scp2.x, scp2.y, p2.x, p2.y);
      ctx.strokeStyle = "rgba(37, 99, 235, 0.25)";
      ctx.lineWidth = lw + 6;
      ctx.stroke();
      ctx.restore();
    }

    // ── Bezier curve ──
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.bezierCurveTo(scp1.x, scp1.y, scp2.x, scp2.y, p2.x, p2.y);
    ctx.strokeStyle = color;
    ctx.lineWidth = lw;
    ctx.lineCap = "round";
    if (d.dash) ctx.setLineDash([8 * zoom, 5 * zoom]);
    ctx.stroke();
    ctx.restore();

    // ── Arrowhead (angle from cp2 → end for bezier tangent) ──
    const arrowAngle = Math.atan2(p2.y - scp2.y, p2.x - scp2.x);
    const headLen = 13 * zoom;
    const spread = Math.PI / 7;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(p2.x, p2.y);
    ctx.lineTo(p2.x - headLen * Math.cos(arrowAngle - spread), p2.y - headLen * Math.sin(arrowAngle - spread));
    ctx.lineTo(p2.x - headLen * Math.cos(arrowAngle + spread), p2.y - headLen * Math.sin(arrowAngle + spread));
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();

    // ── Start dot ──
    ctx.save();
    ctx.beginPath();
    ctx.arc(p1.x, p1.y, 3.5 * zoom, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();

    // ── Label ──
    if (d.label) {
      // Calculate midpoint of bezier (t=0.5)
      const t = 0.5;
      const mx = (1-t)**3*p1.x + 3*(1-t)**2*t*scp1.x + 3*(1-t)*t**2*scp2.x + t**3*p2.x;
      const my = (1-t)**3*p1.y + 3*(1-t)**2*t*scp1.y + 3*(1-t)*t**2*scp2.y + t**3*p2.y;
      ctx.save();
      ctx.font = `600 ${Math.max(10, 11 * zoom)}px 'Inter', sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const tw = ctx.measureText(d.label).width;
      const pad = 6 * zoom;
      // pill bg
      ctx.fillStyle = "rgba(255,255,255,0.94)";
      ctx.beginPath();
      ctx.roundRect(mx - tw/2 - pad, my - 9*zoom, tw + pad*2, 18*zoom, 6*zoom);
      ctx.fill();
      ctx.strokeStyle = color + "30";
      ctx.lineWidth = 1;
      ctx.stroke();
      // text
      ctx.fillStyle = "#334155";
      ctx.fillText(d.label, mx, my);
      ctx.restore();
    }
  }
}

/** Draw anchor indicators on shapes when connector tool is active. */
export function renderAnchors(
  canvas: fabric.Canvas,
  ctx: CanvasRenderingContext2D,
  opts: { hoveredShapeId?: string | null; connectingFromId?: string | null } = {},
): void {
  const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
  const zoom = canvas.getZoom();
  const positions: AnchorPosition[] = ["top", "right", "bottom", "left"];

  for (const obj of canvas.getObjects()) {
    if (!obj.data?.shapeId || obj.data?.type === "connector") continue;
    const id = obj.data.shapeId as string;
    const show = id === opts.hoveredShapeId || id === opts.connectingFromId || canvas.getActiveObject() === obj;
    if (!show) continue;

    const isFrom = id === opts.connectingFromId;
    for (const anchor of positions) {
      const p = getAnchorPoint(obj, anchor);
      const sp = toScreen(p.x, p.y, vpt);
      const r = 8 * zoom;
      ctx.save();
      // glow
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, r + 2, 0, Math.PI * 2);
      ctx.fillStyle = isFrom ? "rgba(16,185,129,0.2)" : "rgba(37,99,235,0.15)";
      ctx.fill();
      // ring
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, r * 0.7, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
      ctx.strokeStyle = isFrom ? "#10b981" : "#2563eb";
      ctx.lineWidth = 2 * zoom;
      ctx.stroke();
      // dot
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, r * 0.3, 0, Math.PI * 2);
      ctx.fillStyle = isFrom ? "#10b981" : "#2563eb";
      ctx.fill();
      ctx.restore();
    }
  }
}
